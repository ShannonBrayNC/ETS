@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral RC1B preflight job name.')
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

@description('Directory-only runtime identity attached to the live Gateway.')
@minLength(1)
param directoryIdentityResourceId string

@description('Client ID of the directory-only runtime identity.')
@minLength(1)
param directoryIdentityClientId string

@description('Approved private ACR login server.')
@minLength(1)
param registryServer string

@description('Exact immutable image currently deployed to the Gateway.')
@minLength(1)
param containerImage string

@description('Stable base Microsoft connector instance identifier.')
@minLength(1)
@maxLength(128)
param connectorInstanceId string

@secure()
@description('Approved SharePoint/OneDrive drive ID used only for a negative authorization check.')
@minLength(1)
param sharePointDriveId string

var probeScript = '''
import base64
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

GRAPH_ROOT = "https://graph.microsoft.com"
GRAPH_SCOPE = GRAPH_ROOT + "/.default"
MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024
RESULT_MARKER = "ETS_M365_RC1B_PREFLIGHT_B64="
FAILURE_MARKER = "ETS_M365_RC1B_PREFLIGHT_FAILURE_B64="
FAILURE_CODE = "probe_initialization_failed"


def emit_sanitized_failure(exception_type, exception, traceback):
    payload = {
        "schema_version": "ets.live_microsoft.rc1b_preflight_runtime_failure.v1",
        "failure_code": FAILURE_CODE,
        "raw_directory_payload_retained": False,
        "customer_identifiers_retained": False,
        "reusable_credential_retained": False,
        "public_evidence_safe": True,
        "rc1b_live_qualified": False,
        "soak_clock_started": False,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    print(FAILURE_MARKER + base64.urlsafe_b64encode(raw).decode("ascii"))
    sys.__excepthook__(exception_type, exception, traceback)


sys.excepthook = emit_sanitized_failure

from azure.identity import ManagedIdentityCredential
from ets.qualification.microsoft_rc1b_polling_matrix import (
    run_rc1b_directory_drive_fault_matrix,
)

STATE_DIR = Path("/mnt/gateway-state")
BASE_INSTANCE_ID = os.environ["ETS_RC1B_INSTANCE_ID"]
DIRECTORY_CLIENT_ID = os.environ["ETS_RC1B_DIRECTORY_CLIENT_ID"]
SHAREPOINT_DRIVE_ID = os.environ["ETS_RC1B_SHAREPOINT_DRIVE_ID"]
USERS_INSTANCE_ID = BASE_INSTANCE_ID + ".entra-users"
GROUPS_INSTANCE_ID = BASE_INSTANCE_ID + ".entra-groups"


def request_json(url, token):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
            "User-Agent": "ets-live-microsoft-rc1b-preflight/1.0",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=30.0) as response:
            status = response.status
            content_type = response.headers.get_content_type()
            body = response.read(MAXIMUM_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = exc.code
        content_type = exc.headers.get_content_type()
        body = exc.read(MAXIMUM_RESPONSE_BYTES + 1)
    if len(body) > MAXIMUM_RESPONSE_BYTES:
        raise RuntimeError("Microsoft Graph preflight response exceeded its bound")
    if content_type != "application/json":
        raise RuntimeError("Microsoft Graph preflight response was not JSON")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Microsoft Graph preflight returned invalid JSON") from exc
    return status, payload


def validate_delta_page(collection, status, payload):
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError("Microsoft Graph " + collection + " delta preflight failed")
    if not isinstance(payload.get("value"), list):
        raise RuntimeError("Microsoft Graph " + collection + " delta omitted its value array")
    next_link = payload.get("@odata.nextLink")
    delta_link = payload.get("@odata.deltaLink")
    if (next_link is None) == (delta_link is None):
        raise RuntimeError("Microsoft Graph delta page must expose exactly one continuation")
    continuation = next_link if next_link is not None else delta_link
    if not isinstance(continuation, str):
        raise RuntimeError("Microsoft Graph delta continuation is invalid")
    parsed = urlparse(continuation)
    expected_path = "/v1.0/" + collection + "/delta"
    if (
        parsed.scheme != "https"
        or parsed.hostname != "graph.microsoft.com"
        or parsed.port not in {None, 443}
        or parsed.path != expected_path
        or parsed.fragment
    ):
        raise RuntimeError("Microsoft Graph delta continuation escaped the qualified boundary")


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
    if "$deltatoken=" in lowered or "%24deltatoken=" in lowered:
        return "delta"
    if "$skiptoken=" in lowered or "%24skiptoken=" in lowered:
        return "page"
    return "other"


def read_runtime_rows():
    snapshots = {}
    with connect_ro("connector-runtime.db") as connection:
        for label, instance_id in (
            ("users", USERS_INSTANCE_ID),
            ("groups", GROUPS_INSTANCE_ID),
        ):
            row = connection.execute(
                """
                SELECT checkpoint_json, checkpoint_revision, retry_count,
                       last_success_at_utc, observation_state, gap_open,
                       lease_owner, lease_expires_at_utc
                FROM connector_runtime WHERE instance_id = ?
                """,
                (instance_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("live " + label + " connector runtime row is unavailable")
            snapshots[label] = {
                "checkpoint_present": row["checkpoint_json"] is not None,
                "checkpoint_revision": int(row["checkpoint_revision"]),
                "checkpoint_kind": checkpoint_kind(row["checkpoint_json"]),
                "retry_count": int(row["retry_count"]),
                "last_success_present": row["last_success_at_utc"] is not None,
                "observation_state": str(row["observation_state"]),
                "gap_open": bool(row["gap_open"]),
                "lease_active": row["lease_owner"] is not None,
            }
    return snapshots


def runtime_is_stable(snapshot):
    return all(
        item["checkpoint_present"]
        and item["checkpoint_kind"] == "delta"
        and item["checkpoint_revision"] > 0
        and item["retry_count"] == 0
        and item["last_success_present"]
        and item["observation_state"] == "healthy_observation"
        and not item["gap_open"]
        and not item["lease_active"]
        for item in snapshot.values()
    )


def runtime_failure_code(snapshot):
    if any(item["gap_open"] for item in snapshot.values()):
        return "directory_runtime_collection_gap"
    if any(
        item["retry_count"] > 0
        or item["observation_state"] == "degraded_observation"
        for item in snapshot.values()
    ):
        return "directory_runtime_retry_pending"
    if any(
        item["checkpoint_present"]
        and item["checkpoint_kind"] not in {"delta", "page"}
        for item in snapshot.values()
    ):
        return "directory_runtime_checkpoint_invalid"
    if any(
        not item["checkpoint_present"]
        or item["checkpoint_revision"] < 1
        or item["checkpoint_kind"] == "page"
        or not item["last_success_present"]
        for item in snapshot.values()
    ):
        return "directory_runtime_initialization_incomplete"
    if any(
        item["observation_state"] != "healthy_observation"
        for item in snapshot.values()
    ):
        return "directory_runtime_observation_unhealthy"
    if any(item["lease_active"] for item in snapshot.values()):
        return "directory_runtime_collection_active"
    if not runtime_is_stable(snapshot):
        return "directory_runtime_state_unstable"
    return None


def core_sync_failure_code(snapshot):
    if any(item["terminal_failure"] for item in snapshot.values()):
        return "directory_core_sync_terminal_failure"
    if any(item["retryable_failure"] for item in snapshot.values()):
        return "directory_core_sync_retryable_failure"
    if any(item["pending"] or item["in_flight"] for item in snapshot.values()):
        return "directory_core_sync_backlog"
    if any(item["invalid"] for item in snapshot.values()):
        return "directory_core_sync_state_invalid"
    if not all(item["synchronized"] for item in snapshot.values()):
        return "directory_core_sync_observation_absent"
    return None


FAILURE_CODE = "directory_identity_token_acquisition_failed"
credential = ManagedIdentityCredential(client_id=DIRECTORY_CLIENT_ID)
try:
    access_token = credential.get_token(GRAPH_SCOPE).token
finally:
    credential.close()
if not isinstance(access_token, str) or not access_token:
    raise RuntimeError("directory managed identity returned an empty token")

FAILURE_CODE = "users_delta_request_failed"
users_status, users_payload = request_json(
    GRAPH_ROOT + "/v1.0/users/delta?$select=id&$top=1",
    access_token,
)
FAILURE_CODE = "groups_delta_request_failed"
groups_status, groups_payload = request_json(
    GRAPH_ROOT + "/v1.0/groups/delta?$select=id&$top=1",
    access_token,
)
FAILURE_CODE = "users_delta_validation_failed"
validate_delta_page("users", users_status, users_payload)
FAILURE_CODE = "groups_delta_validation_failed"
validate_delta_page("groups", groups_status, groups_payload)

FAILURE_CODE = "directory_sharepoint_negative_control_request_failed"
drive_status, _ = request_json(
    GRAPH_ROOT
    + "/v1.0/drives/"
    + quote(SHAREPOINT_DRIVE_ID, safe="")
    + "/root?$select=id",
    access_token,
)
FAILURE_CODE = "directory_sharepoint_negative_control_failed"
if drive_status != 403:
    raise RuntimeError("directory identity was not denied access to the SharePoint drive")

FAILURE_CODE = "directory_runtime_state_unavailable"
runtime = None
for _ in range(20):
    runtime = read_runtime_rows()
    if runtime_is_stable(runtime):
        break
    time.sleep(3)
failure_code = (
    "directory_runtime_state_unavailable"
    if runtime is None
    else runtime_failure_code(runtime)
)
if failure_code is not None:
    FAILURE_CODE = failure_code
    raise RuntimeError("live Entra connector runtimes did not reach stable delta state")

FAILURE_CODE = "directory_event_state_incomplete"
event_state = {
    "users": {"observed": False, "removed": False},
    "groups": {"observed": False, "removed": False},
}
with connect_ro("gateway-events.db") as connection:
    rows = connection.execute("SELECT event_json FROM events").fetchall()
    for row in rows:
        try:
            event = json.loads(str(row["event_json"]))
        except json.JSONDecodeError:
            continue
        if event.get("source_system") != "microsoft.entra.directory_delta":
            continue
        metadata = event.get("metadata")
        capture = metadata.get("capture_metadata") if isinstance(metadata, dict) else None
        instance_id = capture.get("connector_instance_id") if isinstance(capture, dict) else None
        claim = (
            capture.get("connector_source_event_type_claim")
            if isinstance(capture, dict)
            else None
        )
        if instance_id == USERS_INSTANCE_ID:
            label = "users"
        elif instance_id == GROUPS_INSTANCE_ID:
            label = "groups"
        else:
            continue
        if claim == "microsoft.entra.directory_object.observed":
            event_state[label]["observed"] = True
        elif claim == "microsoft.entra.directory_object.removed":
            event_state[label]["removed"] = True

if not event_state["users"]["observed"] or not event_state["groups"]["observed"]:
    raise RuntimeError("live Entra connectors have not committed both collection families")

FAILURE_CODE = "directory_core_sync_state_unavailable"
queue_state = {
    "users": {
        "pending": False,
        "in_flight": False,
        "synchronized": False,
        "retryable_failure": False,
        "terminal_failure": False,
        "invalid": False,
    },
    "groups": {
        "pending": False,
        "in_flight": False,
        "synchronized": False,
        "retryable_failure": False,
        "terminal_failure": False,
        "invalid": False,
    },
}
with connect_ro("gateway-sync.db") as connection:
    rows = connection.execute("SELECT payload_json, state FROM sync_queue").fetchall()
    for row in rows:
        try:
            payload = json.loads(str(row["payload_json"]))
        except json.JSONDecodeError:
            continue
        capture = payload.get("capture") if isinstance(payload, dict) else None
        source_id = capture.get("source_id") if isinstance(capture, dict) else None
        state = str(row["state"])
        if source_id == USERS_INSTANCE_ID:
            label = "users"
        elif source_id == GROUPS_INSTANCE_ID:
            label = "groups"
        else:
            continue
        if state in {
            "pending",
            "in_flight",
            "synchronized",
            "retryable_failure",
            "terminal_failure",
        }:
            queue_state[label][state] = True
        else:
            queue_state[label]["invalid"] = True

failure_code = core_sync_failure_code(queue_state)
if failure_code is not None:
    FAILURE_CODE = failure_code
    raise RuntimeError("live Entra Core synchronization is incomplete or unhealthy")

FAILURE_CODE = "directory_drive_fault_matrix_failed"
try:
    fault_matrix = run_rc1b_directory_drive_fault_matrix()
except Exception as exc:
    raise RuntimeError("RC1B directory/drive fault matrix failed") from exc

FAILURE_CODE = "preflight_result_emission_failed"
result = {
    "schema_version": "ets.live_microsoft.rc1b_preflight.v2",
    "directory_identity_token_acquired": True,
    "users_delta_reachable": True,
    "groups_delta_reachable": True,
    "directory_sharepoint_access_denied": True,
    "users_checkpoint_present": runtime["users"]["checkpoint_present"],
    "users_checkpoint_revision": runtime["users"]["checkpoint_revision"],
    "users_checkpoint_kind": runtime["users"]["checkpoint_kind"],
    "users_last_success_present": runtime["users"]["last_success_present"],
    "users_healthy_observation": runtime["users"]["observation_state"] == "healthy_observation",
    "users_gap_open": runtime["users"]["gap_open"],
    "users_event_present": event_state["users"]["observed"],
    "users_removed_event_present": event_state["users"]["removed"],
    "users_core_synchronized": queue_state["users"]["synchronized"],
    "groups_checkpoint_present": runtime["groups"]["checkpoint_present"],
    "groups_checkpoint_revision": runtime["groups"]["checkpoint_revision"],
    "groups_checkpoint_kind": runtime["groups"]["checkpoint_kind"],
    "groups_last_success_present": runtime["groups"]["last_success_present"],
    "groups_healthy_observation": runtime["groups"]["observation_state"] == "healthy_observation",
    "groups_gap_open": runtime["groups"]["gap_open"],
    "groups_event_present": event_state["groups"]["observed"],
    "groups_removed_event_present": event_state["groups"]["removed"],
    "groups_core_synchronized": queue_state["groups"]["synchronized"],
    "raw_directory_payload_retained": False,
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    **fault_matrix,
    "rc1b_live_qualified": True,
    "soak_clock_started": False,
}
raw = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
print(RESULT_MARKER + base64.urlsafe_b64encode(raw).decode("ascii"))
'''

resource preflightJob 'Microsoft.App/jobs@2025-01-01' = {
  name: jobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryPullIdentityResourceId}': {}
      '${directoryIdentityResourceId}': {}
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
      replicaTimeout: 300
      identitySettings: [
        {
          identity: registryPullIdentityResourceId
          lifecycle: 'None'
        }
        {
          identity: directoryIdentityResourceId
          lifecycle: 'Main'
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
          name: 'microsoft-rc1b-preflight'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [probeScript]
          env: [
            {
              name: 'ETS_RC1B_INSTANCE_ID'
              value: connectorInstanceId
            }
            {
              name: 'ETS_RC1B_DIRECTORY_CLIENT_ID'
              value: directoryIdentityClientId
            }
            {
              name: 'ETS_RC1B_SHAREPOINT_DRIVE_ID'
              value: sharePointDriveId
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

output preflightJobName string = preflightJob.name
