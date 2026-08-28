@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral state probe job name.')
@minLength(2)
@maxLength(32)
param jobName string

@description('Existing live Container Apps managed environment resource ID.')
@minLength(1)
param managedEnvironmentResourceId string

@description('Existing managed-environment storage name mounted by the live Gateway.')
@minLength(1)
param gatewayStateStorageName string

@description('Dedicated pull-only identity used by the live Gateway.')
@minLength(1)
param registryPullIdentityResourceId string

@description('Approved private ACR login server.')
@minLength(1)
param registryServer string

@description('Exact image currently deployed to the Gateway.')
@minLength(1)
param containerImage string

@description('Stable live connector instance identifier.')
@minLength(1)
param connectorInstanceId string

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

MARKER = "ETS_SP_STATE_PROBE_B64="
STATE_DIR = Path("/mnt/gateway-state")
instance_id = os.environ["ETS_SP_INSTANCE_ID"]
marker = os.environ["ETS_SP_MARKER"]
file_name = "ets-live-qualification-" + marker + ".txt"


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


def checkpoint_kind(raw):
    if raw is None:
        return "none"
    try:
        payload = json.loads(str(raw))
    except json.JSONDecodeError:
        return "invalid"
    cursor = payload.get("cursor") if isinstance(payload, dict) else None
    if not isinstance(cursor, str) or not cursor:
        return "missing_cursor"
    lowered = cursor.casefold()
    if "$skiptoken=" in lowered or "%24skiptoken=" in lowered:
        return "page"
    # This state belongs to the dedicated SharePoint/OneDrive delta collector. Graph
    # is allowed to return an opaque terminal delta cursor, so a valid non-page
    # cursor is a durable delta checkpoint even when it does not expose a literal
    # $deltatoken query parameter.
    return "delta"


with connect_ro("connector-runtime.db") as connection:
    runtime = connection.execute(
        """
        SELECT checkpoint_json, checkpoint_revision, retry_count,
               next_attempt_at_utc, last_success_at_utc,
               observation_state, gap_open, lease_owner, lease_expires_at_utc
        FROM connector_runtime WHERE instance_id = ?
        """,
        (instance_id,),
    ).fetchone()
    if runtime is None:
        raise RuntimeError("live connector runtime row is unavailable")

marker_event_ids = set()
with connect_ro("gateway-events.db") as connection:
    rows = connection.execute("SELECT event_id, event_json FROM events").fetchall()
    local_event_count = len(rows)
    sharepoint_local_count = 0
    marker_local_count = 0
    for row in rows:
        try:
            event = json.loads(str(row["event_json"]))
        except json.JSONDecodeError:
            continue
        if event.get("source_system") != "microsoft.sharepoint.onedrive_delta":
            continue
        sharepoint_local_count += 1
        metadata = event.get("metadata")
        capture = metadata.get("capture_metadata") if isinstance(metadata, dict) else None
        committed = (
            capture.get("committed_connector_metadata")
            if isinstance(capture, dict)
            else None
        )
        source_metadata = committed.get("metadata") if isinstance(committed, dict) else None
        if isinstance(source_metadata, dict) and source_metadata.get("name") == file_name:
            marker_local_count += 1
            marker_event_ids.add(str(row["event_id"]))

with connect_ro("gateway-sync.db") as connection:
    states = {
        "pending": 0,
        "in_flight": 0,
        "retryable_failure": 0,
        "terminal_failure": 0,
        "synchronized": 0,
    }
    marker_states = dict(states)
    queue_rows = connection.execute(
        "SELECT event_id, state FROM sync_queue"
    ).fetchall()
    for row in queue_rows:
        state = str(row["state"])
        if state in states:
            states[state] += 1
            if str(row["event_id"]) in marker_event_ids:
                marker_states[state] += 1

result = {
    "schema_version": "ets.live_sharepoint.state_probe.v1",
    "checkpoint_present": runtime["checkpoint_json"] is not None,
    "checkpoint_revision": int(runtime["checkpoint_revision"]),
    "checkpoint_kind": checkpoint_kind(runtime["checkpoint_json"]),
    "retry_count": int(runtime["retry_count"]),
    "next_attempt_present": runtime["next_attempt_at_utc"] is not None,
    "last_success_present": runtime["last_success_at_utc"] is not None,
    "observation_state": str(runtime["observation_state"]),
    "gap_open": bool(runtime["gap_open"]),
    "lease_active": runtime["lease_owner"] is not None,
    "local_event_count": local_event_count,
    "sharepoint_local_event_count": sharepoint_local_count,
    "marker_local_event_count": marker_local_count,
    "queue_pending": states["pending"],
    "queue_in_flight": states["in_flight"],
    "queue_retryable_failure": states["retryable_failure"],
    "queue_terminal_failure": states["terminal_failure"],
    "queue_synchronized": states["synchronized"],
    "marker_queue_pending": marker_states["pending"],
    "marker_queue_in_flight": marker_states["in_flight"],
    "marker_queue_retryable_failure": marker_states["retryable_failure"],
    "marker_queue_terminal_failure": marker_states["terminal_failure"],
    "marker_queue_synchronized": marker_states["synchronized"],
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
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
    userAssignedIdentities: {
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
      replicaTimeout: 180
      identitySettings: [
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
          name: 'sharepoint-state-probe'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [probeScript]
          env: [
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

output probeJobName string = probeJob.name