# EDGEW-RT0-VT0 Sanitized Host Baseline — PowerEdge T430

Status: observed lab-host baseline, not a qualification claim  
Role: dedicated `EDGEW-RT0-VT0` KVM/libvirt host  
Recorded: 2026-09-17

## Observed capacity

The dedicated Ubuntu host has been bootstrapped successfully for the VT0 KVM/libvirt path.

Sanitized observations retained here:

- host class: Dell PowerEdge T430;
- usable memory observed: approximately 123 GiB total, approximately 118 GiB free at capture time;
- CPU class: dual Intel Xeon E5-2603 v3, 2 sockets, 6 physical cores per socket, 1 thread per core, 12 CPUs total;
- NUMA topology: 2 NUMA nodes, one per socket; the observed CPU sets are node 0 = 0,2,4,6,8,10 and node 1 = 1,3,5,7,9,11;
- hardware virtualization: VMX available;
- `/dev/kvm`: present and usable;
- IOMMU: available, DMAR observed;
- libvirt: 12.0.0;
- QEMU: 10.2.1;
- physical Ethernet interfaces observed: two active interfaces on the same LAN;
- both Ethernet interfaces currently carry DHCP default routes; `eno1` is preferred by metric and `eno2` is secondary, so neither is yet approved for fault-path reassignment;
- ETS virtual networks provisioned: `edgew-vt-mgmt`, `edgew-vt-source`, `edgew-vt-upstream`, `edgew-vt-fault`;
- system/root disk class: approximately 1 TiB;
- secondary LVM storage: one approximately 3.64 TiB logical volume spanning two approximately 2 TiB devices, with no free extents in that volume group;
- additional disk: approximately 7.28 TiB with GPT metadata, a single approximately 16 MiB Microsoft Reserved partition, and otherwise apparently unallocated capacity;
- the additional disk reports that its backup GPT is not located at the physical end of the device, so the partition table must be treated as stale/inconsistent until explicitly reviewed; no repair or rewrite has been authorized.

Exact disk serials, PARTUUIDs, host UUIDs, IP addresses, and interface MAC addresses are intentionally excluded from this public/sanitized artifact. The controlled inventory under `/var/lib/ets-lab/inventory` remains the source for exact identifiers.

## Current interpretation

The host has ample memory for a representative virtual Edge DUT plus an upstream/Gateway workload while retaining substantial host reserve. CPU allocation must respect the two-socket NUMA topology rather than treating the 12 CPUs as a uniform pool.

Initial VT0 allocation target:

- `EDGEW-RT0-VT0` DUT: 4 vCPU, 16 GiB RAM, with the vCPUs pinned within one NUMA node for the baseline run;
- DUT OS disk: 64 GiB sparse;
- DUT qualification disk: 512 GiB sparse;
- upstream/Gateway VM: 4 vCPU, 8 GiB RAM, preferably pinned within the other NUMA node;
- host reserve: at least 4 physical CPU cores total plus at least 16 GiB RAM during ordinary rehearsal;
- independent observer/verifier context: external workstation.

The 4-vCPU DUT baseline better matches the planned four-core physical Edge reference and avoids an unnecessary cross-NUMA baseline. Larger vCPU allocations are reserved for bounded capacity/pressure experiments and must not silently redefine the reference profile.

The 16 GiB DUT memory allocation intentionally matches the current Edge MVP minimum instead of consuming the host's full capacity. Larger allocations can be used later for bounded capacity/pressure experiments but must not silently redefine the reference profile.

Before enforcing NUMA memory pinning, capture per-node memory capacity and free-memory observations so a node is not overcommitted merely because total host memory is abundant.

Suggested read-only checks:

```bash
lscpu -e=CPU,NODE,SOCKET,CORE
for n in /sys/devices/system/node/node[0-9]*; do
  echo "=== ${n##*/} ==="
  grep -E 'MemTotal|MemFree' "$n/meminfo" || true
done
```

## Storage decision gate

Do not place destructive qualification fault cases on the host root filesystem.

The approximately 3.64 TiB LVM logical volume is the preferred first VM/snapshot candidate only after its mountpoint, existing contents, and available filesystem capacity are confirmed.

The approximately 7.28 TiB disk is a promising retained-evidence/soak-data candidate because only a tiny Microsoft Reserved partition is visible, but it must remain unmodified until the stale GPT condition and any legacy/recoverable metadata are explicitly dispositioned.

The observed disk condition is specifically:

- GPT present;
- only an approximately 16 MiB Microsoft Reserved partition is defined;
- most device capacity is not represented by a partition;
- backup GPT is not at the end of the device;
- no filesystem has been established on the visible partition.

This is not authorization to run `sgdisk -e`, `parted ... fix`, `mkfs`, `wipefs` without `-n`, or any partition-table write operation.

Additional read-only inspection may include:

```bash
sudo wipefs -n /dev/sdd /dev/sdd1
sudo blkid /dev/sdd /dev/sdd1 || true
sudo fdisk -l /dev/sdd
sudo parted -s /dev/sdd unit s print free
sudo sgdisk -v /dev/sdd
```

The first four commands are inspection-only in this usage. `sgdisk -v` is used only for verification; do not use repair/write options until the disk is explicitly cleared for reuse.

## Network decision gate

The host exposes two active physical Ethernet interfaces, but both currently have DHCP addresses and default routes on the same LAN. The observed route preference uses `eno1` first and `eno2` second by metric.

Therefore **neither interface is yet a safe fault-path candidate**. Do not enslave `eno2` to a bridge merely because it has the higher route metric: it currently participates in host reachability and may be part of failover/recovery behavior.

Before physical router bridging:

1. preserve `eno1` as the primary management path;
2. decide whether `eno2` should remain a management backup or be deliberately removed from the host default-route configuration;
3. verify console/out-of-band recovery before changing `eno2`;
4. only then bind a dedicated physical interface to the Linksys/D-Link source/fault bridge.

If retaining both current host routes is desirable, add a separate PCIe/USB Ethernet interface or use a managed switch/VLAN design rather than consuming `eno2`.

The four ETS virtual bridges may show `DOWN`/`NO-CARRIER` before guest TAP devices are attached; this alone is not evidence that the libvirt networks failed. The authoritative check is:

```bash
virsh --connect qemu:///system net-list --all
```

## Evidence boundary

This baseline establishes only that the PowerEdge host is suitable lab infrastructure for VT0 rehearsal. It does not qualify the host as `EDGEW-RT0-DUT`, does not qualify the future physical Edge appliance, and does not convert virtual power/network/storage fault behavior into physical hardware evidence.
