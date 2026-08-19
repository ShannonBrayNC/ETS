@description('Azure region used by the existing live Container Apps environment.')
param location string

@description('Ephemeral live authorization qualification job name.')
@minLength(2)
@maxLength(32)
param clientName string

@description('Existing live Container Apps managed environment name.')
@minLength(1)
param managedEnvironmentName string

@description('Runtime managed identity used to acquire the ETS Core token.')
@minLength(1)
param runtimeIdentityResourceId string

@secure()
@description('Client ID of the runtime managed identity. Not retained in public evidence.')
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
@description('Server-authoritative ETS tenant identifier for the qualification event.')
@minLength(1)
param etsTenantId string

@secure()
@description('Server-authoritative ETS workspace identifier for the qualification event.')
@minLength(1)
param etsWorkspaceId string

@description('GitHub Actions run identifier used only for synthetic event uniqueness.')
@minLength(1)
param runId string

@description('Expected authorization outcome for the runtime identity.')
@allowed([
  'producer'
  'denied'
])
param mode string

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' existing = {
  name: managedEnvironmentName
}

var qualificationScript = '''
import base64
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from azure.identity import ManagedIdentityCredential
from ets.core import InclusionProof
from ets.core.proofs import verify_inclusion_proof

MARKER = "ETS_LIVE_AUTH_RESULT_B64="


def decode_json(body):
    if not body:
        return {}
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("qualification endpoint returned non-object JSON")
    return value


def request_json(method, url, token=None, payload=None, expected=(200,)):
    headers = {"Accept": "application/json"}
    data = None
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20.0) as response:
            status = response.status
            body = response.read()
    except HTTPError as exc:
        status = exc.code
        body = exc.read()
    except (TimeoutError, URLError) as exc:
        raise RuntimeError("live Core qualification endpoint was unreachable") from exc
    decoded = decode_json(body)
    if status not in expected:
        raise RuntimeError("live Core returned unexpected HTTP status " + str(status))
    return status, decoded


def decode_claims(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise RuntimeError("managed identity token was not a JWT")
    padding = "=" * (-len(parts[1]) % 4)
    raw = base64.urlsafe_b64decode(parts[1] + padding)
    claims = json.loads(raw.decode("utf-8"))
    if not isinstance(claims, dict):
        raise RuntimeError("managed identity token claims were not an object")
    return claims


def normalize_roles(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return sorted(set(value))
    raise RuntimeError("managed identity token roles claim had an unsupported shape")


def acquire_token(client_id, scope):
    credential = ManagedIdentityCredential(client_id=client_id)
    last_error = None
    try:
        for attempt in range(12):
            try:
                access = credential.get_token(scope)
                if not access.token:
                    raise RuntimeError("managed identity returned an empty Core token")
                return access.token
            except Exception as exc:
                last_error = exc
                if attempt < 11:
                    time.sleep(5)
        raise RuntimeError("managed identity could not acquire the Core token") from last_error
    finally:
        credential.close()


def synthetic_event(mode, run_id, tenant_id, workspace_id):
    marker = ("live-auth:" + mode + ":" + run_id).encode("utf-8")
    event_id = "live-auth-" + mode + "-" + run_id
    return {
        "event_id": event_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "evidence_id": "qualification-" + mode + "-" + run_id,
        "event_type": "qualification.authorization",
        "subject_ref": "ets://qualification/live-authorization/" + mode + "/" + run_id,
        "content_hash": hashlib.sha256(marker).hexdigest(),
        "content_hash_alg": "sha256",
        "metadata": {
            "qualification": "LIVE-GATEWAY-AUTH",
            "synthetic": True,
            "contains_real_pii": False,
            "raw_customer_evidence": False,
        },
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_system": "ets-live-authorization-qualification",
    }


def emit(result):
    raw = json.dumps(result, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii")
    print(MARKER + encoded)


mode = os.environ["ETS_AUTH_QUALIFICATION_MODE"]
client_id = os.environ["ETS_AUTH_CLIENT_ID"]
core_base = os.environ["ETS_AUTH_CORE_BASE_URL"].rstrip("/")
scope = os.environ["ETS_AUTH_CORE_SCOPE"]
tenant_id = os.environ["ETS_AUTH_TENANT_ID"]
workspace_id = os.environ["ETS_AUTH_WORKSPACE_ID"]
run_id = os.environ["ETS_AUTH_RUN_ID"]

_, health = request_json("GET", core_base + "/health")
_, ready = request_json("GET", core_base + "/ready")
if health.get("status") != "ok" or ready.get("status") != "ready":
    raise RuntimeError("live Core was not healthy and ready")

token = acquire_token(client_id, scope)
claims = decode_claims(token)
if claims.get("idtyp") != "app":
    raise RuntimeError("Core qualification requires an app-only managed identity token")
claim_client = claims.get("azp") or claims.get("appid")
if not isinstance(claim_client, str) or claim_client.casefold() != client_id.casefold():
    raise RuntimeError("managed identity token client claim did not match the runtime identity")
scope_prefix = "api://"
scope_suffix = "/.default"
if not scope.startswith(scope_prefix) or not scope.endswith(scope_suffix):
    raise RuntimeError("managed identity Core scope did not use the governed api://<appId>/.default form")
expected_audience = scope[len(scope_prefix) : -len(scope_suffix)]
if not expected_audience:
    raise RuntimeError("managed identity Core scope did not contain an application id")
audience = claims.get("aud")
if not isinstance(audience, str) or audience.casefold() != expected_audience.casefold():
    raise RuntimeError("managed identity token audience did not match ETS Core")
roles = normalize_roles(claims.get("roles"))
event = synthetic_event(mode, run_id, tenant_id, workspace_id)

result = {
    "schema_version": "ets.live_gateway.authorization_qualification.v1",
    "mode": mode,
    "core_health_verified": True,
    "core_readiness_verified": True,
    "managed_identity_token_acquired": True,
    "app_only_token_verified": True,
    "runtime_client_claim_verified": True,
    "core_audience_verified": True,
    "producer_role_present": "evidence_producer" in roles,
    "append_accepted": False,
    "negative_control_forbidden": False,
    "inclusion_proof_verified": False,
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
}

if mode == "producer":
    if roles != ["evidence_producer"]:
        raise RuntimeError("Gateway Core token did not contain exactly evidence_producer")
    _, append = request_json(
        "POST",
        core_base + "/api/v1/events",
        token=token,
        payload=event,
        expected=(201,),
    )
    if append.get("event_id") != event["event_id"]:
        raise RuntimeError("Core acknowledged a different qualification event")
    _, proof_payload = request_json(
        "GET",
        core_base + "/api/v1/proofs/inclusion/" + event["event_id"],
        token=token,
    )
    proof = InclusionProof.model_validate(proof_payload)
    verification = verify_inclusion_proof(proof)
    if not verification.valid:
        raise RuntimeError("independent inclusion proof verification failed")
    result["append_accepted"] = True
    result["inclusion_proof_verified"] = True
elif mode == "denied":
    if roles:
        raise RuntimeError("negative-control token unexpectedly contained ETS Core app roles")
    status, response = request_json(
        "POST",
        core_base + "/api/v1/events",
        token=token,
        payload=event,
        expected=(403,),
    )
    error = response.get("error")
    if status != 403 or not isinstance(error, dict):
        raise RuntimeError("negative control did not return the bounded forbidden response")
    if error.get("code") != "ETS_AUTH_FORBIDDEN":
        raise RuntimeError("negative control returned an unexpected authorization code")
    result["negative_control_forbidden"] = True
else:
    raise RuntimeError("unsupported qualification mode")

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
          name: 'auth-client'
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
              name: 'ETS_AUTH_QUALIFICATION_MODE'
              value: mode
            }
            {
              name: 'ETS_AUTH_CLIENT_ID'
              value: runtimeIdentityClientId
            }
            {
              name: 'ETS_AUTH_CORE_BASE_URL'
              value: coreBaseUrl
            }
            {
              name: 'ETS_AUTH_CORE_SCOPE'
              value: coreScope
            }
            {
              name: 'ETS_AUTH_TENANT_ID'
              value: etsTenantId
            }
            {
              name: 'ETS_AUTH_WORKSPACE_ID'
              value: etsWorkspaceId
            }
            {
              name: 'ETS_AUTH_RUN_ID'
              value: runId
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
