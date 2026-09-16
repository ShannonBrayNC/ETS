# EDGEW-RT0-VT0 Dedicated Ubuntu Host Bootstrap v1

Status: executable lab-host preparation  
Host role: dedicated ETS virtualization and qualification-rehearsal server  
Virtual target: `EDGEW-RT0-VT0`

## Purpose

The available freshly installed Ubuntu physical server is assigned as a dedicated ETS lab host. It may use the full available CPU, memory, storage, NICs, and virtualization facilities for VT0 work, subject to explicit fault-safety boundaries.

The server is **lab infrastructure**, not the physical `EDGEW-RT0-DUT` qualification target. Results produced by VT0 remain simulated unless a later profile explicitly qualifies the server itself as a named DUT.

## Trust and role topology

Preferred topology:

- dedicated Ubuntu server — KVM/QEMU/libvirt host; VT0 DUT and upstream/Gateway VMs;
- operator workstation — independent observer, artifact receiver, and HQP-2 verifier context;
- Linksys/D-Link hardware — physical source-side/network-fault boundary and possible later legacy-source candidates;
- future `EDGEW-RT0-DUT` — separately procured and separately identified physical Edge target.

The dedicated host may also run an on-host observer for debugging, but that observer is not a substitute for externally retained observation when independence matters.

## First-run sequence

From a normal sudo-capable account:

```bash
git clone https://github.com/ShannonBrayNC/ETS.git
cd ETS
git fetch origin hqp/edge-rt0-physical-runbook
git switch hqp/edge-rt0-physical-runbook
chmod +x scripts/qualification/edgew_vt0/*.sh
./scripts/qualification/edgew_vt0/bootstrap_host.sh
```

After bootstrap, log out and back in or reboot so `libvirt`/`kvm` group membership is effective.

Then capture the host inventory:

```bash
cd ETS
./scripts/qualification/edgew_vt0/capture_host_inventory.sh
```

The resulting inventory is stored under `/var/lib/ets-lab/inventory` by default. It can contain machine serial numbers and interface MAC addresses and MUST NOT be committed casually to the public repository.

Provision the initial virtual-only networks:

```bash
./scripts/qualification/edgew_vt0/provision_networks.sh
```

This creates:

- `edgew-vt-mgmt` — NAT-enabled management/package path;
- `edgew-vt-source` — isolated source-side path;
- `edgew-vt-upstream` — isolated Gateway/upstream path;
- `edgew-vt-fault` — isolated observer/fault path.

The network script does not edit Netplan and does not bind a physical NIC. Physical router bridging is a later explicit step after the server NICs and router hardware revisions are inventoried.

## Immediate validation

Run:

```bash
virsh --connect qemu:///system list --all
virsh --connect qemu:///system net-list --all
ls -l /dev/kvm
sudo virt-host-validate
free -h
lsblk -o NAME,MODEL,SERIAL,SIZE,TYPE,FSTYPE,MOUNTPOINTS
ip -br link
```

Expected minimum conditions before VM creation:

- `/dev/kvm` exists;
- `virt-host-validate` has no KVM-blocking failure;
- the operator can access `qemu:///system` without running the shell as root;
- sufficient free RAM exists for the DUT plus upstream workload;
- sufficient storage exists for a 64 GiB OS image, sparse 512 GiB qualification disk, snapshots, and retained artifacts;
- the host's management path is stable before physical fault-network work begins.

### Interpreting `virt-host-validate`

For the VT0 KVM/libvirt path, QEMU/KVM results are the gate. In particular, hardware virtualization, `/dev/kvm` existence/accessibility, cgroup support needed by QEMU, and usable IOMMU support should pass.

Two non-green checks can be non-blocking when the lab is using QEMU/KVM rather than LXC or confidential-guest features:

- a QEMU warning that no SEV/SEV-ES/SEV-SNP/TDX secure-guest technology is available does not block ordinary VT0 virtualization; those technologies are not a VT0 requirement;
- an LXC `freezer` cgroup failure does not block VT0 when no LXC container case depends on that controller. Record it as a host observation rather than silently discarding it.

Do not reinterpret these exceptions as blanket permission to ignore `virt-host-validate` failures. Any QEMU/KVM, `/dev/kvm`, IOMMU, device-node, or required-cgroup failure remains a blocker until explicitly bounded and documented.

## Resource policy

Because this server is dedicated to ETS, VT0 may consume most of its resources. However:

- reserve enough RAM and disk for the host to remain observable and recoverable;
- never fill the host root filesystem as a disk-exhaustion test;
- apply disk pressure only to dedicated virtual disks/volumes;
- apply network faults only to dedicated VT0 networks or explicitly selected lab NICs;
- never alter the host management link as part of an automated fault case unless an independent out-of-band recovery path exists;
- retain a recoverable VM baseline before PWR, DSK, TMP, UPD, or CAP testing.

A practical initial reservation is at least 4 GiB RAM and 20% free host filesystem capacity outside guest allocations. Increase the reserve if the server also performs packet capture or evidence retention.

## Physical NIC assignment

Do not assign NIC roles by interface name alone. After inventory, bind roles using stable hardware observations such as PCI location and MAC address.

Planned physical roles when enough NICs are available:

1. host management / SSH — never faulted during early testing;
2. Linksys/D-Link/source bridge — physical source-side fault boundary;
3. optional upstream/Gateway physical path;
4. optional dedicated observer/mirror path.

If the server has only one physical NIC, keep management on it and perform source/upstream/fault separation virtually until a USB/PCIe Ethernet adapter or managed switch is deliberately introduced.

## Router integration gate

Before connecting either old router into a qualification rehearsal, record:

- manufacturer;
- exact model;
- hardware revision;
- firmware version;
- LAN/WAN MAC addresses where visible;
- available syslog/log-export settings;
- whether factory reset is acceptable;
- whether it remains stock firmware.

Use `LEGACY_ROUTER_LAB_INVENTORY_TEMPLATE.md` for that characterization.

Do not flash alternate firmware before stock behavior and hardware revision are retained.

## Evidence boundary

The following statements remain mandatory:

- the dedicated Ubuntu server is a VT0 host, not automatically a qualified Edge DUT;
- KVM/vTPM/virtual Secure Boot results are simulated platform evidence;
- VM hard-stop is not proof of physical AC-loss or NVMe power-loss durability;
- libvirt network interruption is not proof of physical NIC reliability;
- successful VT0 completion does not qualify the future Protectli or any other physical model;
- an external verifier result about VT0 proves the bounded virtual package, not physical hardware truth or production readiness.
