# EDGEW-RT0-VT0 Sanitized Host Baseline — PowerEdge T430

Status: observed lab-host baseline, not a qualification claim  
Role: dedicated `EDGEW-RT0-VT0` KVM/libvirt host  
Recorded: 2026-09-15

## Observed capacity

The dedicated Ubuntu host has been bootstrapped successfully for the VT0 KVM/libvirt path.

Sanitized observations retained here:

- host class: Dell PowerEdge T430;
- usable memory observed: approximately 123 GiB total, approximately 118 GiB free at capture time;
- hardware virtualization: VMX available;
- `/dev/kvm`: present and usable;
- IOMMU: available, DMAR observed;
- libvirt: 12.0.0;
- QEMU: 10.2.1;
- physical Ethernet interfaces observed: two active interfaces;
- ETS virtual networks provisioned: `edgew-vt-mgmt`, `edgew-vt-source`, `edgew-vt-upstream`, `edgew-vt-fault`;
- system/root disk class: approximately 1 TiB;
- secondary LVM storage: one approximately 3.64 TiB logical volume spanning two approximately 2 TiB devices, with no free extents in that volume group;
- additional disk: approximately 7.3 TiB with a GPT partition table and one approximately 7.3 TiB partition; no recognized filesystem signature was established by the bounded inspection performed so far.

Exact disk serials, PARTUUIDs, host UUIDs, and interface MAC addresses are intentionally excluded from this public/sanitized artifact. The controlled inventory under `/var/lib/ets-lab/inventory` remains the source for exact identifiers.

## Current interpretation

The host has ample memory for a representative virtual Edge DUT plus an upstream/Gateway workload while retaining substantial host reserve.

Initial VT0 allocation target:

- `EDGEW-RT0-VT0` DUT: 8 vCPU, 16 GiB RAM;
- DUT OS disk: 64 GiB sparse;
- DUT qualification disk: 512 GiB sparse;
- upstream/Gateway VM: 4 vCPU, 8 GiB RAM;
- host reserve: at least 16 GiB RAM during ordinary rehearsal;
- independent observer/verifier context: external workstation.

The 16 GiB DUT memory allocation intentionally matches the current Edge MVP minimum instead of consuming the host's full capacity. Larger allocations can be used later for bounded capacity/pressure experiments but must not silently redefine the reference profile.

## Storage decision gate

Do not place destructive qualification fault cases on the host root filesystem.

The approximately 3.64 TiB LVM logical volume is the preferred first VM/snapshot candidate only after its mountpoint, existing contents, and available filesystem capacity are confirmed.

The approximately 7.3 TiB partition is a promising retained-evidence/soak-data candidate, but it must remain unmodified until non-destructive inspection confirms that no legacy filesystem, data, or recoverable metadata needs preservation.

Required non-destructive checks before any format/mount decision:

```bash
findmnt -S /dev/mapper/vg_comfy-lv_comfy || true
df -hT
sudo wipefs -n /dev/sdd /dev/sdd1
sudo blkid /dev/sdd /dev/sdd1 || true
sudo fdisk -l /dev/sdd
sudo parted -s /dev/sdd print
```

`wipefs -n` is inspection-only in this use; do not omit `-n`.

## Network decision gate

The host exposes two active physical Ethernet interfaces. Before binding either one to a physical router/fault bridge, identify the management/default-route interface and preserve it as the recovery path.

```bash
ip -br addr
ip route show default
ethtool -i eno1 || true
ethtool -i eno2 || true
```

The non-management interface may later be assigned as the physical Linksys/D-Link source/fault path after router model/revision/firmware characterization.

The four ETS virtual bridges may show `DOWN`/`NO-CARRIER` before guest TAP devices are attached; this alone is not evidence that the libvirt networks failed. The authoritative check is:

```bash
virsh --connect qemu:///system net-list --all
```

## Evidence boundary

This baseline establishes only that the PowerEdge host is suitable lab infrastructure for VT0 rehearsal. It does not qualify the host as `EDGEW-RT0-DUT`, does not qualify the future physical Edge appliance, and does not convert virtual power/network/storage fault behavior into physical hardware evidence.
