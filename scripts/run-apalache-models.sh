#!/usr/bin/env bash
set -euo pipefail

APALACHE_BIN="${APALACHE_BIN:-tools/apalache/bin/apalache-mc}"
OUT_DIR="${APALACHE_OUTPUT_DIR:-artifacts/proofs}"
mkdir -p "$OUT_DIR"

SUMMARY_MD="$OUT_DIR/summary.md"
RESULTS_JSON="$OUT_DIR/results.json"
: > "$SUMMARY_MD"
printf '[\n' > "$RESULTS_JSON"

cat >> "$SUMMARY_MD" <<EOF
# Apalache Symbolic Evidence Summary

| Target | Model | Invariant | Result | Exit Code | Duration Seconds | Log |
| --- | --- | --- | --- | ---: | ---: | --- |
EOF

targets=(
  "etslog:formal/apalache/models/ETSLogSymbolic.tla:TypeOK"
  "federation:formal/apalache/models/ETSVerifierFederationSymbolic.tla:AcceptedRequiresQuorum"
  "transport:formal/apalache/models/ETSAsyncTransportSymbolic.tla:ReplayRequiresDelivery"
  "liveness:formal/apalache/models/ETSLivenessProgressSymbolic.tla:BoundedProgress"
)

failure_count=0
first_entry=true

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

for entry in "${targets[@]}"; do
  name="${entry%%:*}"
  rest="${entry#*:}"
  model="${rest%%:*}"
  invariant="${rest##*:}"
  target_dir="$OUT_DIR/$name"
  mkdir -p "$target_dir"
  log_file="$target_dir/output.txt"

  echo "Running Apalache target $name ($invariant)"
  start_epoch=$(date +%s)

  set +e
  "$APALACHE_BIN" check \
    --init=Init \
    --next=Next \
    --inv="$invariant" \
    "$model" > "$log_file" 2>&1
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

  echo "| $name | $model | $invariant | $result | $status | $duration | $name/output.txt |" >> "$SUMMARY_MD"

  if [ "$first_entry" = true ]; then
    first_entry=false
  else
    printf ',\n' >> "$RESULTS_JSON"
  fi

  printf '  {"target": %s, "model": %s, "invariant": %s, "result": %s, "exit_code": %s, "duration_seconds": %s, "log": %s}' \
    "$(json_escape "$name")" \
    "$(json_escape "$model")" \
    "$(json_escape "$invariant")" \
    "$(json_escape "$result")" \
    "$status" \
    "$duration" \
    "$(json_escape "$name/output.txt")" >> "$RESULTS_JSON"
done

printf '\n]\n' >> "$RESULTS_JSON"

{
  echo ""
  echo "## Aggregate Result"
  echo ""
  echo "- Symbolic target failures: ${failure_count}"
  echo "- Current liveness verification represents bounded progress reasoning, not universal temporal liveness theorem proof."
} >> "$SUMMARY_MD"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  cat "$SUMMARY_MD" >> "$GITHUB_STEP_SUMMARY"
fi

if [ "$failure_count" -gt 0 ]; then
  echo "Apalache evidence capture completed with ${failure_count} failure(s). See $OUT_DIR."
  exit 1
fi

echo "Apalache evidence capture completed successfully. See $OUT_DIR."
