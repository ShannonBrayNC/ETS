# EDGEW-RT0-VT0 DUT Provisioning Runbook v1

Status: executable virtual-lab setup, simulated evidence only  
Target: `EDGEW-RT0-VT0`  
Physical target class: `EDGE-RT0`

## Verified host assumptions

The dedicated PowerEdge T430 host has already established the following bounded facts:

- KVM/libvirt is operational;
- four ETS libvirt networks are active, persistent, and autostarting;
- approximately 123 GiB RAM is available across two NUMA nodes;
- the host has two sockets with six physical cores per socket and no SMT;
- NUMA node 0 exposes host CPUs `0,2,4,6,8,10`;
- NUMA node 1 exposes host CPUs `1,3,5,7,9,11`;
- both physical Ethernet interfaces currently participate in host networking and are not yet eligible for fault-path bridging;
- the approximately 8 TB disk has stale/inconsistent GPT metadata and remains read-only pending explicit disposition.

The first DUT baseline is therefore pinned inside NUMA node 0 rather than spanning sockets.

## DUT baseline

`edgew-rt0-vt0-dut` is created with:

- 4 vCPU;
- host CPU set `0,2,4,6`;
- strict memory allocation from NUMA node 0;
- 16 GiB RAM;
- Q35 machine type;
- host-passthrough CPU;
- UEFI/OVMF;
- emulated TPM 2.0 using `swtpm` with CRB model;
- Ubuntu 24.04 LTS amd64 cloud image;
- 64 GiB OS qcow2 disk;
- 512 GiB sparse qualification qcow2 disk;
- one virtio NIC on each of `edgew-vt-mgmt`, `edgew-vt-source`, `edgew-vt-upstream`, and `edgew-vt-fault`.

The 4-vCPU baseline intentionally matches the planned minimum physical Edge CPU envelope and avoids cross-NUMA scheduling during baseline qualification rehearsal.

## Storage gate

The provisioner requires an explicit `--storage-root` and refuses a path that resolves to the host root filesystem unless `--allow-root-storage` is also supplied.

Do **not** use `--allow-root-storage` for DSK, CAP, or any fault case that could consume substantial storage. The host root filesystem must remain a recovery boundary.

Before applying the provisioner, identify the mounted data filesystem:

```bash
findmnt -S /dev/mapper/vg_comfy-lv_comfy -n -o TARGET,SOURCE,FSTYPE,SIZE,AVAIL
```

If that returns no mountpoint, stop. Do not mount, format, resize, or otherwise repurpose the logical volume until its existing filesystem/content disposition is known.

The approximately 8 TB disk is not an alternative yet. Its GPT metadata is inconsistent and remains read-only until explicitly dispositioned.

## Plan-only execution

From the repository branch containing the provisioner:

```bash
bash scripts/qualification/edgew_vt0/provision_vt0_dut.sh \
  --storage-root /CONFIRMED/DATA/MOUNT
```

The default invocation performs validation and prints the complete VM plan without creating disks or a libvirt domain.

Review at least:

- resolved filesystem source;
- host CPU set;
- NUMA node;
- disk paths and sizes;
- four required libvirt networks;
- UEFI/vTPM configuration;
- simulated-only claim boundary.

## Apply

After the plan is reviewed:

```bash
bash scripts/qualification/edgew_vt0/provision_vt0_dut.sh \
  --storage-root /CONFIRMED/DATA/MOUNT \
  --apply
```

The provisioner will:

1. validate libvirt access and all four required networks;
2. validate that CPUs `0,2,4,6` belong to NUMA node 0;
3. refuse an existing domain or existing target disk rather than overwrite it;
4. create a dedicated local SSH key if the default VT0 key is absent;
5. download the current Ubuntu 24.04 cloud image only if a base image is not supplied;
6. verify the downloaded image against Canonical's published SHA-256 manifest;
7. create the 64 GiB OS and sparse 512 GiB qualification disks;
8. define/start the UEFI + vTPM 2.0 DUT with four ETS network interfaces;
9. enable domain autostart;
10. print domain and interface state for operator retention.

## Initial validation

After creation:

```bash
virsh --connect qemu:///system dominfo edgew-rt0-vt0-dut
virsh --connect qemu:///system domiflist edgew-rt0-vt0-dut
virsh --connect qemu:///system vcpupin edgew-rt0-vt0-dut
virsh --connect qemu:///system numatune edgew-rt0-vt0-dut
virsh --connect qemu:///system net-dhcp-leases edgew-vt-mgmt
```

Once the management lease is visible, SSH using the generated private key and the Ubuntu cloud-image user:

```bash
ssh -i ~/.ssh/edgew_vt0 ubuntu@<MGMT_IP>
```

Inside the guest, retain:

```bash
hostnamectl
uname -a
cat /etc/os-release
lscpu
free -h
lsblk
ip -br addr
```

## Evidence boundary

This VM is a software/virtualization twin. Successful creation or successful HQP rehearsal does not establish physical power-loss durability, physical TPM custody, Secure Boot implementation on the future appliance, NVMe endurance, thermal limits, physical NIC reliability, pilot readiness, or production readiness.

The future physical `EDGEW-RT0-DUT` must execute a new exact-identity HQP run. VT0 results remain historical simulated evidence and are never promoted into a physical qualification result.


## Partial-run recovery and QEMU datastore permissions

If qcow2 disks were created but libvirt did not define the domain, do not delete or overwrite them automatically. Inspect the retained `virt-install.log` first.

The provisioner supports bounded recovery:

```bash
bash scripts/qualification/edgew_vt0/provision_vt0_dut.sh \
  --storage-root /srv/ets-lab \
  --resume-partial \
  --apply
```

`--resume-partial` requires both expected qcow2 files and validates their format and virtual sizes before reuse.

System libvirt runs QEMU as a non-root runtime identity. The provisioner resolves the local QEMU service account (normally `libvirt-qemu` on Ubuntu), grants a narrow POSIX ACL for traversal of the ETS storage root and read/write access to the VM directory/disks, and verifies access as that runtime account before calling `virt-install`.

Do not solve datastore access failures by making the ETS datastore world-writable. If the ACL preflight succeeds but VM start is still denied, inspect the retained `virt-install.log` and Ubuntu AppArmor audit messages separately; DAC and AppArmor are distinct enforcement layers.


## Deterministic guest networking

VT0 uses four distinct guest NIC roles. The provisioner must provide an explicit cloud-init `network-config`; multi-NIC fallback selection is not an acceptable qualification baseline.

Canonical mapping:

| Role | Libvirt network | Guest behavior |
|---|---|---|
| management | `edgew-vt-mgmt` | static `192.168.250.10/24`; default route via `192.168.250.1` |
| source | `edgew-vt-source` | static `192.168.251.10/24`; no default route |
| upstream | `edgew-vt-upstream` | static `192.168.252.10/24`; no default route |
| fault | `edgew-vt-fault` | static `192.168.253.10/24`; no default route |

The provisioner binds each role by a deterministic libvirt MAC address and passes the matching network configuration into the first-boot NoCloud ISO. The management address is deliberately outside the libvirt DHCP pool (`.100-.199`) so the baseline does not depend on DHCP timing or lease retention.

### Existing VM recovery

A VT0 VM created before explicit network configuration may boot successfully but have no DHCP/ARP observations on any of the four networks. Do not set a console password merely to repair networking.

Install the offline guest-disk tooling on the host:

```bash
sudo apt-get install -y libguestfs-tools
```

Plan the repair:

```bash
bash scripts/qualification/edgew_vt0/repair_vt0_guest_network.sh
```

After verifying the discovered libvirt MAC-to-role mapping:

```bash
bash scripts/qualification/edgew_vt0/repair_vt0_guest_network.sh --apply
```

The repair:

1. requests a graceful shutdown and refuses to force-destroy the VM;
2. creates a stopped-guest qcow2 backup of the OS disk;
3. writes MAC-bound Netplan configuration offline with `virt-customize`;
4. disables cloud-init network rewriting;
5. restarts the guest and waits for the management DHCP lease.

`virt-customize` must never be run against a live guest disk.


### Ubuntu supermin/libguestfs kernel readability

On Ubuntu hosts, `virt-customize` may fail while building its supermin helper appliance if the operator cannot read the selected host kernel under `/boot`. The repair script does not relax `/boot` permissions globally. It copies the currently running kernel to controlled ETS storage with mode `0644`, points `SUPERMIN_KERNEL` at that copy, points `SUPERMIN_MODULES` at the matching `/lib/modules/<running-kernel>` tree, and uses the direct libguestfs backend.

If a previous repair attempt already created a `.pre-network-<timestamp>.qcow2` backup, the script reuses the newest retained backup instead of producing another full copy.

If libguestfs still fails, the script retains `virt-customize-network-repair.log` beside the VT0 disks and prints the environment required for a verbose diagnostic rerun.


## Canonical VT0 operator account

The VT0 guest must expose one deterministic management account: `etsadmin`.

Security posture:

- password is locked;
- SSH public-key authentication uses the dedicated host key `~/.ssh/edgew_vt0.pub`;
- direct root SSH is disabled;
- `etsadmin` is a member of `sudo`;
- passwordless sudo is permitted only for this isolated qualification VM so automated HQP cases can perform bounded privileged operations without storing a password.

New VT0 guests receive `etsadmin` through cloud-init user-data. For an already-created guest with no normal interactive account, the offline repair creates `etsadmin` before SSH key injection.

The account is a lab-management identity only; it is not the Edge device cryptographic identity and must not be represented as evidence of device identity, key custody, or production access control.
