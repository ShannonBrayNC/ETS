# ETS Qualification Program

This directory contains cross-product qualification contracts, execution packages, conformance fixtures, product-specific corpora, and roadmap traceability artifacts.

## Authoritative rule

ETS separates **capability maturity** from **qualification state**.

`implemented != qualified != production-ready`

Roadmap status describes capability maturity. Qualification artifacts describe whether a named hardware/build/profile combination has retained evidence sufficient to support a bounded qualification claim.

Historical issue checkboxes are requirements inputs and traceability records; they are not authoritative proof of current implementation or qualification state.

## Canonical qualification chain

```text
device-under-test
→ qualification environment
→ test profile
→ software/build identity
→ observer identity
→ starting state
→ stimulus
→ observations
→ resulting state
→ Evidence Object(s)
→ independent verifier result
→ qualification report
```

## Wave 0 — Hardware Qualification Baseline

### HQP-0 — common normative profile — complete

Tracking issue: #790  
Merged by PR #793.

- [`ETS_HARDWARE_QUALIFICATION_PROFILE_V1.md`](ETS_HARDWARE_QUALIFICATION_PROFILE_V1.md)
- schema: `schemas/qualification/v1/hardware-qualification-profile.schema.json`

HQP-0 defines the product-neutral claim boundary, qualification states, required evidence classes, verifier requirements, requalification, supersession, and non-claims.

### HQP-1 — execution package and deterministic report — complete

Tracking issue: #794  
Merged by PR #802.

- [`ETS_HARDWARE_QUALIFICATION_EXECUTION_PACKAGE_V1.md`](ETS_HARDWARE_QUALIFICATION_EXECUTION_PACKAGE_V1.md)
- run schema: `schemas/qualification/v1/hardware-qualification-run.schema.json`
- report schema: `schemas/qualification/v1/hardware-qualification-report.schema.json`
- executable contract: `ets/qualification/hardware.py`
- valid conformance fixtures: `docs/qualification/fixtures/hqp1/valid/`
- negative mutation vectors: `docs/qualification/fixtures/hqp1/invalid/mutations.json`

HQP-1 binds a concrete test execution to the exact DUT, environment, build, observer chain, starting state, stimulus, observations, resulting state, retained artifacts, Evidence Objects, verifier result, deviations, and final disposition. Completed run/report digests reuse `ets.core.canonical_json`.

### HQP-2 — independent verifier — complete

Tracking issue: #795  
Merged by PR #804.

- [`ETS_HARDWARE_QUALIFICATION_VERIFIER_V1.md`](ETS_HARDWARE_QUALIFICATION_VERIFIER_V1.md)
- verifier runtime: `ets/qualification/verifier.py`
- profile runtime mirror: `ets/qualification/profile.py`
- verification schema: `schemas/qualification/v1/hardware-qualification-verification.schema.json`
- clean-room CLI: `python -m ets.hqp_verify`
- valid retained fixture: `docs/qualification/fixtures/hqp2/valid/`
- negative mutation vectors: `docs/qualification/fixtures/hqp2/invalid/mutations.json`

HQP-2 consumes the HQP-1 run/report/fixture contract from a clean environment and determines structural completeness, digest integrity, Evidence Object bindings, reference integrity, test completion, observation/result linkage, deviation handling, and eligibility for the claimed disposition without trusting the DUT runtime or producer-side verifier narrative.

### HQP-3 — Edge executable corpus — active

Tracking issue: #796  
Parent: #140  
First source corpus: #145.

- [`ETS_EDGE_HARDWARE_QUALIFICATION_CORPUS_V1.md`](ETS_EDGE_HARDWARE_QUALIFICATION_CORPUS_V1.md)
- Edge profile: `docs/qualification/profiles/ets-edge-hardware-qualification-v1.json`
- executable corpus: `docs/qualification/corpora/ets-edge-hqp-corpus-v1.json`
- corpus schema: `schemas/qualification/v1/edge-hardware-qualification-corpus.schema.json`
- runtime/validator/sealer: `ets/qualification/edge_corpus.py`
- CLI: `python -m ets.edge_hqp`

HQP-3 translates requirements from #140-#145 into 17 versioned Edge cases covering build identity, enrollment/key custody, boot/storage security posture, durability, abrupt power loss, disk pressure, backpressure, offline operation, resumable synchronization, checkpoint continuity, clock faults, signer lifecycle, tamper detection, update/recovery, backup/restore, capacity/soak, and source-to-proof/export verification.

Repository CI can prove the profile/corpus/tooling is internally executable. CI cannot satisfy the physical DUT execution gate. The producer tooling can seal a complete capture as `lab_tested` but deliberately cannot self-promote a DUT to `qualified`.

### HQP-4 — Provenance Android and legacy hardware reuse

Tracking issue: #797.

Android Phase 1A and selected legacy devices reuse the same HQP run/report/verifier semantics rather than define separate hardware evidence methodologies.

### HQP-5 — qualification index and roadmap governance

Tracking issue: #798.

Publishes bounded claims tied to exact profile, DUT revision, immutable build, retained evidence, verifier result, limitations, expiry, and supersession state.

## Initial product traceability

| Product / program | Qualification role | Current Wave 0 relationship |
|---|---|---|
| ETS Edge | First HQP specialization | #140 is the Edge qualification/pilot-readiness parent. #145 plus #141-#144 are the requirements provenance for HQP-3. |
| Provenance / ETS Mobile | Second physical target | Android Phase 1A consumes the common HQP contract rather than defining a separate evidence methodology. |
| Legacy hardware lab | Third physical target | Legacy devices/adapters use the same DUT/build/stimulus/observation/result/verifier/report chain. |
| Ranger / VRX | Cyber-physical research consumer | Physical experiments inherit HQP while adding motion, actuator, measurement, uncertainty, safety, and consequence-custody requirements. |
| AI Witness / Black Box / Fleet | Later appliance consumers | Product-specific profiles may add stricter controls but may not silently weaken common HQP evidence requirements. |

## Governance and claim boundary

No later wave may treat successful software CI alone as physical qualification evidence. No hardware qualification may silently inherit across a hardware revision, software build, profile version, firmware/security-element change, or claim-critical environment change.

HQP packages reuse ETS Evidence Object semantics rather than create a second provenance model. Qualification evidence may support a bounded claim about what was tested and observed; it does not by itself prove complete observation, semantic truth, legal admissibility, regulatory compliance, safety certification, general availability, or production readiness.
