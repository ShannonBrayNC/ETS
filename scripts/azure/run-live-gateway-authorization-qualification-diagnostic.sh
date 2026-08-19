#!/usr/bin/env bash
set -euo pipefail

REAL_AZ="$(command -v az)"
if [ -z "$REAL_AZ" ]; then
  echo "::error::Azure CLI is not available for live authorization qualification"
  exit 1
fi

SHIM_DIR="$(mktemp -d)"
PRIVATE_RAW="$RUNNER_TEMP/live-auth-private-container-log.txt"
FAILURE_JSON="evidence/live-gateway-authorization/failure.json"

cleanup_wrapper() {
  rm -f "$PRIVATE_RAW"
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

if [ "${1:-}" = "containerapp" ] && [ "${2:-}" = "job" ] && [ "${3:-}" = "logs" ] && [ "${4:-}" = "show" ]; then
  latest=""
  rc=1
  for _ in $(seq 1 12); do
    set +e
    latest="$($ETS_REAL_AZ "$@" 2>&1)"
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
export PATH="$SHIM_DIR:$PATH"

set +e
bash scripts/azure/run-live-gateway-authorization-qualification.sh
rc=$?
set -e

if [ "$rc" -ne 0 ] && [ -f "$FAILURE_JSON" ]; then
  python - "$FAILURE_JSON" "$PRIVATE_RAW" <<'PY'
import json
import re
import sys
from pathlib import Path

failure_path = Path(sys.argv[1])
raw_path = Path(sys.argv[2])
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

if refined == "qualification_job_failed_unclassified":
    if not source.strip():
        refined = "qualification_log_unavailable"
    elif re.search(r"(log|logs).*(not found|unavailable|failed)", source, re.IGNORECASE):
        refined = "qualification_log_unavailable"

payload["failure_class"] = refined
payload["diagnostic_refined"] = refined != "qualification_job_failed_unclassified"
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
