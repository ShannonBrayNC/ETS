#!/usr/bin/env bash
set -euo pipefail

EVIDENCE_DIR="evidence/live-sharepoint-source-to-proof"
JOB_NAME="ets-spq-${GITHUB_RUN_ID}"
RAW_LOG="${RUNNER_TEMP}/live-sharepoint-source-to-proof.log"
PARAMS="${RUNNER_TEMP}/live-sharepoint-source-to-proof.parameters.json"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
HANDOFF_JSON="${EVIDENCE_DIR}/handoff.json"
FAILURE_JSON="${EVIDENCE_DIR}/failure.json"
CLEANUP_DONE=0
CORE_FQDN=""
GATEWAY_FQDN=""
MANAGED_ENVIRONMENT_NAME=""
GATEWAY_IDENTITY_ID=""
GATEWAY_CLIENT_ID=""
PULL_IDENTITY_ID=""

mkdir -p "$EVIDENCE_DIR"
rm -f "$RESULT_JSON" "$HANDOFF_JSON" "$FAILURE_JSON"

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
  SOURCE_TO_PROOF_ISSUE
  CORE_SCOPE
  SHAREPOINT_DRIVE_ID
  QUALIFICATION_MARKER
  EXPECTED_OBSERVATIONS
)
for name in "${required_env[@]}"; do
  if [ -z "${!name:-}" ]; then
    echo "::error::required SharePoint qualification value is missing: $name"
    exit 1
  fi
done

test "$GITHUB_REF" = "refs/heads/main"
test "$GITHUB_EVENT_NAME" = "workflow_dispatch"
test -f infra/azure/ets-live-sharepoint-source-proof-client.bicep
test "$CONTAINER_IMAGE" = "${ACR_NAME}.azurecr.io/ets/hosted-q1@${Q0_IMAGE_DIGEST}"

if ! [[ "$QUALIFICATION_MARKER" =~ ^[a-z0-9][a-z0-9-]{5,31}$ ]]; then
  echo "::error::marker must match ^[a-z0-9][a-z0-9-]{5,31}$"
  exit 1
fi
if ! [[ "$EXPECTED_OBSERVATIONS" =~ ^[0-9]+$ ]] ||
  [ "$EXPECTED_OBSERVATIONS" -lt 1 ] || [ "$EXPECTED_OBSERVATIONS" -gt 10 ]; then
  echo "::error::expected_observations must be between 1 and 10"
  exit 1
fi

echo "::add-mask::$CORE_SCOPE"
echo "::add-mask::$SHAREPOINT_DRIVE_ID"

delete_job_if_present() {
  local name="$1"
  az containerapp job delete \
    --name "$name" \
    --resource-group "$RESOURCE_GROUP" \
    --yes \
    --only-show-errors >/dev/null 2>&1 || true
}

cleanup() {
  if [ "$CLEANUP_DONE" -eq 1 ]; then
    return
  fi
  CLEANUP_DONE=1
  delete_job_if_present "$JOB_NAME"
  rm -f "$RAW_LOG" "$PARAMS"
}
trap cleanup EXIT

cleanup_stale_jobs() {
  local names
  names="$(az containerapp job list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?starts_with(name, 'ets-spq-')].name" \
    -o tsv 2>/dev/null || true)"
  if [ -n "$names" ]; then
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      delete_job_if_present "$name"
    done <<< "$names"
  fi
}

resolve_runtime() {
  local apps_json="$RUNNER_TEMP/live-sp-apps.json"
  local identity_json="$RUNNER_TEMP/live-sp-gateway-identity.json"
  local resolved="$RUNNER_TEMP/live-sp-resolved.txt"

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
    env = {item.get("name"): item.get("value") for item in containers[0].get("env") or []}
    if env.get("ETS_STORAGE_PROVIDER") == "azure_table":
        core.append((app, env))
    if env.get("ETS_GATEWAY_SHAREPOINT_DRIVE_ID"):
        gateway.append((app, env))

if len(core) != 1 or len(gateway) != 1:
    raise SystemExit("expected exactly one live Core and one SharePoint Gateway")
core_app, core_env = core[0]
gateway_app, gateway_env = gateway[0]
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

if gateway_env.get("ETS_GATEWAY_CORE_SCOPE") != os.environ["CORE_SCOPE"]:
    raise SystemExit("deployed Gateway Core scope differs from the protected contract")
if gateway_env.get("ETS_GATEWAY_SHAREPOINT_DRIVE_ID") != os.environ["SHAREPOINT_DRIVE_ID"]:
    raise SystemExit("deployed Gateway SharePoint drive differs from the protected contract")
if gateway_env.get("ETS_GATEWAY_POLL_INTERVAL_SECONDS") != "60":
    raise SystemExit("live SharePoint qualification requires the governed 60-second poll cadence")

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
    raise SystemExit("live Gateway does not attach the qualified Gateway UAMI")
if gateway_env.get("ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID", "").casefold() != gateway_client_id.casefold():
    raise SystemExit("Gateway runtime client ID differs from the exact Gateway UAMI")

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

core_fqdn = str((core_props.get("configuration") or {}).get("ingress", {}).get("fqdn") or "")
gateway_fqdn = str((gateway_props.get("configuration") or {}).get("ingress", {}).get("fqdn") or "")
if not core_fqdn or not gateway_fqdn:
    raise SystemExit("live internal Core/Gateway FQDN is unavailable")

print("CORE_FQDN=" + core_fqdn)
print("GATEWAY_FQDN=" + gateway_fqdn)
print("MANAGED_ENVIRONMENT_NAME=" + managed_environment_name)
print("GATEWAY_IDENTITY_ID=" + gateway_identity_id)
print("GATEWAY_CLIENT_ID=" + gateway_client_id)
print("PULL_IDENTITY_ID=" + pull_identity_id)
PY

  while IFS='=' read -r key value; do
    test -n "$key"
    test -n "$value"
    echo "::add-mask::$value"
    printf -v "$key" '%s' "$value"
  done < "$resolved"
  rm -f "$apps_json" "$identity_json" "$resolved"
}

build_params() {
  export SP_PARAMS="$PARAMS"
  export SP_JOB_NAME="$JOB_NAME"
  export SP_CORE_FQDN="$CORE_FQDN"
  export SP_GATEWAY_FQDN="$GATEWAY_FQDN"
  export SP_GATEWAY_IDENTITY_ID="$GATEWAY_IDENTITY_ID"
  export SP_GATEWAY_CLIENT_ID="$GATEWAY_CLIENT_ID"
  export SP_PULL_IDENTITY_ID="$PULL_IDENTITY_ID"
  python - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "location": {"value": os.environ["LOCATION"]},
        "clientName": {"value": os.environ["SP_JOB_NAME"]},
        "managedEnvironmentName": {"value": os.environ["MANAGED_ENVIRONMENT_NAME"]},
        "runtimeIdentityResourceId": {"value": os.environ["SP_GATEWAY_IDENTITY_ID"]},
        "runtimeIdentityClientId": {"value": os.environ["SP_GATEWAY_CLIENT_ID"]},
        "registryPullIdentityResourceId": {"value": os.environ["SP_PULL_IDENTITY_ID"]},
        "registryServer": {"value": os.environ["ACR_NAME"] + ".azurecr.io"},
        "containerImage": {"value": os.environ["CONTAINER_IMAGE"]},
        "coreBaseUrl": {"value": "https://" + os.environ["SP_CORE_FQDN"]},
        "coreScope": {"value": os.environ["CORE_SCOPE"]},
        "gatewayBaseUrl": {"value": "https://" + os.environ["SP_GATEWAY_FQDN"]},
        "sharePointDriveId": {"value": os.environ["SHAREPOINT_DRIVE_ID"]},
        "marker": {"value": os.environ["QUALIFICATION_MARKER"]},
        "expectedObservations": {"value": int(os.environ["EXPECTED_OBSERVATIONS"])},
    },
}
Path(os.environ["SP_PARAMS"]).write_text(json.dumps(payload), encoding="utf-8")
PY
}

classify_failure() {
  local status="$1"
  python - "$RAW_LOG" "$status" "$FAILURE_JSON" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
status = sys.argv[2]
rules = (
    ("live Gateway was not healthy and ready", "gateway_not_ready"),
    ("managed identity could not acquire a qualification token", "managed_identity_token_acquisition"),
    ("Graph returned a different qualification file", "graph_item_mismatch"),
    ("Graph qualification file omitted eTag", "graph_etag_missing"),
    ("Graph qualification object was not a file", "graph_object_not_file"),
    ("Gateway Graph identity escaped the approved SharePoint site scope", "graph_scope_denial_failed"),
    ("Gateway did not relay the expected SharePoint revision into Core", "sharepoint_relay_timeout"),
    ("current SharePoint revision did not map to exactly one ETS event", "exact_revision_cardinality_failed"),
    ("SharePoint revision history did not reach the expected observation count", "revision_history_incomplete"),
    ("independent SharePoint inclusion proof verification failed", "inclusion_proof_verification_failed"),
    ("duplicate polling changed the retained SharePoint ETS event set", "duplicate_suppression_failed"),
    ("duplicate polling changed the SharePoint observation count", "duplicate_count_changed"),
    ("unexpectedly retained raw source payload", "raw_source_payload_retained"),
    ("raw evidence exclusion", "raw_evidence_exclusion_failed"),
    ("unexpectedly retained source evidence content", "source_content_retained"),
)
failure_class = "sharepoint_source_to_proof_failed_unclassified"
for needle, value in rules:
    if needle in source:
        failure_class = value
        break
payload = {
    "schema_version": "ets.live_sharepoint.source_to_proof_failure.v1",
    "marker": __import__("os").environ["QUALIFICATION_MARKER"],
    "expected_observations": int(__import__("os").environ["EXPECTED_OBSERVATIONS"]),
    "failure_class": failure_class,
    "job_execution_status": status or "unknown",
    "m365_source_to_proof_claimed": False,
    "soak_clock_started": False,
    "customer_identifiers_retained": False,
    "reusable_credential_retained": False,
    "public_evidence_safe": True,
}
Path(sys.argv[3]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(failure_class)
PY
}

validate_result() {
  local status="$1"
  python - "$RAW_LOG" "$status" "$RESULT_JSON" "$HANDOFF_JSON" <<'PY'
import base64
import json
import os
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
status = sys.argv[2]
if status != "Succeeded":
    raise SystemExit("SharePoint qualification job did not succeed")
matches = re.findall(r"ETS_LIVE_SP_RESULT_B64=([A-Za-z0-9_=-]+)", source)
if not matches:
    raise SystemExit("SharePoint qualification did not emit a result marker")
result = json.loads(base64.urlsafe_b64decode(matches[-1]).decode("utf-8"))
expected = int(os.environ["EXPECTED_OBSERVATIONS"])
if result.get("marker") != os.environ["QUALIFICATION_MARKER"]:
    raise SystemExit("SharePoint qualification emitted a different marker")
if result.get("expected_observations") != expected:
    raise SystemExit("SharePoint qualification emitted a different expected observation count")
for name in (
    "gateway_health_verified",
    "gateway_readiness_verified",
    "graph_item_metadata_verified",
    "graph_scope_denial_403_verified",
    "delta_recovery_without_notification_verified",
    "exact_version_event_verified",
    "inclusion_proof_verified",
    "duplicate_suppression_verified",
    "durable_retention_verified",
    "public_evidence_safe",
):
    if result.get(name) is not True:
        raise SystemExit("SharePoint qualification did not prove every required predicate")
if not isinstance(result.get("core_observation_count"), int) or result["core_observation_count"] < expected:
    raise SystemExit("SharePoint qualification observation count is below the governed expectation")
if expected >= 2 and result.get("revision_evidence_verified") is not True:
    raise SystemExit("SharePoint qualification did not prove revision evidence")
for name in (
    "raw_document_content_retrieved",
    "raw_source_payload_retained",
    "customer_identifiers_retained",
    "reusable_credential_retained",
    "soak_clock_started",
):
    if result.get(name) is not False:
        raise SystemExit("SharePoint qualification violated a fail-closed evidence boundary")

Path(sys.argv[3]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
handoff = dict(result)
handoff.update(
    {
        "schema_version": "ets.live_sharepoint.source_to_proof_handoff.v1",
        "release_source_sha": os.environ["Q0_SOURCE_SHA"],
        "release_image_digest": os.environ["Q0_IMAGE_DIGEST"],
        "workflow_run_id": os.environ["GITHUB_RUN_ID"],
        "m365_source_to_proof_claimed": True,
        "full_microsoft_runtime_health_claimed": False,
        "customer_identifiers_retained": False,
        "reusable_credential_retained": False,
        "public_evidence_safe": True,
        "soak_clock_started": False,
    }
)
Path(sys.argv[4]).write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

publish_handoff() {
  python - "$HANDOFF_JSON" > "$RUNNER_TEMP/live-sp-comment.md" <<'PY'
import json
import sys
from pathlib import Path

p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
revision = "true" if p.get("revision_evidence_verified") else "false / second revision still required"
print("### Live EchoMedia SharePoint source-to-proof qualification")
print()
print(f"- workflow run: `{p['workflow_run_id']}`")
print(f"- release source: `{p['release_source_sha']}`")
print(f"- release image digest: `{p['release_image_digest']}`")
print(f"- synthetic marker: `{p['marker']}`")
print(f"- expected observations: **{p['expected_observations']}**")
print(f"- Gateway health/readiness verified: **{str(p['gateway_health_verified'] and p['gateway_readiness_verified']).lower()}**")
print(f"- approved SharePoint metadata observed by Gateway UAMI: **{str(p['graph_item_metadata_verified']).lower()}**")
print(f"- ungranted SharePoint scope denied with 403: **{str(p['graph_scope_denial_403_verified']).lower()}**")
print(f"- delta recovery without notification verified: **{str(p['delta_recovery_without_notification_verified']).lower()}**")
print(f"- durable Core observation count: **{p['core_observation_count']}**")
print(f"- exact current version event verified: **{str(p['exact_version_event_verified']).lower()}**")
print(f"- inclusion proof independently verified: **{str(p['inclusion_proof_verified']).lower()}**")
print(f"- duplicate suppression verified: **{str(p['duplicate_suppression_verified']).lower()}**")
print(f"- retained observation re-read verified: **{str(p['durable_retention_verified']).lower()}**")
print(f"- revision evidence verified: **{revision}**")
print("- raw document content retrieved: **false**")
print("- customer identifiers retained in public evidence: **false**")
print("- reusable credentials retained: **false**")
print("- 72-hour soak clock started: **false**")
PY
  gh issue comment "$SOURCE_TO_PROOF_ISSUE" --repo "$GITHUB_REPOSITORY" --body-file "$RUNNER_TEMP/live-sp-comment.md"
  gh issue comment "$HANDOFF_ISSUE" --repo "$GITHUB_REPOSITORY" --body-file "$RUNNER_TEMP/live-sp-comment.md"
  rm -f "$RUNNER_TEMP/live-sp-comment.md"
}

publish_failure() {
  python - "$FAILURE_JSON" > "$RUNNER_TEMP/live-sp-failure-comment.md" <<'PY'
import json
import sys
from pathlib import Path
p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("### Live EchoMedia SharePoint source-to-proof qualification — fail closed")
print()
print(f"- workflow run: `{__import__('os').environ['GITHUB_RUN_ID']}`")
print(f"- synthetic marker: `{p['marker']}`")
print(f"- bounded failure class: `{p['failure_class']}`")
print("- M365 source-to-proof claimed: **false**")
print("- 72-hour soak clock started: **false**")
print("- customer identifiers retained in public evidence: **false**")
print("- reusable credentials retained: **false**")
PY
  gh issue comment "$SOURCE_TO_PROOF_ISSUE" --repo "$GITHUB_REPOSITORY" --body-file "$RUNNER_TEMP/live-sp-failure-comment.md" || true
  rm -f "$RUNNER_TEMP/live-sp-failure-comment.md"
}

cleanup_stale_jobs
resolve_runtime
build_params

az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --name "ets-live-spq-${GITHUB_RUN_ID}" \
  --template-file infra/azure/ets-live-sharepoint-source-proof-client.bicep \
  --parameters "@$PARAMS" \
  --only-show-errors >/dev/null

execution="$(az containerapp job start \
  --name "$JOB_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query name -o tsv)"
test -n "$execution"

status=""
for _ in $(seq 1 130); do
  status="$(az containerapp job execution show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --job-execution-name "$execution" \
    --query properties.status -o tsv 2>/dev/null || true)"
  case "$status" in
    Succeeded|Failed|Canceled) break ;;
  esac
  sleep 5
done

: > "$RAW_LOG"
for _ in $(seq 1 12); do
  az containerapp job logs show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --execution "$execution" \
    --container sharepoint-proof-client \
    --tail 200 \
    --format text \
    --only-show-errors > "$RAW_LOG" 2>&1 || true
  if grep -q 'ETS_LIVE_SP_RESULT_B64=' "$RAW_LOG"; then
    break
  fi
  [ "$status" = "Succeeded" ] || [ "$status" = "Failed" ] || break
  sleep 5
done

if [ "$status" != "Succeeded" ]; then
  failure_class="$(classify_failure "$status")"
  echo "::error::live SharePoint source-to-proof qualification failed: $failure_class"
  publish_failure
  exit 1
fi

if ! validate_result "$status"; then
  failure_class="$(classify_failure "$status")"
  echo "::error::live SharePoint source-to-proof result validation failed: $failure_class"
  publish_failure
  exit 1
fi

publish_handoff
