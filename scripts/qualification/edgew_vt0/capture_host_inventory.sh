#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-/var/lib/ets-lab/inventory}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${OUT_DIR}/edgew-vt0-host-${TIMESTAMP}.json"

mkdir -p "${OUT_DIR}"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

sudo dmidecode -t system > "${TMP}/system.txt" 2>/dev/null || true
sudo dmidecode -t baseboard > "${TMP}/baseboard.txt" 2>/dev/null || true
lscpu -J > "${TMP}/lscpu.json"
lsblk -J -o NAME,MODEL,SERIAL,SIZE,TYPE,FSTYPE,MOUNTPOINTS > "${TMP}/lsblk.json"
ip -j link > "${TMP}/links.json"
virsh --connect qemu:///system version > "${TMP}/virsh.txt" 2>&1 || true

python3 - "${TMP}" "${OUT}" <<'PY'
import json
import pathlib
import platform
import re
import socket
import sys
from datetime import datetime, timezone

src = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])

def text(name):
    p = src / name
    return p.read_text(errors="replace") if p.exists() else ""

def first(pattern, data):
    m = re.search(pattern, data, re.MULTILINE)
    return m.group(1).strip() if m else None

system = text("system.txt")
board = text("baseboard.txt")
lscpu = json.loads(text("lscpu.json") or '{"lscpu": []}')
lsblk = json.loads(text("lsblk.json") or '{"blockdevices": []}')
links = json.loads(text("links.json") or '[]')

cpu = {entry.get("field", "").rstrip(":"): entry.get("data") for entry in lscpu.get("lscpu", [])}
net = []
for link in links:
    net.append({
        "ifname": link.get("ifname"),
        "address": link.get("address"),
        "mtu": link.get("mtu"),
        "operstate": link.get("operstate"),
        "link_type": link.get("link_type"),
    })

doc = {
    "schema": "ets.edgew.vt0.host-inventory.v1",
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "hostname": socket.gethostname(),
    "kernel": platform.release(),
    "system": {
        "manufacturer": first(r"Manufacturer:\s*(.+)", system),
        "product_name": first(r"Product Name:\s*(.+)", system),
        "version": first(r"Version:\s*(.+)", system),
        "serial_number": first(r"Serial Number:\s*(.+)", system),
        "uuid": first(r"UUID:\s*(.+)", system),
    },
    "baseboard": {
        "manufacturer": first(r"Manufacturer:\s*(.+)", board),
        "product_name": first(r"Product Name:\s*(.+)", board),
        "version": first(r"Version:\s*(.+)", board),
        "serial_number": first(r"Serial Number:\s*(.+)", board),
    },
    "cpu": cpu,
    "block_devices": lsblk.get("blockdevices", []),
    "network_interfaces": net,
    "virtualization": {
        "kvm_device_present": pathlib.Path("/dev/kvm").exists(),
        "libvirt_version_output": text("virsh.txt").strip(),
    },
    "claim_boundary": "host_inventory_only_not_hardware_qualification_or_physical_dut_evidence",
}

out.write_text(json.dumps(doc, indent=2) + "\n")
print(out)
PY

chmod 0640 "${OUT}"
printf 'Captured host inventory: %s\n' "${OUT}"
printf 'Keep this file local or in controlled evidence storage; it can contain serial numbers and MAC addresses.\n'
