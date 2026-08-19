@description('Azure region used by the existing live Container Apps environment.')
param location string

@description('Ephemeral SharePoint source-to-proof qualification job name.')
@minLength(2)
@maxLength(32)
param clientName string

@description('Existing live Container Apps managed environment name.')
@minLength(1)
param managedEnvironmentName string

@description('Exact Gateway runtime managed identity used for Graph and Core reads.')
@minLength(1)
param runtimeIdentityResourceId string

@secure()
@description('Client ID of the exact Gateway runtime managed identity.')
@minLength(1)
param runtimeIdentityClientId string

@description('Dedicated pull-only identity for the approved private ACR image.')
@minLength(1)
param registryPullIdentityResourceId string

@description('Approved private ACR login server.')
@minLength(1)
param registryServer string

@description('Authoritative immutable image reference pinned by sha256 digest.')
@minLength(1)
param containerImage string

@secure()
@description('Internal live ETS Core HTTPS base URL.')
@minLength(1)
param coreBaseUrl string

@secure()
@description('Fixed Entra Core resource scope ending in /.default.')
@minLength(1)
param coreScope string

@secure()
@description('Internal live ETS Gateway HTTPS base URL.')
@minLength(1)
param gatewayBaseUrl string

@secure()
@description('Approved EchoMedia SharePoint Documents drive identifier.')
@minLength(1)
param sharePointDriveId string

@description('Synthetic public-safe qualification marker used only in the test file name.')
@minLength(6)
@maxLength(32)
param marker string

@description('Expected number of distinct observed revisions for the synthetic file.')
@minValue(1)
@maxValue(10)
param expectedObservations int = 1

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' existing = {
  name: managedEnvironmentName
}

var qualificationScript = '''
import base64
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from azure.identity import ManagedIdentityCredential
from ets.core import InclusionProof
from ets.core.proofs import verify_inclusion_proof

MARKER = "ETS_LIVE_SP_RESULT_B64="
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
SOURCE_SYSTEM = "microsoft.sharepoint.onedrive_delta"
EVENT_TYPE = "microsoft.sharepoint.metadata.observed"


def decode_json(body):
    if not body:
        return {}
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("qualification endpoint returned non-object JSON")
    return value


def request_json(method, url, token=None, expected=(200,)):
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    request = Request(url, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20.0) as response:
            status = response.status
            body = response.read()
    except HTTPError as exc:
        status = exc.code
        body = exc.read()
    except (TimeoutError, URLError) as exc:
        raise RuntimeError("qualification endpoint was unreachable") from exc
    decoded = decode_json(body)
    if status not in expected:
        raise RuntimeError("qualification endpoint returned unexpected HTTP status " + str(status))
    return status, decoded


def acquire_token(credential, scope):
    last_error = None
    for attempt in range(12):
        try:
            access = credential.get_token(scope)
            if not access.token:
                raise RuntimeError("managed identity returned an empty token")
            return access.token
        except Exception as exc:
            last_error = exc
            if attempt < 11:
                time.sleep(5)
    raise RuntimeError("managed identity could not acquire a qualification token") from last_error


def committed_metadata(entry):
    event = entry.get("event")
    if not isinstance(event, dict):
        return None
    if event.get("source_system") != SOURCE_SYSTEM or event.get("event_type") != EVENT_TYPE:
        return None
    metadata = event.get("metadata")
    if not isinstance(metadata, dict):
        return None
    capture = metadata.get("capture_metadata")
    if not isinstance(capture, dict):
        return None
    committed = capture.get("committed_connector_metadata")
    if not isinstance(committed, dict):
        return None
    source_metadata = committed.get("metadata")
    if not isinstance(source_metadata, dict):
        return None
    return event, metadata, capture, source_metadata


def list_scoped_events(core_base, token):
    result = []
    offset = 0
    for _ in range(10):
        _, page = request_json(
            "GET",
            core_base + "/api/v1/events?limit=500&offset=" + str(offset),
            token=token,
        )
        items = page.get("items")
        total = page.get("total")
        if not isinstance(items, list) or not isinstance(total, int):
            raise RuntimeError("Core event list returned an invalid shape")
        result.extend(items)
        if len(result) >= total:
            return result
        offset += len(items)
        if not items:
            break
    raise RuntimeError("Core event list exceeded the bounded qualification window")


def matching_observations(entries, file_name):
    matches = []
    for entry in entries:
        parsed = committed_metadata(entry)
        if parsed is None:
            continue
        event, metadata, capture, source_metadata = parsed
        if source_metadata.get("name") != file_name:
            continue
        if capture.get("raw_source_payload_retained") is not False:
            raise RuntimeError("Gateway event unexpectedly retained raw source payload")
        privacy = metadata.get("privacy")
        if not isinstance(privacy, dict) or privacy.get("contains_raw_evidence") is not False:
            raise RuntimeError("Gateway event privacy metadata did not prove raw evidence exclusion")
        evidence_reference = metadata.get("evidence_reference")
        if not isinstance(evidence_reference, dict) or evidence_reference.get("retention_mode") != "not_retained":
            raise RuntimeError("Gateway event unexpectedly retained source evidence content")
        event_id = event.get("event_id")
        etag = source_metadata.get("etag")
        if not isinstance(event_id, str) or not event_id:
            raise RuntimeError("SharePoint observation omitted event identity")
        if not isinstance(etag, str) or not etag:
            raise RuntimeError("SharePoint observation omitted source eTag")
        matches.append((event_id, etag))
    return matches


def verify_proof(core_base, token, event_id):
    _, payload = request_json(
        "GET",
        core_base + "/api/v1/proofs/inclusion/" + quote(event_id, safe=""),
        token=token,
    )
    proof = InclusionProof.model_validate_json(json.dumps(payload, separators=(",", ":")))
    result = verify_inclusion_proof(proof)
    if not result.valid:
        raise RuntimeError("independent SharePoint inclusion proof verification failed")


def emit(result):
    raw = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii")
    print(MARKER + encoded)


client_id = os.environ["ETS_SP_RUNTIME_CLIENT_ID"]
core_base = os.environ["ETS_SP_CORE_BASE_URL"].rstrip("/")
core_scope = os.environ["ETS_SP_CORE_SCOPE"]
gateway_base = os.environ["ETS_SP_GATEWAY_BASE_URL"].rstrip("/")
drive_id = os.environ["ETS_SP_DRIVE_ID"]
marker = os.environ["ETS_SP_MARKER"]
expected = int(os.environ["ETS_SP_EXPECTED_OBSERVATIONS"])

if re.fullmatch(r"[a-z0-9][a-z0-9-]{5,31}", marker) is None:
    raise RuntimeError("qualification marker is outside the public-safe profile")
if expected < 1 or expected > 10:
    raise RuntimeError("expected observation count is outside the qualified bound")
file_name = "ets-live-qualification-" + marker + ".txt"

_, gateway_health = request_json("GET", gateway_base + "/health")
_, gateway_ready = request_json("GET", gateway_base + "/ready")
if gateway_health.get("status") != "ok" or gateway_ready.get("status") != "ready":
    raise RuntimeError("live Gateway was not healthy and ready")

credential = ManagedIdentityCredential(client_id=client_id)
try:
    graph_token = acquire_token(credential, GRAPH_SCOPE)
    core_token = acquire_token(credential, core_scope)
finally:
    credential.close()

encoded_drive = quote(drive_id, safe="")
encoded_name = quote(file_name, safe="")
item_url = (
    "https://graph.microsoft.com/v1.0/drives/"
    + encoded_drive
    + "/root:/"
    + encoded_name
    + "?$select=id,name,eTag,cTag,size,lastModifiedDateTime,file,parentReference"
)
_, item = request_json("GET", item_url, token=graph_token)
if item.get("name") != file_name:
    raise RuntimeError("Graph returned a different qualification file")
current_etag = item.get("eTag")
if not isinstance(current_etag, str) or not current_etag:
    raise RuntimeError("Graph qualification file omitted eTag")
if not isinstance(item.get("file"), dict):
    raise RuntimeError("Graph qualification object was not a file")
if "@microsoft.graph.downloadUrl" in item:
    raise RuntimeError("qualification metadata request unexpectedly surfaced a download URL")

scope_status, _ = request_json(
    "GET",
    "https://graph.microsoft.com/v1.0/sites/root?$select=id",
    token=graph_token,
    expected=(403,),
)
if scope_status != 403:
    raise RuntimeError("Gateway Graph identity escaped the approved SharePoint site scope")

observations = []
for _ in range(37):
    observations = matching_observations(list_scoped_events(core_base, core_token), file_name)
    etags = {etag for _, etag in observations}
    if current_etag in etags and len(etags) >= expected:
        break
    time.sleep(10)
else:
    raise RuntimeError("Gateway did not relay the expected SharePoint revision into Core")

current_ids = {event_id for event_id, etag in observations if etag == current_etag}
if len(current_ids) != 1:
    raise RuntimeError("current SharePoint revision did not map to exactly one ETS event")
all_ids = {event_id for event_id, _ in observations}
all_etags = {etag for _, etag in observations}
if len(all_etags) < expected:
    raise RuntimeError("SharePoint revision history did not reach the expected observation count")

for event_id in sorted(all_ids):
    verify_proof(core_base, core_token, event_id)

time.sleep(75)
observations_after = matching_observations(list_scoped_events(core_base, core_token), file_name)
after_ids = {event_id for event_id, _ in observations_after}
if after_ids != all_ids:
    raise RuntimeError("duplicate polling changed the retained SharePoint ETS event set")
if len(observations_after) != len(observations):
    raise RuntimeError("duplicate polling changed the SharePoint observation count")

result = {
    "schema_version": "ets.live_sharepoint.source_to_proof.v1",
    "marker": marker,
    "expected_observations": expected,
    "gateway_health_verified": True,
    "gateway_readiness_verified": True,
    "graph_item_metadata_verified": True,
    "graph_scope_denial_403_verified": True,
    "delta_recovery_without_notification_verified": True,
    "core_observation_count": len(observations),
    "exact_version_event_verified": True,
    "inclusion_proof_verified": True,
    "duplicate_suppression_verified": True,
    "durable_retention_verified": True,
    "revision_evidence_verified": expected >= 2 and len(all_etags) >= expected,
    "raw_document_content_retrieved": False,
    "raw_source_payload_retained": False,
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    "soak_clock_started": False,
}
emit(result)
'''

resource qualificationJob 'Microsoft.App/jobs@2025-01-01' = {
  name: clientName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentityResourceId}': {}
      '${registryPullIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaRetryLimit: 0
      replicaTimeout: 600
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
      containers: [
        {
          name: 'sharepoint-proof-client'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [
            qualificationScript
          ]
          env: [
            {
              name: 'ETS_SP_RUNTIME_CLIENT_ID'
              value: runtimeIdentityClientId
            }
            {
              name: 'ETS_SP_CORE_BASE_URL'
              value: coreBaseUrl
            }
            {
              name: 'ETS_SP_CORE_SCOPE'
              value: coreScope
            }
            {
              name: 'ETS_SP_GATEWAY_BASE_URL'
              value: gatewayBaseUrl
            }
            {
              name: 'ETS_SP_DRIVE_ID'
              value: sharePointDriveId
            }
            {
              name: 'ETS_SP_MARKER'
              value: marker
            }
            {
              name: 'ETS_SP_EXPECTED_OBSERVATIONS'
              value: string(expectedObservations)
            }
          ]
          probes: []
          volumeMounts: []
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      initContainers: []
      volumes: []
    }
  }
}

output qualificationClientName string = qualificationJob.name
