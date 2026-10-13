# EDGEW-RT0-VT0 Guest Pristine Baseline and Qualification Disk Initialization v1

Status: executable simulated-lab gate  
Depends on: deterministic VT0 networking and canonical `etsadmin` management identity  
Physical claim state: none

## Purpose

Before the 512 GiB qualification disk is partitioned or formatted, retain a pristine guest-state package from the T430 host. This preserves the distinction between:

- host observation of the virtual machine,
- guest self-report,
- the exact blank qualification-disk starting state,
- later storage initialization and fault-test results.

The guest must not be the sole historian of its own starting state.

## Pristine baseline

Run on the T430 host, not inside the guest:

```bash
bash scripts/qualification/edgew_vt0/capture_vt0_guest_baseline.sh
```

The capture records both independent host observations and read-only guest observations over SSH. The package includes:

- libvirt state, XML, block and interface bindings, CPU/NUMA observations;
- the host-side qcow2 identity for the qualification disk;
- guest OS/kernel identity and management account;
- the deterministic four-interface network state and route table;
- guest block topology and mounts;
- TPM device observations;
- SSH listener state;
- Netplan and cloud-init network-disable configuration;
- exact `/dev/vdb` size, udev properties, wipefs state, and partition-table state;
- a machine-readable summary and SHA-256 manifest.

The baseline must report:

```text
all_pristine_checks_pass: true
```

before the qualification disk can be initialized.

## Qualification disk contract

The dedicated virtual qualification disk is:

```text
guest device: /dev/vdb
virtual size: 512 GiB
starting state: blank, unpartitioned, unmounted
```

Initialization uses:

```text
partition table: GPT
partition: /dev/vdb1
filesystem: ext4
filesystem label: ETS_QUAL
mountpoint: /var/lib/ets-qualification
persistence: filesystem UUID in /etc/fstab
mount options: defaults,noatime
```

The initialization script is plan-only by default:

```bash
bash scripts/qualification/edgew_vt0/initialize_vt0_qualification_disk.sh
```

After reviewing the plan:

```bash
bash scripts/qualification/edgew_vt0/initialize_vt0_qualification_disk.sh --apply
```

The script refuses to proceed unless the latest pristine baseline passed, `/dev/vdb` remains exactly 512 GiB, the target does not overlap the guest root filesystem, and the target still has no partitions, mounts, or detectable signatures.

## Resulting evidence

After initialization, the host retains:

- the pristine-baseline summary and manifest;
- the initialization plan and command output;
- post-initialization `lsblk`, `blkid`, `findmnt`, and `fstab` observations;
- the filesystem UUID and partition UUID;
- a machine-readable initialization summary;
- a SHA-256 manifest with self-verification.

## Evidence boundary

A passing pristine baseline proves only that the observed virtual guest matched the bounded starting-state contract at capture time.

A passing disk-initialization result proves only that the 512 GiB VT0 disk was initialized according to the bounded virtual storage contract.

Neither result establishes:

- physical SSD/NVMe endurance;
- physical power-loss behavior;
- hardware-backed key custody;
- physical Secure Boot;
- physical NIC reliability;
- thermal limits;
- semantic truth or completeness;
- compliance, safety, pilot readiness, GA, or production readiness.

These artifacts remain `simulated` until the separate physical EDGE-RT0 DUT campaign is executed and independently verified.

## Next gate

After disk initialization, begin the virtual HQP sequence against the mounted qualification volume:

`BLD -> ID -> SEC -> DUR -> BKR -> BPR -> OFF -> SYN -> CHK -> OPS -> TIM -> KEY -> UPD -> DSK -> TMP -> PWR simulation -> CAP`.

The virtual sequence is a preflight for the later physical campaign, not a substitute for it.
