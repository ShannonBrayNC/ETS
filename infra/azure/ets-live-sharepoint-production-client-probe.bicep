@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral production-client probe job name.')
@minLength(2)
@maxLength(32)
param jobName string

@description('Existing live Container Apps managed environment resource ID.')
@minLength(1)
param managedEnvironmentResourceId string

@description('Exact Gateway runtime managed identity resource ID.')
@minLength(1)
param runtimeIdentityResourceId string

@secure()
@description('Client ID of the exact Gateway runtime managed identity.')
@minLength(1)
param runtimeIdentityClientId string

@description('Dedicated pull-only identity for the approved private image.')
@minLength(1)
param registryPullIdentityResourceId string

@description('Approved private ACR login server.')
@minLength(1)
param registryServer string

@description('Exact image currently deployed to the Gateway.')
@minLength(1)
param containerImage string

@secure()
@description('Approved EchoMedia SharePoint Documents drive identifier.')
@minLength(1)
param sharePointDriveId string

var probeScript = '''
import base64
import json
import os
from urllib.parse import quote, urlsplit

from azure.identity import ManagedIdentityCredential

from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaRequestProfile,
)
from ets.connectors.enterprise.microsoft_sharepoint_http import (
    MicrosoftSharePointDeltaAuthenticationError,
    MicrosoftSharePointDeltaAuthorizationError,
    MicrosoftSharePointDeltaClientError,
    MicrosoftSharePointDeltaHttpClient,
    MicrosoftSharePointDeltaRedirectError,
    MicrosoftSharePointDeltaResponseTooLargeError,
    MicrosoftSharePointDeltaRetryableError,
    MicrosoftSharePointDeltaStateExpiredError,
    MicrosoftSharePointDeltaTerminalError,
    MicrosoftSharePointDeltaThrottleError,
)

MARKER = "ETS_SP_PRODUCTION_CLIENT_PROBE_B64="
GRAPH_ROOT = "https://graph.microsoft.com"
GRAPH_SCOPE = GRAPH_ROOT + "/.default"


def parser_class(exc):
    cause = exc.__cause__
    if cause is None:
        return "none"
    text = str(cause)
    rules = (
        ("exactly one nextLink or deltaLink", "continuation_cardinality"),
        ("continuation escaped", "continuation_path"),
        ("continuation must be a string", "continuation_type"),
        ("response value must be an array", "value_shape"),
        ("array contains a non-object", "record_shape"),
        ("delta id is invalid", "record_id"),
        ("parentReference must be an object", "parent_reference"),
        ("file facet must be an object", "file_facet"),
        ("folder facet must be an object", "folder_facet"),
        ("package facet must be an object", "package_facet"),
        ("contentType must be an object", "content_type_facet"),
        ("shared facet must be an object", "shared_facet"),
        ("shared facet scope is invalid", "shared_scope"),
        ("sharedChanged annotation is invalid", "shared_changed"),
        ("not valid UTF-8 JSON", "json_decode"),
        ("response must be an object", "response_shape"),
        ("exceeds configured record bound", "record_bound"),
        ("exceeds configured byte bound", "byte_bound"),
    )
    for needle, code in rules:
        if needle in text:
            return code
    if isinstance(cause, ValueError):
        return "qualified_parser_other"
    return "non_parser"


client_id = os.environ["ETS_SP_RUNTIME_CLIENT_ID"]
drive_id = os.environ["ETS_SP_DRIVE_ID"]
resource_path = "/v1.0/drives/" + quote(drive_id, safe="") + "/root/delta"
profile = MicrosoftSharePointDeltaRequestProfile(
    tenant_profile_id="live-production-client-probe",
    cloud="global",
    graph_root=GRAPH_ROOT,
    scope="drive",
    resource_path=resource_path,
    initial_url=GRAPH_ROOT + resource_path,
)

credential = ManagedIdentityCredential(client_id=client_id)
try:
    graph_token = credential.get_token(GRAPH_SCOPE).token
finally:
    credential.close()

outcome = "unknown"
parser_failure_class = "none"
record_count = -1
cycle_complete = False
checkpoint_shape = "none"
client = MicrosoftSharePointDeltaHttpClient(
    profile,
    graph_token.encode("ascii"),
    timeout_seconds=30.0,
    maximum_response_bytes=1024 * 1024,
)
try:
    page = client.fetch()
    outcome = "ok"
    record_count = len(page.records)
    cycle_complete = page.cycle_complete
    parsed = urlsplit(page.checkpoint_url)
    if parsed.path == resource_path and parsed.query:
        checkpoint_shape = "query"
    elif parsed.path.startswith(resource_path + "("):
        checkpoint_shape = "function"
    elif parsed.path == resource_path:
        checkpoint_shape = "bare"
    else:
        checkpoint_shape = "other"
except MicrosoftSharePointDeltaAuthenticationError:
    outcome = "authentication_failed"
except MicrosoftSharePointDeltaAuthorizationError:
    outcome = "authorization_failed"
except MicrosoftSharePointDeltaThrottleError:
    outcome = "throttled"
except MicrosoftSharePointDeltaStateExpiredError:
    outcome = "state_expired"
except MicrosoftSharePointDeltaRedirectError:
    outcome = "redirect_error"
except MicrosoftSharePointDeltaResponseTooLargeError:
    outcome = "response_too_large"
except MicrosoftSharePointDeltaRetryableError:
    outcome = "retryable_error"
except MicrosoftSharePointDeltaTerminalError as exc:
    outcome = "terminal_error"
    parser_failure_class = parser_class(exc)
except MicrosoftSharePointDeltaClientError:
    outcome = "client_error"
finally:
    client.close()

result = {
    "schema_version": "ets.live_sharepoint.production_client_probe.v1",
    "production_client_outcome": outcome,
    "parser_failure_class": parser_failure_class,
    "record_count": record_count,
    "cycle_complete": cycle_complete,
    "checkpoint_shape": checkpoint_shape,
    "customer_identifiers_retained": False,
    "graph_payload_retained": False,
    "continuation_url_retained": False,
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
      replicaTimeout: 180
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
          name: 'sharepoint-production-client-probe'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [probeScript]
          env: [
            {
              name: 'ETS_SP_RUNTIME_CLIENT_ID'
              value: runtimeIdentityClientId
            }
            {
              name: 'ETS_SP_DRIVE_ID'
              value: sharePointDriveId
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

output probeJobName string = probeJob.name
