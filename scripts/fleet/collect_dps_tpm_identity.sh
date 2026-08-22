#!/usr/bin/env bash
set -euo pipefail

umask 077

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 OUTPUT_DIR [EK_HANDLE]" >&2
  exit 2
fi

output_dir=$1
ek_handle=${2:-0x81010001}

if [[ ! "$ek_handle" =~ ^0x[0-9A-Fa-f]{8}$ ]]; then
  echo "EK_HANDLE must be an 8-digit hexadecimal TPM handle" >&2
  exit 3
fi

for command_name in tpm2_readpublic sha256sum base64 date; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "required command not found: $command_name" >&2
    exit 4
  fi
done

mkdir -p "$output_dir"
ek_public="$output_dir/endorsement-key.public.tpm2b"
ek_base64="$output_dir/endorsement-key.public.b64"
public_manifest="$output_dir/public-manifest.json"

# Qualification is intentionally read-only. The referenced EK must already exist.
tpm2_readpublic -Q -c "$ek_handle" -o "$ek_public"

registration_id="$(sha256sum "$ek_public" | awk '{print $1}')"
if [[ ! "$registration_id" =~ ^[0-9a-f]{64}$ ]]; then
  echo "failed to derive canonical TPM registration ID" >&2
  exit 5
fi

base64 -w0 "$ek_public" >"$ek_base64"
printf '\n' >>"$ek_base64"
printf '%s\n' "$registration_id" >"$output_dir/provider-registration-id.txt"
printf '%s\n' "$ek_handle" >"$output_dir/ek-handle.txt"
date -u +%Y-%m-%dT%H:%M:%SZ >"$output_dir/collected-at-utc.txt"

collected_at="$(cat "$output_dir/collected-at-utc.txt")"
cat >"$public_manifest" <<JSON
{
  "schema_version": "ets.fleet.azure-dps.tpm-provider-identity.v1",
  "provider_registration_id": "$registration_id",
  "endorsement_key_fingerprint_sha256": "$registration_id",
  "ek_handle": "$ek_handle",
  "collected_at_utc": "$collected_at",
  "hardware_identity_collected": true,
  "hardware_attested": false,
  "fresh_quote_required": true,
  "raw_endorsement_key_retained_in_public_manifest": false,
  "private_key_material_exported": false,
  "shared_or_sas_credential_used": false
}
JSON

(
  cd "$output_dir"
  sha256sum \
    endorsement-key.public.tpm2b \
    endorsement-key.public.b64 \
    provider-registration-id.txt \
    public-manifest.json >private-bundle.sha256
)

printf 'TPM DPS provider identity collected at %s\n' "$output_dir"
printf 'Public-safe manifest: %s\n' "$public_manifest"
printf 'Operator-private EK material: %s\n' "$ek_base64"
