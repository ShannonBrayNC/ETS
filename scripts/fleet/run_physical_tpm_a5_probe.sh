#!/usr/bin/env bash
set -euo pipefail

umask 077

if [[ $# -ne 3 ]]; then
  echo "usage: $0 PHASE OUTPUT_DIR CONFIG_PATH" >&2
  exit 2
fi

phase=$1
output_dir=$2
config_path=$3

case "$phase" in
  authorized|dps-disabled-hub-enabled|hub-disabled-reconnect|dps-disabled-reprovision) ;;
  *)
    echo "unsupported phase: $phase" >&2
    exit 3
    ;;
esac

if [[ ! -r "$config_path" ]]; then
  echo "configuration file is not readable: $config_path" >&2
  exit 3
fi

for command_name in iotedge aziotctl sha256sum date sudo python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "required command not found: $command_name" >&2
    exit 4
  fi
done

iotedge_version=$(iotedge --version 2>&1 | head -n 1)
if [[ "$iotedge_version" != *"1.6"* ]]; then
  echo "FLEET-A5 reference qualification requires IoT Edge 1.6 LTS" >&2
  exit 5
fi

mkdir -p "$output_dir/private"
config_sha=$(sha256sum "$config_path" | awk '{print $1}')

run_capture() {
  local name=$1
  shift
  set +e
  "$@" >"$output_dir/private/$name.stdout" 2>"$output_dir/private/$name.stderr"
  local rc=$?
  set -e
  printf '%s' "$rc"
}

if [[ "$phase" == "authorized" || "$phase" == "dps-disabled-reprovision" ]]; then
  if [[ "$phase" == "authorized" && -f /etc/aziot/config.toml ]]; then
    if ! sudo test -f /etc/aziot/config.toml.ets-a5-backup; then
      sudo cp /etc/aziot/config.toml /etc/aziot/config.toml.ets-a5-backup
      sudo chmod 0600 /etc/aziot/config.toml.ets-a5-backup
    fi
  fi
  sudo install -m 0600 "$config_path" /etc/aziot/config.toml
  apply_rc=$(run_capture config-apply sudo iotedge config apply)
else
  apply_rc=0
fi

restart_rc=$(run_capture system-restart sudo iotedge system restart)
status_rc=$(run_capture system-status sudo iotedge system status)
identity_rc=$(run_capture identity-check sudo aziotctl check)
edge_check_rc=$(run_capture edge-check sudo iotedge check)

identity_success=false
if [[ "$identity_rc" -eq 0 ]]; then
  identity_success=true
fi

expected_success=false
case "$phase" in
  authorized|dps-disabled-hub-enabled)
    expected_success=true
    if [[ "$apply_rc" -ne 0 || "$restart_rc" -ne 0 || "$identity_rc" -ne 0 ]]; then
      echo "A5 positive identity/reconnect probe failed" >&2
      exit 6
    fi
    ;;
  hub-disabled-reconnect|dps-disabled-reprovision)
    if [[ "$identity_rc" -eq 0 ]]; then
      echo "A5 negative identity probe unexpectedly succeeded" >&2
      exit 7
    fi
    ;;
esac

hash_or_empty() {
  local path=$1
  if [[ -f "$path" ]]; then
    sha256sum "$path" | awk '{print $1}'
  else
    printf ''
  fi
}

identity_stdout_sha=$(hash_or_empty "$output_dir/private/identity-check.stdout")
identity_stderr_sha=$(hash_or_empty "$output_dir/private/identity-check.stderr")
edge_stdout_sha=$(hash_or_empty "$output_dir/private/edge-check.stdout")
edge_stderr_sha=$(hash_or_empty "$output_dir/private/edge-check.stderr")
observed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python3 - "$output_dir/device-probe.json" <<PY
import json
import sys

path = sys.argv[1]
payload = {
    "schema_version": "ets.fleet.physical-tpm-a5.device-probe.v1",
    "phase": "$phase",
    "reference_client": "azure-iot-edge-1.6-lts",
    "iotedge_version": "$iotedge_version",
    "config_sha256": "$config_sha",
    "config_apply_exit_code": int("$apply_rc"),
    "system_restart_exit_code": int("$restart_rc"),
    "system_status_exit_code": int("$status_rc"),
    "identity_check_exit_code": int("$identity_rc"),
    "edge_check_exit_code": int("$edge_check_rc"),
    "identity_check_succeeded": "$identity_success" == "true",
    "expected_identity_success": "$expected_success" == "true",
    "identity_stdout_sha256": "$identity_stdout_sha",
    "identity_stderr_sha256": "$identity_stderr_sha",
    "edge_check_stdout_sha256": "$edge_stdout_sha",
    "edge_check_stderr_sha256": "$edge_stderr_sha",
    "private_logs_retained_locally": True,
    "private_key_material_exported": False,
    "shared_or_sas_credential_used": False,
    "observed_at_utc": "$observed_at",
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

printf 'A5 device probe complete: %s\n' "$phase"
printf 'Public-safe result: %s/device-probe.json\n' "$output_dir"
printf '%s\n' 'Private command output remains local under the output directory.'
