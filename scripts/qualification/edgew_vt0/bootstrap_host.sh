#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a dedicated Ubuntu host for EDGEW-RT0-VT0 qualification rehearsal.
# This script intentionally does not modify the host's physical NIC/netplan configuration.

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run this script as the normal operator account; it will use sudo when needed." >&2
  exit 2
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required." >&2
  exit 2
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify operating system." >&2
  exit 2
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "This bootstrap is intended for Ubuntu; detected ID=${ID:-unknown}." >&2
  exit 2
fi

OPERATOR="${SUDO_USER:-${USER}}"
STATE_DIR="/var/lib/ets-lab"

printf 'ETS EDGEW-RT0-VT0 dedicated host bootstrap\n'
printf 'Ubuntu: %s\n' "${PRETTY_NAME:-unknown}"
printf 'Operator: %s\n' "${OPERATOR}"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  qemu-kvm \
  libvirt-daemon-system \
  libvirt-clients \
  virtinst \
  ovmf \
  swtpm \
  swtpm-tools \
  cpu-checker \
  bridge-utils \
  jq \
  git \
  python3 \
  python3-venv \
  tcpdump \
  iperf3 \
  smartmontools

sudo systemctl enable --now libvirtd
sudo usermod -aG libvirt,kvm "${OPERATOR}"

sudo install -d -m 0750 -o "${OPERATOR}" -g libvirt "${STATE_DIR}"
sudo install -d -m 0750 -o "${OPERATOR}" -g libvirt "${STATE_DIR}/inventory"
sudo install -d -m 0750 -o "${OPERATOR}" -g libvirt "${STATE_DIR}/evidence"
sudo install -d -m 0750 -o "${OPERATOR}" -g libvirt "${STATE_DIR}/images"
sudo install -d -m 0750 -o "${OPERATOR}" -g libvirt "${STATE_DIR}/tpm"

VIRT_COUNT="$(grep -Eoc '(vmx|svm)' /proc/cpuinfo || true)"
if [[ "${VIRT_COUNT}" -eq 0 ]]; then
  echo "ERROR: CPU virtualization flags (vmx/svm) were not detected." >&2
  echo "Enable Intel VT-x/AMD-V in firmware before continuing." >&2
  exit 3
fi

if [[ ! -e /dev/kvm ]]; then
  echo "ERROR: /dev/kvm is absent even though CPU virtualization flags are present." >&2
  echo "Check firmware virtualization settings and loaded KVM modules." >&2
  exit 3
fi

printf '\nHost virtualization checks:\n'
kvm-ok || true
virsh --connect qemu:///system version

printf '\nState directory: %s\n' "${STATE_DIR}"
printf 'Physical host networking was NOT modified.\n'
printf 'Log out and back in (or reboot) before relying on the new libvirt/kvm group membership.\n'
printf 'Next: run capture_host_inventory.sh, then provision_networks.sh.\n'
