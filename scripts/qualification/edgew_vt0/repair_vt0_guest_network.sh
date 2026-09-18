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

for cmd in virsh virt-customize virt-cat qemu-img awk mktemp uname install ping ip timeout bash grep; do
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
SSH_PUB="${HOME}/.ssh/edgew_vt0.pub"
if [[ ! -f "$OS_DISK" ]]; then
  echo "ERROR: expected OS disk not found: $OS_DISK" >&2
  exit 2
fi
if [[ ! -r "$SSH_PUB" ]]; then
  echo "ERROR: dedicated VT0 SSH public key not found: $SSH_PUB" >&2
  exit 2
fi

mac_for_network() {
  local network="$1"
  # Consume the complete virsh stream. Do not exit awk early: with
  # set -o pipefail, an early consumer exit can SIGPIPE virsh and cause a
  # silent set -e termination inside command substitution.
  virsh --connect qemu:///system domiflist "$VM_NAME" \
    | awk -v want="$network" '$3 == want && !found {print $5; found=1}'
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
      addresses:
        - 192.168.250.10/24
      routes:
        - to: default
          via: 192.168.250.1
          metric: 100
      nameservers:
        addresses:
          - 192.168.250.1
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
echo "  management:  $MGMT_MAC -> 192.168.250.10/24 via 192.168.250.1"
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
shopt -s nullglob
existing_backups=("${OS_DISK}.pre-network-"*.qcow2)
shopt -u nullglob

if (( ${#existing_backups[@]} > 0 )); then
  BACKUP="${existing_backups[${#existing_backups[@]}-1]}"
  echo "Reusing retained pre-network backup: $BACKUP"
else
  BACKUP="${OS_DISK}.pre-network-${TIMESTAMP}.qcow2"
  echo "Creating stopped-guest qcow2 backup: $BACKUP"
  qemu-img convert -p -O qcow2 "$OS_DISK" "$BACKUP"
fi

VM_DIR="$(dirname "$OS_DISK")"
LIBGUESTFS_DIR="${STORAGE_ROOT}/libguestfs"
KVER="$(uname -r)"
HOST_KERNEL="/boot/vmlinuz-${KVER}"
HOST_MODULES="/lib/modules/${KVER}"
SUPERMIN_KERNEL_COPY="${LIBGUESTFS_DIR}/vmlinuz-${KVER}"
CUSTOMIZE_LOG="${VM_DIR}/virt-customize-network-repair.log"

if [[ ! -f "$HOST_KERNEL" ]]; then
  echo "ERROR: running-kernel image not found: $HOST_KERNEL" >&2
  exit 4
fi
if [[ ! -d "$HOST_MODULES" ]]; then
  echo "ERROR: running-kernel modules not found: $HOST_MODULES" >&2
  exit 4
fi

mkdir -p "$LIBGUESTFS_DIR"
if [[ ! -r "$HOST_KERNEL" ]]; then
  echo "Host kernel is not readable by the operator; creating a controlled readable copy for supermin."
  sudo install -m 0644 "$HOST_KERNEL" "$SUPERMIN_KERNEL_COPY"
else
  install -m 0644 "$HOST_KERNEL" "$SUPERMIN_KERNEL_COPY"
fi

echo "Discovering guest SSH account..."
GUEST_PASSWD="$(
  env \
    SUPERMIN_KERNEL="$SUPERMIN_KERNEL_COPY" \
    SUPERMIN_MODULES="$HOST_MODULES" \
    LIBGUESTFS_BACKEND=direct \
    virt-cat -a "$OS_DISK" /etc/passwd
)"

if grep -q '^ubuntu:' <<<"$GUEST_PASSWD"; then
  GUEST_USER="ubuntu"
else
  GUEST_USER="$(
    awk -F: '
      $3 >= 1000 && $3 < 65534 &&
      $6 ~ /^\/home\// &&
      $7 !~ /(nologin|false)$/ {
        print $1
        exit
      }
    ' <<<"$GUEST_PASSWD"
  )"
fi

CREATE_GUEST_USER=0
if [[ -z "$GUEST_USER" ]]; then
  GUEST_USER="etsadmin"
  CREATE_GUEST_USER=1
  echo "No normal interactive guest account exists; canonical VT0 account will be created: $GUEST_USER"
else
  echo "Detected guest SSH account: $GUEST_USER"
fi

GUEST_ACCOUNT_ARGS=()
if [[ "$CREATE_GUEST_USER" -eq 1 ]]; then
  GUEST_ACCOUNT_ARGS+=(
    --run-command "useradd -m -s /bin/bash -G sudo $GUEST_USER"
    --run-command "passwd -l $GUEST_USER"
    --run-command "printf '%s\\n' '$GUEST_USER ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/90-ets-vt0"
    --run-command "chmod 0440 /etc/sudoers.d/90-ets-vt0"
  )
fi

echo "VT0 SSH account: $GUEST_USER"
echo "Applying deterministic guest network configuration and SSH access offline..."
echo "  supermin kernel:  $SUPERMIN_KERNEL_COPY"
echo "  supermin modules: $HOST_MODULES"
echo "  log:              $CUSTOMIZE_LOG"

if ! env \
  SUPERMIN_KERNEL="$SUPERMIN_KERNEL_COPY" \
  SUPERMIN_MODULES="$HOST_MODULES" \
  LIBGUESTFS_BACKEND=direct \
  virt-customize \
    -a "$OS_DISK" \
    --run-command 'rm -f /etc/netplan/50-cloud-init.yaml' \
    --upload "$NETPLAN:/etc/netplan/90-ets-vt0.yaml" \
    --chmod 0600:/etc/netplan/90-ets-vt0.yaml \
    --upload "$CLOUDCFG:/etc/cloud/cloud.cfg.d/99-ets-network-config.cfg" \
    --chmod 0644:/etc/cloud/cloud.cfg.d/99-ets-network-config.cfg \
    --run-command 'netplan generate' \
    --install openssh-server \
    "${GUEST_ACCOUNT_ARGS[@]}" \
    --ssh-inject "$GUEST_USER:file:$SSH_PUB" \
    --run-command 'ssh-keygen -A' \
    --run-command 'systemctl enable ssh.socket 2>/dev/null || systemctl enable ssh.service' \
    --run-command 'test -x /usr/sbin/sshd' \
    > >(tee "$CUSTOMIZE_LOG") 2>&1
then
  echo "ERROR: offline guest customization failed." >&2
  echo "Retained log: $CUSTOMIZE_LOG" >&2
  echo "Backup remains untouched: $BACKUP" >&2
  echo "For deeper diagnostics, run:" >&2
  echo "  LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1 SUPERMIN_KERNEL='$SUPERMIN_KERNEL_COPY' SUPERMIN_MODULES='$HOST_MODULES' LIBGUESTFS_BACKEND=direct virt-customize -v -x -a '$OS_DISK' ..." >&2
  exit 4
fi

echo "Starting guest..."
virsh --connect qemu:///system start "$VM_NAME"

MGMT_IP="192.168.250.10"
echo "Waiting for deterministic management address and SSH: $MGMT_IP"
for _ in {1..30}; do
  ping_ok=0
  ssh_ok=0
  if ping -c 1 -W 1 "$MGMT_IP" >/dev/null 2>&1; then
    ping_ok=1
  fi
  if timeout 2 bash -c "cat < /dev/null > /dev/tcp/${MGMT_IP}/22" >/dev/null 2>&1; then
    ssh_ok=1
  fi
  if [[ "$ping_ok" -eq 1 && "$ssh_ok" -eq 1 ]]; then
    echo "Management address reachable: $MGMT_IP"
    echo "SSH port reachable: $MGMT_IP:22"
    echo "SSH with: ssh -o IdentitiesOnly=yes -i ~/.ssh/edgew_vt0 $GUEST_USER@$MGMT_IP"
    echo "Backup retained: $BACKUP"
    exit 0
  fi
  sleep 2
done

echo "WARNING: guest restarted but management readiness did not complete within 60 seconds." >&2
echo "Host route/neighbor observations:" >&2
ip route get "$MGMT_IP" >&2 || true
ip neigh show dev virbr250 >&2 || true
echo "SSH probe:" >&2
timeout 2 bash -c "cat < /dev/null > /dev/tcp/${MGMT_IP}/22" >&2 || true
echo "Inspect with: virsh --connect qemu:///system console $VM_NAME" >&2
echo "Backup retained: $BACKUP" >&2
exit 4
