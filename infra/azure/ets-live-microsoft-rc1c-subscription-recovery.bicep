@description('Azure region used by the live Container Apps environment.')
param location string

@description('Ephemeral RC1C subscription recovery job name.')
@minLength(2)
@maxLength(32)
param jobName string

@description('Existing live Container Apps managed environment resource ID.')
@minLength(1)
param managedEnvironmentResourceId string

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

@secure()
@description('Deployment-authoritative Microsoft tenant identifier.')
@minLength(36)
@maxLength(36)
param microsoftTenantId string

@description('Prior protected failure run proving restoration to enabled, or 0 for a first attempt.')
@minLength(1)
@maxLength(20)
param restoredFailureWorkflowRunId string = '0'

var recoveryScript = '''
import base64
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from azure.identity import ManagedIdentityCredential

MANAGEMENT_ROOT = "https://manage.office.com"
MANAGEMENT_SCOPE = MANAGEMENT_ROOT + "/.default"
CONTENT_TYPE = "Audit.General"
MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024
MAXIMUM_SUBSCRIPTIONS = 16
MAXIMUM_CONTENT_DESCRIPTORS = 5000
SUCCESS_MARKER = "ETS_M365_RC1C_SUBSCRIPTION_RECOVERY_B64="
FAILURE_MARKER = "ETS_M365_RC1C_SUBSCRIPTION_RECOVERY_FAILURE_B64="
PURVIEW_CLIENT_ID = os.environ["ETS_RC1C_PURVIEW_CLIENT_ID"]
MICROSOFT_TENANT_ID = os.environ["ETS_RC1C_MICROSOFT_TENANT_ID"]
RESTORED_FAILURE_WORKFLOW_RUN_ID = os.environ[
    "ETS_RC1C_RESTORED_FAILURE_WORKFLOW_RUN_ID"
]


class QualificationFailure(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise QualificationFailure("credential_redirect_rejected")


def emit(marker, payload):
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    print(marker + base64.urlsafe_b64encode(raw).decode("ascii"), flush=True)


def decode_claims(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise QualificationFailure("token_not_jwt")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationFailure("token_claims_invalid") from exc
    if not isinstance(claims, dict):
        raise QualificationFailure("token_claims_invalid")
    return claims


def retry_after_seconds(headers):
    raw = headers.get("Retry-After") if headers is not None else None
    try:
        value = int(raw) if raw is not None else 1
    except ValueError:
        value = 1
    return max(1, min(value, 8))


opener = build_opener(RejectRedirects())
api_retry_count = 0


def request(
    method,
    operation,
    token,
    *,
    content_type=False,
    expect_json=True,
    expected_statuses=(200,),
):
    global api_retry_count
    query = {"PublisherIdentifier": MICROSOFT_TENANT_ID}
    if content_type:
        query["contentType"] = CONTENT_TYPE
    url = (
        MANAGEMENT_ROOT
        + "/api/v1.0/"
        + MICROSOFT_TENANT_ID
        + "/activity/feed/"
        + operation
        + "?"
        + urlencode(query)
    )
    for attempt in range(3):
        req = Request(
            url,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + token,
                "User-Agent": "ets-live-microsoft-rc1c-subscription-recovery/1.0",
            },
        )
        try:
            with opener.open(req, timeout=30.0) as response:
                status = response.status
                content_type_header = response.headers.get_content_type()
                body = response.read(MAXIMUM_RESPONSE_BYTES + 1)
        except QualificationFailure:
            raise
        except HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                api_retry_count += 1
                time.sleep(retry_after_seconds(exc.headers))
                continue
            if exc.code == 401:
                raise QualificationFailure("purview_authentication_failure") from exc
            if exc.code == 403:
                raise QualificationFailure("purview_authorization_failure") from exc
            if exc.code == 429:
                raise QualificationFailure("purview_throttle_exhausted") from exc
            if 500 <= exc.code <= 599:
                raise QualificationFailure("purview_retryable_failure_exhausted") from exc
            raise QualificationFailure("purview_terminal_http_failure") from exc
        except (TimeoutError, URLError, OSError) as exc:
            if attempt < 2:
                api_retry_count += 1
                time.sleep(1)
                continue
            raise QualificationFailure("purview_transport_failure") from exc
        if status not in expected_statuses:
            operation_code = operation.replace("/", "_")
            raise QualificationFailure(
                "purview_" + operation_code + "_unexpected_http_status"
            )
        if len(body) > MAXIMUM_RESPONSE_BYTES:
            raise QualificationFailure("purview_response_too_large")
        if not expect_json:
            if body:
                raise QualificationFailure("purview_stop_response_not_empty")
            return None
        if content_type_header != "application/json":
            raise QualificationFailure("purview_response_not_json")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise QualificationFailure("purview_response_invalid_json") from exc
    raise QualificationFailure("purview_retry_bound_exhausted")


def list_audit_general(token):
    payload = request("GET", "subscriptions/list", token)
    if not isinstance(payload, list) or len(payload) > MAXIMUM_SUBSCRIPTIONS:
        raise QualificationFailure("subscription_list_shape_invalid")
    audit_general = None
    seen = set()
    for item in payload:
        if not isinstance(item, dict) or set(item) - {"contentType", "status", "webhook"}:
            raise QualificationFailure("subscription_item_shape_invalid")
        item_type = item.get("contentType")
        if not isinstance(item_type, str) or not item_type or item_type in seen:
            raise QualificationFailure("subscription_content_type_invalid")
        seen.add(item_type)
        if item_type != CONTENT_TYPE:
            raise QualificationFailure("out_of_profile_subscription_present")
        if item.get("status") not in {"enabled", "disabled"}:
            raise QualificationFailure("subscription_status_invalid")
        if item.get("webhook") is not None:
            raise QualificationFailure("webhook_configuration_present")
        audit_general = item
    if audit_general is None:
        return "absent"
    return str(audit_general["status"])


def start_subscription(token):
    payload = request("POST", "subscriptions/start", token, content_type=True)
    if not isinstance(payload, dict) or set(payload) - {"contentType", "status", "webhook"}:
        raise QualificationFailure("start_response_shape_invalid")
    if payload.get("contentType") != CONTENT_TYPE or payload.get("status") != "enabled":
        raise QualificationFailure("start_response_not_enabled")
    if payload.get("webhook") is not None:
        raise QualificationFailure("start_created_webhook")


def stop_subscription(token):
    request(
        "POST",
        "subscriptions/stop",
        token,
        content_type=True,
        expect_json=False,
        expected_statuses=(200, 204),
    )


def list_content_count(token):
    payload = request("GET", "subscriptions/content", token, content_type=True)
    if not isinstance(payload, list) or len(payload) > MAXIMUM_CONTENT_DESCRIPTORS:
        raise QualificationFailure("content_list_shape_invalid")
    for item in payload:
        if not isinstance(item, dict):
            raise QualificationFailure("content_descriptor_shape_invalid")
        if item.get("contentType") != CONTENT_TYPE:
            raise QualificationFailure("content_descriptor_type_invalid")
    return len(payload)


mutated = False
recovery_attempted = False
recovery_restored = False
final_state = "unknown"
failure_code = None
access_token = None
credential = ManagedIdentityCredential(client_id=PURVIEW_CLIENT_ID)
try:
    access_token = credential.get_token(MANAGEMENT_SCOPE).token
    if not isinstance(access_token, str) or not access_token:
        raise QualificationFailure("token_empty")
    claims = decode_claims(access_token)
    if claims.get("aud") != MANAGEMENT_ROOT:
        raise QualificationFailure("token_audience_mismatch")
    if str(claims.get("tid") or "").casefold() != MICROSOFT_TENANT_ID.casefold():
        raise QualificationFailure("token_tenant_mismatch")
    application_claim = claims.get("appid") or claims.get("azp")
    if str(application_claim or "").casefold() != PURVIEW_CLIENT_ID.casefold():
        raise QualificationFailure("token_application_mismatch")
    if claims.get("roles") != ["ActivityFeed.Read"] or "scp" in claims:
        raise QualificationFailure("token_permission_mismatch")

    initial_state = list_audit_general(access_token)
    if initial_state not in {"absent", "enabled"}:
        raise QualificationFailure("initial_subscription_not_recoverable")
    if initial_state == "enabled" and RESTORED_FAILURE_WORKFLOW_RUN_ID == "0":
        raise QualificationFailure("enabled_resume_evidence_missing")
    if initial_state == "absent" and RESTORED_FAILURE_WORKFLOW_RUN_ID != "0":
        raise QualificationFailure("restored_failure_state_not_enabled")

    mutated = True
    start_subscription(access_token)
    if list_audit_general(access_token) != "enabled":
        raise QualificationFailure("initial_start_not_observed_enabled")
    content_count = list_content_count(access_token)

    stop_subscription(access_token)
    stopped_state = list_audit_general(access_token)
    if stopped_state not in {"absent", "disabled"}:
        raise QualificationFailure("stop_not_observed")

    recovery_attempted = True
    start_subscription(access_token)
    final_state = list_audit_general(access_token)
    if final_state != "enabled":
        raise QualificationFailure("recovery_start_not_observed_enabled")
    recovery_restored = True

    emit(
        SUCCESS_MARKER,
        {
            "schema_version": "ets.live_microsoft.rc1c_subscription_recovery.v1",
            "subscription_initial_state": initial_state,
            "initial_start_verified": True,
            "content_listing_reachable": True,
            "content_descriptors_observed": content_count,
            "stop_verified": True,
            "subscription_stopped_state": stopped_state,
            "recovery_start_verified": True,
            "subscription_final_state": final_state,
            "purview_webhook_configured": False,
            "api_retry_count": api_retry_count,
            "graph_operation_performed": False,
            "raw_purview_payload_retained": False,
            "customer_identifiers_retained": False,
            "reusable_credential_retained": False,
            "public_evidence_safe": True,
            "qualification_pass": True,
            "rc1c_live_qualified": False,
            "soak_clock_started": False,
        },
    )
except QualificationFailure as exc:
    failure_code = exc.code
except Exception:
    failure_code = "unexpected_failure"
finally:
    if failure_code is not None and mutated and access_token:
        recovery_attempted = True
        try:
            start_subscription(access_token)
            final_state = list_audit_general(access_token)
            recovery_restored = final_state == "enabled"
        except Exception:
            recovery_restored = False
        if not recovery_restored:
            failure_code = "recovery_restore_failed"
    access_token = None
    credential.close()

if failure_code is not None:
    emit(
        FAILURE_MARKER,
        {
            "schema_version": "ets.live_microsoft.rc1c_subscription_recovery_failure.v1",
            "failure_code": failure_code,
            "mutation_attempted": mutated,
            "recovery_attempted": recovery_attempted,
            "recovery_restored": recovery_restored,
            "subscription_final_state": final_state,
            "purview_webhook_configured": False,
            "graph_operation_performed": False,
            "raw_purview_payload_retained": False,
            "customer_identifiers_retained": False,
            "reusable_credential_retained": False,
            "public_evidence_safe": True,
            "qualification_pass": False,
            "rc1c_live_qualified": False,
            "soak_clock_started": False,
        },
    )
    raise SystemExit(1)
'''

resource recoveryJob 'Microsoft.App/jobs@2025-01-01' = {
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
      replicaTimeout: 360
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
      containers: [
        {
          name: 'microsoft-rc1c-subscription-recovery'
          image: containerImage
          command: [
            'python'
            '-c'
          ]
          args: [recoveryScript]
          env: [
            {
              name: 'ETS_RC1C_PURVIEW_CLIENT_ID'
              value: purviewIdentityClientId
            }
            {
              name: 'ETS_RC1C_MICROSOFT_TENANT_ID'
              secretRef: 'microsoft-tenant-id'
            }
            {
              name: 'ETS_RC1C_RESTORED_FAILURE_WORKFLOW_RUN_ID'
              value: restoredFailureWorkflowRunId
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
    }
  }
}

output recoveryJobName string = recoveryJob.name
