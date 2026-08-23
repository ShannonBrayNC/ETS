@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral RC1C preflight job name.')
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

@description('Purview-only runtime identity attached to the live Gateway.')
@minLength(1)
param purviewIdentityResourceId string

@description('Client ID of the Purview-only runtime identity.')
@minLength(1)
param purviewIdentityClientId string

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
@description('Deployment-authoritative Microsoft tenant identifier.')
@minLength(36)
@maxLength(36)
param microsoftTenantId string

var probeScript = '''
import base64
import json
import os
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from azure.identity import ManagedIdentityCredential

MANAGEMENT_ROOT = "https://manage.office.com"
MANAGEMENT_SCOPE = MANAGEMENT_ROOT + "/.default"
MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024
RESULT_MARKER = "ETS_M365_RC1C_PREFLIGHT_B64="
STATE_DIR = Path("/mnt/gateway-state")
BASE_INSTANCE_ID = os.environ["ETS_RC1C_INSTANCE_ID"]
PURVIEW_INSTANCE_ID = BASE_INSTANCE_ID + ".purview-audit-general"
PURVIEW_CLIENT_ID = os.environ["ETS_RC1C_PURVIEW_CLIENT_ID"]
MICROSOFT_TENANT_ID = os.environ["ETS_RC1C_MICROSOFT_TENANT_ID"]


def decode_claims(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise RuntimeError("Purview managed-identity token is not a JWT")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Purview managed-identity token claims are invalid") from exc
    if not isinstance(claims, dict):
        raise RuntimeError("Purview managed-identity token claims are not an object")
    return claims


def request_json(url, token):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
            "User-Agent": "ets-live-microsoft-rc1c-preflight/1.0",
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
        raise RuntimeError("Purview preflight response exceeded its bound")
    if content_type != "application/json":
        raise RuntimeError("Purview preflight response was not JSON")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Purview preflight returned invalid JSON") from exc
    return status, payload


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


def validate_instance_and_runtime():
    with connect_ro("connector-runtime.db") as connection:
        row = connection.execute(
            """
            SELECT i.payload_json, r.checkpoint_json, r.checkpoint_revision,
                   r.retry_count, r.last_success_at_utc, r.observation_state,
                   r.gap_open, r.lease_owner
            FROM connector_instances i
            JOIN connector_runtime r ON r.instance_id = i.instance_id
            WHERE i.instance_id = ?
            """,
            (PURVIEW_INSTANCE_ID,),
        ).fetchone()
    if row is None:
        raise RuntimeError("live Purview connector instance is unavailable")
    try:
        instance = json.loads(str(row["payload_json"]))
    except json.JSONDecodeError as exc:
        raise RuntimeError("live Purview connector instance is invalid") from exc
    if not isinstance(instance, dict):
        raise RuntimeError("live Purview connector instance is not an object")
    authentication = instance.get("authentication")
    settings = instance.get("settings")
    if (
        instance.get("connector_id") != "microsoft.purview.activity"
        or not isinstance(authentication, dict)
        or authentication.get("credential_ref")
        != "azure-mi://office-365-management/purview"
        or not isinstance(settings, dict)
        or settings.get("content_type") != "Audit.General"
        or settings.get("include_client_ip") is not False
        or settings.get("service_specific_allowlist") != []
    ):
        raise RuntimeError("live Purview connector escaped the bounded P0 profile")
    return {
        "checkpoint_present": row["checkpoint_json"] is not None,
        "checkpoint_revision": int(row["checkpoint_revision"]),
        "retry_count": int(row["retry_count"]),
        "last_success_present": row["last_success_at_utc"] is not None,
        "healthy_observation": str(row["observation_state"]) == "healthy_observation",
        "gap_open": bool(row["gap_open"]),
        "lease_active": row["lease_owner"] is not None,
    }


def assert_no_durable_graph_subscription():
    path = STATE_DIR / "microsoft-graph-subscriptions.db"
    if not path.exists():
        return
    with connect_ro("microsoft-graph-subscriptions.db") as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'graph_subscriptions'"
        ).fetchone()
        if table is None:
            raise RuntimeError("durable Graph state database has an unexpected schema")
        count = connection.execute("SELECT COUNT(*) FROM graph_subscriptions").fetchone()[0]
    if int(count) != 0:
        raise RuntimeError("durable Graph subscription state exists before callback authorization")


credential = ManagedIdentityCredential(client_id=PURVIEW_CLIENT_ID)
try:
    access_token = credential.get_token(MANAGEMENT_SCOPE).token
finally:
    credential.close()
if not isinstance(access_token, str) or not access_token:
    raise RuntimeError("Purview managed identity returned an empty token")

claims = decode_claims(access_token)
if claims.get("aud") != MANAGEMENT_ROOT:
    raise RuntimeError("Purview token audience escaped the Office 365 Management boundary")
if str(claims.get("tid") or "").casefold() != MICROSOFT_TENANT_ID.casefold():
    raise RuntimeError("Purview token tenant differs from deployment configuration")
application_claim = claims.get("appid") or claims.get("azp")
if str(application_claim or "").casefold() != PURVIEW_CLIENT_ID.casefold():
    raise RuntimeError("Purview token application differs from the dedicated UAMI")
roles = claims.get("roles")
if not isinstance(roles, list) or roles != ["ActivityFeed.Read"]:
    raise RuntimeError("Purview token roles differ from the exact ActivityFeed.Read allowlist")
if "scp" in claims:
    raise RuntimeError("Purview token unexpectedly contains delegated scopes")

query = urlencode({"PublisherIdentifier": MICROSOFT_TENANT_ID})
subscriptions_url = (
    MANAGEMENT_ROOT
    + "/api/v1.0/"
    + MICROSOFT_TENANT_ID
    + "/activity/feed/subscriptions/list?"
    + query
)
status, subscriptions = request_json(subscriptions_url, access_token)
if status != 200 or not isinstance(subscriptions, list):
    raise RuntimeError("Purview subscription-list preflight failed")
if len(subscriptions) > 16:
    raise RuntimeError("Purview subscription-list response exceeded its item bound")

audit_general = None
seen_content_types = set()
for item in subscriptions:
    if not isinstance(item, dict):
        raise RuntimeError("Purview subscription-list item is not an object")
    if set(item) - {"contentType", "status", "webhook"}:
        raise RuntimeError("Purview subscription-list item exposed an unexpected field")
    content_type = item.get("contentType")
    if not isinstance(content_type, str) or not content_type:
        raise RuntimeError("Purview subscription-list item omitted contentType")
    if content_type in seen_content_types:
        raise RuntimeError("Purview subscription-list contains a duplicate content type")
    seen_content_types.add(content_type)
    if content_type != "Audit.General":
        raise RuntimeError("dedicated Purview identity has an out-of-profile subscription")
    state = item.get("status")
    if state not in {"enabled", "disabled"}:
        raise RuntimeError("Purview Audit.General subscription status is invalid")
    if item.get("webhook") is not None:
        raise RuntimeError("Purview polling preflight found an unapproved webhook")
    audit_general = item

runtime = validate_instance_and_runtime()
assert_no_durable_graph_subscription()
subscription_status = "absent" if audit_general is None else str(audit_general["status"])

result = {
    "schema_version": "ets.live_microsoft.rc1c_preflight.v1",
    "purview_identity_token_acquired": True,
    "purview_token_audience_exact": True,
    "purview_token_tenant_exact": True,
    "purview_token_application_exact": True,
    "purview_token_roles_exact": True,
    "purview_subscriptions_list_reachable": True,
    "purview_subscription_present": audit_general is not None,
    "purview_subscription_status": subscription_status,
    "purview_webhook_configured": False,
    "purview_instance_present": True,
    "purview_checkpoint_present": runtime["checkpoint_present"],
    "purview_checkpoint_revision": runtime["checkpoint_revision"],
    "purview_retry_count": runtime["retry_count"],
    "purview_last_success_present": runtime["last_success_present"],
    "purview_healthy_observation": runtime["healthy_observation"],
    "purview_gap_open": runtime["gap_open"],
    "purview_lease_active": runtime["lease_active"],
    "graph_durable_subscription_present": False,
    "raw_purview_payload_retained": False,
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
    "rc1c_live_qualified": False,
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
      '${purviewIdentityResourceId}': {}
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
          identity: purviewIdentityResourceId
          lifecycle: 'Main'
        }
      ]
      secrets: [
        {
          name: 'microsoft-tenant-id'
          value: microsoftTenantId
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
          name: 'microsoft-rc1c-preflight'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [probeScript]
          env: [
            {
              name: 'ETS_RC1C_INSTANCE_ID'
              value: connectorInstanceId
            }
            {
              name: 'ETS_RC1C_PURVIEW_CLIENT_ID'
              value: purviewIdentityClientId
            }
            {
              name: 'ETS_RC1C_MICROSOFT_TENANT_ID'
              secretRef: 'microsoft-tenant-id'
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
