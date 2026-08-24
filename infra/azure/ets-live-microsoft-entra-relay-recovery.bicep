@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral Microsoft Entra relay recovery job name.')
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

var recoveryScript = '''
import base64
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from azure.identity import ManagedIdentityCredential
from ets.core.canonical_json import canonical_sha256
from ets.core.models import EvidenceEvent

RESULT_MARKER = "ETS_ENTRA_RELAY_RECOVERY_B64="
STATE_DIR = Path("/mnt/gateway-state")
MAX_TERMINAL = 20
MAX_RESPONSE_BYTES = 1024 * 1024
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
            "User-Agent": "ets-microsoft-entra-relay-recovery/1.0",
        },
    )
    with opener.open(request, timeout=15.0) as response:
        return read_json_response(response)


def validate_event(event, event_hash):
    if not isinstance(event, dict):
        return False
    if event.get("tenant_id") != tenant_id or event.get("workspace_id") != workspace_id:
        return False
    if event.get("source_system") != "microsoft.entra.directory_delta":
        return False
    if event.get("redaction_profile") != "microsoft_entra_directory_metadata_v1":
        return False
    try:
        validated = EvidenceEvent.model_validate(event)
    except ValueError:
        return False
    return canonical_sha256(validated.hashable_payload()) == event_hash


def validate_core_event(payload, event_id, event_hash):
    event = payload.get("event")
    log_index = payload.get("log_index")
    return (
        payload.get("event_hash") == event_hash
        and isinstance(event, dict)
        and event.get("event_id") == event_id
        and validate_event(event, event_hash)
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
    blocking_before = int(connection.execute(
        """
        SELECT COUNT(*) FROM sync_queue
        WHERE state IN ('pending', 'in_flight', 'retryable_failure')
        """
    ).fetchone()[0])

if not terminal_rows:
    raise RuntimeError("no terminal relay rows are available for controlled recovery")
if len(terminal_rows) > MAX_TERMINAL:
    raise RuntimeError("terminal relay state exceeds controlled recovery bound")
if blocking_before != 0:
    raise RuntimeError("active or retryable relay rows must be resolved before terminal recovery")

counts = {
    "terminal_total_before": len(terminal_rows),
    "terminal_entra_count": 0,
    "terminal_profile_count": 0,
    "terminal_local_invariants_ok": 0,
    "terminal_local_invariant_failure": 0,
    "core_present_match": 0,
    "core_present_mismatch": 0,
    "core_not_found": 0,
    "core_auth_failure": 0,
    "core_transport_error": 0,
    "queue_reconciled": 0,
}

qualified = []
for row in terminal_rows:
    event_id = str(row["event_id"])
    event_hash = str(row["event_hash"])
    local_row = local.get(event_id)
    if local_row is None:
        counts["terminal_local_invariant_failure"] += 1
        continue
    try:
        event = json.loads(str(local_row["event_json"]))
    except json.JSONDecodeError:
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("source_system") == "microsoft.entra.directory_delta":
        counts["terminal_entra_count"] += 1
    if event.get("redaction_profile") == "microsoft_entra_directory_metadata_v1":
        counts["terminal_profile_count"] += 1
    if str(local_row["event_hash"]) != event_hash:
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("tenant_id") != str(row["tenant_id"]):
        counts["terminal_local_invariant_failure"] += 1
        continue
    if event.get("workspace_id") != str(row["workspace_id"]):
        counts["terminal_local_invariant_failure"] += 1
        continue
    if not validate_event(event, event_hash):
        counts["terminal_local_invariant_failure"] += 1
        continue
    counts["terminal_local_invariants_ok"] += 1
    qualified.append(
        {
            "idempotency_key": str(row["idempotency_key"]),
            "event_id": event_id,
            "event_hash": event_hash,
        }
    )

if counts["terminal_local_invariant_failure"] != 0:
    raise RuntimeError("terminal relay local invariants failed; recovery refused")
if counts["terminal_entra_count"] != counts["terminal_total_before"]:
    raise RuntimeError("terminal recovery set contains non-Microsoft Entra events")
if counts["terminal_profile_count"] != counts["terminal_total_before"]:
    raise RuntimeError("terminal recovery set contains an unapproved redaction profile")

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
with connect("gateway-events.db", readonly=True) as event_connection:
    with connect("gateway-sync.db") as connection:
        connection.execute("BEGIN IMMEDIATE")
        for item in qualified:
            local_row = event_connection.execute(
                "SELECT event_json, event_hash FROM events WHERE event_id = ?",
                (item["event_id"],),
            ).fetchone()
            if local_row is None:
                raise RuntimeError("local event disappeared before reconciliation")
            try:
                event = json.loads(str(local_row["event_json"]))
            except json.JSONDecodeError as exc:
                raise RuntimeError("local event became invalid before reconciliation") from exc
            if str(local_row["event_hash"]) != item["event_hash"]:
                raise RuntimeError("local event hash changed before reconciliation")
            if not validate_event(event, item["event_hash"]):
                raise RuntimeError("local event invariants changed before reconciliation")

            row = connection.execute(
                """
                SELECT event_id, event_hash, tenant_id, workspace_id, state
                FROM sync_queue WHERE idempotency_key = ?
                """,
                (item["idempotency_key"],),
            ).fetchone()
            if row is None:
                raise RuntimeError("terminal row disappeared before reconciliation")
            if str(row["state"]) != "terminal_failure":
                raise RuntimeError("terminal row changed state before reconciliation")
            if str(row["event_id"]) != item["event_id"]:
                raise RuntimeError("terminal row event identifier changed before reconciliation")
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
            acknowledgement_hash = canonical_sha256(acknowledgement)
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

        terminal_after = int(connection.execute(
            "SELECT COUNT(*) FROM sync_queue WHERE state = 'terminal_failure'"
        ).fetchone()[0])
        retryable_after = int(connection.execute(
            "SELECT COUNT(*) FROM sync_queue WHERE state = 'retryable_failure'"
        ).fetchone()[0])
        blocking_after = int(connection.execute(
            "SELECT COUNT(*) FROM sync_queue WHERE state IN ('pending', 'in_flight')"
        ).fetchone()[0])
        synchronized_after = int(connection.execute(
            "SELECT COUNT(*) FROM sync_queue WHERE state = 'synchronized'"
        ).fetchone()[0])
        if terminal_after != 0 or retryable_after != 0 or blocking_after != 0:
            raise RuntimeError("queue failures or active rows remain after bounded reconciliation")
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

recovery_pass = (
    counts["terminal_local_invariants_ok"] == counts["terminal_total_before"]
    and counts["terminal_local_invariant_failure"] == 0
    and counts["terminal_entra_count"] == counts["terminal_total_before"]
    and counts["terminal_profile_count"] == counts["terminal_total_before"]
    and counts["core_present_match"] == counts["terminal_total_before"]
    and counts["core_present_mismatch"] == 0
    and counts["core_not_found"] == 0
    and counts["core_auth_failure"] == 0
    and counts["core_transport_error"] == 0
    and counts["queue_reconciled"] == counts["terminal_total_before"]
    and terminal_after == 0
    and retryable_after == 0
    and upstream_status_after == "healthy"
)

result = {
    "schema_version": "ets.live_microsoft_entra.relay_recovery.v1",
    **counts,
    "queue_terminal_after": terminal_after,
    "queue_retryable_after": retryable_after,
    "queue_synchronized_after": synchronized_after,
    "upstream_healthy_after": upstream_status_after == "healthy",
    "recovery_pass": recovery_pass,
    "customer_identifiers_retained": False,
    "event_identifiers_retained": False,
    "event_hashes_retained": False,
    "core_payload_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    "queue_state_mutated": True,
    "connector_runtime_mutated": False,
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
          name: 'microsoft-entra-relay-recovery'
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
