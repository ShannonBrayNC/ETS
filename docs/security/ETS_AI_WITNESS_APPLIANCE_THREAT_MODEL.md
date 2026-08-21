# ETS AI Witness Physical Appliance Threat Model

Status: pilot security candidate  
Profile: `ets.ai-witness.appliance.pilot.v1`

## 1. Security objective

The physical appliance should make it materially harder for a compromised workload, local attacker, network attacker, or failed upstream service to alter, fabricate, reorder, suppress without signal, or silently destroy AI Witness evidence after the appliance has accepted it.

No appliance can prove events it never observed. The threat model therefore separates evidence integrity from observation completeness.

## 2. Protected assets

- Witness evidence-signing key.
- TPM attestation key and platform identity.
- Queue encryption/sealing key.
- Signed Witness records awaiting upstream acknowledgement.
- Tenant/workspace/fleet enrollment binding.
- Appliance update trust roots and anti-rollback state.
- Boot measurements and attestation evidence.
- Runtime adapter credentials/peer mappings.
- Clock-quality evidence.
- Recovery configuration and audit trail.

## 3. Adversaries

### Compromised AI/runtime workload

May submit malicious metadata, replay observations, falsely claim tenant/model/actor identity, inject oversized events, attempt to include secrets, or omit events.

### Network attacker

May intercept, replay, redirect, delay, or modify runtime-adapter, time, Gateway, enrollment, update, and sync traffic.

### Local software attacker

May gain application-level or root-level access after boot and attempt to read keys, modify queue state, replace binaries, alter time, suppress services, or forge health signals.

### Physical attacker

May remove storage, power-cycle during writes/updates, replace boot media, reset firmware settings, or attempt TPM/key extraction.

### Compromised update infrastructure

May serve stale, malicious, selectively targeted, or rollback update material.

### Compromised Gateway/fleet service

May issue invalid scope bindings, replay enrollment, revoke a device, or attempt to make a device appear enrolled outside its authorized tenant/workspace.

## 4. Threats and mitigations

### T1 — Exported signing key

**Threat:** application or disk compromise exposes the Witness signing private key, allowing forged historical-looking records.

**Mitigation:** pilot signing keys are TPM-backed and non-exportable; application code receives signing operations, not private bytes. Key ID/fingerprint is bound into signed evidence.

**Residual risk:** a fully compromised authorized signer path may still request signatures while the key is usable. Revocation and platform-attestation policy are required to bound that risk.

### T2 — Boot-chain replacement

**Threat:** attacker boots modified firmware, bootloader, kernel, initramfs, or critical runtime and continues signing evidence.

**Mitigation:** UEFI Secure Boot plus TPM measured boot; remote verifier appraises PCR quote, event log, freshness nonce, and approved reference measurements.

**Residual risk:** Secure Boot only authenticates configured signing trust. A cryptographically authorized but malicious component can still boot. Reference-state policy remains necessary.

### T3 — Replay of old attestation

**Threat:** attacker reuses a previously good TPM quote after the machine state changes.

**Mitigation:** verifier-supplied nonce is bound into quote evidence; enrollment/attestation validity is time bounded.

### T4 — Queue theft

**Threat:** attacker copies NVMe/storage and reads pending Witness records.

**Mitigation:** complete queue records are AES-256-GCM encrypted with purpose-separated key material expected to be TPM sealed in the physical profile.

**Residual risk:** record digests and SQLite structural metadata remain observable. Full volume encryption is recommended in addition to record encryption.

### T5 — Queue modification

**Threat:** attacker alters ciphertext, row ordering, or immutable digest references.

**Mitigation:** AES-GCM authenticated decryption, record-digest consistency checks, immutable digest uniqueness, signed per-session record chaining, SQLite integrity checks.

### T6 — Power loss during capture

**Threat:** abrupt power removal causes acknowledged records to disappear or become partially committed.

**Mitigation:** WAL mode, `synchronous=FULL`, transaction completion before local queue acknowledgement, deterministic restart/replay.

**Qualification requirement:** physical power-cut testing is mandatory; software restart tests alone are insufficient.

### T7 — Upstream outage or partition

**Threat:** Gateway/ETS unavailability causes evidence loss.

**Mitigation:** bounded encrypted local queue, idempotent replay, explicit capacity/backpressure signals, acknowledgement-based deletion.

**Residual risk:** once local capacity is exhausted the device cannot guarantee capture. It must reject/backpressure rather than report success.

### T8 — Malicious or rollback update

**Threat:** attacker installs unsigned code, a modified image, or a previously valid vulnerable version.

**Mitigation:** signed manifest binds target digest/size, monotonic release sequence, metadata version, expiry, and signing-key identity. Equal/older release sequences are rejected.

**Residual risk:** a compromised authorized update key can sign malicious targets. Production update distribution should use TUF-style role separation, offline root authority, threshold signatures, rotation, and revocation.

### T9 — Runtime identity spoofing

**Threat:** payload declares a privileged tenant, workspace, actor, or model identity not associated with the authenticated sender.

**Mitigation:** authenticated runtime adapters; transport identity retained separately; server-owned enrollment/source mapping controls tenant/workspace scope.

### T10 — Prompt/output secret leakage

**Threat:** AI content contains secrets, PII, credentials, proprietary data, or regulated content and gets persisted by the Witness.

**Mitigation:** base appliance profile is digest-only and strict-schema. Unknown raw content fields are rejected.

### T11 — Time manipulation

**Threat:** attacker changes wall clock to make evidence appear earlier/later, bypass update expiry, or confuse ordering.

**Mitigation:** clock source/quality/offset/uncertainty are evidence; NTS preferred; monotonic time used for local duration/retry logic; update/enrollment validity checks use qualified wall-clock state.

**Residual risk:** authenticated time transport does not prove semantic correctness of the time source and delay attacks remain possible.

### T12 — Enrollment replay or scope escalation

**Threat:** valid enrollment from another device/scope is replayed to authorize this Witness.

**Mitigation:** signed binding includes Witness/device-key fingerprint, tenant, workspace, fleet, Gateway, freshness nonce, issue/expiry window, and signer identity.

### T13 — Device falsely reports healthy

**Threat:** management UI reports healthy because services are running even though attestation, time, queue, or enrollment evidence is missing.

**Mitigation:** readiness assessment is policy-bound and separates service health from qualification. Missing evidence produces `unknown`/`unqualified`, not healthy.

### T14 — Observation bypass

**Threat:** AI workload communicates through an unobserved path or disables its adapter.

**Mitigation:** deployment architecture should route supported runtime evidence through authenticated adapters and monitor adapter liveness/gaps.

**Residual risk:** the Witness cannot cryptographically prove completeness from its own event stream. Independent topology, runtime, or policy evidence is required for completeness claims.

## 5. TPM trust boundary

The pilot does not treat `TPM present=true` as assurance. Qualification requires:

1. approved TPM version/profile;
2. non-exportable key attributes;
3. known enrollment of the attestation public key;
4. nonce-bound TPM quote verification;
5. SHA-256 PCR selection under explicit policy;
6. corresponding event-log availability;
7. event-log/PCR reconstruction;
8. reference baseline/RIM appraisal;
9. revocation/rotation handling.

## 6. Update trust boundary

The initial ETS manifest is deliberately smaller than TUF. It provides signature, hash/size, expiration, and anti-rollback semantics needed for the pilot code path. Before production, distribution should separate root, targets, snapshot, and timestamp responsibilities or provide equivalent compromise-resilient update metadata governance.

## 7. Recovery boundary

Recovery is security-sensitive. Recovery mode must not become an unsigned alternate boot path that can access production keys. Recovery media/partition must be independently authenticated, must preserve audit evidence, and must require re-attestation before the device returns to qualified service.

## 8. Claims explicitly excluded

Even after physical qualification, ETS AI Witness must not claim solely from device evidence that:

- every AI event was observed;
- the source system told the truth;
- model output was correct, fair, safe, or explainable;
- a human reviewer understood the decision;
- an authorized tool action was semantically appropriate;
- the device is immune to physical attack;
- regulatory or legal compliance is automatically established.
