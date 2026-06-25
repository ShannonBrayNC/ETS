#!/usr/bin/env bash
set -euo pipefail

TLC_JAR="${TLC_JAR:-tools/tla2tools.jar}"
TLA_DIR="${TLA_DIR:-formal/tla}"
OUT_DIR="${TLC_OUTPUT_DIR:-artifacts/tlc}"
TIMEOUT_SECONDS="${TLC_TIMEOUT_SECONDS:-180}"
FAIL_ON_TIMEOUT="${TLC_FAIL_ON_TIMEOUT:-false}"

mkdir -p "$OUT_DIR"

SUMMARY_MD="$OUT_DIR/summary.md"
RESULTS_JSON="$OUT_DIR/results.json"
: > "$SUMMARY_MD"
printf '[\n' > "$RESULTS_JSON"

cat >> "$SUMMARY_MD" <<EOF
# TLC Evidence Capture Summary

| Model | Config | Result | Exit Code | Duration Seconds | Log |
| --- | --- | --- | ---: | ---: | --- |
EOF

models=(
  "ETSLog.tla:ETSLog.cfg"
  "ETSVerifierFederation.tla:ETSVerifierFederation.cfg"
  "ETSTemporalByzantineFederation.tla:ETSTemporalByzantineFederation.cfg"
  "ETSProbabilisticTrust.tla:ETSProbabilisticTrust.cfg"
  "ETSLivenessFederation.tla:ETSLivenessFederation.cfg"
  "ETSAsyncTransport.tla:ETSAsyncTransport.cfg"
  "ETSTemporalLivenessTheorems.tla:ETSTemporalLivenessTheorems.cfg"
  "ETSUniversalTemporalLiveness.tla:ETSUniversalTemporalLiveness.cfg"
)

failure_count=0
timeout_count=0
first_entry=true

json_escape() {
  python -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

for entry in "${models[@]}"; do
  model="${entry%%:*}"
  config="${entry##*:}"
  label="${model%.tla}"
  log_file="$OUT_DIR/${label}.log"

  echo "Running TLC $label with timeout ${TIMEOUT_SECONDS}s"
  start_epoch=$(date +%s)

  set +e
  (
    cd "$TLA_DIR"
    timeout "${TIMEOUT_SECONDS}s" java -cp "../../${TLC_JAR}" tlc2.TLC "$model" -config "$config" -deadlock
  ) > "$log_file" 2>&1
  status=$?
  set -e

  end_epoch=$(date +%s)
  duration=$((end_epoch - start_epoch))

  if [ "$status" -eq 0 ]; then
    result="passed"
  elif [ "$status" -eq 124 ]; then
    result="timeout"
    timeout_count=$((timeout_count + 1))
    if [ "$FAIL_ON_TIMEOUT" = "true" ]; then
      failure_count=$((failure_count + 1))
    fi
  else
    result="failed"
    failure_count=$((failure_count + 1))
  fi

  echo "| $label | $config | $result | $status | $duration | ${label}.log |" >> "$SUMMARY_MD"

  if [ "$first_entry" = true ]; then
    first_entry=false
  else
    printf ',\n' >> "$RESULTS_JSON"
  fi

  printf '  {"model": %s, "config": %s, "result": %s, "exit_code": %s, "duration_seconds": %s, "log": %s}' \
    "$(json_escape "$model")" \
    "$(json_escape "$config")" \
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
  echo "- Timeout policy: ${TIMEOUT_SECONDS}s per model"
  echo "- Fail on timeout: ${FAIL_ON_TIMEOUT}"
  echo "- Non-timeout failures or configured timeout failures: ${failure_count}"
  echo "- Timeouts observed: ${timeout_count}"
} >> "$SUMMARY_MD"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  cat "$SUMMARY_MD" >> "$GITHUB_STEP_SUMMARY"
fi

if [ "$failure_count" -gt 0 ]; then
  echo "TLC evidence capture completed with ${failure_count} failure(s). See $OUT_DIR."
  exit 1
fi

echo "TLC evidence capture completed successfully. See $OUT_DIR."
