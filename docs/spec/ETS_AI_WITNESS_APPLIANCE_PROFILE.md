# ETS AI Witness Physical Appliance Profile v1

Status: pilot qualification candidate  
Profile: `ets.ai-witness.appliance.pilot.v1`  
Date: 2026-08-21

This profile defines the minimum physical and software security boundary for an ETS AI Witness pilot appliance. It extends `ETS_AI_WITNESS_PROFILE.md`; it does not replace the base digest-first witness event contract.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative engineering requirements.

## 1. Product boundary

The appliance is an evidence observer for AI and agentic workloads. It captures bounded, policy-approved evidence about AI requests, responses, retrieval, tools, human oversight, and resulting actions, then projects signed records into ETS.

It is not an AI safety oracle, model firewall, policy decision point, SIEM, EDR, or proof that an observed model conclusion is correct.

## 2. Standards baseline

The pilot profile is informed by the following current specifications and patterns:

- Trusted Computing Group TPM 2.0 Library Specification, Version 185, March 2026.
- TCG PC Client Specific Platform TPM Profile 1.07, March 2026, including July 2026 errata.
- TCG PC Client Platform Firmware Profile and PC Client Reference Integrity Manifest Specification 1.1 Revision 11.
- UEFI Secure Boot and TCG UEFI measured-boot event-log mechanisms.
- RFC 8915, Network Time Security for NTP.
- The Update Framework (TUF) 1.0.x security model for signed metadata, expiry, freshness, key roles, and rollback resistance.

The reference code implements a bounded ETS update manifest inspired by TUF security properties. It does not claim full TUF wire-format or repository conformance.

## 3. Reference hardware capability floor

The physical pilot appliance MUST provide:

- x86-64 CPU with hardware virtualization and modern cryptographic instruction support;
- at least 4 physical cores / 8 logical threads;
- at least 16 GiB RAM; 32 GiB is the reference pilot target;
- at least 1 TB high-endurance NVMe storage;
- discrete or firmware TPM 2.0 conforming to the approved PC Client profile;
- UEFI firmware with Secure Boot capability;
- measured-boot event logging into TPM PCRs;
- at least two logical network zones: management/upstream and observation/adapter ingress;
- hardware watchdog and RTC capability SHOULD be present;
- recovery media or an independently bootable recovery partition SHOULD be supported.

A VM MAY implement the development profile with a vTPM but is not a physical-pilot substitute.

## 4. Requirement registry

### Device identity and TPM

- **AIW-A-001 MUST** use TPM 2.0 for the physical pilot profile.
- **AIW-A-002 MUST** create the production Witness evidence-signing key as non-exportable hardware-backed key material.
- **AIW-A-003 MUST** keep device identity, attestation, evidence signing, queue-sealing, transport, and update trust roles purpose-separated.
- **AIW-A-004 MUST NOT** expose production evidence-signing private-key bytes to the Python application process.
- **AIW-A-005 MUST** support key rotation and revocation without rewriting historical evidence.
- **AIW-A-006 MUST** expose the public key identifier/fingerprint used for each signed Witness record.

### Secure and measured boot

- **AIW-A-010 MUST** require UEFI Secure Boot enabled for physical pilot qualification.
- **AIW-A-011 MUST** collect measured-boot evidence from the TPM SHA-256 PCR bank.
- **AIW-A-012 MUST** retain or digest the corresponding TCG event log needed to reconstruct/appraise PCR state.
- **AIW-A-013 MUST** bind remote attestation to a verifier-provided freshness nonce.
- **AIW-A-014 MUST** distinguish a valid TPM quote from an approved platform state. Quote verification alone does not establish that measured components are trusted.
- **AIW-A-015 MUST** support appraisal against an approved reference baseline/RIM policy before declaring the appliance qualified.
- **AIW-A-016 MUST** surface unknown or incomplete measurement state instead of mapping it to healthy.

### Durable queue and power-loss behavior

- **AIW-A-020 MUST** durably buffer signed Witness records when ETS/Gateway connectivity is unavailable.
- **AIW-A-021 MUST** encrypt complete queued Witness records at rest with authenticated encryption.
- **AIW-A-022 MUST** derive the queue encryption key from purpose-separated key material that is TPM-sealed/non-exportable in the physical pilot.
- **AIW-A-023 MUST** use a crash-consistent durable transaction boundary before acknowledging a record as locally queued.
- **AIW-A-024 MUST NOT** silently discard an acknowledged queued record.
- **AIW-A-025 MUST** make replay idempotent by immutable record digest.
- **AIW-A-026 MUST** delete/ack local queued records only after the configured upstream acknowledgement boundary is satisfied.
- **AIW-A-027 MUST** detect wrong queue keys, ciphertext tampering, duplicate immutable records, and SQLite integrity failures.
- **AIW-A-028 MUST** fail closed when encrypted queue integrity cannot be established.

The software reference uses SQLite WAL, `synchronous=FULL`, HKDF-SHA-256, and AES-256-GCM. Hardware qualification must additionally test abrupt power removal and filesystem recovery.

### Signed update and rollback protection

- **AIW-A-030 MUST** accept only cryptographically authenticated appliance updates.
- **AIW-A-031 MUST** bind update authorization to target digest, target size, release sequence, metadata version, expiration, and signing-key identity.
- **AIW-A-032 MUST** reject rollback to an equal or earlier release sequence.
- **AIW-A-033 MUST** reject expired update metadata.
- **AIW-A-034 MUST** verify the complete downloaded target digest and size before activation.
- **AIW-A-035 MUST** preserve an independently bootable recovery/rollback path.
- **AIW-A-036 MUST NOT** permit rollback policy to reinstall a cryptographically valid but policy-revoked release.
- **AIW-A-037 SHOULD** evolve the distribution service toward a full TUF-compatible role/threshold repository rather than a single online update-signing key.

### Runtime adapter authentication

- **AIW-A-040 MUST** authenticate every provider/runtime adapter source.
- **AIW-A-041 MUST** preserve transport/authenticated peer identity separately from payload-declared model, actor, tenant, or workload identity.
- **AIW-A-042 MUST** derive tenant/workspace authorization from configured enrollment/source mappings rather than payload claims alone.
- **AIW-A-043 SHOULD** use mTLS or workload identity for remote adapters.
- **AIW-A-044 MAY** use an authenticated local Unix-domain socket profile for co-resident runtime adapters.
- **AIW-A-045 MUST** preserve the base Witness digest-only content boundary unless a separately approved content-capture policy is active.

### Time and clock-quality evidence

- **AIW-A-050 MUST** record Witness observation/receipt time separately from source-provided event time.
- **AIW-A-051 MUST** expose bounded clock-quality state, current offset estimate, uncertainty, source, and last synchronization time.
- **AIW-A-052 SHOULD** use NTS under RFC 8915 where the enterprise time service supports it.
- **AIW-A-053 MUST** treat authenticated time transport as evidence about source/transport authenticity, not proof that the supplied time is semantically correct.
- **AIW-A-054 MUST** use monotonic time for retry/backoff/duration calculations that could be corrupted by wall-clock rollback.
- **AIW-A-055 MUST** degrade qualification state when clock uncertainty exceeds the profile ceiling.
- **AIW-A-056** sets the initial pilot qualification ceiling to 5000 ms uncertainty; this is a qualification parameter, not an SLA.

### Gateway and fleet enrollment

- **AIW-A-060 MUST** bind each physical Witness to tenant, workspace, fleet, Gateway, Witness identity, device-key fingerprint, and a freshness nonce.
- **AIW-A-061 MUST** authenticate that binding with an approved Gateway/fleet enrollment trust key.
- **AIW-A-062 MUST** give enrollment assertions explicit issue and expiration times.
- **AIW-A-063 MUST** reject expired, future, wrongly signed, or scope-mismatched enrollment material.
- **AIW-A-064 MUST** audit enrollment, re-enrollment, key rotation, revocation, and fleet-scope changes as ETS evidence.
- **AIW-A-065 MUST NOT** allow a locally supplied tenant/workspace value to override the enrolled scope.

### Failure semantics

- **AIW-A-070 MUST** fail closed for signing-key identity failure, queue integrity failure, invalid update signatures, invalid enrollment, or invalid required attestation evidence.
- **AIW-A-071 MUST** continue safe local capture during bounded upstream outage when local durable capacity remains available.
- **AIW-A-072 MUST** apply explicit backpressure rather than claim successful capture after durable capacity is exhausted.
- **AIW-A-073 MUST** distinguish `healthy`, `degraded`, `unqualified`, and `unknown` appliance state.
- **AIW-A-074 MUST NOT** equate device health with observation completeness or correctness of the observed AI system.

## 5. Software reference implemented in v1

The current reference implementation provides:

- strict TPM attestation evidence and PCR contracts;
- Secure/Measured Boot readiness inputs;
- NTS/NTP/PTP/local clock-evidence contracts;
- authenticated runtime-adapter identity contracts;
- signed, time-bounded fleet enrollment verification;
- signed update manifests with release-sequence rollback protection and expiry;
- encrypted durable SQLite queue with authenticated encryption and restart recovery;
- deterministic pilot-readiness assessment.

## 6. Hardware-only qualification gates

The following cannot be claimed from CI alone and require named physical hardware:

1. TPM key non-exportability demonstrated on the reference board.
2. TPM quote verification with nonce binding and reference PCR/event-log appraisal.
3. Secure Boot enabled with approved key database state.
4. Measured-boot event-log reconstruction across normal and tampered boot variants.
5. Abrupt power-loss tests during enqueue, checkpoint, replay, update, and acknowledgement.
6. TPM-sealed queue key recovery and refusal after unauthorized boot-state change.
7. Signed update install, interrupted update, rollback, recovery, and revoked-release tests.
8. NTS clock synchronization, clock rollback, loss-of-time-source, and uncertainty tests.
9. Gateway enrollment/revocation while online and during bounded disconnection.
10. Thermal, endurance, storage-full, network-loss, and seven-day offline soak qualification.

## 7. Claim boundary

Passing software and physical profile gates establishes that a named appliance configuration can capture and protect configured AI Witness evidence under the tested conditions. It does not prove that every AI event was observable, that model behavior was safe or correct, or that an external policy/legal requirement was satisfied.
