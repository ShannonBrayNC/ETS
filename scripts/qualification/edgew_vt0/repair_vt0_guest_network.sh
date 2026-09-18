#!/usr/bin/env bash
set -euo pipefail

VM_NAME="edgew-rt0-vt0-dut"
STORAGE_ROOT="/srv/ets-lab"
APPLY=0

usage() {
  cat <<'EOF'
Usage:
  repair_vt0_guest_network.sh [--vm NAME] [--storage-root PATH] [--apply]

Default behavior is plan-only. --apply is required before the guest disk is
modified. The script never force-destroys a running VM.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vm) VM_NAME="${2:?missing value for --vm}"; shift 2 ;;
    --storage-root) STORAGE_ROOT="${2:?missing value for --storage-root}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for cmd in virsh virt-customize qemu-img awk mktemp; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    if [[ "$cmd" == "virt-customize" ]]; then
      echo "Install it with: sudo apt-get install -y libguestfs-tools" >&2
    fi
    exit 2
  }
done

if ! virsh --connect qemu:///system dominfo "$VM_NAME" >/dev/null 2>&1; then
  echo "ERROR: libvirt domain not found: $VM_NAME" >&2
  exit 2
fi

OS_DISK="${STORAGE_ROOT}/${VM_NAME}/${VM_NAME}-os.qcow2"
if [[ ! -f "$OS_DISK" ]]; then
  echo "ERROR: expected OS disk not found: $OS_DISK" >&2
  exit 2
fi

mac_for_network() {
  local network="$1"
  virsh --connect qemu:///system domiflist "$VM_NAME"     | awk -v want="$network" '$3 == want {print $5; exit}'
}

MGMT_MAC="$(mac_for_network edgew-vt-mgmt)"
SOURCE_MAC="$(mac_for_network edgew-vt-source)"
UPSTREAM_MAC="$(mac_for_network edgew-vt-upstream)"
FAULT_MAC="$(mac_for_network edgew-vt-fault)"

for pair in   "management:$MGMT_MAC"   "source:$SOURCE_MAC"   "upstream:$UPSTREAM_MAC"   "fault:$FAULT_MAC"
do
  role="${pair%%:*}"
  mac="${pair#*:}"
  if [[ -z "$mac" ]]; then
    echo "ERROR: could not resolve $role MAC from libvirt domain." >&2
    exit 2
  fi
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
NETPLAN="$TMP/90-ets-vt0.yaml"
CLOUDCFG="$TMP/99-ets-network-config.cfg"

cat >"$NETPLAN" <<EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    vtmgmt:
      match:
        macaddress: "$MGMT_MAC"
      set-name: vtmgmt
      dhcp4: true
      dhcp4-overrides:
        route-metric: 100
      optional: false
    vtsource:
      match:
        macaddress: "$SOURCE_MAC"
      set-name: vtsource
      addresses:
        - 192.168.251.10/24
      optional: true
    vtupstream:
      match:
        macaddress: "$UPSTREAM_MAC"
      set-name: vtupstream
      addresses:
        - 192.168.252.10/24
      optional: true
    vtfault:
      match:
        macaddress: "$FAULT_MAC"
      set-name: vtfault
      addresses:
        - 192.168.253.10/24
      optional: true
EOF

cat >"$CLOUDCFG" <<'EOF'
network:
  config: disabled
EOF

echo "EDGEW-RT0-VT0 guest-network repair plan"
echo "  domain:      $VM_NAME"
echo "  OS disk:     $OS_DISK"
echo "  management:  $MGMT_MAC -> DHCP on edgew-vt-mgmt"
echo "  source:      $SOURCE_MAC -> 192.168.251.10/24"
echo "  upstream:    $UPSTREAM_MAC -> 192.168.252.10/24"
echo "  fault:       $FAULT_MAC -> 192.168.253.10/24"
echo "  default route: management only"
echo
cat "$NETPLAN"

if [[ "$APPLY" -ne 1 ]]; then
  echo
  echo "PLAN ONLY: no guest disk or VM state was changed."
  echo "Re-run with --apply after reviewing the MAC/role mapping."
  exit 0
fi

state="$(virsh --connect qemu:///system domstate "$VM_NAME" | tr -d '\r' | xargs)"
if [[ "$state" == "running" ]]; then
  echo "Requesting graceful guest shutdown..."
  virsh --connect qemu:///system shutdown "$VM_NAME"
  for _ in {1..30}; do
    sleep 2
    state="$(virsh --connect qemu:///system domstate "$VM_NAME" | tr -d '\r' | xargs)"
    [[ "$state" == "shut off" ]] && break
  done
fi

if [[ "$state" != "shut off" ]]; then
  echo "ERROR: guest did not reach 'shut off'; refusing offline disk edit." >&2
  echo "Current state: $state" >&2
  echo "No force-destroy was attempted." >&2
  exit 3
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="${OS_DISK}.pre-network-${TIMESTAMP}.qcow2"

echo "Creating stopped-guest qcow2 backup: $BACKUP"
qemu-img convert -p -O qcow2 "$OS_DISK" "$BACKUP"

echo "Applying deterministic guest network configuration offline..."
virt-customize   -a "$OS_DISK"   --run-command 'rm -f /etc/netplan/50-cloud-init.yaml'   --upload "$NETPLAN:/etc/netplan/90-ets-vt0.yaml"   --chmod 0600:/etc/netplan/90-ets-vt0.yaml   --upload "$CLOUDCFG:/etc/cloud/cloud.cfg.d/99-ets-network-config.cfg"   --chmod 0644:/etc/cloud/cloud.cfg.d/99-ets-network-config.cfg

echo "Starting guest..."
virsh --connect qemu:///system start "$VM_NAME"

echo "Waiting for management DHCP lease..."
for _ in {1..30}; do
  lease="$(virsh --connect qemu:///system net-dhcp-leases edgew-vt-mgmt     | awk -v mac="$MGMT_MAC" 'tolower($2) == tolower(mac) {print $5; exit}')"
  if [[ -n "$lease" ]]; then
    echo "Management lease observed: $lease"
    echo "SSH with: ssh -i ~/.ssh/edgew_vt0 ubuntu@${lease%/*}"
    echo "Backup retained: $BACKUP"
    exit 0
  fi
  sleep 2
done

echo "WARNING: guest restarted but no management DHCP lease was observed within 60 seconds." >&2
echo "Inspect with: virsh --connect qemu:///system console $VM_NAME" >&2
echo "Backup retained: $BACKUP" >&2
exit 4
