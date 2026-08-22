#!/usr/bin/env bash
set -euo pipefail

umask 077

if [[ $# -ne 3 ]]; then
  echo "usage: $0 OUTPUT_DIR DPS_ID_SCOPE PROVIDER_REGISTRATION_ID" >&2
  exit 2
fi

output_dir=$1
id_scope=$2
registration_id=${3,,}

if [[ ! "$id_scope" =~ ^[A-Za-z0-9_-]{3,128}$ ]]; then
  echo "DPS_ID_SCOPE has an invalid shape" >&2
  exit 3
fi
if [[ ! "$registration_id" =~ ^[0-9a-f]{64}$ ]]; then
  echo "PROVIDER_REGISTRATION_ID must be a lowercase SHA-256 value" >&2
  exit 3
fi

mkdir -p "$output_dir"

cat >"$output_dir/config.dynamic.toml" <<EOF
auto_reprovisioning_mode = "Dynamic"

[provisioning]
source = "dps"
global_endpoint = "https://global.azure-devices-provisioning.net"
id_scope = "$id_scope"

[provisioning.attestation]
method = "tpm"
registration_id = "$registration_id"
EOF

cat >"$output_dir/config.always-on-startup.toml" <<EOF
auto_reprovisioning_mode = "AlwaysOnStartup"

[provisioning]
source = "dps"
global_endpoint = "https://global.azure-devices-provisioning.net"
id_scope = "$id_scope"

[provisioning.attestation]
method = "tpm"
registration_id = "$registration_id"
EOF

dynamic_sha=$(sha256sum "$output_dir/config.dynamic.toml" | awk '{print $1}')
reprovision_sha=$(sha256sum "$output_dir/config.always-on-startup.toml" | awk '{print $1}')
prepared_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

cat >"$output_dir/a5-device-config-manifest.json" <<EOF
{
  "schema_version": "ets.fleet.physical-tpm-a5.device-config.v1",
  "reference_client": "azure-iot-edge-1.6-lts",
  "global_endpoint": "https://global.azure-devices-provisioning.net",
  "dps_id_scope": "$id_scope",
  "provider_registration_id": "$registration_id",
  "attestation_method": "tpm",
  "dynamic_config_sha256": "$dynamic_sha",
  "always_on_startup_config_sha256": "$reprovision_sha",
  "private_key_material_exported": false,
  "shared_or_sas_credential_used": false,
  "prepared_at_utc": "$prepared_at"
}
EOF

printf 'A5 device qualification configs prepared at %s\n' "$output_dir"
printf '%s\n' 'No system configuration was changed by this preparation step.'
