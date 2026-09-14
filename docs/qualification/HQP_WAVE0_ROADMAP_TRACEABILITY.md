# HQP Wave 0 — Roadmap Traceability

**Status date:** 2026-09-14  
**Tracking:** #790  
**Authoritative capability-status companion:** `docs/PUBLIC_ROADMAP_STATUS.md`

## Purpose

This note binds the public ETS roadmap maturity model to the common Hardware Qualification Profile without changing product maturity merely because HQP exists.

The public roadmap remains authoritative for **capability maturity**. HQP artifacts become authoritative for **physical qualification state** of a named hardware/build/profile combination.

The two dimensions must not be collapsed:

```text
capability maturity != hardware qualification state
implemented != qualified != production-ready
```

## Wave 0 priority

Before additional physical feature expansion, the program establishes one qualification evidence methodology shared by:

1. ETS Edge physical targets;
2. Provenance / ETS Mobile Android Phase 1A;
3. legacy hardware and adapter testing;
4. later Ranger/VRX and physical ETS appliance work.

HQP-0, HQP-1, and HQP-2 are complete. HQP-3 repository implementation is merged and awaits named physical Edge execution. HQP-4 is the active portability layer for Android and legacy hardware.

## Roadmap interpretation

Existing public-roadmap entries retain their September 13, 2026 maturity classifications. HQP does not automatically promote or demote any product.

Where the roadmap states that a product is in `Development + Qualification`, `Qualification`, `Research`, or a pilot-candidate state, any future **physical qualification** claim should point to:

- the HQP-derived profile identifier/version;
- named DUT/revision;
- immutable software/build identity;
- retained Evidence Objects/artifacts;
- independent verifier identity/result;
- qualification report/disposition.

A roadmap statement that implementation exists is not evidence that a physical profile has passed.

## Initial traceability

| Roadmap item | Current roadmap gate | HQP relationship |
|---|---|---|
| ETS Edge | Repeatable live qualification of durability, recovery, identity, synchronization, and verifier-visible custody | #140 is qualification parent. HQP-3 profile/corpus derives from #140-#145 and defines 17 executable Edge cases under target class `EDGE-RT0`; repository implementation merged in #805, physical execution remains #796. |
| Provenance / ETS Mobile | Physical Android Phase 1A qualification | HQP-4 profile `ets.provenance.android-phase1a.hardware-qualification.v1` binds the existing ETS-Mobile device qualification report into HQP-1/HQP-2 without changing MECB semantics. |
| Legacy hardware lab | Hardware/adapter characterization and compatibility testing | HQP-4 profile `ets.legacy-network-syslog.hardware-qualification.v1` defines `LEGACY-NET-SYSLOG-RT0` for a named physical RFC 5424 UDP source while preserving unauthenticated-source identity boundaries. |
| Ranger R0 | Physical terrestrial build and consequence-custody demonstration | Reuse HQP and add cyber-physical observation, uncertainty, actuator, safety, and consequence requirements. |
| VectorRail / VRX | Replace simulated trials with calibrated physical measurements | Reuse HQP and add laboratory measurement/calibration requirements. |
| AI Witness / Black Box / Fleet | Physical/live appliance qualification gates | Later product-specific profiles inherit HQP common evidence and claim-boundary rules. |

## Edge HQP-3 reconciliation

Issues #141-#145 remain provenance for design intent and requirements. Their unchecked historical criteria do not supersede current roadmap status and do not constitute negative evidence about current implementation.

Conversely, later implementation does not justify silently checking those historical boxes. HQP-3 harvests the still-applicable requirements into:

- `docs/qualification/profiles/ets-edge-hardware-qualification-v1.json`;
- `docs/qualification/corpora/ets-edge-hqp-corpus-v1.json`;
- `docs/qualification/ETS_EDGE_HARDWARE_QUALIFICATION_CORPUS_V1.md`.

`EDGE-RT0` is a qualification target class, not a qualified hardware model. A physical run must replace the class abstraction with exact manufacturer/model/revision/firmware/security-element/build/environment values.

Repository CI may validate that the profile, corpus, synthetic capture, and sealing path are executable. It MUST NOT be reported as a physical Edge qualification result.

## HQP-4 portability rule

HQP-4 intentionally permits different product-specific test inventories while prohibiting weaker common evidence semantics.

The Android and legacy profiles must retain the same:

- common HQP evidence classes;
- Evidence Object/raw-artifact requirements;
- verifier checks and verifier-independence requirements;
- qualification disposition policy;
- no-cross-revision rule;
- requalification/supersession/history rules.

The common-semantics fingerprint is computed over these shared contract elements. Matching fingerprints prove repository-level portability of the qualification methodology, not physical qualification of either target.

Android source evidence is pinned to `Lantern-Protocol/ETS-Mobile` Phase 1A qualification contract at `fefba5069da1d33251211dd3d67d176bade478c2`. A later source-contract change requires review of the binding.

The first legacy profile uses the existing Edge RFC 5424 UDP observation boundary. UDP source IP/port and RFC 5424 identity fields remain observations and MUST NOT be presented as authenticated source identity.

Issue #797 remains open until one named physical Android device and one named physical legacy device each produce retained HQP-1 packages accepted by HQP-2 from an independent context.

## Publication rule

Public material may say a capability is implemented, in qualification, or research when supported by the roadmap/status artifacts. It may say a named physical profile is **qualified** only when the applicable HQP evidence package and independent verifier result support that bounded claim.

No HQP result by itself establishes general availability, legal admissibility, regulatory compliance, complete observation, semantic truth, production readiness, or qualification of untested hardware revisions.
