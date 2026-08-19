#!/usr/bin/env bash
set -euo pipefail

REAL_AZ="$(command -v az)"
if [ -z "$REAL_AZ" ]; then
  echo "::error::Azure CLI is not available for live SharePoint qualification"
  exit 1
fi

SHIM_DIR="$(mktemp -d)"
PRIVATE_RAW="$RUNNER_TEMP/live-sp-private-container-log.txt"
PRIVATE_REPLICA="$RUNNER_TEMP/live-sp-private-replica.json"
FAILURE_JSON="evidence/live-sharepoint-source-to-proof/failure.json"

cleanup_wrapper() {
  rm -f "$PRIVATE_RAW" "$PRIVATE_REPLICA"
  rm -rf "$SHIM_DIR"
}
trap cleanup_wrapper EXIT

cat > "$SHIM_DIR/az" <<'SHIM'
#!/usr/bin/env bash
set -uo pipefail

if [ -z "${ETS_REAL_AZ:-}" ]; then
  echo "diagnostic az shim is missing ETS_REAL_AZ" >&2
  exit 127
fi

arg_value() {
  local target="$1"
  shift
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "$target" ]; then
      if [ "$#" -lt 2 ]; then
        return 1
      fi
      printf '%s' "$2"
      return 0
    fi
    shift
  done
  return 1
}

capture_replica_metadata() {
  local job_name="$1"
  local resource_group="$2"
  local execution="$3"
  local replica_json=""
  set +e
  replica_json="$($ETS_REAL_AZ containerapp job replica list \
    --name "$job_name" \
    --resource-group "$resource_group" \
    --execution "$execution" \
    --only-show-errors \
    -o json 2>/dev/null)"
  set -e
  if [ -n "$replica_json" ]; then
    printf '%s\n' "$replica_json" > "${ETS_SP_DIAGNOSTIC_REPLICA:?}"
  fi
}

if [ "${1:-}" = "containerapp" ] && [ "${2:-}" = "job" ] && [ "${3:-}" = "execution" ] && [ "${4:-}" = "show" ]; then
  set +e
  output="$($ETS_REAL_AZ "$@" 2>&1)"
  rc=$?
  set -e
  printf '%s\n' "$output"
  if [ "$rc" -eq 0 ] && printf '%s\n' "$output" | grep -Eq '^(Succeeded|Failed|Canceled)$'; then
    job_name="$(arg_value --name "$@" || true)"
    resource_group="$(arg_value --resource-group "$@" || true)"
    execution="$(arg_value --job-execution-name "$@" || true)"
    if [ -n "$job_name" ] && [ -n "$resource_group" ] && [ -n "$execution" ]; then
      capture_replica_metadata "$job_name" "$resource_group" "$execution"
    fi
  fi
  exit "$rc"
fi

if [ "${1:-}" = "containerapp" ] && [ "${2:-}" = "job" ] && [ "${3:-}" = "logs" ] && [ "${4:-}" = "show" ]; then
  job_name="$(arg_value --name "$@" || true)"
  resource_group="$(arg_value --resource-group "$@" || true)"
  execution="$(arg_value --execution "$@" || true)"
  latest=""
  rc=1
  for _ in $(seq 1 12); do
    replica=""
    if [ -n "$job_name" ] && [ -n "$resource_group" ] && [ -n "$execution" ]; then
      capture_replica_metadata "$job_name" "$resource_group" "$execution"
      set +e
      replica="$($ETS_REAL_AZ containerapp job replica list \
        --name "$job_name" \
        --resource-group "$resource_group" \
        --execution "$execution" \
        --query '[0].name' \
        --only-show-errors \
        -o tsv 2>/dev/null)"
      set -e
    fi

    log_args=("$@")
    if [ -n "$replica" ]; then
      log_args+=(--replica "$replica")
    fi
    log_args+=(--format text --only-show-errors)

    set +e
    latest="$($ETS_REAL_AZ "${log_args[@]}" 2>&1)"
    rc=$?
    set -e
    if [ -n "$latest" ]; then
      printf '%s\n' "$latest" > "${ETS_SP_DIAGNOSTIC_RAW:?}"
      if printf '%s\n' "$latest" | grep -Eq \
        'Traceback|RuntimeError|ValidationError|JSONDecodeError|UnicodeDecodeError|RemoteDisconnected|ConnectionResetError|SSLError|ETS_LIVE_SP_RESULT_B64='; then
        printf '%s\n' "$latest"
        exit "$rc"
      fi
    fi
    sleep 5
  done
  if [ -n "$latest" ]; then
    printf '%s\n' "$latest" > "${ETS_SP_DIAGNOSTIC_RAW:?}"
    printf '%s\n' "$latest"
  fi
  exit "$rc"
fi

exec "$ETS_REAL_AZ" "$@"
SHIM
chmod 700 "$SHIM_DIR/az"

export ETS_REAL_AZ="$REAL_AZ"
export ETS_SP_DIAGNOSTIC_RAW="$PRIVATE_RAW"
export ETS_SP_DIAGNOSTIC_REPLICA="$PRIVATE_REPLICA"
export PATH="$SHIM_DIR:$PATH"

set +e
bash scripts/azure/run-live-sharepoint-source-to-proof.sh
rc=$?
set -e

if [ "$rc" -ne 0 ] && [ -f "$FAILURE_JSON" ]; then
  python - "$FAILURE_JSON" "$PRIVATE_RAW" "$PRIVATE_REPLICA" <<'PY'
import json
import re
import sys
from pathlib import Path

failure_path = Path(sys.argv[1])
raw_path = Path(sys.argv[2])
replica_path = Path(sys.argv[3])
payload = json.loads(failure_path.read_text(encoding="utf-8"))
if payload.get("failure_class") != "sharepoint_source_to_proof_failed_unclassified":
    raise SystemExit(0)

source = ""
if raw_path.exists():
    source = raw_path.read_text(encoding="utf-8", errors="replace")

rules = (
    ("live Gateway was not healthy and ready", "gateway_not_ready"),
    ("managed identity could not acquire a qualification token", "managed_identity_token_acquisition"),
    ("Graph returned a different qualification file", "graph_item_mismatch"),
    ("Graph qualification file omitted eTag", "graph_etag_missing"),
    ("Graph qualification object was not a file", "graph_object_not_file"),
    ("unexpectedly surfaced a download URL", "graph_download_url_exposed"),
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
    ("Core event list returned an invalid shape", "core_event_list_shape_invalid"),
    ("Core event list exceeded the bounded qualification window", "core_event_list_window_exceeded"),
    ("SharePoint observation omitted event identity", "observation_event_id_missing"),
    ("SharePoint observation omitted source eTag", "observation_etag_missing"),
    ("qualification endpoint returned non-object JSON", "qualification_response_shape_invalid"),
    ("qualification endpoint was unreachable", "qualification_endpoint_unreachable"),
    ("InclusionProof.model_validate_json", "inclusion_proof_payload_validation_failed"),
    ("verify_inclusion_proof", "inclusion_proof_verifier_exception"),
    ("JSONDecodeError", "qualification_json_decode_failed"),
    ("UnicodeDecodeError", "qualification_utf8_decode_failed"),
    ("RemoteDisconnected", "qualification_transport_error"),
    ("ConnectionResetError", "qualification_transport_error"),
    ("SSLError", "qualification_transport_error"),
    ("AttributeError", "qualification_client_attribute_error"),
    ("KeyError", "qualification_client_key_error"),
    ("TypeError", "qualification_client_type_error"),
    ("ValueError", "qualification_client_value_error"),
)
refined = "sharepoint_source_to_proof_failed_unclassified"
for needle, value in rules:
    if needle in source:
        refined = value
        break

if refined == "sharepoint_source_to_proof_failed_unclassified":
    match = re.search(r"qualification endpoint returned unexpected HTTP status (\d+)", source)
    if match:
        code = int(match.group(1))
        if "in list_scoped_events" in source:
            refined = "core_event_list_forbidden" if code == 403 else "core_event_list_http_error"
        elif "in verify_proof" in source:
            refined = "inclusion_proof_forbidden" if code == 403 else "inclusion_proof_http_error"
        elif "item_url, token=graph_token" in source:
            if code == 403:
                refined = "graph_item_forbidden"
            elif code == 404:
                refined = "graph_item_not_found"
            else:
                refined = "graph_item_http_error"
        elif "scope_status, _ = request_json" in source:
            refined = "graph_scope_denial_http_error"
        elif 'gateway_base + "/health"' in source:
            refined = "gateway_health_http_error"
        elif 'gateway_base + "/ready"' in source:
            refined = "gateway_readiness_http_error"
        else:
            refined = "qualification_http_error"

codes: set[int] = set()
status_text: list[str] = []
if replica_path.exists():
    try:
        replica_payload = json.loads(replica_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        replica_payload = None

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                lowered = str(key).casefold()
                if lowered in {"code", "exitcode", "exit_code"} and isinstance(item, int):
                    codes.add(item)
                if lowered in {"status", "reason", "additionalinformation", "message"} and isinstance(item, str):
                    status_text.append(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(replica_payload)

if refined == "sharepoint_source_to_proof_failed_unclassified":
    terminal = " ".join(status_text).casefold()
    if "out of memory" in terminal or "oom" in terminal:
        refined = "sharepoint_qualification_container_oom"
    elif "evict" in terminal:
        refined = "sharepoint_qualification_container_evicted"
    elif any(token in terminal for token in ("containercreate", "imagepull", "image pull", "failed to pull")):
        refined = "sharepoint_qualification_container_start_failed"
    elif 137 in codes:
        refined = "sharepoint_qualification_container_exit_137"
    elif 139 in codes:
        refined = "sharepoint_qualification_container_exit_139"
    elif 143 in codes:
        refined = "sharepoint_qualification_container_exit_143"
    elif 127 in codes:
        refined = "sharepoint_qualification_container_exit_127"
    elif 126 in codes:
        refined = "sharepoint_qualification_container_exit_126"
    elif 2 in codes:
        refined = "sharepoint_qualification_container_exit_2"
    elif 1 in codes:
        refined = "sharepoint_qualification_container_exit_1"
    elif any(code != 0 for code in codes):
        refined = "sharepoint_qualification_container_exit_nonzero"
    elif any(token in terminal for token in ("failed", "error", "terminated")):
        refined = "sharepoint_qualification_container_runtime_failed"

if refined == "sharepoint_source_to_proof_failed_unclassified":
    if not source.strip():
        refined = "sharepoint_qualification_log_unavailable"
    elif re.search(
        r"(replica|log|logs).*(not found|unavailable|failed|does not exist)",
        source,
        re.IGNORECASE,
    ):
        refined = "sharepoint_qualification_log_unavailable"
    else:
        refined = "sharepoint_qualification_console_output_unrecognized"

payload["failure_class"] = refined
payload["diagnostic_refined"] = True
payload["customer_identifiers_retained"] = False
payload["reusable_credential_retained"] = False
payload["public_evidence_safe"] = True
payload["m365_source_to_proof_claimed"] = False
payload["soak_clock_started"] = False
failure_path.write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
fi

exit "$rc"
