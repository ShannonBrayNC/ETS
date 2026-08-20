@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral relay state probe job name.')
@minLength(2)
@maxLength(32)
param jobName string

@description('Existing live Container Apps managed environment resource ID.')
@minLength(1)
param managedEnvironmentResourceId string

@description('Existing managed-environment storage name mounted by the live Gateway.')
@minLength(1)
param gatewayStateStorageName string

@description('Gateway runtime identity resource ID used for Core read-only lookup.')
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

var probeScript = '''
import base64
import json
import os
import sqlite3
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from azure.identity import ManagedIdentityCredential

MARKER = "ETS_SP_RELAY_STATE_PROBE_B64="
STATE_DIR = Path("/mnt/gateway-state")
MAX_TERMINAL = 100
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
        raise RuntimeError("redirect")


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


with connect_ro("gateway-events.db") as connection:
    local_rows = connection.execute(
        "SELECT event_id, event_json, event_hash FROM events"
    ).fetchall()
local = {str(row["event_id"]): row for row in local_rows}

with connect_ro("gateway-sync.db") as connection:
    terminal_total = int(
        connection.execute(
            "SELECT COUNT(*) FROM sync_queue WHERE state = 'terminal_failure'"
        ).fetchone()[0]
    )
    if terminal_total > MAX_TERMINAL:
        raise RuntimeError("terminal relay state exceeds diagnostic bound")
    terminal_rows = connection.execute(
        """
        SELECT event_id, event_hash, tenant_id, workspace_id
        FROM sync_queue
        WHERE state = 'terminal_failure'
        ORDER BY id ASC
        """
    ).fetchall()

counts = {
    "terminal_total": terminal_total,
    "terminal_sharepoint_count": 0,
    "terminal_marker_count": 0,
    "terminal_local_missing": 0,
    "terminal_event_hash_mismatch": 0,
    "terminal_tenant_mismatch": 0,
    "terminal_workspace_mismatch": 0,
    "terminal_local_invariants_ok": 0,
    "core_present_match": 0,
    "core_present_mismatch": 0,
    "core_not_found": 0,
    "core_auth_failure": 0,
    "core_retryable_http": 0,
    "core_other_http": 0,
    "core_transport_error": 0,
}

qualified = []
for row in terminal_rows:
    event_id = str(row["event_id"])
    local_row = local.get(event_id)
    if local_row is None:
        counts["terminal_local_missing"] += 1
        continue
    try:
        event = json.loads(str(local_row["event_json"]))
    except json.JSONDecodeError:
        counts["terminal_event_hash_mismatch"] += 1
        continue
    if event.get("source_system") == "microsoft.sharepoint.onedrive_delta":
        counts["terminal_sharepoint_count"] += 1
    if marker_event(event):
        counts["terminal_marker_count"] += 1
    if str(local_row["event_hash"]) != str(row["event_hash"]):
        counts["terminal_event_hash_mismatch"] += 1
        continue
    if event.get("tenant_id") != str(row["tenant_id"]):
        counts["terminal_tenant_mismatch"] += 1
        continue
    if event.get("workspace_id") != str(row["workspace_id"]):
        counts["terminal_workspace_mismatch"] += 1
        continue
    if event.get("tenant_id") != tenant_id:
        counts["terminal_tenant_mismatch"] += 1
        continue
    if event.get("workspace_id") != workspace_id:
        counts["terminal_workspace_mismatch"] += 1
        continue
    counts["terminal_local_invariants_ok"] += 1
    qualified.append((event_id, str(row["event_hash"])))

credential = ManagedIdentityCredential(client_id=client_id)
try:
    token = credential.get_token(core_scope).token
    if not token:
        raise RuntimeError("managed identity returned empty Core token")
    opener = build_opener(RejectRedirects())
    for event_id, event_hash in qualified:
        request = Request(
            core_base_url + "/api/v1/events/" + quote(event_id, safe=""),
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + token,
                "User-Agent": "ets-sharepoint-relay-state-probe/1.0",
            },
        )
        try:
            with opener.open(request, timeout=15.0) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    counts["core_present_mismatch"] += 1
                    continue
            payload = json.loads(body.decode("utf-8"))
            if (
                isinstance(payload, dict)
                and payload.get("event_hash") == event_hash
                and isinstance(payload.get("event"), dict)
                and payload["event"].get("event_id") == event_id
            ):
                counts["core_present_match"] += 1
            else:
                counts["core_present_mismatch"] += 1
        except HTTPError as exc:
            if exc.code == 404:
                counts["core_not_found"] += 1
            elif exc.code in {401, 403}:
                counts["core_auth_failure"] += 1
            elif exc.code in {408, 425, 429} or 500 <= exc.code <= 599:
                counts["core_retryable_http"] += 1
            else:
                counts["core_other_http"] += 1
        except (TimeoutError, URLError, OSError, RuntimeError, UnicodeDecodeError, json.JSONDecodeError):
            counts["core_transport_error"] += 1
finally:
    credential.close()

result = {
    "schema_version": "ets.live_sharepoint.relay_state_probe.v1",
    **counts,
    "customer_identifiers_retained": False,
    "event_identifiers_retained": False,
    "core_payload_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    "queue_state_mutated": False,
    "core_state_mutated": False,
    "m365_source_to_proof_claimed": False,
    "soak_clock_started": False,
}
raw = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
print(MARKER + base64.urlsafe_b64encode(raw).decode("ascii"))
'''

resource probeJob 'Microsoft.App/jobs@2025-01-01' = {
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
      replicaTimeout: 180
      identitySettings: [
        {
          identity: runtimeIdentityResourceId
          lifecycle: 'None'
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
          name: 'sharepoint-relay-state-probe'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [probeScript]
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

output probeJobName string = probeJob.name
