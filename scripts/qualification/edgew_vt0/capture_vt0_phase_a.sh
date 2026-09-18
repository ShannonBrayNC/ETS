#!/usr/bin/env bash
set -euo pipefail

VM_HOST="192.168.250.10"
VM_USER="etsadmin"
SSH_KEY="${HOME}/.ssh/edgew_vt0"
VM_NAME="edgew-rt0-vt0-dut"
QUAL_MOUNT="/var/lib/ets-qualification"
OUT_ROOT="/srv/ets-lab/evidence/vt0-phase-a"

usage() {
  cat <<'EOF'
Usage:
  capture_vt0_phase_a.sh [--host IP] [--user USER] [--ssh-key PATH]
                         [--vm NAME] [--out-root PATH]

Captures simulated VT0 evidence for:
  EDGE-HQP-BLD-001
  EDGE-HQP-ID-001
  EDGE-HQP-SEC-001

The script does not retain API-key or private signing-key bytes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) VM_HOST="${2:?missing value for --host}"; shift 2 ;;
    --user) VM_USER="${2:?missing value for --user}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:?missing value for --ssh-key}"; shift 2 ;;
    --vm) VM_NAME="${2:?missing value for --vm}"; shift 2 ;;
    --out-root) OUT_ROOT="${2:?missing value for --out-root}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for cmd in ssh virsh python3 sha256sum date; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $cmd" >&2
    exit 2
  }
done

SSH=(
  ssh
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=5
  -i "$SSH_KEY"
  "${VM_USER}@${VM_HOST}"
)

"${SSH[@]}" 'sudo -n true' || {
  echo "ERROR: guest SSH/sudo preflight failed." >&2
  exit 2
}

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OUT_ROOT}/${VM_NAME}-${TS}"
mkdir -p "$OUT_DIR"

capture_host() {
  local name="$1"
  shift
  "$@" >"${OUT_DIR}/${name}" 2>&1 || true
}

capture_guest() {
  local name="$1"
  shift
  "${SSH[@]}" "$*" >"${OUT_DIR}/${name}" 2>&1 || true
}

# Host observer context.
capture_host host-domstate.txt virsh --connect qemu:///system domstate "$VM_NAME" --reason
capture_host host-dumpxml.xml virsh --connect qemu:///system dumpxml "$VM_NAME"
capture_host host-domblklist.txt virsh --connect qemu:///system domblklist "$VM_NAME" --details
capture_host host-domiflist.txt virsh --connect qemu:///system domiflist "$VM_NAME"

# BLD-001: immutable build/config/provenance identity.
capture_guest bld-build-commit.txt "cat /opt/ets/current/.ets-build-commit"
capture_guest bld-source-archive-sha256.txt "cat /opt/ets/current/.ets-source-archive-sha256"
capture_guest bld-compose-config.txt "cd /opt/ets/current && sudo docker compose -f edge-demo/docker-compose.yml config"
capture_guest bld-compose-config-sha256.txt "cd /opt/ets/current && sudo docker compose -f edge-demo/docker-compose.yml config | sha256sum"
capture_guest bld-image-list.txt "cd /opt/ets/current && sudo docker compose -f edge-demo/docker-compose.yml images"
capture_guest bld-image-inspect.json "cd /opt/ets/current && ids=\$(sudo docker compose -f edge-demo/docker-compose.yml images -q | sort -u | tr '\n' ' '); sudo docker image inspect \$ids"
capture_guest bld-provenance.txt "sha=\$(cat /opt/ets/current/.ets-build-commit); sudo cat $QUAL_MOUNT/deployment-evidence/\$sha/build-provenance.txt"

# ID-001: virtual identity continuity and software key-custody boundary.
capture_guest id-before.json "curl -fsS http://127.0.0.1:8400/edge/v1/device/identity"
capture_guest id-key-metadata-before.txt "sudo stat -c '%n mode=%a uid=%u gid=%g size=%s' $QUAL_MOUNT/docker/volumes/*/_data/edge-demo-signing-key.hex 2>/dev/null || true"
capture_guest id-api-key-metadata-before.txt "sudo stat -c '%n mode=%a uid=%u gid=%g size=%s' $QUAL_MOUNT/docker/volumes/*/_data/edge-local-api-key 2>/dev/null || true"

"${SSH[@]}" "cd /opt/ets/current && sudo docker compose -f edge-demo/docker-compose.yml restart edge-api"   >"$OUT_DIR/id-restart-receipt.txt" 2>&1

for _ in {1..30}; do
  if "${SSH[@]}" "curl -fsS http://127.0.0.1:8400/edge/v1/device/identity"       >"$OUT_DIR/id-after.json" 2>/dev/null; then
    break
  fi
  sleep 2
done

[[ -s "$OUT_DIR/id-after.json" ]] || {
  echo "ERROR: device identity endpoint did not recover after edge-api restart." >&2
  exit 3
}

capture_guest id-key-metadata-after.txt "sudo stat -c '%n mode=%a uid=%u gid=%g size=%s' $QUAL_MOUNT/docker/volumes/*/_data/edge-demo-signing-key.hex 2>/dev/null || true"
capture_guest id-api-key-metadata-after.txt "sudo stat -c '%n mode=%a uid=%u gid=%g size=%s' $QUAL_MOUNT/docker/volumes/*/_data/edge-local-api-key 2>/dev/null || true"

# Search only retained evidence/config/log material, never secret file contents.
capture_guest id-secret-exposure-scan.txt "grep -RIlE 'BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY|edge-local-api-key[[:space:]]*=' $QUAL_MOUNT/deployment-evidence /opt/ets/current 2>/dev/null || true"

# SEC-001: observation only. No firmware/security mutation.
capture_guest sec-uefi.txt "test -d /sys/firmware/efi && echo uefi_present=true || echo uefi_present=false"
capture_guest sec-secure-boot.txt "if command -v mokutil >/dev/null 2>&1; then mokutil --sb-state; else echo mokutil_not_installed; fi"
capture_guest sec-storage.txt "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS; findmnt /; findmnt $QUAL_MOUNT"
capture_guest sec-crypt.txt "if command -v cryptsetup >/dev/null 2>&1; then sudo cryptsetup status root 2>&1 || true; else echo cryptsetup_not_installed; fi"
capture_guest sec-tpm.txt "ls -l /dev/tpm* 2>/dev/null || true; if command -v tpm2_getcap >/dev/null 2>&1; then sudo tpm2_getcap properties-fixed; else echo tpm2_getcap_not_installed; fi"
capture_guest sec-device-identity.json "curl -fsS http://127.0.0.1:8400/edge/v1/device/identity"
capture_guest sec-boot-cmdline.txt "cat /proc/cmdline"

python3 - "$OUT_DIR" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

out = Path(sys.argv[1])

def text(name: str) -> str:
    return (out / name).read_text(errors="replace").strip()

before = json.loads(text("id-before.json"))
after = json.loads(text("id-after.json"))
sec_identity = json.loads(text("sec-device-identity.json"))

build_commit = text("bld-build-commit.txt")
archive_digest = text("bld-source-archive-sha256.txt")
compose_digest_line = text("bld-compose-config-sha256.txt")
compose_digest = compose_digest_line.split()[0] if compose_digest_line else ""

secret_scan = text("id-secret-exposure-scan.txt")
secure_boot = text("sec-secure-boot.txt")
uefi = text("sec-uefi.txt")
tpm = text("sec-tpm.txt")
storage = text("sec-storage.txt")

device_id_before = before.get("device_id")
device_id_after = after.get("device_id")
custody = after.get("key_custody")
hardware_attested = after.get("hardware_attested")

checks = {
    "BLD": {
        "installed_build_identity_present": len(build_commit) == 40,
        "source_archive_digest_present": len(archive_digest) == 64,
        "configuration_digest_present": len(compose_digest) == 64,
        "provenance_material_retained": bool(text("bld-provenance.txt")),
    },
    "ID": {
        "device_identity_stable_across_restart": (
            bool(device_id_before) and device_id_before == device_id_after
        ),
        "declared_key_custody_is_software_volume": custody == "software_volume",
        "hardware_attestation_not_claimed": hardware_attested is False,
        "secret_exposure_scan_clear": secret_scan == "",
    },
    "SEC": {
        "uefi_observed": "uefi_present=true" in uefi,
        "secure_boot_state_observed": bool(secure_boot),
        "storage_posture_observed": bool(storage),
        "tpm_devices_observed": "/dev/tpm0" in tpm and "/dev/tpmrm0" in tpm,
        "edge_signer_not_misrepresented_as_tpm": (
            sec_identity.get("key_custody") == "software_volume"
            and sec_identity.get("hardware_attested") is False
        ),
    },
}

summary = {
    "schema": "ets.edgew.vt0.phase-a.v1",
    "claim_state": "simulated",
    "cases": {
        "EDGE-HQP-BLD-001": {
            "driver_id": "edge.build-identity.v1",
            "checks": checks["BLD"],
            "pass": all(checks["BLD"].values()),
            "limitation": "Virtual preflight build/provenance capture only.",
        },
        "EDGE-HQP-ID-001": {
            "driver_id": "edge.identity-enrollment.v1",
            "checks": checks["ID"],
            "pass": all(checks["ID"].values()),
            "limitation": (
                "Virtual identity continuity uses a software-held Ed25519 identity. "
                "This is not TPM/HSM custody, remote attestation, or physical enrollment."
            ),
        },
        "EDGE-HQP-SEC-001": {
            "driver_id": "edge.security-posture.v1",
            "checks": checks["SEC"],
            "pass": all(checks["SEC"].values()),
            "limitation": (
                "Observed VM UEFI/vTPM/storage posture only. The Edge signing identity "
                "remains software_volume and hardware_attested=false."
            ),
        },
    },
    "all_phase_a_cases_pass": all(
        all(group.values()) for group in checks.values()
    ),
    "claim_boundary": (
        "vt0_phase_a_simulated_preflight_not_physical_hardware_qualification_"
        "tpm_key_custody_secure_boot_certification_truth_completeness_or_production_readiness"
    ),
}

(out / "phase-a-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
PY

(
  cd "$OUT_DIR"
  find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name SHA256SUMS.verify.txt -printf '%P\n'     | sort | xargs -r sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS > SHA256SUMS.verify.txt
)

chmod -R go-rwx "$OUT_DIR"

echo
echo "VT0 Phase A evidence retained: $OUT_DIR"
echo "Summary: $OUT_DIR/phase-a-summary.json"
echo "This is simulated Phase A preflight evidence only, not physical EDGE-RT0 qualification."
