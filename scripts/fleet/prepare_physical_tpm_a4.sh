#!/usr/bin/env bash
set -euo pipefail

umask 077

if [[ $# -lt 4 || $# -gt 5 ]]; then
  echo "usage: $0 OUTPUT_DIR AK_CONTEXT AK_PUBLIC_PEM NONCE_HEX [EK_HANDLE]" >&2
  exit 2
fi

output_dir=$1
ak_context=$2
ak_public=$3
nonce_hex=${4,,}
ek_handle=${5:-0x81010001}
pcr_selection=sha256:0,2,4,7

if [[ ! "$nonce_hex" =~ ^[0-9a-f]{64}$ ]]; then
  echo "NONCE_HEX must be exactly 32 bytes encoded as 64 hexadecimal characters" >&2
  exit 3
fi
if [[ ! -r "$ak_public" ]]; then
  echo "AK public key is not readable: $ak_public" >&2
  exit 3
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
collector="$script_dir/collect_dps_tpm_identity.sh"
quote_request="$repo_root/scripts/ai_witness/request_tpm_quote.sh"
quote_verify="$repo_root/scripts/ai_witness/verify_tpm_quote.sh"

for path in "$collector" "$quote_request" "$quote_verify"; do
  if [[ ! -x "$path" ]]; then
    echo "required qualification script is not executable: $path" >&2
    exit 4
  fi
done
for command_name in sha256sum cp awk grep date; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "required command not found: $command_name" >&2
    exit 4
  fi
done

mkdir -p "$output_dir"
"$collector" "$output_dir/provider" "$ek_handle"
cp "$ak_public" "$output_dir/attestation-key.public.pem"
"$quote_request" "$output_dir/quote" "$ak_context" "$nonce_hex" "$pcr_selection"
"$quote_verify" \
  "$output_dir/quote" \
  "$output_dir/attestation-key.public.pem" \
  "$nonce_hex" \
  "$pcr_selection"

if ! grep -qx 'result=verified' "$output_dir/quote/quote-verification.txt"; then
  echo "fresh TPM quote did not verify" >&2
  exit 5
fi

provider_registration_id=$(cat "$output_dir/provider/provider-registration-id.txt")
ek_sha256=$(sha256sum "$output_dir/provider/endorsement-key.public.tpm2b" | awk '{print $1}')
ak_sha256=$(sha256sum "$output_dir/attestation-key.public.pem" | awk '{print $1}')
nonce_sha256=$(printf '%s' "$nonce_hex" | sha256sum | awk '{print $1}')
quote_msg_sha256=$(sha256sum "$output_dir/quote/quote.msg" | awk '{print $1}')
quote_sig_sha256=$(sha256sum "$output_dir/quote/quote.sig" | awk '{print $1}')
quote_pcrs_sha256=$(sha256sum "$output_dir/quote/quote.pcrs" | awk '{print $1}')
prepared_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [[ "$provider_registration_id" != "$ek_sha256" ]]; then
  echo "provider registration alias does not match EK public bytes" >&2
  exit 6
fi

cat >"$output_dir/a4-public-manifest.json" <<JSON
{
  "schema_version": "ets.fleet.physical-tpm-a4.device-proof.v1",
  "provider_registration_id": "$provider_registration_id",
  "endorsement_key_fingerprint_sha256": "$ek_sha256",
  "attestation_key_public_sha256": "$ak_sha256",
  "challenge_sha256": "$nonce_sha256",
  "pcr_selection": "$pcr_selection",
  "quote_message_sha256": "$quote_msg_sha256",
  "quote_signature_sha256": "$quote_sig_sha256",
  "quote_pcrs_sha256": "$quote_pcrs_sha256",
  "fresh_tpm_quote_verified": true,
  "tpm_possession_proven": true,
  "hardware_attested": false,
  "azure_control_plane_qualified": false,
  "device_side_provisioning_qualified": false,
  "private_key_material_exported": false,
  "shared_or_sas_credential_used": false,
  "prepared_at_utc": "$prepared_at"
}
JSON

(
  cd "$output_dir"
  sha256sum \
    provider/endorsement-key.public.tpm2b \
    provider/endorsement-key.public.b64 \
    provider/provider-registration-id.txt \
    attestation-key.public.pem \
    quote/qualification-nonce.hex \
    quote/pcr-selection.txt \
    quote/quote.msg \
    quote/quote.sig \
    quote/quote.pcrs \
    quote/quote-verification.txt \
    a4-public-manifest.json >a4-private-bundle.sha256
)

printf 'Physical TPM A4 proof prepared at %s\n' "$output_dir"
printf 'Provider registration alias: %s\n' "$provider_registration_id"
printf '%s\n' 'STOP BOUNDARY: no Azure credential or DPS mutation occurred on the device.'
