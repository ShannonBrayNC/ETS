# Wave 1 — R0.1 Provisioning and R0.2 Identity Persistence

**Tracking:** #820  
**Parent:** #814  
**Prerequisite:** merged W1-1 bench bootstrap (#819)

## Purpose

W1-2 is the first physical execution slice for **Edge Compact R0**. It captures retained evidence for:

- **R0.1 — provisioning and build identity**;
- **R0.2 — ETS Edge public device identity persistence across orderly reboot**.

It deliberately stops before network impairment, storage pressure, clock displacement, hard-power interruption, upgrade failure, recovery-media execution or any other destructive/disruptive stimulus.

A passing W1-2 evaluation is **phase evidence only**. It is not an HQP-2 verification result, a `lab_tested` disposition or a physical qualification claim.

## Canonical identity source

W1-2 does not create a new device identity scheme. It consumes the existing strictly validated ETS Edge public identity:

```text
schema_version=ets.edge.device_identity.v1
device_id=ets-edge:<public-key-fingerprint-prefix>
signing_algorithm=ed25519
key_custody=software_volume
hardware_attested=false
```

The current Edge protected-pilot entrypoint writes the public identity by default to:

```text
/var/lib/ets/edge-device-identity.json
```

or to the path exposed by `ETS_EDGE_DEVICE_IDENTITY_FILE` when the runtime is configured differently.

The snapshot contains the **public** signing key and fingerprint only. It never retains the Edge signing private key or local API credential.

## Preconditions

Before starting R0.1:

1. provision a dedicated x86-64 Edge Compact R0 candidate;
2. complete the W1-1 named-DUT bench manifest;
3. set `manifest_state=ready_for_qualification` only after operator review;
4. confirm `python -m ets.physical_edge validate-manifest --manifest <manifest>` returns success;
5. confirm the independent observer/controller is active and retaining receipts.

The W1-2 CLI is:

```bash
python -m ets.physical_edge_phase1
```

It records and evaluates evidence. It does **not** wipe disks, install an OS, reboot the DUT or inject faults.

---

## R0.1 — Provisioning/build identity

### Operator-controlled action

Provision the DUT using the documented image/media and installation procedure. The operator/controller must retain:

- the installation image SHA-256 digest;
- installation transcript or receipt;
- external observer/controller receipt;
- a secret-scan report demonstrating no reusable bootstrap secret was retained in qualification evidence;
- the exact Edge source revision;
- Edge artifact SHA-256 digest;
- Edge configuration SHA-256 digest.

The last three values are inherited from the validated W1-1 bench manifest and are checked again during phase evaluation.

### Record the provisioning receipt

Example:

```bash
python -m ets.physical_edge_phase1 record-provisioning \
  --manifest edge-r0-001.manifest.json \
  --receipt-id edge-r0-001-provision-001 \
  --operator-id operator-lab-a \
  --installation-method "documented USB/NVMe Edge R0 image install" \
  --image-digest <64-hex-sha256> \
  --install-receipt evidence/install-receipt.txt \
  --secret-scan evidence/secret-scan.txt \
  --observer-receipt evidence/controller-provisioning-receipt.json \
  --started-at 2026-09-16T09:00:00-04:00 \
  --completed-at 2026-09-16T09:20:00-04:00 \
  --output evidence/r0.1-provisioning.json
```

Only hashes of the three supporting receipt/report files are embedded in the machine-readable provisioning receipt. The original files remain retained evidence and should be copied into the later HQP-1 artifact package under their appropriate roles.

### R0.1 pass boundary

R0.1 can pass only when the provisioning receipt matches the ready bench manifest for:

```text
manifest_id
asset_id
observer_id
source_revision
Edge artifact SHA-256
configuration SHA-256
```

The image digest, install receipt digest, secret-scan digest and external observer receipt digest are additionally retained as R0.1 evidence.

---

## R0.2 — Device identity persistence

R0.2 uses Linux boot IDs to prove that compared identity snapshots came from distinct boots.

The default boot identifier is read from:

```text
/proc/sys/kernel/random/boot_id
```

### Snapshot A — initial post-provisioning boot

After Edge has initialized its persistent software signing identity:

```bash
python -m ets.physical_edge_phase1 capture-identity \
  --manifest edge-r0-001.manifest.json \
  --device-identity /var/lib/ets/edge-device-identity.json \
  --transition initial_boot \
  --output evidence/r0.2-identity-boot-a.json
```

The command loads the public identity using the existing strict `load_device_identity()` validator before retaining the snapshot.

### Perform an orderly reboot

The reboot itself is an operator/controller action, not a W1-2 CLI action.

The external observer/controller should retain a receipt proving that an orderly reboot was commanded and observed. That receipt must not come solely from the DUT application log.

Example operator action:

```bash
sudo systemctl reboot
```

### Snapshot B — after orderly reboot

After the DUT is back online and Edge has initialized:

```bash
python -m ets.physical_edge_phase1 capture-identity \
  --manifest edge-r0-001.manifest.json \
  --device-identity /var/lib/ets/edge-device-identity.json \
  --transition orderly_reboot \
  --observer-receipt evidence/controller-orderly-reboot-001.json \
  --output evidence/r0.2-identity-boot-b.json
```

At least two snapshots with **different canonical Linux boot IDs** are required.

### R0.2 stability fields

The following values must remain identical across the distinct boots:

- `device_id`;
- public-key fingerprint SHA-256;
- signing public-key ID;
- signing public key;
- signing algorithm (`ed25519`);
- key custody (`software_volume`);
- `hardware_attested=false`.

Any change is recorded as a failed R0.2 evaluation. Prior evidence is not rewritten to manufacture continuity.

---

## Evaluate W1-2

```bash
python -m ets.physical_edge_phase1 evaluate-phase1 \
  --manifest edge-r0-001.manifest.json \
  --provisioning-receipt evidence/r0.1-provisioning.json \
  --identity-snapshot evidence/r0.2-identity-boot-a.json \
  --identity-snapshot evidence/r0.2-identity-boot-b.json \
  --output evidence/r0-phase1-evaluation.json
```

Exit status:

- `0` — R0.1 and R0.2 phase evidence passes its internal binding checks;
- `2` — one or both cases fail; the failed evaluation is still evidence and should be retained;
- parser/model errors — malformed evidence artifact.

The evaluation is intentionally stamped:

```text
disposition=phase_evidence_only
claim_boundary=r0_1_r0_2_phase_evidence_not_a_physical_qualification_result
```

It cannot produce `lab_tested`, `qualified` or `qualified_with_deviation`.

## Evidence package for later HQP-1 assembly

Retain together:

```text
edge-r0-001.manifest.json
r0.1-provisioning.json
install receipt/transcript
secret-scan report
controller provisioning receipt
r0.2-identity-boot-a.json
controller orderly-reboot receipt
r0.2-identity-boot-b.json
r0-phase1-evaluation.json
```

These become artifact inputs to the later canonical `HardwareQualificationRun`. W1-2 does not replace HQP-1.

## Failure handling

If R0.1 or R0.2 fails:

1. retain the failed evidence exactly as produced;
2. record the engineering cause separately;
3. do not edit the failed receipt/snapshot/evaluation into a pass;
4. remediate the DUT/image/configuration;
5. start a new provisioning or identity-persistence attempt with new artifact IDs.

A key rotation, regenerated software-volume key or changed device ID is a real identity transition. It must not be described as persistence.

## Next gate

After W1-2 passes on a named physical DUT, proceed to **R0.3 — normal sustained capture and independently verifiable proof**. Only after the normal path is clean should Wave 1 advance into offline/network and destructive fault cases.
