# ETS Qualification Program

This directory contains cross-product qualification contracts, execution packages, conformance fixtures, product-specific corpora, reuse bindings, publication governance, and roadmap traceability artifacts.

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
→ qualification index publication state
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

### HQP-3 — Edge executable corpus — active physical gate

Tracking issue: #796  
Parent: #140  
First source corpus: #145  
Repository implementation merged by PR #805.

- [`ETS_EDGE_HARDWARE_QUALIFICATION_CORPUS_V1.md`](ETS_EDGE_HARDWARE_QUALIFICATION_CORPUS_V1.md)
- Edge profile: `docs/qualification/profiles/ets-edge-hardware-qualification-v1.json`
- executable corpus: `docs/qualification/corpora/ets-edge-hqp-corpus-v1.json`
- corpus schema: `schemas/qualification/v1/edge-hardware-qualification-corpus.schema.json`
- runtime/validator/sealer: `ets/qualification/edge_corpus.py`
- CLI: `python -m ets.edge_hqp`

HQP-3 translates requirements from #140-#145 into 17 versioned Edge cases covering build identity, enrollment/key custody, boot/storage security posture, durability, abrupt power loss, disk pressure, backpressure, offline operation, resumable synchronization, checkpoint continuity, clock faults, signer lifecycle, tamper detection, update/recovery, backup/restore, capacity/soak, and source-to-proof/export verification.

Repository CI proves the profile/corpus/tooling is internally executable. CI cannot satisfy the physical DUT execution gate. The producer tooling can seal a complete capture as `lab_tested` but deliberately cannot self-promote a DUT to `qualified`.

### HQP-4 — Provenance Android and legacy hardware reuse — repository implementation active

Tracking issue: #797.  
Repository portability layer merged by PR #806.

- [`ETS_HQP_CROSS_PRODUCT_REUSE_V1.md`](ETS_HQP_CROSS_PRODUCT_REUSE_V1.md)
- Android profile: `docs/qualification/profiles/ets-provenance-android-phase1a-hardware-qualification-v1.json`
- Android binding: `docs/qualification/reuse/android-phase1a-hqp-reuse-v1.json`
- legacy syslog profile: `docs/qualification/profiles/ets-legacy-network-syslog-hardware-qualification-v1.json`
- legacy binding: `docs/qualification/reuse/legacy-network-syslog-hqp-reuse-v1.json`
- reuse schema: `schemas/qualification/v1/cross-product-reuse.schema.json`
- runtime: `ets/qualification/reuse.py`
- CLI: `python -m ets.hqp_reuse`

HQP-4 keeps product-specific cases separate while requiring identical common HQP evidence/verifier/disposition semantics. `common_hqp_semantics_fingerprint()` makes that portability invariant machine-checkable.

The Android binding consumes the existing ETS-Mobile Phase 1A physical-device qualification contract rather than creating a mobile-only evidence methodology. The first legacy target class is a named physical RFC 5424 UDP source observed by the existing Edge syslog boundary; UDP/message identity remains observational, not authenticated.

Repository CI is not the HQP-4 exit gate. #797 remains open until one named physical Android target and one named physical legacy target each produce HQP-1 packages that pass HQP-2 independent verification.

### HQP-5 — qualification index and roadmap governance — active repository implementation

Tracking issue: #798.

- [`ETS_HARDWARE_QUALIFICATION_INDEX_V1.md`](ETS_HARDWARE_QUALIFICATION_INDEX_V1.md)
- public index: `docs/qualification/qualification-index.json`
- index schema: `schemas/qualification/v1/hardware-qualification-index.schema.json`
- runtime/cross-checker: `ets/qualification/index.py`
- CLI: `python -m ets.hqp_index`

HQP-5 is the publication firewall. A published physical qualification result must identify the exact profile/version/digest, DUT/revision, immutable build/configuration, retained HQP-1 package, HQP-2 result, limitations, validity window, requalification triggers, and supersession state.

The initial public index intentionally contains **zero published physical qualified claims**. Edge, Android Phase 1A, and the first legacy target appear as pending physical gates. Existence of a target profile, simulator, virtual appliance, CI result, or laboratory tooling cannot create a qualified public claim.

## Initial product traceability

| Product / program | Qualification role | Current Wave 0 relationship |
|---|---|---|
| ETS Edge | First HQP specialization | #140 is the Edge qualification/pilot-readiness parent. #145 plus #141-#144 are the requirements provenance for HQP-3. HQP-5 lists `EDGE-RT0` as pending physical qualification, not a qualified model. |
| Provenance / ETS Mobile | Second physical target | HQP-4 binds the existing Android Phase 1A device report into the common HQP run/report/verifier contract. HQP-5 lists `ANDROID-PHASE1A-RT0` as pending physical qualification. |
| Legacy hardware lab | Third physical target | HQP-4 defines `LEGACY-NET-SYSLOG-RT0` for a named physical RFC 5424 UDP source using the same HQP evidence/verifier chain. HQP-5 lists it as not yet physically tested. |
| Ranger / VRX | Cyber-physical research consumer | Physical experiments inherit HQP while adding motion, actuator, measurement, uncertainty, safety, and consequence-custody requirements. |
| AI Witness / Black Box / Fleet | Later appliance consumers | Product-specific profiles may add stricter controls but may not silently weaken common HQP evidence requirements. |

## Governance and claim boundary

No later wave may treat successful software CI alone as physical qualification evidence. No hardware qualification may silently inherit across a hardware revision, software build, profile version, firmware/security-element change, or claim-critical environment change.

A roadmap or publication may call a named physical target **qualified** only when an active HQP-5 index record points to the exact retained HQP-1/HQP-2 evidence supporting that bounded statement.

HQP packages reuse ETS Evidence Object semantics rather than create a second provenance model. Qualification evidence may support a bounded claim about what was tested and observed; it does not by itself prove complete observation, semantic truth, legal admissibility, regulatory compliance, safety certification, general availability, or production readiness.
