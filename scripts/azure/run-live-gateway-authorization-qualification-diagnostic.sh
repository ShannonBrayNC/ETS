#!/usr/bin/env bash
set -euo pipefail

REAL_AZ="$(command -v az)"
if [ -z "$REAL_AZ" ]; then
  echo "::error::Azure CLI is not available for live authorization qualification"
  exit 1
fi

SHIM_DIR="$(mktemp -d)"
PRIVATE_RAW="$RUNNER_TEMP/live-auth-private-container-log.txt"
PRIVATE_REPLICA="$RUNNER_TEMP/live-auth-private-replica.json"
FAILURE_JSON="evidence/live-gateway-authorization/failure.json"

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
    printf '%s\n' "$replica_json" > "${ETS_AUTH_DIAGNOSTIC_REPLICA:?}"
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
      printf '%s\n' "$latest" > "${ETS_AUTH_DIAGNOSTIC_RAW:?}"
      if printf '%s\n' "$latest" | grep -Eq \
        'Traceback|RuntimeError|ValidationError|JSONDecodeError|UnicodeDecodeError|RemoteDisconnected|ConnectionResetError|SSLError|ETS_LIVE_AUTH_RESULT_B64='; then
        printf '%s\n' "$latest"
        exit "$rc"
      fi
    fi
    sleep 5
  done
  if [ -n "$latest" ]; then
    printf '%s\n' "$latest" > "${ETS_AUTH_DIAGNOSTIC_RAW:?}"
    printf '%s\n' "$latest"
  fi
  exit "$rc"
fi

exec "$ETS_REAL_AZ" "$@"
SHIM
chmod 700 "$SHIM_DIR/az"

export ETS_REAL_AZ="$REAL_AZ"
export ETS_AUTH_DIAGNOSTIC_RAW="$PRIVATE_RAW"
export ETS_AUTH_DIAGNOSTIC_REPLICA="$PRIVATE_REPLICA"
export PATH="$SHIM_DIR:$PATH"

set +e
bash scripts/azure/run-live-gateway-authorization-qualification.sh
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
if payload.get("failure_class") != "qualification_job_failed_unclassified":
    raise SystemExit(0)

source = ""
if raw_path.exists():
    source = raw_path.read_text(encoding="utf-8", errors="replace")

rules = (
    ("qualification endpoint returned non-object JSON", "core_response_shape_invalid"),
    ("managed identity Core scope did not use", "core_scope_contract_invalid"),
    ("managed identity Core scope did not contain an application id", "core_scope_contract_invalid"),
    ("InclusionProof.model_validate", "inclusion_proof_payload_validation_failed"),
    ("verify_inclusion_proof", "inclusion_proof_verifier_exception"),
    ("JSONDecodeError", "qualification_json_decode_failed"),
    ("UnicodeDecodeError", "qualification_utf8_decode_failed"),
    ("RemoteDisconnected", "core_transport_error"),
    ("ConnectionResetError", "core_transport_error"),
    ("SSLError", "core_transport_error"),
    ("AttributeError", "qualification_client_attribute_error"),
    ("KeyError", "qualification_client_key_error"),
    ("TypeError", "qualification_client_type_error"),
    ("ValueError", "qualification_client_value_error"),
)
refined = "qualification_job_failed_unclassified"
for needle, value in rules:
    if needle in source:
        refined = value
        break

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

if refined == "qualification_job_failed_unclassified":
    terminal = " ".join(status_text).casefold()
    if "out of memory" in terminal or "oom" in terminal:
        refined = "qualification_container_oom"
    elif "evict" in terminal:
        refined = "qualification_container_evicted"
    elif any(token in terminal for token in ("containercreate", "imagepull", "image pull", "failed to pull")):
        refined = "qualification_container_start_failed"
    elif 137 in codes:
        refined = "qualification_container_exit_137"
    elif 139 in codes:
        refined = "qualification_container_exit_139"
    elif 143 in codes:
        refined = "qualification_container_exit_143"
    elif 127 in codes:
        refined = "qualification_container_exit_127"
    elif 126 in codes:
        refined = "qualification_container_exit_126"
    elif 2 in codes:
        refined = "qualification_container_exit_2"
    elif 1 in codes:
        refined = "qualification_container_exit_1"
    elif any(code != 0 for code in codes):
        refined = "qualification_container_exit_nonzero"
    elif any(token in terminal for token in ("failed", "error", "terminated")):
        refined = "qualification_container_runtime_failed"

if refined == "qualification_job_failed_unclassified":
    if not source.strip():
        refined = "qualification_log_unavailable"
    elif re.search(
        r"(replica|log|logs).*(not found|unavailable|failed|does not exist)",
        source,
        re.IGNORECASE,
    ):
        refined = "qualification_log_unavailable"
    else:
        refined = "qualification_console_output_unrecognized"

payload["failure_class"] = refined
payload["diagnostic_refined"] = True
# Preserve the established public-safety contract. Never retain raw logs or identifiers.
payload["customer_identifiers_retained"] = False
payload["reusable_credential_retained"] = False
payload["public_evidence_safe"] = True
failure_path.write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
fi

exit "$rc"
