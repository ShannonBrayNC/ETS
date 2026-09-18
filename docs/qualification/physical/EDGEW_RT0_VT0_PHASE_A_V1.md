# EDGEW-RT0-VT0 HQP Phase A — Build, Identity, Security v1

Status: executable simulated preflight  
Cases:
- `EDGE-HQP-BLD-001`
- `EDGE-HQP-ID-001`
- `EDGE-HQP-SEC-001`

## Purpose

Phase A installs an exact ETS source commit into the virtual Edge DUT, binds Docker runtime state to the dedicated qualification volume, and captures the first three HQP cases without converting VM observations into physical qualification claims.

## Runtime deployment

Run from the T430 host on the intended exact repository commit:

```bash
bash scripts/qualification/edgew_vt0/deploy_vt0_edge_runtime.sh
```

The default is plan-only. The script refuses an ambiguous local source tree with uncommitted changes.

After reviewing the source commit, destination, and Docker storage boundary:

```bash
bash scripts/qualification/edgew_vt0/deploy_vt0_edge_runtime.sh --apply
```

The deployment:

1. verifies `/var/lib/ets-qualification` is the `ETS_QUAL` ext4 filesystem on `/dev/vdb1`;
2. places Docker's data-root under that qualification volume;
3. archives the exact Git commit and verifies the transferred archive digest;
4. expands it under `/opt/ets/releases/<commit>`;
5. records the exact source commit, archive SHA-256, compose/Dockerfile digests, Docker/Compose versions, image metadata, build log, and readiness observations;
6. builds and starts the four-service Edge Virtual stack.

No API-key bytes or signing private-key bytes are retained in host evidence.

## BLD-001

Required virtual-preflight observations include:

- installed source commit;
- source archive SHA-256;
- rendered Compose configuration and digest;
- image IDs/metadata;
- retained build provenance.

This satisfies only simulated build/provenance preflight. It does not make an unmerged commit a release or physical appliance image.

## ID-001

The virtual identity driver records the public Edge device identity before and after an `edge-api` restart, file metadata for the private signing/API-key files without reading their contents, and a retained-material secret-exposure scan.

The expected virtual posture is:

```text
key_custody = software_volume
hardware_attested = false
```

Stable identity across restart demonstrates continuity of the software-held virtual identity only. It is not TPM/HSM custody, remote attestation, or physical enrollment.

## SEC-001

The security-posture capture is observation-only. It records:

- VM UEFI presence;
- Secure Boot observation when `mokutil` is available;
- root and qualification-storage posture;
- encryption observation;
- TPM device exposure and optional TPM capabilities;
- Edge signer/public identity posture.

The vTPM and the Edge software signing identity are distinct facts. The presence of `/dev/tpm0` and `/dev/tpmrm0` does not permit the Edge signer to be described as TPM-backed while the device identity reports `software_volume` and `hardware_attested=false`.

## Capture

After the runtime is healthy:

```bash
bash scripts/qualification/edgew_vt0/capture_vt0_phase_a.sh
```

A successful virtual preflight reports:

```text
all_phase_a_cases_pass: true
```

The evidence package is retained under:

```text
/srv/ets-lab/evidence/vt0-phase-a/
```

with a SHA-256 manifest and self-verification result.

## Evidence boundary

Phase A remains `simulated`.

It does not establish physical:

- manufacturer/model qualification;
- TPM/HSM key custody;
- Secure Boot certification;
- storage encryption/endurance;
- rollback resistance;
- device enrollment;
- semantic truth/completeness;
- compliance, safety, production readiness, or GA.

The later physical EDGE-RT0 campaign must repeat the normative cases on the exact physical DUT and feed HQP-1/HQP-2 independently.


## Container runtime storage boundary

Docker `data-root` and containerd's content store are separate storage decisions on Ubuntu.

The first live VT0 build demonstrated this boundary: Docker was configured under
`/var/lib/ets-qualification/docker`, but BuildKit/containerd still attempted to
write layer content under `/var/lib/containerd` on the 64 GiB guest OS disk and
failed with `no space left on device`.

Before any retry, the deployment helper now:

1. stops Docker and containerd;
2. retains a bounded inventory of the abandoned root-filesystem containerd cache
   under `/var/lib/ets-qualification/runtime-recovery/`;
3. removes that disposable failed-build cache while both daemons are stopped;
4. configures Docker data-root as `/var/lib/ets-qualification/docker`;
5. configures containerd root as `/var/lib/ets-qualification/containerd`;
6. restarts both daemons and verifies the configured roots;
7. requires at least 100 GiB available on the qualification filesystem before
   building the images.

This correction is part of the simulated VT0 storage/runtime contract. It is not
a physical storage-endurance or capacity qualification result.
