@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral SharePoint relay recovery job name.')
@minLength(2)
@maxLength(32)
param jobName string

@description('Existing live Container Apps managed environment resource ID.')
@minLength(1)
param managedEnvironmentResourceId string

@description('Existing managed-environment storage name mounted by the live Gateway.')
@minLength(1)
param gatewayStateStorageName string

@description('Gateway runtime identity resource ID used for Core verification.')
@minLength(1)
param runtimeIdentityResourceId string

@description('Gateway runtime identity client ID used for Core token acquisition.')
@minLength(1)
param runtimeIdentityClientId string

@description('Dedicated pull-only identity used by the live Gateway.')
@minLength(1)
param registryPullIdentityResourceId string

@description('Approved private ACR login server.')
@minLength(1)
param registryServer string

@description('Exact image currently deployed to the Gateway.')
@minLength(1)
param containerImage string

@description('Private ETS Core base URL copied from deployed Gateway configuration.')
@minLength(1)
param coreBaseUrl string

@description('Fixed ETS Core application scope copied from deployed Gateway configuration.')
@minLength(1)
param coreScope string

@description('Server-authoritative ETS tenant ID copied from deployed Gateway configuration.')
@minLength(1)
param tenantId string

@description('Server-authoritative ETS workspace ID copied from deployed Gateway configuration.')
@minLength(1)
param workspaceId string

@description('Stable live connector instance identifier.')
@minLength(1)
param connectorInstanceId string

@description('Synthetic public-safe qualification marker.')
@minLength(6)
@maxLength(32)
param marker string

var recoveryScript = '''
import base64
import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from azure.identity import ManagedIdentityCredential

RESULT_MARKER = "ETS_SP_RELAY_RECOVERY_B64="
STATE_DIR = Path("/mnt/gateway-state")
MAX_TERMINAL = 20
MAX_RESPONSE_BYTES = 1024 * 1024
instance_id = os.environ["ETS_SP_INSTANCE_ID"]
marker = os.environ["ETS_SP_MARKER"]
file_name = "ets-live-qualification-" + marker + ".txt"
core_base_url = os.environ["ETS_CORE_BASE_URL"].strip().rstrip("/")
core_scope = os.environ["ETS_CORE_SCOPE"].strip()
tenant_id = os.environ["ETS_TENANT_ID"]
workspace_id = os.environ["ETS_WORKSPACE_ID"]
client_id = os.environ["ETS_RUNTIME_IDENTITY_CLIENT_ID"]


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("credential-bearing Core request redirected")


def utc_now():
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def connect(name, *, readonly=False):
    path = STATE_DIR / name
    if not path.is_file():
        raise RuntimeError("required Gateway state database is unavailable: " + name)
    if readonly:
        connection = sqlite3.connect(
            "file:" + str(path) + "?mode=ro",
            uri=True,
            timeout=10.0,
        )
        connection.execute("PRAGMA query_only = ON")
    else:
        connection = sqlite3.connect(path, timeout=10.0)
        connection.execute("PRAGMA synchronous=FULL")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def marker_event(event):
    if event.get("source_system") != "microsoft.sharepoint.onedrive_delta":
        return False
    metadata = event.get("metadata")
    capture = metadata.get("capture_metadata") if isinstance(metadata, dict) else None
    committed = capture.get("committed_connector_metadata") if isinstance(capture, dict) else None
    source_metadata = committed.get("metadata") if isinstance(committed, dict) else None
    return isinstance(source_metadata, dict) and source_metadata.get("name") == file_name


def read_json_response(response):
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError("Core response exceeded qualified byte bound")
    content_type = (response.headers.get("Content-Type") or "").partition(";")[0].strip().lower()
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise RuntimeError("Core response Content-Type is not JSON")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Core response JSON must be an object")
    return payload


def request_json(opener, token, path):
    request = Request(
        core_base_url + path,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
            "User-Agent": "ets-sharepoint-relay-recovery/1.0",
        },
    )
    with opener.open(request, timeout=15.0) as response:
        return read_json_response(response)


def validate_core_event(payload, event_id, event_hash):
    event = payload.get("event")
    log_index = payload.get("log_index")
    return (
        payload.get("event_hash") == event_hash
        and isinstance(event, dict)
        and event.get("event_id") == event_id
        and isinstance(log_index, int)
        and log_index >= 0
    )


with connect("gateway-events.db", readonly=True) as connection:
    local_rows = connection.execute(
        "SELECT event_id, event_json, event_hash FROM events"
    ).fetchall()
local = {str(row["event_id"]): row for row in local_rows}

with connect("gateway-sync.db", readonly=True) as connection:
    terminal_rows = connection.execute(
        """
        SELECT idempotency_key, event_id, event_hash, tenant_id, workspace_id
        FROM sync_queue
        WHERE state = 'terminal_failure'
        ORDER BY id ASC
        """
    ).fetchall()
    retryable_before = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'retryable_failure'"
    ).fetchone()[0])

if not terminal_rows:
    raise RuntimeError("no terminal relay rows are available for controlled recovery")
if len(terminal_rows) > MAX_TERMINAL:
    raise RuntimeError("terminal relay state exceeds controlled recovery bound")
if retryable_before != 0:
    raise RuntimeError("retryable relay failures must be resolved before terminal recovery")

with connect("connector-runtime.db", readonly=True) as connection:
    runtime_before = connection.execute(
        """
        SELECT checkpoint_json, checkpoint_revision, last_success_at_utc,
               observation_state, gap_open, lease_owner
        FROM connector_runtime WHERE instance_id = ?
        """,
        (instance_id,),
    ).fetchone()
if runtime_before is None:
    raise RuntimeError("live connector runtime row is unavailable")
if runtime_before["checkpoint_json"] is None:
    raise RuntimeError("connector has no persisted checkpoint for recovery")
if runtime_before["last_success_at_utc"] is None:
    raise RuntimeError("connector has no prior successful collection for recovery")
if runtime_before["lease_owner"] is not None:
    raise RuntimeError("connector lease is active; refusing concurrent recovery")
if not bool(runtime_before["gap_open"]):
    raise RuntimeError("connector collection gap is not open")
if str(runtime_before["observation_state"]) != "collection_gap":
    raise RuntimeError("connector observation state is not collection_gap")

counts = {
    "terminal_total_before": len(terminal_rows),
    "terminal_sharepoint_count": 0,
    "terminal_marker_count": 0,
    "terminal_local_invariants_ok": 0,
    "terminal_local_invariant_failure": 0,
    "core_present_match": 0,
    "core_present_mismatch": 0,
    "core_not_found": 0,
    "core_auth_failure": 0,
    "core_transport_error": 0,
    "queue_reconciled": 0,
    "marker_reconciled": 0,
}

qualified = []
for row in terminal_rows:
    event_id = str(row["event_id"])
    local_row = local.get(event_id)
    if local_row is None:
        counts["terminal_local_invariant_failure"] += 1
        continue
    try:
        event = json.loads(str(local_row["event_json"]))
    except json.JSONDecodeError:
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("source_system") == "microsoft.sharepoint.onedrive_delta":
        counts["terminal_sharepoint_count"] += 1
    is_marker = marker_event(event)
    if is_marker:
        counts["terminal_marker_count"] += 1
    if str(local_row["event_hash"]) != str(row["event_hash"]):
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("tenant_id") != str(row["tenant_id"]):
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("workspace_id") != str(row["workspace_id"]):
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("tenant_id") != tenant_id or event.get("workspace_id") != workspace_id:
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("source_system") != "microsoft.sharepoint.onedrive_delta":
        counts["terminal_local_invariant_failure"] += 1
        continue
    counts["terminal_local_invariants_ok"] += 1
    qualified.append(
        {
            "idempotency_key": str(row["idempotency_key"]),
            "event_id": event_id,
            "event_hash": str(row["event_hash"]),
            "is_marker": is_marker,
        }
    )

if counts["terminal_local_invariant_failure"] != 0:
    raise RuntimeError("terminal relay local invariants failed; recovery refused")
if counts["terminal_sharepoint_count"] != counts["terminal_total_before"]:
    raise RuntimeError("terminal recovery set contains non-SharePoint events")

credential = ManagedIdentityCredential(client_id=client_id)
opener = build_opener(RejectRedirects())
try:
    token = credential.get_token(core_scope).token
    if not token:
        raise RuntimeError("managed identity returned empty Core token")
    for item in qualified:
        event_id = item["event_id"]
        event_hash = item["event_hash"]
        try:
            existing = request_json(
                opener,
                token,
                "/api/v1/events/" + quote(event_id, safe=""),
            )
        except HTTPError as exc:
            if exc.code == 404:
                counts["core_not_found"] += 1
            elif exc.code in {401, 403}:
                counts["core_auth_failure"] += 1
            else:
                counts["core_transport_error"] += 1
            continue
        except (TimeoutError, URLError, OSError, RuntimeError, UnicodeDecodeError, json.JSONDecodeError):
            counts["core_transport_error"] += 1
            continue
        if validate_core_event(existing, event_id, event_hash):
            counts["core_present_match"] += 1
            item["core_log_index"] = int(existing["log_index"])
        else:
            counts["core_present_mismatch"] += 1
finally:
    credential.close()

qualified_count = len(qualified)
if counts["core_present_match"] != qualified_count:
    raise RuntimeError("not every terminal event has a matching immutable Core copy")
if any(
    counts[key] != 0
    for key in (
        "core_present_mismatch",
        "core_not_found",
        "core_auth_failure",
        "core_transport_error",
    )
):
    raise RuntimeError("Core verification failed; recovery refused")

now = utc_now()
with connect("gateway-sync.db") as connection:
    connection.execute("BEGIN IMMEDIATE")
    for item in qualified:
        row = connection.execute(
            """
            SELECT event_hash, tenant_id, workspace_id, state
            FROM sync_queue WHERE idempotency_key = ?
            """,
            (item["idempotency_key"],),
        ).fetchone()
        if row is None:
            raise RuntimeError("terminal row disappeared before reconciliation")
        if str(row["state"]) != "terminal_failure":
            raise RuntimeError("terminal row changed state before reconciliation")
        if str(row["event_hash"]) != item["event_hash"]:
            raise RuntimeError("terminal row event hash changed before reconciliation")
        if str(row["tenant_id"]) != tenant_id or str(row["workspace_id"]) != workspace_id:
            raise RuntimeError("terminal row scope changed before reconciliation")
        acknowledgement = {
            "status": "already_present",
            "event_id": item["event_id"],
            "event_hash": item["event_hash"],
            "core_log_index": item["core_log_index"],
        }
        acknowledgement_hash = hashlib.sha256(
            canonical_json(acknowledgement).encode("utf-8")
        ).hexdigest()
        cursor = connection.execute(
            """
            UPDATE sync_queue
            SET state = 'synchronized', acknowledgement_hash = ?,
                synchronized_at_utc = ?, updated_at_utc = ?, last_error = NULL
            WHERE idempotency_key = ? AND state = 'terminal_failure'
            """,
            (acknowledgement_hash, now, now, item["idempotency_key"]),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("terminal row reconciliation lost its atomic state guard")
        counts["queue_reconciled"] += 1
        if item["is_marker"]:
            counts["marker_reconciled"] += 1

    terminal_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'terminal_failure'"
    ).fetchone()[0])
    retryable_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'retryable_failure'"
    ).fetchone()[0])
    synchronized_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'synchronized'"
    ).fetchone()[0])
    if terminal_after != 0 or retryable_after != 0:
        raise RuntimeError("queue failures remain after bounded terminal reconciliation")
    connection.execute(
        """
        INSERT INTO sync_meta(key, value) VALUES ('last_successful_sync', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (now,),
    )
    connection.execute(
        """
        INSERT INTO sync_meta(key, value) VALUES ('upstream_status', 'healthy')
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """
    )
    connection.commit()

with connect("connector-runtime.db") as connection:
    connection.execute("BEGIN IMMEDIATE")
    runtime = connection.execute(
        """
        SELECT checkpoint_json, checkpoint_revision, last_success_at_utc,
               observation_state, gap_open, lease_owner
        FROM connector_runtime WHERE instance_id = ?
        """,
        (instance_id,),
    ).fetchone()
    if runtime is None:
        raise RuntimeError("connector runtime disappeared before gap reconciliation")
    if runtime["lease_owner"] is not None:
        raise RuntimeError("connector lease became active before gap reconciliation")
    if runtime["checkpoint_json"] is None or runtime["last_success_at_utc"] is None:
        raise RuntimeError("connector lost checkpoint/success state before gap reconciliation")
    if str(runtime["observation_state"]) != "collection_gap" or not bool(runtime["gap_open"]):
        raise RuntimeError("connector gap state changed before controlled reconciliation")
    cursor = connection.execute(
        """
        UPDATE connector_runtime
        SET observation_state = 'healthy_observation', gap_open = 0, updated_at_utc = ?
        WHERE instance_id = ? AND gap_open = 1 AND observation_state = 'collection_gap'
        """,
        (now, instance_id),
    )
    if cursor.rowcount != 1:
        raise RuntimeError("connector gap reconciliation lost its atomic state guard")
    connection.commit()

with connect("gateway-sync.db", readonly=True) as connection:
    terminal_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'terminal_failure'"
    ).fetchone()[0])
    retryable_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'retryable_failure'"
    ).fetchone()[0])
    synchronized_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'synchronized'"
    ).fetchone()[0])
    upstream_row = connection.execute(
        "SELECT value FROM sync_meta WHERE key = 'upstream_status'"
    ).fetchone()
    upstream_status_after = None if upstream_row is None else str(upstream_row[0])

with connect("connector-runtime.db", readonly=True) as connection:
    runtime_after = connection.execute(
        """
        SELECT checkpoint_json, checkpoint_revision, last_success_at_utc,
               observation_state, gap_open, lease_owner
        FROM connector_runtime WHERE instance_id = ?
        """,
        (instance_id,),
    ).fetchone()
if runtime_after is None:
    raise RuntimeError("connector runtime unavailable after recovery")

recovery_pass = (
    counts["terminal_local_invariants_ok"] == counts["terminal_total_before"]
    and counts["core_present_match"] == counts["terminal_total_before"]
    and counts["queue_reconciled"] == counts["terminal_total_before"]
    and counts["marker_reconciled"] == counts["terminal_marker_count"]
    and terminal_after == 0
    and retryable_after == 0
    and upstream_status_after == "healthy"
    and runtime_after["checkpoint_json"] is not None
    and runtime_after["last_success_at_utc"] is not None
    and str(runtime_after["observation_state"]) == "healthy_observation"
    and not bool(runtime_after["gap_open"])
    and runtime_after["lease_owner"] is None
)

result = {
    "schema_version": "ets.live_sharepoint.relay_recovery.v1",
    **counts,
    "queue_terminal_after": terminal_after,
    "queue_retryable_after": retryable_after,
    "queue_synchronized_after": synchronized_after,
    "checkpoint_present_after": runtime_after["checkpoint_json"] is not None,
    "last_success_present_after": runtime_after["last_success_at_utc"] is not None,
    "gap_open_before": bool(runtime_before["gap_open"]),
    "gap_open_after": bool(runtime_after["gap_open"]),
    "observation_healthy_after": str(runtime_after["observation_state"]) == "healthy_observation",
    "upstream_healthy_after": upstream_status_after == "healthy",
    "recovery_pass": recovery_pass,
    "customer_identifiers_retained": False,
    "event_identifiers_retained": False,
    "event_hashes_retained": False,
    "core_payload_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    "queue_state_mutated": True,
    "connector_runtime_mutated": True,
    "core_state_mutated": False,
    "m365_source_to_proof_claimed": False,
    "soak_clock_started": False,
}
raw = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
print(RESULT_MARKER + base64.urlsafe_b64encode(raw).decode("ascii"))
if not recovery_pass:
    raise SystemExit(2)
'''

resource recoveryJob 'Microsoft.App/jobs@2025-01-01' = {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: union(
      {
        '${registryPullIdentityResourceId}': {}
      },
      {
        '${runtimeIdentityResourceId}': {}
      }
    )
  }
  properties: {
    environmentId: managedEnvironmentResourceId
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaRetryLimit: 0
      replicaTimeout: 240
      identitySettings: [
        {
          identity: runtimeIdentityResourceId
          lifecycle: 'Main'
        }
        {
          identity: registryPullIdentityResourceId
          lifecycle: 'None'
        }
      ]
      registries: [
        {
          server: registryServer
          identity: registryPullIdentityResourceId
        }
      ]
    }
    template: {
      volumes: [
        {
          name: 'gateway-state'
          storageName: gatewayStateStorageName
          storageType: 'AzureFile'
          mountOptions: 'nobrl'
        }
      ]
      containers: [
        {
          name: 'sharepoint-relay-recovery'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [recoveryScript]
          env: [
            {
              name: 'ETS_RUNTIME_IDENTITY_CLIENT_ID'
              value: runtimeIdentityClientId
            }
            {
              name: 'ETS_CORE_BASE_URL'
              value: coreBaseUrl
            }
            {
              name: 'ETS_CORE_SCOPE'
              value: coreScope
            }
            {
              name: 'ETS_TENANT_ID'
              value: tenantId
            }
            {
              name: 'ETS_WORKSPACE_ID'
              value: workspaceId
            }
            {
              name: 'ETS_SP_INSTANCE_ID'
              value: connectorInstanceId
            }
            {
              name: 'ETS_SP_MARKER'
              value: marker
            }
          ]
          probes: []
          volumeMounts: [
            {
              volumeName: 'gateway-state'
              mountPath: '/mnt/gateway-state'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      initContainers: []
    }
  }
}

output recoveryJobName string = recoveryJob.name
