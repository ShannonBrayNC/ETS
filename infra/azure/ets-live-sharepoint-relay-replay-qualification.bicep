@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral relay replay qualification job name.')
@minLength(2)
@maxLength(32)
param jobName string

@description('Existing live Container Apps managed environment resource ID.')
@minLength(1)
param managedEnvironmentResourceId string

@description('Existing managed-environment storage name mounted by the live Gateway.')
@minLength(1)
param gatewayStateStorageName string

@description('Gateway runtime identity resource ID used for Core qualification.')
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

@description('Synthetic public-safe qualification marker.')
@minLength(6)
@maxLength(32)
param marker string

var qualificationScript = '''
import base64
import json
import os
import sqlite3
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from azure.identity import ManagedIdentityCredential

RESULT_MARKER = "ETS_SP_RELAY_REPLAY_B64="
STATE_DIR = Path("/mnt/gateway-state")
MAX_TERMINAL = 20
MAX_RESPONSE_BYTES = 1024 * 1024
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


def connect_ro(name):
    path = STATE_DIR / name
    if not path.is_file():
        raise RuntimeError("required Gateway state database is unavailable: " + name)
    connection = sqlite3.connect(
        "file:" + str(path) + "?mode=ro",
        uri=True,
        timeout=5.0,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
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


def request_json(opener, token, method, path, body=None):
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
        "User-Agent": "ets-sharepoint-relay-replay-qualification/1.0",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = body
    request = Request(core_base_url + path, data=data, method=method, headers=headers)
    with opener.open(request, timeout=15.0) as response:
        return read_json_response(response)


def validate_core_event(payload, event_id, event_hash):
    event = payload.get("event")
    return (
        payload.get("event_hash") == event_hash
        and isinstance(event, dict)
        and event.get("event_id") == event_id
    )


with connect_ro("gateway-events.db") as connection:
    local_rows = connection.execute(
        "SELECT event_id, event_json, event_hash FROM events"
    ).fetchall()
local = {str(row["event_id"]): row for row in local_rows}

with connect_ro("gateway-sync.db") as connection:
    terminal_rows = connection.execute(
        """
        SELECT event_id, event_hash, tenant_id, workspace_id
        FROM sync_queue
        WHERE state = 'terminal_failure'
        ORDER BY id ASC
        """
    ).fetchall()

if not terminal_rows:
    raise RuntimeError("no terminal relay rows are available for qualification")
if len(terminal_rows) > MAX_TERMINAL:
    raise RuntimeError("terminal relay state exceeds qualification bound")

counts = {
    "terminal_total": len(terminal_rows),
    "terminal_sharepoint_count": 0,
    "terminal_marker_count": 0,
    "terminal_local_invariants_ok": 0,
    "terminal_local_invariant_failure": 0,
    "replay_accepted": 0,
    "replay_already_present": 0,
    "replay_auth_failure": 0,
    "replay_validation_failure": 0,
    "replay_retryable_http": 0,
    "replay_other_http": 0,
    "replay_transport_error": 0,
    "replay_ack_mismatch": 0,
    "core_readback_match": 0,
    "core_readback_mismatch": 0,
    "duplicate_reconciled": 0,
    "duplicate_unexpected": 0,
    "proof_endpoint_ok": 0,
    "proof_endpoint_failure": 0,
    "marker_replayed": 0,
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
    counts["terminal_local_invariants_ok"] += 1
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode("utf-8")
    qualified.append((event_id, str(row["event_hash"]), body, is_marker))

credential = ManagedIdentityCredential(client_id=client_id)
opener = build_opener(RejectRedirects())
try:
    token = credential.get_token(core_scope).token
    if not token:
        raise RuntimeError("managed identity returned empty Core token")

    for event_id, event_hash, body, is_marker in qualified:
        proof_path = None
        replay_ok = False
        try:
            response = request_json(opener, token, "POST", "/api/v1/events", body)
            if (
                response.get("event_id") == event_id
                and response.get("event_hash") == event_hash
                and isinstance(response.get("log_index"), int)
                and isinstance(response.get("tree_head"), dict)
                and isinstance(response.get("inclusion_proof_url"), str)
                and response["inclusion_proof_url"].startswith("/")
            ):
                counts["replay_accepted"] += 1
                replay_ok = True
                proof_path = response["inclusion_proof_url"]
            else:
                counts["replay_ack_mismatch"] += 1
        except HTTPError as exc:
            if exc.code == 409:
                try:
                    existing = request_json(
                        opener,
                        token,
                        "GET",
                        "/api/v1/events/" + quote(event_id, safe=""),
                    )
                    if validate_core_event(existing, event_id, event_hash):
                        counts["replay_already_present"] += 1
                        replay_ok = True
                    else:
                        counts["replay_ack_mismatch"] += 1
                except Exception:
                    counts["replay_ack_mismatch"] += 1
            elif exc.code in {401, 403}:
                counts["replay_auth_failure"] += 1
            elif exc.code in {400, 413, 422}:
                counts["replay_validation_failure"] += 1
            elif exc.code in {408, 425, 429} or 500 <= exc.code <= 599:
                counts["replay_retryable_http"] += 1
            else:
                counts["replay_other_http"] += 1
        except (TimeoutError, URLError, OSError, RuntimeError, UnicodeDecodeError, json.JSONDecodeError):
            counts["replay_transport_error"] += 1

        if not replay_ok:
            continue
        if is_marker:
            counts["marker_replayed"] += 1

        try:
            existing = request_json(
                opener,
                token,
                "GET",
                "/api/v1/events/" + quote(event_id, safe=""),
            )
            if validate_core_event(existing, event_id, event_hash):
                counts["core_readback_match"] += 1
            else:
                counts["core_readback_mismatch"] += 1
        except Exception:
            counts["core_readback_mismatch"] += 1

        if proof_path is not None:
            try:
                proof = request_json(opener, token, "GET", proof_path)
                if proof:
                    counts["proof_endpoint_ok"] += 1
                else:
                    counts["proof_endpoint_failure"] += 1
            except Exception:
                counts["proof_endpoint_failure"] += 1

        try:
            request_json(opener, token, "POST", "/api/v1/events", body)
            counts["duplicate_unexpected"] += 1
        except HTTPError as exc:
            if exc.code != 409:
                counts["duplicate_unexpected"] += 1
            else:
                try:
                    existing = request_json(
                        opener,
                        token,
                        "GET",
                        "/api/v1/events/" + quote(event_id, safe=""),
                    )
                    if validate_core_event(existing, event_id, event_hash):
                        counts["duplicate_reconciled"] += 1
                    else:
                        counts["duplicate_unexpected"] += 1
                except Exception:
                    counts["duplicate_unexpected"] += 1
        except Exception:
            counts["duplicate_unexpected"] += 1
finally:
    credential.close()

qualified_count = counts["terminal_local_invariants_ok"]
qualification_pass = (
    qualified_count > 0
    and counts["terminal_local_invariant_failure"] == 0
    and counts["terminal_sharepoint_count"] == counts["terminal_total"]
    and counts["replay_accepted"] + counts["replay_already_present"] == qualified_count
    and counts["replay_auth_failure"] == 0
    and counts["replay_validation_failure"] == 0
    and counts["replay_retryable_http"] == 0
    and counts["replay_other_http"] == 0
    and counts["replay_transport_error"] == 0
    and counts["replay_ack_mismatch"] == 0
    and counts["core_readback_match"] == qualified_count
    and counts["core_readback_mismatch"] == 0
    and counts["duplicate_reconciled"] == qualified_count
    and counts["duplicate_unexpected"] == 0
    and counts["proof_endpoint_failure"] == 0
    and counts["marker_replayed"] == counts["terminal_marker_count"]
)

result = {
    "schema_version": "ets.live_sharepoint.relay_replay_qualification.v1",
    **counts,
    "qualification_pass": qualification_pass,
    "customer_identifiers_retained": False,
    "event_identifiers_retained": False,
    "event_hashes_retained": False,
    "core_payload_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    "queue_state_mutated": False,
    "core_state_mutated": True,
    "m365_source_to_proof_claimed": False,
    "soak_clock_started": False,
}
raw = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
print(RESULT_MARKER + base64.urlsafe_b64encode(raw).decode("ascii"))
if not qualification_pass:
    raise SystemExit(2)
'''

resource replayJob 'Microsoft.App/jobs@2025-01-01' = {
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
          name: 'sharepoint-relay-replay-qualification'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [qualificationScript]
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

output replayJobName string = replayJob.name
