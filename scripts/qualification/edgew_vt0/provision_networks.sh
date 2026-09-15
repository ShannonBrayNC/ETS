#!/usr/bin/env bash
set -euo pipefail

# Creates only libvirt virtual networks. It does not change netplan or bind physical NICs.
# A physical Linksys/D-Link bridge can be added later after exact NIC/router inventory.

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as the normal libvirt operator account, not root." >&2
  exit 2
fi

if ! virsh --connect qemu:///system list --all >/dev/null 2>&1; then
  echo "Cannot access qemu:///system. Log out/back in after bootstrap or check libvirt group membership." >&2
  exit 2
fi

create_net() {
  local name="$1"
  local bridge="$2"
  local gateway="$3"
  local start="$4"
  local end="$5"
  local mode="$6"

  if virsh --connect qemu:///system net-info "${name}" >/dev/null 2>&1; then
    echo "Network ${name} already exists; leaving it unchanged."
    return
  fi

  local xml
  xml="$(mktemp)"
  trap 'rm -f "${xml:-}"' RETURN

  if [[ "${mode}" == "nat" ]]; then
    cat >"${xml}" <<EOF
<network>
  <name>${name}</name>
  <forward mode='nat'/>
  <bridge name='${bridge}' stp='on' delay='0'/>
  <ip address='${gateway}' netmask='255.255.255.0'>
    <dhcp><range start='${start}' end='${end}'/></dhcp>
  </ip>
</network>
EOF
  else
    cat >"${xml}" <<EOF
<network>
  <name>${name}</name>
  <bridge name='${bridge}' stp='on' delay='0'/>
  <ip address='${gateway}' netmask='255.255.255.0'>
    <dhcp><range start='${start}' end='${end}'/></dhcp>
  </ip>
</network>
EOF
  fi

  virsh --connect qemu:///system net-define "${xml}"
  virsh --connect qemu:///system net-autostart "${name}"
  virsh --connect qemu:///system net-start "${name}"
  rm -f "${xml}"
  trap - RETURN
}

# Management is NAT-enabled so guests can obtain packages without bridging a physical NIC.
create_net edgew-vt-mgmt     virbr250 192.168.250.1 192.168.250.100 192.168.250.199 nat
# Source, upstream, and fault networks are isolated by default.
create_net edgew-vt-source   virbr251 192.168.251.1 192.168.251.100 192.168.251.199 isolated
create_net edgew-vt-upstream virbr252 192.168.252.1 192.168.252.100 192.168.252.199 isolated
create_net edgew-vt-fault    virbr253 192.168.253.1 192.168.253.100 192.168.253.199 isolated

printf '\nEDGEW-RT0-VT0 libvirt networks:\n'
virsh --connect qemu:///system net-list --all | grep -E 'Name|edgew-vt-' || true
printf '\nNo physical interface was modified or enslaved to a bridge.\n'
