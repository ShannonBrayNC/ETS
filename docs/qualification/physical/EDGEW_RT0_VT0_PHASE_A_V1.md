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


## Cloud-image root filesystem expansion

The first live retry also exposed a separate guest-image boundary: the virtual OS
disk is 64 GiB, but the Ubuntu cloud-image root partition remained at roughly
2.5 GiB because cloud-init growroot was not allowed to run after the bounded
first-boot provisioning path. The resulting root filesystem reached 100% usage
even though the 512 GiB qualification volume was essentially empty.

Before package/runtime work, the deployment helper now verifies the exact root
topology. For the known VT0 layout only (`/dev/vda1`, ext4, 64 GiB parent
`/dev/vda`, root partition <16 GiB), it:

1. retains pre-expansion `lsblk`, `sfdisk`, and `df` observations under
   `ETS_QUAL/runtime-recovery/root-expansion/`;
2. requires the existing `growpart` utility rather than installing tooling into
   an already-full root filesystem;
3. grows partition 1 and then expands ext4 with `resize2fs`;
4. retains the post-expansion topology;
5. requires at least 8 GiB free on `/` before continuing.

The helper does not apply a generic partition-growth algorithm to unknown disk
layouts. A topology different from the bounded VT0 layout is an execution
stop, not a reason to resize an arbitrary partition.


### Root-growth dry-run gate

The VT0 image contains multiple boot-related partitions in addition to the ext4
root partition. Partition numbers alone do not prove physical on-disk ordering,
so the helper must not infer that partition 1 can consume the remaining virtual
disk.

Plan mode now retains/displays `sfdisk -d /dev/vda` and a read-only
`growpart -N /dev/vda 1` result. Apply mode repeats that dry run and requires
an explicit `CHANGE:` result before modifying the partition table. A
`NOCHANGE:` result or an indeterminate result stops execution with no
partition-table mutation.


## Deployment evidence ownership

Deployment evidence under `ETS_QUAL/deployment-evidence/<commit>/` is retained
as root-owned material. The guest operator must not be granted write ownership
merely to simplify capture.

The live VT0 deployment exposed this boundary when shell redirection by
`etsadmin` attempted to create `ready.json` in the root-owned evidence
directory and failed with `Permission denied`.

The deployment helper now:

- captures readiness/version/device-identity payloads through privileged
  `tee` writes;
- captures Compose/image metadata through the same root-owned path;
- creates the SHA-256 manifest through privileged writes;
- leaves the evidence directory root-owned rather than weakening permissions.

A write failure in this directory is an evidence-retention defect, not proof
that the Edge runtime itself failed readiness.


## Secret-exposure scan semantics

The first live Phase A capture produced a false-negative case result because the
scanner treated source/config references to secret filenames as if they were
secret-value disclosure.

The corrected scan distinguishes a reference from exposure:

- the actual local API-key and software signing-key values are read only inside
  the guest;
- those values are never printed or copied into host evidence;
- retained deployment evidence and installed source/config material are searched
  for exact matches to those values;
- only the secret type/name and matching target path are reported if exposure is
  found;
- PEM/OpenSSH private-key markers are independently prohibited in retained
  deployment evidence;
- missing or implausibly short secret material produces a scan error rather than
  a false pass.

A filename such as `edge-local-api-key` appearing in source, documentation, or
configuration is therefore not itself evidence that the credential value was
disclosed.
