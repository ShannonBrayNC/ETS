# ETS Qualification Program

This directory contains cross-product qualification contracts and traceability artifacts.

## Authoritative rule

ETS separates **capability maturity** from **qualification state**.

`implemented != qualified != production-ready`

Roadmap status describes capability maturity. Qualification artifacts describe whether a named hardware/build/profile combination has retained evidence sufficient to support a bounded qualification claim.

Historical issue checkboxes are requirements inputs and traceability records; they are not authoritative proof of current implementation or qualification state.

## Wave 0 — Hardware Qualification Baseline

Tracking issue: #790

The common normative contract is:

- [`ETS_HARDWARE_QUALIFICATION_PROFILE_V1.md`](ETS_HARDWARE_QUALIFICATION_PROFILE_V1.md)
- schema: `schemas/qualification/v1/hardware-qualification-profile.schema.json`

Canonical qualification chain:

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

## Initial product traceability

| Product / program | Qualification role | Current Wave 0 relationship |
|---|---|---|
| ETS Edge | First HQP specialization | Issue #140 is the Edge qualification/pilot-readiness parent. Issue #145 is the source corpus for the first Edge hardware qualification cases. |
| Provenance / ETS Mobile | Second physical target | Android Phase 1A will consume the common HQP contract rather than define a separate evidence methodology. |
| Legacy hardware lab | Third physical target | Legacy devices/adapters will use the same DUT/build/stimulus/observation/result/verifier/report chain. |
| Ranger / VRX | Cyber-physical research consumer | Physical experiments inherit HQP while adding motion, actuator, measurement, uncertainty, safety, and consequence-custody requirements. |
| AI Witness / Black Box / Fleet | Later appliance consumers | Product-specific profiles may add stricter controls but may not silently weaken common HQP evidence requirements. |

## Planned sequence

- **HQP-0** — normative profile, schema, terminology, lifecycle, traceability.
- **HQP-1** — machine-readable execution/evidence package and deterministic qualification report.
- **HQP-2** — independent qualification verifier.
- **HQP-3** — Edge hardware qualification corpus derived from #145 and retained #140 outcomes.
- **HQP-4** — Provenance Android Phase 1A and legacy-hardware reuse of the same profile.
- **HQP-5** — roadmap/governance qualification index and publication rules.

No later wave may treat successful software CI alone as physical qualification evidence.