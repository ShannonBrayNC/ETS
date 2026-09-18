# EDGEW-RT0-VT0 Runtime Baseline v1

Status: executable simulated-runtime baseline  
Virtual twin: `EDGEW-RT0-VT0`  
Physical target class: `EDGE-RT0`

## Purpose

This baseline is the first retained runtime observation after the VT0 domain has been created successfully. It proves only that the virtual twin exists in the intended libvirt topology and that the expected virtual resources are bound as configured.

It does **not** establish physical hardware qualification.

## Required baseline

The runtime capture verifies:

- domain state is running;
- four vCPUs;
- 16 GiB guest memory;
- all four vCPUs constrained to host CPU set `0,2,4,6`;
- runtime vCPU affinity remains bounded to that CPU set;
- strict NUMA allocation to node 0;
- four virtual networks:
  - `edgew-vt-mgmt`
  - `edgew-vt-source`
  - `edgew-vt-upstream`
  - `edgew-vt-fault`
- UEFI/OVMF guest firmware;
- emulated TPM 2.0 using the CRB model;
- 64 GiB qcow2 OS disk;
- sparse 512 GiB qcow2 qualification disk.

The management DHCP lease is recorded separately because cloud-init/network initialization can lag domain creation. Absence of the first lease does not invalidate the structural baseline; it means guest-network readiness remains pending.

## Capture

On the virtualization host:

```bash
cd ~/Desktop/ETS

bash scripts/qualification/edgew_vt0/capture_vt0_runtime_baseline.sh
```

The default output is retained under:

```text
/var/lib/ets-lab/evidence/vt0-runtime/
```

The package contains the libvirt domain XML, domain state and reason, CPU-set/affinity observations, NUMA policy, block-device binding, interface binding, management DHCP leases, qemu image metadata, libvirt/host version observations, a machine-readable summary, and a SHA-256 manifest.

The capture performs its own SHA-256 verification from inside the evidence directory. For later manual verification, change into the evidence directory first:

```bash
(cd "$LATEST" && sha256sum -c SHA256SUMS)
```

The filenames in `SHA256SUMS` are package-relative by design.

## Interpretation

`all_structural_checks_pass=true` means the currently observed virtual domain matches the bounded VT0 resource/topology contract. A non-running domain remains a structural baseline failure and must be investigated rather than normalized away.

It does **not** mean:

- the future physical Edge device is qualified;
- the physical TPM/security element is proven;
- the virtual TPM provides physical key custody;
- physical Secure Boot implementation is proven;
- storage power-loss behavior or endurance is proven;
- thermal limits are proven;
- physical NIC or router reliability is proven;
- the software produced complete or semantically true evidence;
- compliance, safety, pilot readiness, GA, or production readiness is established.

## Next gate

After the runtime structure is retained:

1. observe a management DHCP lease;
2. SSH to the Ubuntu 24.04 guest using the dedicated VT0 key;
3. wait for cloud-init completion;
4. inventory guest OS/build/network/TPM state;
5. initialize the dedicated qualification disk inside the guest;
6. capture the guest baseline as a new retained artifact package;
7. begin HQP-3 virtual preflight in the existing safe sequence:
   BLD -> ID -> SEC -> DUR -> BKR -> BPR -> OFF -> SYN -> CHK -> OPS -> TIM -> KEY -> UPD -> DSK -> TMP -> PWR simulation -> CAP.

Each result remains `simulated` until the separate physical DUT run.
