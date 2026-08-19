#!/usr/bin/env bash
set -euo pipefail

EVIDENCE_DIR="evidence/live-gateway-authorization"
PRODUCER_JOB="ets-authp-${GITHUB_RUN_ID}"
NEGATIVE_JOB="ets-authn-${GITHUB_RUN_ID}"
CONTROL_NAME="ets-live-authctl-${GITHUB_RUN_ID}"
CONTROL_CREATED=0
SCOPE_MAP_MUTATED=0
CLEANUP_DONE=0
CORE_NAME=""
CORE_FQDN=""
MANAGED_ENVIRONMENT_NAME=""
GATEWAY_IDENTITY_ID=""
GATEWAY_CLIENT_ID=""
PULL_IDENTITY_ID=""
CONTROL_ID=""
CONTROL_CLIENT_ID=""

mkdir -p "$EVIDENCE_DIR"

required_env=(
  GITHUB_REF
  GITHUB_EVENT_NAME
  GITHUB_RUN_ID
  GITHUB_REPOSITORY
  GITHUB_SHA
  LOCATION
  RESOURCE_GROUP
  GATEWAY_IDENTITY_NAME
  ACR_NAME
  CONTAINER_IMAGE
  Q0_SOURCE_SHA
  Q0_IMAGE_DIGEST
  HANDOFF_ISSUE
  CORE_SCOPE
  AUTH_APP_SCOPE_MAP_JSON
  ETS_TENANT_ID
  ETS_WORKSPACE_ID
)
for name in "${required_env[@]}"; do
  if [ -z "${!name:-}" ]; then
    echo "::error::required qualification environment value is missing: $name"
    exit 1
  fi
done

test "$GITHUB_REF" = "refs/heads/main"
test "$GITHUB_EVENT_NAME" = "workflow_dispatch"
test -f infra/azure/ets-live-auth-qualification-client.bicep
test "$CONTAINER_IMAGE" = "${ACR_NAME}.azurecr.io/ets/hosted-q1@${Q0_IMAGE_DIGEST}"

echo "::add-mask::$CORE_SCOPE"
echo "::add-mask::$AUTH_APP_SCOPE_MAP_JSON"
echo "::add-mask::$ETS_TENANT_ID"
echo "::add-mask::$ETS_WORKSPACE_ID"

classify_failure() {
  local raw_log="$1"
  local status="$2"
  local mode="$3"
  local output="$4"
  python - "$raw_log" "$status" "$mode" "$output" <<'PY'
import json
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
status = sys.argv[2]
mode = sys.argv[3]

rules = (
    ("No module named 'azure'", "runtime_dependency_missing"),
    ("No module named 'ets'", "runtime_package_missing"),
    ("live Core qualification endpoint was unreachable", "core_unreachable"),
    ("live Core was not healthy and ready", "core_not_ready"),
    ("managed identity could not acquire the Core token", "managed_identity_token_acquisition"),
    ("managed identity returned an empty Core token", "managed_identity_empty_token"),
    ("managed identity token was not a JWT", "managed_identity_token_not_jwt"),
    ("managed identity token claims were not an object", "managed_identity_claims_invalid"),
    ("Core qualification requires an app-only managed identity token", "managed_identity_token_not_app_only"),
    ("managed identity token client claim did not match", "managed_identity_client_claim_mismatch"),
    ("managed identity token audience did not match ETS Core", "managed_identity_audience_mismatch"),
    ("managed identity token roles claim had an unsupported shape", "managed_identity_roles_invalid"),
    ("Gateway Core token did not contain exactly evidence_producer", "producer_role_mismatch"),
    ("Core acknowledged a different qualification event", "producer_append_ack_mismatch"),
    ("independent inclusion proof verification failed", "inclusion_proof_verification_failed"),
    ("negative-control token unexpectedly contained ETS Core app roles", "negative_control_role_present"),
    ("negative control did not return the bounded forbidden response", "negative_control_response_invalid"),
    ("negative control returned an unexpected authorization code", "negative_control_error_code_invalid"),
    ("unsupported authorization qualification mode", "qualification_mode_invalid"),
)
failure_class = "qualification_job_failed_unclassified"
for needle, value in rules:
    if needle in source:
        failure_class = value
        break

if failure_class == "qualification_job_failed_unclassified":
    match = re.search(r"live Core returned unexpected HTTP status ([0-9]{3})", source)
    if match:
        failure_class = f"core_http_{match.group(1)}"

if failure_class == "qualification_job_failed_unclassified" and "ValidationError" in source:
    failure_class = "qualification_payload_validation_failed"

payload = {
    "schema_version": "ets.live_gateway.authorization_failure.v1",
    "mode": mode,
    "failure_class": failure_class,
    "job_execution_status": status or "unknown",
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
}
Path(sys.argv[4]).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(failure_class)
PY
}

validate_result() {
  local raw_log="$1"
  local status="$2"
  local mode="$3"
  local output="$4"
  python - "$raw_log" "$status" "$mode" "$output" <<'PY'
import base64
import json
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
status = sys.argv[2]
mode = sys.argv[3]
if status != "Succeeded":
    raise SystemExit("qualification job did not succeed")
matches = re.findall(r"ETS_LIVE_AUTH_RESULT_B64=([A-Za-z0-9_=-]+)", source)
if not matches:
    raise SystemExit("qualification did not emit a result marker")
result = json.loads(base64.urlsafe_b64decode(matches[-1]).decode("utf-8"))
if result.get("mode") != mode:
    raise SystemExit("qualification emitted the wrong mode")
common_true = (
    "core_health_verified",
    "core_readiness_verified",
    "managed_identity_token_acquired",
    "app_only_token_verified",
    "runtime_client_claim_verified",
    "core_audience_verified",
    "public_evidence_safe",
)
if any(result.get(name) is not True for name in common_true):
    raise SystemExit("qualification did not prove every common predicate")
if result.get("customer_identifiers_retained") is not False:
    raise SystemExit("qualification evidence retained customer identifiers")
if result.get("reusable_credential_retained") is not False:
    raise SystemExit("qualification evidence retained reusable credentials")
if mode == "producer":
    for name in ("producer_role_present", "append_accepted", "inclusion_proof_verified"):
        if result.get(name) is not True:
            raise SystemExit("producer qualification did not prove every producer predicate")
    if result.get("negative_control_forbidden") is not False:
        raise SystemExit("producer qualification mixed negative-control claims")
elif mode == "denied":
    if result.get("negative_control_forbidden") is not True:
        raise SystemExit("negative control did not prove forbidden ingestion")
    if result.get("producer_role_present") is not False:
        raise SystemExit("negative-control token unexpectedly had evidence_producer")
    if result.get("append_accepted") is not False:
        raise SystemExit("negative control unexpectedly accepted evidence ingestion")
else:
    raise SystemExit("unsupported qualification mode")
Path(sys.argv[4]).write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
}

delete_job_if_present() {
  local name="$1"
  az containerapp job delete \
    --name "$name" \
    --resource-group "$RESOURCE_GROUP" \
    --yes \
    --only-show-errors >/dev/null 2>&1 || true
}

resolve_runtime() {
  local apps_json="$RUNNER_TEMP/live-auth-apps.json"
  local identity_json="$RUNNER_TEMP/live-auth-gateway-identity.json"
  local resolved="$RUNNER_TEMP/live-auth-resolved.txt"

  az containerapp list --resource-group "$RESOURCE_GROUP" -o json > "$apps_json"
  az identity show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$GATEWAY_IDENTITY_NAME" \
    -o json > "$identity_json"

  python - "$apps_json" "$identity_json" > "$resolved" <<'PY'
import json
import os
import sys
from pathlib import Path

apps = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
identity = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
if not isinstance(apps, list):
    raise SystemExit("live Container Apps listing was not an array")

core = []
gateway = []
for app in apps:
    props = app.get("properties") or {}
    template = props.get("template") or {}
    containers = template.get("containers") or []
    if len(containers) != 1:
        continue
    env = {
        item.get("name"): item.get("value")
        for item in containers[0].get("env") or []
    }
    if env.get("ETS_STORAGE_PROVIDER") == "azure_table":
        core.append((app, env))
    if env.get("ETS_GATEWAY_CORE_SCOPE"):
        gateway.append((app, env))

if len(core) != 1 or len(gateway) != 1:
    raise SystemExit("expected exactly one live Core and one live Gateway")
core_app, _ = core[0]
gateway_app, _ = gateway[0]
if core_app.get("name") == gateway_app.get("name"):
    raise SystemExit("Core and Gateway resolved to the same Container App")

expected_image = os.environ["CONTAINER_IMAGE"]
for label, app in (("Core", core_app), ("Gateway", gateway_app)):
    props = app.get("properties") or {}
    ingress = (props.get("configuration") or {}).get("ingress") or {}
    if ingress.get("external") is not False:
        raise SystemExit(label + " ingress is not internal")
    containers = (props.get("template") or {}).get("containers") or []
    if containers[0].get("image") != expected_image:
        raise SystemExit(label + " image is not the authoritative digest")

core_props = core_app.get("properties") or {}
gateway_props = gateway_app.get("properties") or {}
core_environment = str(core_props.get("environmentId") or "")
gateway_environment = str(gateway_props.get("environmentId") or "")
if not core_environment or core_environment.casefold() != gateway_environment.casefold():
    raise SystemExit("Core and Gateway are not in the same managed environment")
managed_environment_name = core_environment.rstrip("/").split("/")[-1]

gateway_identity_id = str(identity.get("id") or "")
gateway_client_id = str(identity.get("clientId") or "")
if not gateway_identity_id or not gateway_client_id:
    raise SystemExit("live Gateway UAMI is missing resource/client identity")
assigned = (gateway_app.get("identity") or {}).get("userAssignedIdentities") or {}
if gateway_identity_id.casefold() not in {key.casefold() for key in assigned}:
    raise SystemExit("live Gateway app does not attach the qualified Gateway UAMI")

registries = (gateway_props.get("configuration") or {}).get("registries") or []
if len(registries) != 1:
    raise SystemExit("live Gateway must have exactly one private ACR binding")
registry = registries[0]
if str(registry.get("server") or "").casefold() != (
    os.environ["ACR_NAME"] + ".azurecr.io"
).casefold():
    raise SystemExit("live Gateway registry server changed")
pull_identity_id = str(registry.get("identity") or "")
if not pull_identity_id or pull_identity_id.casefold() == gateway_identity_id.casefold():
    raise SystemExit("Gateway registry identity must remain pull-only and distinct")

scope_map = json.loads(os.environ["AUTH_APP_SCOPE_MAP_JSON"])
if not isinstance(scope_map, dict) or len(scope_map) != 1:
    raise SystemExit("live app scope map must contain exactly one Gateway client")
key = next(iter(scope_map))
if key.casefold() != gateway_client_id.casefold():
    raise SystemExit("live app scope map does not target the exact Gateway UAMI")
binding = scope_map[key]
if not isinstance(binding, dict):
    raise SystemExit("Gateway scope binding is not an object")
if binding.get("tenant_id") != os.environ["ETS_TENANT_ID"]:
    raise SystemExit("Gateway scope binding tenant changed")
if binding.get("workspace_id") != os.environ["ETS_WORKSPACE_ID"]:
    raise SystemExit("Gateway scope binding workspace changed")

core_fqdn = str((core_props.get("configuration") or {}).get("ingress", {}).get("fqdn") or "")
if not core_fqdn:
    raise SystemExit("live Core internal FQDN is unavailable")

print("CORE_NAME=" + str(core_app.get("name") or ""))
print("CORE_FQDN=" + core_fqdn)
print("MANAGED_ENVIRONMENT_NAME=" + managed_environment_name)
print("GATEWAY_IDENTITY_ID=" + gateway_identity_id)
print("GATEWAY_CLIENT_ID=" + gateway_client_id)
print("PULL_IDENTITY_ID=" + pull_identity_id)
PY

  while IFS='=' read -r key value; do
    test -n "$key"
    test -n "$value"
    case "$key" in
      CORE_NAME|MANAGED_ENVIRONMENT_NAME)
        ;;
      *)
        echo "::add-mask::$value"
        ;;
    esac
    printf -v "$key" '%s' "$value"
  done < "$resolved"
}

cleanup_stale_jobs() {
  local names
  names="$(az containerapp job list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?starts_with(name, 'ets-authp-') || starts_with(name, 'ets-authn-')].name" \
    -o tsv || true)"
  if [ -n "$names" ]; then
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      delete_job_if_present "$name"
    done <<< "$names"
  fi
}

build_params() {
  local output="$1"
  local job_name="$2"
  local runtime_identity_id="$3"
  local runtime_client_id="$4"
  local mode="$5"
  export AUTH_PARAMS="$output"
  export AUTH_JOB_NAME="$job_name"
  export AUTH_RUNTIME_ID="$runtime_identity_id"
  export AUTH_RUNTIME_CLIENT_ID="$runtime_client_id"
  export AUTH_MODE="$mode"
  python - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "location": {"value": os.environ["LOCATION"]},
        "clientName": {"value": os.environ["AUTH_JOB_NAME"]},
        "managedEnvironmentName": {"value": os.environ["MANAGED_ENVIRONMENT_NAME"]},
        "runtimeIdentityResourceId": {"value": os.environ["AUTH_RUNTIME_ID"]},
        "runtimeIdentityClientId": {"value": os.environ["AUTH_RUNTIME_CLIENT_ID"]},
        "registryPullIdentityResourceId": {"value": os.environ["PULL_IDENTITY_ID"]},
        "registryServer": {"value": os.environ["ACR_NAME"] + ".azurecr.io"},
        "containerImage": {"value": os.environ["CONTAINER_IMAGE"]},
        "coreBaseUrl": {"value": "https://" + os.environ["CORE_FQDN"]},
        "coreScope": {"value": os.environ["CORE_SCOPE"]},
        "etsTenantId": {"value": os.environ["ETS_TENANT_ID"]},
        "etsWorkspaceId": {"value": os.environ["ETS_WORKSPACE_ID"]},
        "runId": {"value": os.environ["GITHUB_RUN_ID"]},
        "mode": {"value": os.environ["AUTH_MODE"]},
    },
}
Path(os.environ["AUTH_PARAMS"]).write_text(json.dumps(payload), encoding="utf-8")
Path(os.environ["AUTH_PARAMS"]).chmod(0o600)
PY
}

run_qualification_job() {
  local mode="$1"
  local job_name="$2"
  local runtime_identity_id="$3"
  local runtime_client_id="$4"
  local output="$5"
  local failure_output="$6"
  local deployment="$job_name"
  local params="$RUNNER_TEMP/${job_name}-params.json"
  local raw_log="$RUNNER_TEMP/${job_name}.log"

  build_params "$params" "$job_name" "$runtime_identity_id" "$runtime_client_id" "$mode"
  az deployment group create \
    --name "$deployment" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infra/azure/ets-live-auth-qualification-client.bicep \
    --parameters "@$params" \
    --output none
  rm -f "$params"
  az deployment group delete \
    --name "$deployment" \
    --resource-group "$RESOURCE_GROUP" \
    --only-show-errors

  local execution
  execution="$(az containerapp job start \
    --name "$job_name" \
    --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv)"
  test -n "$execution"

  local status=""
  for _ in $(seq 1 120); do
    status="$(az containerapp job execution show \
      --name "$job_name" \
      --resource-group "$RESOURCE_GROUP" \
      --job-execution-name "$execution" \
      --query properties.status -o tsv)"
    case "$status" in
      Succeeded|Failed|Canceled) break ;;
    esac
    sleep 5
  done

  az containerapp job logs show \
    --name "$job_name" \
    --resource-group "$RESOURCE_GROUP" \
    --execution "$execution" \
    --container auth-client \
    --tail 200 > "$raw_log" 2>&1 || true

  if [ "$status" != "Succeeded" ]; then
    local failure_class
    failure_class="$(classify_failure "$raw_log" "$status" "$mode" "$failure_output")"
    rm -f "$raw_log"
    echo "::error::Live Gateway authorization qualification failed: $failure_class"
    return 1
  fi

  if ! validate_result "$raw_log" "$status" "$mode" "$output"; then
    local failure_class
    failure_class="$(classify_failure "$raw_log" "$status" "$mode" "$failure_output")"
    rm -f "$raw_log"
    echo "::error::Live Gateway authorization result validation failed: $failure_class"
    return 1
  fi
  rm -f "$raw_log"
}

restore_scope_map() {
  if [ "$SCOPE_MAP_MUTATED" -ne 1 ]; then
    return 0
  fi

  az containerapp update \
    --name "$CORE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --set-env-vars "ETS_AUTH_APP_SCOPE_MAP_JSON=$AUTH_APP_SCOPE_MAP_JSON" \
    --output none

  local core_json="$RUNNER_TEMP/live-auth-restored-core.json"
  az containerapp show \
    --name "$CORE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    -o json > "$core_json"

  python - "$core_json" <<'PY'
import json
import os
import sys
from pathlib import Path

app = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
containers = ((app.get("properties") or {}).get("template") or {}).get("containers") or []
if len(containers) != 1:
    raise SystemExit("restored Core did not contain exactly one container")
env = {
    item.get("name"): item.get("value")
    for item in containers[0].get("env") or []
}
actual = json.loads(env.get("ETS_AUTH_APP_SCOPE_MAP_JSON") or "null")
expected = json.loads(os.environ["AUTH_APP_SCOPE_MAP_JSON"])
if actual != expected:
    raise SystemExit("live Core app scope map did not restore exactly")
if not isinstance(actual, dict) or len(actual) != 1:
    raise SystemExit("restored Core scope map must contain exactly one client")
key = next(iter(actual))
if key.casefold() != os.environ["GATEWAY_CLIENT_ID"].casefold():
    raise SystemExit("restored Core scope map no longer targets the Gateway UAMI")
PY
  SCOPE_MAP_MUTATED=0
}

delete_control_identity() {
  if [ "$CONTROL_CREATED" -eq 1 ]; then
    az identity delete \
      --name "$CONTROL_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --only-show-errors >/dev/null
    CONTROL_CREATED=0
  fi
}

perform_cleanup() {
  local failed=0
  set +e
  restore_scope_map || failed=1
  delete_job_if_present "$PRODUCER_JOB"
  delete_job_if_present "$NEGATIVE_JOB"
  delete_control_identity || failed=1
  rm -f \
    "$RUNNER_TEMP/live-auth-temporary-scope-map.json" \
    "$RUNNER_TEMP/${PRODUCER_JOB}-params.json" \
    "$RUNNER_TEMP/${NEGATIVE_JOB}-params.json" \
    "$RUNNER_TEMP/${PRODUCER_JOB}.log" \
    "$RUNNER_TEMP/${NEGATIVE_JOB}.log"
  set -e
  if [ "$failed" -ne 0 ]; then
    echo "::error::Live Gateway authorization cleanup did not fully restore the bounded state"
    return 1
  fi
  CLEANUP_DONE=1
}

on_exit() {
  local rc=$?
  trap - EXIT
  if [ "$CLEANUP_DONE" -ne 1 ]; then
    if ! perform_cleanup; then
      rc=1
    fi
  fi
  exit "$rc"
}
trap on_exit EXIT

resolve_runtime
export CORE_NAME CORE_FQDN MANAGED_ENVIRONMENT_NAME
export GATEWAY_IDENTITY_ID GATEWAY_CLIENT_ID PULL_IDENTITY_ID
cleanup_stale_jobs

run_qualification_job \
  "producer" \
  "$PRODUCER_JOB" \
  "$GATEWAY_IDENTITY_ID" \
  "$GATEWAY_CLIENT_ID" \
  "$EVIDENCE_DIR/producer.json" \
  "$EVIDENCE_DIR/failure.json"

control_json="$RUNNER_TEMP/live-auth-control.json"
az identity create \
  --name "$CONTROL_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  -o json > "$control_json"
CONTROL_ID="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$control_json")"
CONTROL_CLIENT_ID="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["clientId"])' "$control_json")"
test -n "$CONTROL_ID"
test -n "$CONTROL_CLIENT_ID"
CONTROL_CREATED=1
echo "::add-mask::$CONTROL_ID"
echo "::add-mask::$CONTROL_CLIENT_ID"

temporary_map="$RUNNER_TEMP/live-auth-temporary-scope-map.json"
export CONTROL_CLIENT_ID
python - "$temporary_map" <<'PY'
import json
import os
import sys
from pathlib import Path

current = json.loads(os.environ["AUTH_APP_SCOPE_MAP_JSON"])
if not isinstance(current, dict) or len(current) != 1:
    raise SystemExit("live scope map changed before negative control")
control = os.environ["CONTROL_CLIENT_ID"]
if control in current:
    raise SystemExit("negative-control client unexpectedly already existed in live scope map")
temporary = dict(current)
temporary[control] = {
    "tenant_id": os.environ["ETS_TENANT_ID"],
    "workspace_id": os.environ["ETS_WORKSPACE_ID"],
}
Path(sys.argv[1]).write_text(
    json.dumps(temporary, separators=(",", ":"), sort_keys=True),
    encoding="utf-8",
)
Path(sys.argv[1]).chmod(0o600)
PY

temporary_scope_map="$(cat "$temporary_map")"
echo "::add-mask::$temporary_scope_map"
az containerapp update \
  --name "$CORE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars "ETS_AUTH_APP_SCOPE_MAP_JSON=$temporary_scope_map" \
  --output none
SCOPE_MAP_MUTATED=1

run_qualification_job \
  "denied" \
  "$NEGATIVE_JOB" \
  "$CONTROL_ID" \
  "$CONTROL_CLIENT_ID" \
  "$EVIDENCE_DIR/negative.json" \
  "$EVIDENCE_DIR/failure.json"

perform_cleanup

python - <<'PY'
import json
import os
from pathlib import Path

producer = json.loads(
    Path("evidence/live-gateway-authorization/producer.json").read_text(encoding="utf-8")
)
negative = json.loads(
    Path("evidence/live-gateway-authorization/negative.json").read_text(encoding="utf-8")
)
payload = {
    "schema_version": "ets.live_gateway.authorization_handoff.v1",
    "orchestrator_source_sha": os.environ["GITHUB_SHA"],
    "q0_image_source_sha": os.environ["Q0_SOURCE_SHA"],
    "q0_image_digest": os.environ["Q0_IMAGE_DIGEST"],
    "core_health_verified": producer["core_health_verified"],
    "core_readiness_verified": producer["core_readiness_verified"],
    "gateway_uami_app_only_token_verified": producer["app_only_token_verified"],
    "gateway_uami_core_audience_verified": producer["core_audience_verified"],
    "producer_role_verified": producer["producer_role_present"],
    "producer_append_accepted": producer["append_accepted"],
    "producer_inclusion_proof_verified": producer["inclusion_proof_verified"],
    "negative_control_app_only_token_verified": negative["app_only_token_verified"],
    "negative_control_has_producer_role": negative["producer_role_present"],
    "negative_control_forbidden_403_verified": negative["negative_control_forbidden"],
    "scope_map_restored": True,
    "ephemeral_control_identity_removed": True,
    "runtime_health_claimed": False,
    "m365_source_to_proof_claimed": False,
    "soak_clock_started": False,
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
}
Path("evidence/live-gateway-authorization/handoff.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

body=$(cat <<EOF
### Live Gateway authorization qualification

- release image source: \`$Q0_SOURCE_SHA\`
- release image digest: \`$Q0_IMAGE_DIGEST\`
- exact Gateway UAMI acquired a Core app-only token: **true**
- Core audience binding verified: **true**
- \`evidence_producer\` role verified on the Gateway token: **true**
- live synthetic evidence append accepted: **true**
- returned inclusion proof independently verified: **true**
- mapped app-only negative control had \`evidence_producer\`: **false**
- negative-control ingestion denied with 403 \`ETS_AUTH_FORBIDDEN\`: **true**
- original one-client Core app-scope map restored: **true**
- ephemeral negative-control identity removed: **true**
- full Gateway/Microsoft runtime health claimed: **false**
- M365 source-to-proof claimed: **false**
- 72-hour soak clock started: **false**
- customer identifiers retained in public evidence: **false**
- reusable credentials retained: **false**

Next gate: provision the approved EchoMedia SharePoint \`Sites.Selected\` boundary and qualify #390 document-to-ETS source-to-proof, including recovery, duplicate suppression, unauthorized-site denial, and retained proof across restart before starting the 72-hour soak.
EOF
)

gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  "/repos/$GITHUB_REPOSITORY/issues/$HANDOFF_ISSUE/comments" \
  -f body="$body" >/dev/null

rm -f "$EVIDENCE_DIR/failure.json"
