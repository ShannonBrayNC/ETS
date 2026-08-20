@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral HTTP probe job name.')
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
@description('Internal ETS Core HTTPS base URL.')
@minLength(1)
param coreBaseUrl string

@secure()
@description('Entra Core resource scope ending in /.default.')
@minLength(1)
param coreScope string

@secure()
@description('Approved EchoMedia SharePoint Documents drive identifier.')
@minLength(1)
param sharePointDriveId string

@description('Synthetic qualification marker used only to form the bounded test filename.')
@minLength(6)
@maxLength(32)
param marker string

var probeScript = '''
import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from azure.identity import ManagedIdentityCredential

MARKER = "ETS_SP_HTTP_PROBE_B64="
GRAPH_SCOPE = "https://graph.microsoft.com/.default"


def status(url, token):
    req = Request(
        url,
        headers={"Accept": "application/json", "Authorization": "Bearer " + token},
        method="GET",
    )
    try:
        with urlopen(req, timeout=20.0) as response:
            response.read()
            return response.status
    except HTTPError as exc:
        exc.read()
        return exc.code
    except (TimeoutError, URLError):
        return -1


client_id = os.environ["ETS_SP_RUNTIME_CLIENT_ID"]
drive_id = os.environ["ETS_SP_DRIVE_ID"]
core_base = os.environ["ETS_SP_CORE_BASE_URL"].rstrip("/")
core_scope = os.environ["ETS_SP_CORE_SCOPE"]
marker = os.environ["ETS_SP_MARKER"]
file_name = "ets-live-qualification-" + marker + ".txt"

credential = ManagedIdentityCredential(client_id=client_id)
try:
    graph_token = credential.get_token(GRAPH_SCOPE).token
    core_token = credential.get_token(core_scope).token
finally:
    credential.close()

item_url = (
    "https://graph.microsoft.com/v1.0/drives/"
    + quote(drive_id, safe="")
    + "/root:/"
    + quote(file_name, safe="")
    + "?$select=id,name,eTag,file"
)

result = {
    "schema_version": "ets.live_sharepoint.http_probe.v1",
    "graph_item_status": status(item_url, graph_token),
    "graph_root_scope_status": status(
        "https://graph.microsoft.com/v1.0/sites/root?$select=id", graph_token
    ),
    "core_events_status": status(
        core_base + "/api/v1/events?limit=1&offset=0", core_token
    ),
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
          name: 'sharepoint-http-probe'
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
            {
              name: 'ETS_SP_CORE_BASE_URL'
              value: coreBaseUrl
            }
            {
              name: 'ETS_SP_CORE_SCOPE'
              value: coreScope
            }
            {
              name: 'ETS_SP_MARKER'
              value: marker
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
