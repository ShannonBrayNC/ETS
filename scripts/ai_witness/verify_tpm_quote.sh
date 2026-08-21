#!/usr/bin/env bash
set -euo pipefail

umask 077

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "usage: $0 QUOTE_DIR AK_PUBLIC_PEM NONCE_HEX [PCR_SELECTION]" >&2
  exit 2
fi

quote_dir=$1
ak_public=$2
nonce_hex=$3
pcr_selection=${4:-sha256:0,2,4,7}

if [[ ! -r "$ak_public" ]]; then
  echo "AK public key is not readable: $ak_public" >&2
  exit 3
fi
if [[ ! "$nonce_hex" =~ ^[0-9A-Fa-f]+$ ]] || (( ${#nonce_hex} % 2 != 0 )); then
  echo "NONCE_HEX must contain an even number of hexadecimal characters" >&2
  exit 3
fi
if [[ ! "$pcr_selection" =~ ^sha256:[0-9,]+$ ]]; then
  echo "PCR_SELECTION must use the form sha256:0,2,4,7" >&2
  exit 3
fi

for artifact in quote.msg quote.sig quote.pcrs; do
  if [[ ! -r "$quote_dir/$artifact" ]]; then
    echo "quote artifact is not readable: $quote_dir/$artifact" >&2
    exit 4
  fi
done

for command_name in tpm2_checkquote sha256sum date; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "required command not found: $command_name" >&2
    exit 5
  fi
done

result_file="$quote_dir/quote-verification.txt"
{
  printf 'verified_at_utc='
  date -u +%Y-%m-%dT%H:%M:%SZ
  printf 'pcr_selection=%s\n' "$pcr_selection"
  printf 'nonce_sha256='
  printf '%s' "$nonce_hex" | sha256sum | awk '{print $1}'
  printf 'ak_public_sha256='
  sha256sum "$ak_public" | awk '{print $1}'
} >"$result_file"

if tpm2_checkquote \
  -u "$ak_public" \
  -m "$quote_dir/quote.msg" \
  -s "$quote_dir/quote.sig" \
  -f "$quote_dir/quote.pcrs" \
  -g sha256 \
  -q "$nonce_hex" \
  -l "$pcr_selection" \
  >>"$result_file" 2>"$quote_dir/quote-verification.stderr"; then
  printf '%s\n' 'result=verified' >>"$result_file"
else
  status=$?
  printf 'result=failed\nexit_code=%d\n' "$status" >>"$result_file"
  exit "$status"
fi

printf 'TPM quote verification succeeded: %s\n' "$result_file"
