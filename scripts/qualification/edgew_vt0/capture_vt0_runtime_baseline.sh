#!/usr/bin/env bash
set -euo pipefail

VM_NAME="${1:-edgew-rt0-vt0-dut}"
DEFAULT_OUT_ROOT="/var/lib/ets-lab/evidence/vt0-runtime"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${2:-${DEFAULT_OUT_ROOT}/${VM_NAME}-${TIMESTAMP}}"

for cmd in virsh qemu-img python3 sha256sum; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 2
  }
done

if ! virsh --connect qemu:///system dominfo "$VM_NAME" >/dev/null 2>&1; then
  echo "ERROR: libvirt domain not found: $VM_NAME" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

capture() {
  local name="$1"
  shift
  "$@" >"${OUT_DIR}/${name}" 2>&1 || true
}

capture dominfo.txt virsh --connect qemu:///system dominfo "$VM_NAME"
capture domstate.txt virsh --connect qemu:///system domstate "$VM_NAME"
capture dumpxml.xml virsh --connect qemu:///system dumpxml "$VM_NAME"
capture vcpupin.txt virsh --connect qemu:///system vcpupin "$VM_NAME"
capture numatune.txt virsh --connect qemu:///system numatune "$VM_NAME"
capture domblklist.txt virsh --connect qemu:///system domblklist "$VM_NAME" --details
capture domiflist.txt virsh --connect qemu:///system domiflist "$VM_NAME"
capture domstats.txt virsh --connect qemu:///system domstats "$VM_NAME"
capture mgmt-dhcp-leases.txt virsh --connect qemu:///system net-dhcp-leases edgew-vt-mgmt
capture libvirt-version.txt virsh --connect qemu:///system version
uname -a >"${OUT_DIR}/host-uname.txt"
date -u --iso-8601=seconds >"${OUT_DIR}/captured-at.txt"

OS_DISK="/srv/ets-lab/${VM_NAME}/${VM_NAME}-os.qcow2"
QUAL_DISK="/srv/ets-lab/${VM_NAME}/${VM_NAME}-qualification.qcow2"

for disk in "$OS_DISK" "$QUAL_DISK"; do
  if [[ -f "$disk" ]]; then
    base="$(basename "$disk")"
    qemu-img info --output=json "$disk" >"${OUT_DIR}/${base}.qemu-img.json"
  fi
done

python3 - "$OUT_DIR" "$VM_NAME" "$OS_DISK" "$QUAL_DISK" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

out_dir = Path(sys.argv[1])
vm_name = sys.argv[2]
os_disk = Path(sys.argv[3])
qual_disk = Path(sys.argv[4])

xml_path = out_dir / "dumpxml.xml"
root = ET.fromstring(xml_path.read_text())

vcpu_text = root.findtext("vcpu")
vcpu = int(vcpu_text) if vcpu_text else None

memory = root.find("memory")
memory_kib = int(memory.text) if memory is not None and memory.text else None

interfaces = []
for iface in root.findall("./devices/interface"):
    source = iface.find("source")
    interfaces.append(source.get("network") if source is not None else None)

tpm = root.find("./devices/tpm")
tpm_model = tpm.get("model") if tpm is not None else None
backend = tpm.find("backend") if tpm is not None else None
tpm_version = backend.get("version") if backend is not None else None

loader = root.find("./os/loader")
firmware = root.get("firmware")

state_text = (out_dir / "domstate.txt").read_text(errors="replace").strip().lower()
running = state_text.startswith("running")

pin_text = (out_dir / "vcpupin.txt").read_text(errors="replace")
expected_pins = {"0": "0", "1": "2", "2": "4", "3": "6"}
actual_pins: dict[str, str] = {}
for line in pin_text.splitlines():
    m = re.match(r"^\s*(\d+)\s+([0-9,-]+)\s*$", line)
    if m:
        actual_pins[m.group(1)] = m.group(2)

numa_text = (out_dir / "numatune.txt").read_text(errors="replace")
numa_node0 = bool(re.search(r"nodeset\s*:\s*0\b", numa_text))
numa_strict = bool(re.search(r"mode\s*:\s*strict\b", numa_text))

def qemu_info(path: Path) -> dict[str, object] | None:
    p = out_dir / f"{path.name}.qemu-img.json"
    return json.loads(p.read_text()) if p.exists() else None

os_info = qemu_info(os_disk)
qual_info = qemu_info(qual_disk)

checks = {
    "domain_running": running,
    "vcpu_is_4": vcpu == 4,
    "memory_is_16_gib": memory_kib == 16 * 1024 * 1024,
    "cpu_pinning_matches_baseline": actual_pins == expected_pins,
    "numa_mode_strict": numa_strict,
    "numa_nodeset_0": numa_node0,
    "four_expected_networks_attached": set(interfaces)
    == {
        "edgew-vt-mgmt",
        "edgew-vt-source",
        "edgew-vt-upstream",
        "edgew-vt-fault",
    },
    "tpm_crb_present": tpm_model == "tpm-crb",
    "tpm_2_0_present": tpm_version == "2.0",
    "uefi_loader_present": loader is not None or firmware == "efi",
    "os_disk_qcow2_64_gib": bool(
        os_info
        and os_info.get("format") == "qcow2"
        and os_info.get("virtual-size") == 64 * 1024**3
    ),
    "qualification_disk_qcow2_512_gib": bool(
        qual_info
        and qual_info.get("format") == "qcow2"
        and qual_info.get("virtual-size") == 512 * 1024**3
    ),
}

lease_text = (out_dir / "mgmt-dhcp-leases.txt").read_text(errors="replace")
has_mgmt_lease = bool(re.search(r"\b192\.168\.250\.\d+/\d+\b", lease_text))

summary = {
    "schema": "ets.edgew.vt0.runtime-baseline.v1",
    "vm_name": vm_name,
    "checks": checks,
    "all_structural_checks_pass": all(checks.values()),
    "management_dhcp_lease_observed": has_mgmt_lease,
    "claim_state": "simulated",
    "claim_boundary": (
        "vt0_runtime_baseline_only_not_physical_hardware_qualification_"
        "truth_completeness_compliance_safety_or_production_readiness"
    ),
}

(out_dir / "runtime-baseline-summary.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
print(json.dumps(summary, indent=2))
PY

(
  cd "$OUT_DIR"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%P\n'     | sort     | xargs -r sha256sum > SHA256SUMS
)

chmod -R go-rwx "$OUT_DIR"

echo
echo "Captured VT0 runtime baseline: $OUT_DIR"
echo "Summary: $OUT_DIR/runtime-baseline-summary.json"
echo "Manifest: $OUT_DIR/SHA256SUMS"
echo "This is simulated VT0 runtime evidence, not physical EDGE-RT0 qualification."
