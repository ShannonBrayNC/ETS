#!/usr/bin/env bash
set -euo pipefail

umask 077

if [[ $# -ne 1 ]]; then
  echo "usage: $0 OUTPUT_DIR" >&2
  exit 2
fi

output_dir=$1
mkdir -p "$output_dir"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "required command not found: $1" >&2
    exit 3
  fi
}

require_command tpm2_getcap
require_command tpm2_pcrread
require_command sha256sum
require_command uname
require_command date

capture() {
  local name=$1
  shift
  "$@" >"$output_dir/$name" 2>"$output_dir/$name.stderr"
}

capture timestamp.txt date -u +%Y-%m-%dT%H:%M:%SZ
capture uname.txt uname -a

if [[ -r /etc/os-release ]]; then
  cp /etc/os-release "$output_dir/os-release.txt"
fi

capture tpm-properties-fixed.yaml tpm2_getcap properties-fixed
capture tpm-algorithms.yaml tpm2_getcap algorithms
capture tpm-ecc-curves.yaml tpm2_getcap ecc-curves
capture tpm-pcr-banks.yaml tpm2_getcap pcrs
capture pcr-sha256.yaml tpm2_pcrread sha256

if command -v mokutil >/dev/null 2>&1; then
  capture secure-boot.txt mokutil --sb-state
else
  printf '%s\n' "mokutil unavailable; inspect UEFI SecureBoot variable separately" \
    >"$output_dir/secure-boot.txt"
fi

if [[ -d /sys/firmware/efi ]]; then
  printf '%s\n' "uefi=true" >"$output_dir/uefi-state.txt"
else
  printf '%s\n' "uefi=false" >"$output_dir/uefi-state.txt"
fi

event_log=/sys/kernel/security/tpm0/binary_bios_measurements
if [[ -r "$event_log" ]]; then
  cp "$event_log" "$output_dir/tcg-event-log.bin"
  sha256sum "$output_dir/tcg-event-log.bin" >"$output_dir/tcg-event-log.sha256"
else
  printf '%s\n' "TPM event log unavailable at $event_log" \
    >"$output_dir/tcg-event-log.unavailable.txt"
fi

if [[ -r /sys/class/dmi/id/product_name ]]; then
  cp /sys/class/dmi/id/product_name "$output_dir/product-name.txt"
fi
if [[ -r /sys/class/dmi/id/product_version ]]; then
  cp /sys/class/dmi/id/product_version "$output_dir/product-version.txt"
fi
if [[ -r /sys/class/dmi/id/bios_vendor ]]; then
  cp /sys/class/dmi/id/bios_vendor "$output_dir/bios-vendor.txt"
fi
if [[ -r /sys/class/dmi/id/bios_version ]]; then
  cp /sys/class/dmi/id/bios_version "$output_dir/bios-version.txt"
fi
if [[ -r /sys/class/dmi/id/bios_date ]]; then
  cp /sys/class/dmi/id/bios_date "$output_dir/bios-date.txt"
fi

(
  cd "$output_dir"
  find . -maxdepth 1 -type f ! -name 'manifest.sha256' -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    >manifest.sha256
)

printf 'AI Witness platform evidence written to %s\n' "$output_dir"
