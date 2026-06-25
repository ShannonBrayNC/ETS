#!/usr/bin/env bash
set -euo pipefail

LEAN_DIR="${LEAN_DIR:-formal/lean}"
OUT_DIR="${LEAN_OUTPUT_DIR:-artifacts/lean-proofs}"
mkdir -p "$OUT_DIR"

SUMMARY_MD="$OUT_DIR/summary.md"
RESULTS_JSON="$OUT_DIR/results.json"
: > "$SUMMARY_MD"
printf '[\n' > "$RESULTS_JSON"

cat >> "$SUMMARY_MD" <<EOF
# Lean Proof Evidence Summary

| Proof File | Result | Exit Code | Duration Seconds | Log |
| --- | --- | ---: | ---: | --- |
EOF

proofs=(
  "src/ETSProofs/TemporalLiveness.lean"
  "src/ETSProofs/Fairness.lean"
  "src/ETSProofs/ByzantineTemporal.lean"
)

failure_count=0
first_entry=true

json_escape() {
  python -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

for proof in "${proofs[@]}"; do
  label="${proof//\//_}"
  log_file="$OUT_DIR/${label}.log"
  echo "Running Lean proof validation for $proof"
  start_epoch=$(date +%s)

  set +e
  (cd "$LEAN_DIR" && lean "$proof") > "$log_file" 2>&1
  status=$?
  set -e

  end_epoch=$(date +%s)
  duration=$((end_epoch - start_epoch))

  if [ "$status" -eq 0 ]; then
    result="passed"
  else
    result="failed"
    failure_count=$((failure_count + 1))
  fi

  echo "| $proof | $result | $status | $duration | ${label}.log |" >> "$SUMMARY_MD"

  if [ "$first_entry" = true ]; then
    first_entry=false
  else
    printf ',\n' >> "$RESULTS_JSON"
  fi

  printf '  {"proof": %s, "result": %s, "exit_code": %s, "duration_seconds": %s, "log": %s}' \
    "$(json_escape "$proof")" \
    "$(json_escape "$result")" \
    "$status" \
    "$duration" \
    "$(json_escape "${label}.log")" >> "$RESULTS_JSON"
done

printf '\n]\n' >> "$RESULTS_JSON"

{
  echo ""
  echo "## Aggregate Result"
  echo ""
  echo "- Proof failures: ${failure_count}"
} >> "$SUMMARY_MD"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  cat "$SUMMARY_MD" >> "$GITHUB_STEP_SUMMARY"
fi

if [ "$failure_count" -gt 0 ]; then
  echo "Lean proof evidence capture completed with ${failure_count} failure(s). See $OUT_DIR."
  exit 1
fi

echo "Lean proof evidence capture completed successfully. See $OUT_DIR."
