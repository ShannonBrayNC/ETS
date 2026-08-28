@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral SharePoint relay fault-stage job name.')
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

var stageScript = '''
import base64
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from azure.identity import ManagedIdentityCredential

RESULT_MARKER = "ETS_SP_RELAY_FAULT_STAGE_B64="
STATE_DIR = Path("/mnt/gateway-state")
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
            "User-Agent": "ets-sharepoint-relay-fault-stage/1.0",
        },
    )
    with opener.open(request, timeout=15.0) as response:
        return read_json_response(response)


with connect("connector-runtime.db", readonly=True) as connection:
    runtime = connection.execute(
        """
        SELECT checkpoint_json, checkpoint_revision, retry_count,
               next_attempt_at_utc, last_success_at_utc,
               observation_state, gap_open, lease_owner
        FROM connector_runtime WHERE instance_id = ?
        """,
        (instance_id,),
    ).fetchone()
if runtime is None:
    raise RuntimeError("live connector runtime row is unavailable")
if runtime["checkpoint_json"] is None or runtime["last_success_at_utc"] is None:
    raise RuntimeError("connector lacks a durable successful checkpoint")
if int(runtime["checkpoint_revision"]) < 1 or int(runtime["retry_count"]) != 0:
    raise RuntimeError("connector checkpoint/retry state is not healthy")
if runtime["next_attempt_at_utc"] is not None or runtime["lease_owner"] is not None:
    raise RuntimeError("connector has active retry or lease state")
if bool(runtime["gap_open"]) or str(runtime["observation_state"]) != "healthy_observation":
    raise RuntimeError("connector must be healthy with a closed gap before fault staging")

with connect("gateway-events.db", readonly=True) as connection:
    local_rows = connection.execute(
        "SELECT event_id, event_json, event_hash FROM events"
    ).fetchall()
local = {str(row["event_id"]): row for row in local_rows}
marker_ids = set()
for row in local_rows:
    try:
        event = json.loads(str(row["event_json"]))
    except json.JSONDecodeError:
        continue
    if marker_event(event):
        marker_ids.add(str(row["event_id"]))
if not marker_ids:
    raise RuntimeError("synthetic marker is not present in immutable local Gateway evidence")

with connect("gateway-sync.db", readonly=True) as connection:
    failures = {
        state: int(connection.execute(
            "SELECT COUNT(*) FROM sync_queue WHERE state = ?", (state,)
        ).fetchone()[0])
        for state in ("pending", "in_flight", "retryable_failure", "terminal_failure")
    }
    if any(failures.values()):
        raise RuntimeError("Gateway relay queue must be fully healthy before fault staging")
    synchronized = connection.execute(
        """
        SELECT id, idempotency_key, event_id, event_hash, tenant_id, workspace_id,
               acknowledgement_hash, synchronized_at_utc
        FROM sync_queue
        WHERE state = 'synchronized'
        ORDER BY id DESC
        """
    ).fetchall()

marker_rows = [row for row in synchronized if str(row["event_id"]) in marker_ids]
if not marker_rows:
    raise RuntimeError("no synchronized queue row exists for the synthetic marker")
target = marker_rows[0]
event_id = str(target["event_id"])
local_row = local.get(event_id)
if local_row is None:
    raise RuntimeError("selected marker queue row has no immutable local event")
try:
    event = json.loads(str(local_row["event_json"]))
except json.JSONDecodeError as exc:
    raise RuntimeError("selected marker local event is invalid JSON") from exc
if not marker_event(event):
    raise RuntimeError("selected queue row is not the bounded synthetic marker")
if str(local_row["event_hash"]) != str(target["event_hash"]):
    raise RuntimeError("selected marker queue/local event hash mismatch")
if event.get("tenant_id") != tenant_id or event.get("workspace_id") != workspace_id:
    raise RuntimeError("selected marker event is outside the deployed Gateway scope")
if str(target["tenant_id"]) != tenant_id or str(target["workspace_id"]) != workspace_id:
    raise RuntimeError("selected marker queue row is outside the deployed Gateway scope")

credential = ManagedIdentityCredential(client_id=client_id)
opener = build_opener(RejectRedirects())
core_match = False
try:
    token = credential.get_token(core_scope).token
    if not token:
        raise RuntimeError("managed identity returned empty Core token")
    try:
        existing = request_json(opener, token, "/api/v1/events/" + quote(event_id, safe=""))
    except HTTPError as exc:
        raise RuntimeError("Core immutable marker readback failed") from exc
    core_event = existing.get("event")
    core_match = (
        existing.get("event_hash") == str(target["event_hash"])
        and isinstance(core_event, dict)
        and core_event.get("event_id") == event_id
        and isinstance(existing.get("log_index"), int)
        and int(existing["log_index"]) >= 0
    )
finally:
    credential.close()
if not core_match:
    raise RuntimeError("synthetic marker does not have a matching immutable Core copy")

now = utc_now()
with connect("gateway-sync.db") as connection:
    connection.execute("BEGIN IMMEDIATE")
    current = connection.execute(
        """
        SELECT state, event_id, event_hash, tenant_id, workspace_id,
               acknowledgement_hash, synchronized_at_utc
        FROM sync_queue WHERE id = ?
        """,
        (int(target["id"]),),
    ).fetchone()
    if current is None or str(current["state"]) != "synchronized":
        raise RuntimeError("synthetic marker queue row changed before bounded staging")
    if str(current["event_id"]) != event_id or str(current["event_hash"]) != str(target["event_hash"]):
        raise RuntimeError("synthetic marker queue identity changed before bounded staging")
    if current["acknowledgement_hash"] != target["acknowledgement_hash"]:
        raise RuntimeError("synthetic marker acknowledgement changed before bounded staging")
    if current["synchronized_at_utc"] != target["synchronized_at_utc"]:
        raise RuntimeError("synthetic marker synchronization time changed before bounded staging")
    cursor = connection.execute(
        """
        UPDATE sync_queue
        SET state = 'terminal_failure', acknowledgement_hash = NULL,
            synchronized_at_utc = NULL, updated_at_utc = ?,
            last_error = 'ETS_RC1D_SYNTHETIC_RELAY_FAULT'
        WHERE id = ? AND state = 'synchronized'
        """,
        (now, int(target["id"])),
    )
    if cursor.rowcount != 1:
        raise RuntimeError("bounded marker queue fault staging lost its atomic state guard")
    terminal_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'terminal_failure'"
    ).fetchone()[0])
    retryable_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE state = 'retryable_failure'"
    ).fetchone()[0])
    marker_terminal_after = int(connection.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE id = ? AND state = 'terminal_failure'",
        (int(target["id"]),),
    ).fetchone()[0])
    if terminal_after != 1 or retryable_after != 0 or marker_terminal_after != 1:
        raise RuntimeError("bounded queue fault staging produced an unexpected relay state")
    connection.commit()

try:
    with connect("connector-runtime.db") as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE connector_runtime
            SET observation_state = 'collection_gap', gap_open = 1, updated_at_utc = ?
            WHERE instance_id = ? AND observation_state = 'healthy_observation'
              AND gap_open = 0 AND lease_owner IS NULL
            """,
            (now, instance_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("bounded collection-gap staging lost its atomic runtime guard")
        after = connection.execute(
            "SELECT observation_state, gap_open, lease_owner FROM connector_runtime WHERE instance_id = ?",
            (instance_id,),
        ).fetchone()
        if after is None or str(after["observation_state"]) != "collection_gap" or not bool(after["gap_open"]):
            raise RuntimeError("bounded collection-gap staging did not latch")
        if after["lease_owner"] is not None:
            raise RuntimeError("connector lease became active during bounded fault staging")
        connection.commit()
except Exception:
    # Restore the exact prior synchronized row if runtime gap staging cannot complete.
    with connect("gateway-sync.db") as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE sync_queue
            SET state = 'synchronized', acknowledgement_hash = ?,
                synchronized_at_utc = ?, last_error = NULL, updated_at_utc = ?
            WHERE id = ? AND state = 'terminal_failure'
              AND last_error = 'ETS_RC1D_SYNTHETIC_RELAY_FAULT'
            """,
            (
                target["acknowledgement_hash"],
                target["synchronized_at_utc"],
                utc_now(),
                int(target["id"]),
            ),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            raise RuntimeError("fault-stage compensation could not restore the exact synchronized marker row")
        connection.commit()
    raise

result = {
    "schema_version": "ets.live_sharepoint.relay_fault_stage.v1",
    "checkpoint_present_before": True,
    "checkpoint_revision_before": int(runtime["checkpoint_revision"]),
    "last_success_present_before": True,
    "observation_healthy_before": True,
    "gap_open_before": False,
    "lease_active_before": False,
    "marker_local_count_before": len(marker_ids),
    "marker_synchronized_count_before": len(marker_rows),
    "queue_failures_before": sum(failures.values()),
    "core_present_match": 1,
    "terminal_total_after": terminal_after,
    "retryable_after": retryable_after,
    "marker_terminal_after": marker_terminal_after,
    "gap_open_after": True,
    "observation_collection_gap_after": True,
    "lease_active_after": False,
    "stage_pass": True,
    "queue_state_mutated": True,
    "connector_runtime_mutated": True,
    "core_state_mutated": False,
    "customer_identifiers_retained": False,
    "event_identifiers_retained": False,
    "event_hashes_retained": False,
    "core_payload_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    "m365_source_to_proof_claimed": False,
    "soak_clock_started": False,
}
raw = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
print(RESULT_MARKER + base64.urlsafe_b64encode(raw).decode("ascii"))
'''

resource stageJob 'Microsoft.App/jobs@2025-01-01' = {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentityResourceId}': {}
      '${registryPullIdentityResourceId}': {}
    }
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
          name: 'sharepoint-relay-fault-stage'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [stageScript]
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

output stageJobName string = stageJob.name