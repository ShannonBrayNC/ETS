#!/usr/bin/env bash
set -euo pipefail

umask 077

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "usage: $0 OUTPUT_DIR AK_CONTEXT NONCE_HEX [PCR_SELECTION]" >&2
  exit 2
fi

output_dir=$1
ak_context=$2
nonce_hex=$3
pcr_selection=${4:-sha256:0,2,4,7}

if [[ ! "$nonce_hex" =~ ^[0-9A-Fa-f]+$ ]] || (( ${#nonce_hex} % 2 != 0 )); then
  echo "NONCE_HEX must contain an even number of hexadecimal characters" >&2
  exit 3
fi
if (( ${#nonce_hex} < 32 || ${#nonce_hex} > 128 )); then
  echo "NONCE_HEX must encode between 16 and 64 bytes" >&2
  exit 3
fi
if [[ -z "$ak_context" || "$ak_context" == *$'\0'* ]]; then
  echo "AK_CONTEXT must be a non-empty TPM context path or persistent handle" >&2
  exit 3
fi
if [[ ! "$pcr_selection" =~ ^sha256:[0-9,]+$ ]]; then
  echo "PCR_SELECTION must use the form sha256:0,2,4,7" >&2
  exit 3
fi

for command_name in tpm2_quote sha256sum date; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "required command not found: $command_name" >&2
    exit 4
  fi
done

mkdir -p "$output_dir"
printf '%s\n' "$nonce_hex" >"$output_dir/qualification-nonce.hex"
printf '%s\n' "$pcr_selection" >"$output_dir/pcr-selection.txt"
printf '%s\n' "$ak_context" >"$output_dir/ak-context.txt"
date -u +%Y-%m-%dT%H:%M:%SZ >"$output_dir/quote-requested-at.txt"

tpm2_quote \
  -Q \
  -c "$ak_context" \
  -l "$pcr_selection" \
  -q "$nonce_hex" \
  -m "$output_dir/quote.msg" \
  -s "$output_dir/quote.sig" \
  -o "$output_dir/quote.pcrs" \
  -g sha256

(
  cd "$output_dir"
  sha256sum quote.msg quote.sig quote.pcrs >quote-artifacts.sha256
)

printf 'Nonce-bound TPM quote written to %s\n' "$output_dir"
