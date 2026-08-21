# ETS Black Box Threat Model

## Objective

Preserve a trustworthy, independently verifiable record of what the recorder observed immediately before
and after a consequential trigger while minimizing sensitive data collection.

The Black Box does not promise monitored-source truth. It protects the recorder's observation history and
makes tampering/gaps visible.

## Protected assets

- recorder signing key and device enrollment identity;
- rolling pre-trigger frames;
- frozen active-trigger state;
- sealed incident segments;
- boot counter/measured-boot state;
- clock-quality evidence;
- export/proof references;
- update/recovery trust anchors.

## Adversary capabilities

Assume an attacker may have network adjacency, send malformed/high-rate observations, control a source,
obtain operator/application/OS credentials, access database/media, interrupt power, replay old state or
software, block upstream networking, or obtain physical access to the appliance.

## Threats and mitigations

### Delete pre-incident history

**Threat:** allow rotation or force pruning before/after trigger.

**Control:** trigger freezes an explicit first sequence; active capture blocks normal pruning; seal copies
the complete frozen window. Missing frozen frames fail closed.

### Rewrite, reorder, omit, or splice frames

**Control:** global sequence, predecessor hash, SHA-256 frame digest, Ed25519 signature, ordered frame hash
list in the segment payload, and independent verification.

### Substitute signing identity

**Control:** signing-key ID is part of frame/segment signed payloads; device ID is bound into observations
and segment. Physical deployment additionally attests key/device binding to fleet enrollment.

### Roll back device state/software

**Control:** monotonic boot counter and boot-ID checks, measured boot, signed anti-rollback updates,
hardware-rooted counter in production, and remote Core/Vault/checkpoint anchors.

Software alone cannot detect rollback if an attacker atomically restores the entire software state and
its trust material; hardware/remote anchors are therefore a production requirement.

### Cut power during capture/seal

**Control:** atomic frame/state and segment/state transactions, power-loss-imminent forced seal, PLP media,
hold-up energy, destructive power-cut testing, and restart validation.

SQLite `synchronous=FULL` is not proof that consumer hardware preserves acknowledged writes after abrupt
power loss.

### Compromise OS/root

**Control:** TPM/secure-element non-exportable signing key, Secure Boot/measured boot, sealed storage
outside ordinary filesystem permissions, hardened update/recovery, and remote attestation/anchoring.

The software reference key is exportable and is not a production defense against root compromise.

### Firmware implant/downgrade

**Control:** NIST SP 800-193 protect/detect/recover pattern, signed firmware, anti-rollback versioning,
measured boot, protected recovery, fleet quarantine on unexpected measurements.

### Trigger suppression

**Control:** deployment-specific independent trigger sources (watchdog, power supervisor, source fault,
security detector, operator), trigger-health telemetry, qualification of adapters, and optional periodic
remote checkpoints even when no incident occurs.

### Trigger flooding / resource exhaustion

**Control:** strict schema, canonical size caps, one active incident in v1, bounded pre/post windows,
source admission/rate limits, and reserved sealed storage capacity in the physical design.

### Sensitive data overcollection

**Control:** digest-only base observation, extra raw fields forbidden, bounded attributes, manifest-only
Core projection, and encrypted artifact/Vault storage for authorized full content.

### Time manipulation

**Control:** global recorder sequence, per-boot monotonic counter, UTC clock-quality/error evidence,
authenticated/qualified production time, and optional external timestamp/transparency anchoring.

### Direct SQLite/media editing

**Control:** signatures reveal many modifications, but a privileged attacker can replace software state
and keys. The SQLite backend is classified `software`, not `hardware`, and fails production readiness.

### Physical removal/destruction

**Control:** encrypted media, hardware-protected keys, tamper evidence, protected debug interfaces,
remote replica/export, and target-domain enclosure/environmental qualification. Software cannot create
mechanical crash/fire/water survivability.

## Required production security evidence

Before production claim, prove TPM/secure-element non-exportability, measured boot/attestation, signed
anti-rollback update/recovery, encrypted media, PLP/hold-up performance under destructive cuts,
write-once sealed storage, tamper indication, source bounds/authentication, management isolation, key
rotation/revocation/history, independent export/anchoring, and NIST SP 800-88 Rev. 2 decommissioning.

## Residual risk

A compromised sensor can provide false data that is faithfully recorded; all trigger sources can fail;
a single physical unit can be destroyed; a compromised signing key can create apparently valid records
until trust policy reacts; cryptographic integrity does not prove semantic truth/completeness; and UTC
quality remains dependent on deployment time sources.
