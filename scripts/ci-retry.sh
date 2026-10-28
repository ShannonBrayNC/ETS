#!/usr/bin/env bash
# Bounded retries for setup/download commands only; never wrap proof execution.
set -uo pipefail
if [[ $# -lt 4 || ! $1 =~ ^[1-5]$ || ! $2 =~ ^[1-9][0-9]*$ || ! $3 =~ ^[0-9]+$ ]]; then
  echo 'Usage: ci-retry.sh ATTEMPTS(1-5) TIMEOUT_SECONDS DELAY_SECONDS COMMAND [ARGS...]' >&2
  exit 2
fi
attempts=$1
seconds=$2
delay=$3
shift 3
status=1
for ((attempt=1; attempt<=attempts; attempt++)); do
  echo "Setup attempt $attempt/$attempts (timeout ${seconds}s)" >&2
  if timeout --kill-after=10s "${seconds}s" "$@"; then
    exit 0
  else
    status=$?
  fi
  echo "Setup attempt $attempt failed with exit $status" >&2
  if (( attempt < attempts )); then
    sleep "$delay"
  fi
done
exit "$status"
