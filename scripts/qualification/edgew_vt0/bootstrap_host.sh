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
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

printf 'ETS EDGEW-RT0-VT0 dedicated host bootstrap\n'
printf 'Ubuntu: %s\n' "${PRETTY_NAME:-unknown}"
printf 'Operator: %s\n' "${OPERATOR}"

# Fresh desktop/server installs can retain the installation ISO as an active
# APT source. apt-get update will fail after successfully contacting Internet
# mirrors, which previously made the virtualization failure look unrelated.
if sudo python3 - <<'PY'
from pathlib import Path
import re
import sys

paths = []
main = Path('/etc/apt/sources.list')
if main.exists():
    paths.append(main)
d = Path('/etc/apt/sources.list.d')
if d.exists():
    paths.extend(sorted(d.glob('*.list')))
    paths.extend(sorted(d.glob('*.sources')))

active = []
for path in paths:
    text = path.read_text(errors='replace')
    if path.suffix == '.sources':
        for stanza in re.split(r'\n\s*\n', text):
            if 'cdrom:' not in stanza and 'file:/cdrom' not in stanza:
                continue
            if re.search(r'(?mi)^Enabled:\s*no\s*$', stanza):
                continue
            active.append(str(path))
            break
    else:
        for line in text.splitlines():
            if line.lstrip().startswith('#'):
                continue
            if 'cdrom:' in line or 'file:/cdrom' in line:
                active.append(str(path))
                break

if active:
    print('Active installer-media APT source detected:', file=sys.stderr)
    for path in sorted(set(active)):
        print('  ' + path, file=sys.stderr)
    sys.exit(1)
PY
then
  :
else
  echo "ERROR: Ubuntu installation-media APT source is still active." >&2
  echo "Run: bash ${SCRIPT_DIR}/disable_install_media_source.sh" >&2
  echo "Then rerun this bootstrap." >&2
  exit 3
fi

sudo apt-get update

# Ubuntu 26.04 no longer exposes qemu-kvm as an installable package on amd64;
# use qemu-system-x86 there. Retain qemu-kvm compatibility for older Ubuntu releases.
if apt-cache show qemu-kvm >/dev/null 2>&1 && apt-cache policy qemu-kvm | grep -q 'Candidate: [^()]'; then
  QEMU_PACKAGE="qemu-kvm"
elif apt-cache show qemu-system-x86 >/dev/null 2>&1 && apt-cache policy qemu-system-x86 | grep -q 'Candidate: [^()]'; then
  QEMU_PACKAGE="qemu-system-x86"
elif apt-cache show qemu-system >/dev/null 2>&1 && apt-cache policy qemu-system | grep -q 'Candidate: [^()]'; then
  QEMU_PACKAGE="qemu-system"
else
  echo "ERROR: no supported QEMU system package has an install candidate." >&2
  exit 3
fi

printf 'Selected QEMU package: %s\n' "${QEMU_PACKAGE}"

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  "${QEMU_PACKAGE}" \
  libvirt-daemon-system \
  libvirt-daemon-common \
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

# libvirt 12 on Ubuntu 26.04 still ships libvirtd.service/socket. Prefer socket
# activation when present, with a service fallback for older supported releases.
if systemctl list-unit-files --type=socket | grep -q '^libvirtd\.socket'; then
  sudo systemctl enable --now libvirtd.socket
fi
if systemctl list-unit-files --type=service | grep -q '^libvirtd\.service'; then
  sudo systemctl enable --now libvirtd.service
fi

if ! getent group libvirt >/dev/null 2>&1; then
  echo "ERROR: libvirt group was not created by package installation." >&2
  exit 3
fi
if ! getent group kvm >/dev/null 2>&1; then
  echo "ERROR: kvm group is absent even though /dev/kvm is expected." >&2
  exit 3
fi

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

if ! command -v virsh >/dev/null 2>&1; then
  echo "ERROR: virsh was not installed successfully." >&2
  exit 3
fi
if ! command -v virt-host-validate >/dev/null 2>&1; then
  echo "ERROR: virt-host-validate was not installed successfully." >&2
  exit 3
fi

printf '\nHost virtualization checks:\n'
kvm-ok || true
sudo virt-host-validate || true

# The current shell will not yet have the newly-added libvirt/kvm groups, so
# validate the system libvirt socket as root here. The operator validates
# unprivileged virsh after re-login/reboot.
if ! sudo virsh --connect qemu:///system version; then
  echo "ERROR: libvirt system connection is not available after installation." >&2
  echo "Inspect: systemctl status libvirtd.service libvirtd.socket --no-pager" >&2
  exit 3
fi

printf '\nState directory: %s\n' "${STATE_DIR}"
printf 'Physical host networking was NOT modified.\n'
printf 'Bootstrap package/service checks passed.\n'
printf 'Log out and back in (or reboot) before relying on the new libvirt/kvm group membership.\n'
printf 'Next after re-login: run capture_host_inventory.sh, then provision_networks.sh.\n'
