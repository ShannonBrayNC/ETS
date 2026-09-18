#!/usr/bin/env bash
set -euo pipefail

VM_NAME="edgew-rt0-vt0-dut"
GUEST_HOST="192.168.250.10"
GUEST_USER="etsadmin"
SSH_KEY="${HOME}/.ssh/edgew_vt0"
OUT_ROOT="/srv/ets-lab/evidence/vt0-guest-baseline"

usage() {
  cat <<'EOF'
Usage:
  capture_vt0_guest_baseline.sh [--vm NAME] [--host IP] [--user USER]
                                [--ssh-key PATH] [--out-root PATH]

Captures a read-only host+guest baseline before the 512 GiB qualification
disk is initialized. The guest is observed over SSH; no guest state is changed.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vm) VM_NAME="${2:?missing value for --vm}"; shift 2 ;;
    --host) GUEST_HOST="${2:?missing value for --host}"; shift 2 ;;
    --user) GUEST_USER="${2:?missing value for --user}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:?missing value for --ssh-key}"; shift 2 ;;
    --out-root) OUT_ROOT="${2:?missing value for --out-root}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for cmd in ssh virsh qemu-img python3 sha256sum date find; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 2
  }
done

[[ -r "$SSH_KEY" ]] || {
  echo "ERROR: SSH private key not readable: $SSH_KEY" >&2
  exit 2
}

virsh --connect qemu:///system dominfo "$VM_NAME" >/dev/null 2>&1 || {
  echo "ERROR: libvirt domain not found: $VM_NAME" >&2
  exit 2
}

SSH=(
  ssh
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=5
  -i "$SSH_KEY"
  "${GUEST_USER}@${GUEST_HOST}"
)

"${SSH[@]}" 'id >/dev/null && sudo -n true' || {
  echo "ERROR: SSH/sudo preflight failed for ${GUEST_USER}@${GUEST_HOST}" >&2
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

# Independent host-side observations.
capture_host host-dominfo.txt virsh --connect qemu:///system dominfo "$VM_NAME"
capture_host host-domstate.txt virsh --connect qemu:///system domstate "$VM_NAME" --reason
capture_host host-dumpxml.xml virsh --connect qemu:///system dumpxml "$VM_NAME"
capture_host host-domblklist.txt virsh --connect qemu:///system domblklist "$VM_NAME" --details
capture_host host-domiflist.txt virsh --connect qemu:///system domiflist "$VM_NAME"
capture_host host-vcpupin.txt virsh --connect qemu:///system vcpupin "$VM_NAME"
capture_host host-numatune.txt virsh --connect qemu:///system numatune "$VM_NAME"
capture_host host-mgmt-neighbor.txt ip neigh show dev virbr250
capture_host host-route-to-guest.txt ip route get "$GUEST_HOST"

QUAL_HOST_PATH="/srv/ets-lab/${VM_NAME}/${VM_NAME}-qualification.qcow2"
if [[ -f "$QUAL_HOST_PATH" ]]; then
  capture_host host-qualification-qemu-img.json qemu-img info --output=json "$QUAL_HOST_PATH"
fi

# Guest-side observations. These commands are read-only.
capture_guest guest-date.txt "date -u --iso-8601=seconds"
capture_guest guest-id.txt "id; sudo -n true && echo sudo_noninteractive=true"
capture_guest guest-hostnamectl.txt "hostnamectl"
capture_guest guest-uname.txt "uname -a"
capture_guest guest-os-release.txt "cat /etc/os-release"
capture_guest guest-ip-addr.json "ip -j addr"
capture_guest guest-ip-route.json "ip -j route"
capture_guest guest-lsblk.json "lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,SERIAL"
capture_guest guest-findmnt.json "findmnt -J"
capture_guest guest-blkid.txt "sudo blkid || true"
capture_guest guest-fstab.txt "sudo cat /etc/fstab"
capture_guest guest-netplan.txt "sudo cat /etc/netplan/90-ets-vt0.yaml"
capture_guest guest-cloud-network-disable.txt "sudo cat /etc/cloud/cloud.cfg.d/99-ets-network-config.cfg 2>/dev/null || true"
capture_guest guest-ssh-status.txt "sudo systemctl status ssh.socket ssh.service --no-pager || true"
capture_guest guest-listeners.txt "sudo ss -lntp"
capture_guest guest-tpm-devices.txt "ls -l /dev/tpm* 2>/dev/null || true"
capture_guest guest-tpm-dmesg.txt "sudo dmesg | grep -i -E 'tpm|secure' || true"
capture_guest guest-tpm-capabilities.txt "if command -v tpm2_getcap >/dev/null 2>&1; then sudo tpm2_getcap properties-fixed; else echo tpm2_getcap_not_installed; fi"
capture_guest guest-secure-boot.txt "if command -v mokutil >/dev/null 2>&1; then mokutil --sb-state; else echo mokutil_not_installed; fi"

# Exact pristine qualification-disk observations.
capture_guest qual-device-size.txt "sudo blockdev --getsize64 /dev/vdb"
capture_guest qual-device-udev.txt "sudo udevadm info --query=property --name=/dev/vdb"
capture_guest qual-device-wipefs.txt "sudo wipefs -n /dev/vdb"
capture_guest qual-device-sfdisk.txt "sudo sfdisk -d /dev/vdb 2>&1 || true"

python3 - "$OUT_DIR" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

out = Path(sys.argv[1])

def read(name: str) -> str:
    return (out / name).read_text(errors="replace")

lsblk = json.loads(read("guest-lsblk.json"))
addr = json.loads(read("guest-ip-addr.json"))
routes = json.loads(read("guest-ip-route.json"))

blocks = {item["name"]: item for item in lsblk["blockdevices"]}
vda = blocks.get("vda")
vdb = blocks.get("vdb")

addresses: dict[str, set[str]] = {}
for iface in addr:
    addresses[iface["ifname"]] = {
        info.get("local", "")
        for info in iface.get("addr_info", [])
        if info.get("family") == "inet"
    }

default_routes = [
    route for route in routes
    if route.get("dst") == "default"
]

wipefs_text = read("qual-device-wipefs.txt").strip()
sfdisk_text = read("qual-device-sfdisk.txt").lower()
tpm_text = read("guest-tpm-devices.txt")
listeners = read("guest-listeners.txt")
guest_id = read("guest-id.txt")
host_state = read("host-domstate.txt").strip().lower()

checks = {
    "domain_running_from_host": host_state.startswith("running"),
    "guest_operator_is_etsadmin": bool(re.search(r"uid=\d+\(etsadmin\)", guest_id)),
    "guest_noninteractive_sudo": "sudo_noninteractive=true" in guest_id,
    "management_address": "192.168.250.10" in addresses.get("vtmgmt", set()),
    "source_address": "192.168.251.10" in addresses.get("vtsource", set()),
    "upstream_address": "192.168.252.10" in addresses.get("vtupstream", set()),
    "fault_address": "192.168.253.10" in addresses.get("vtfault", set()),
    "single_default_route_on_management": (
        len(default_routes) == 1
        and default_routes[0].get("dev") == "vtmgmt"
        and default_routes[0].get("gateway") == "192.168.250.1"
    ),
    "os_disk_is_64_gib": bool(
        vda and vda.get("type") == "disk" and vda.get("size") == 64 * 1024**3
    ),
    "qualification_disk_is_512_gib": bool(
        vdb and vdb.get("type") == "disk" and vdb.get("size") == 512 * 1024**3
    ),
    "qualification_disk_has_no_children": bool(vdb and not vdb.get("children")),
    "qualification_disk_has_no_filesystem": bool(vdb and not vdb.get("fstype")),
    "qualification_disk_has_no_wipefs_signatures": wipefs_text == "",
    "qualification_disk_has_no_partition_table": (
        "does not contain a recognized partition table" in sfdisk_text
        or "unrecognized partition table" in sfdisk_text
        or "no partition table" in sfdisk_text
        or sfdisk_text.strip() == ""
    ),
    "tpm0_present": "/dev/tpm0" in tpm_text,
    "tpmrm0_present": "/dev/tpmrm0" in tpm_text,
    "ssh_listening_on_22": bool(re.search(r":22\s", listeners)),
}

summary = {
    "schema": "ets.edgew.vt0.guest-pristine-baseline.v1",
    "claim_state": "simulated",
    "qualification_disk_target": "/dev/vdb",
    "checks": checks,
    "all_pristine_checks_pass": all(checks.values()),
    "claim_boundary": (
        "vt0_pristine_guest_baseline_only_not_physical_hardware_qualification_"
        "truth_completeness_compliance_safety_or_production_readiness"
    ),
}
(out / "guest-baseline-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
PY

(
  cd "$OUT_DIR"
  find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name SHA256SUMS.verify.txt -printf '%P\n'     | sort     | xargs -r sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS > SHA256SUMS.verify.txt
)

chmod -R go-rwx "$OUT_DIR"

echo
echo "Captured pristine VT0 guest baseline: $OUT_DIR"
echo "Summary: $OUT_DIR/guest-baseline-summary.json"
echo "Manifest self-check: $OUT_DIR/SHA256SUMS.verify.txt"
echo "Do not initialize /dev/vdb unless all_pristine_checks_pass is true."
echo "This remains simulated VT0 evidence, not physical EDGE-RT0 qualification."
