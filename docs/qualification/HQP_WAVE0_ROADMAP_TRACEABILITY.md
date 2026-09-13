# HQP Wave 0 — Roadmap Traceability

**Status date:** 2026-09-13  
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
| ETS Edge | Repeatable live qualification of durability, recovery, identity, synchronization, and verifier-visible custody | #140 is qualification parent; #145 is first test-source corpus; HQP-3 will define executable Edge cases. |
| Provenance / ETS Mobile | Physical Android Phase 1A qualification | Reuse HQP rather than inventing a mobile-only qualification evidence methodology. |
| Legacy hardware lab | Hardware/adapter characterization and compatibility testing | Reuse HQP DUT/build/stimulus/observation/result/verifier/report chain. |
| Ranger R0 | Physical terrestrial build and consequence-custody demonstration | Reuse HQP and add cyber-physical observation, uncertainty, actuator, safety, and consequence requirements. |
| VectorRail / VRX | Replace simulated trials with calibrated physical measurements | Reuse HQP and add laboratory measurement/calibration requirements. |
| AI Witness / Black Box / Fleet | Physical/live appliance qualification gates | Later product-specific profiles inherit HQP common evidence and claim-boundary rules. |

## Historical Edge issue reconciliation

Issues #141–#145 remain provenance for design intent and requirements. Their unchecked historical criteria do not supersede current roadmap status and do not constitute negative evidence about current implementation.

Conversely, later implementation does not justify silently checking those historical boxes. Requirements still relevant to physical qualification are to be harvested into versioned HQP test cases and proven with retained evidence.

## Publication rule

Public material may say a capability is implemented, in qualification, or research when supported by the roadmap/status artifacts. It may say a named physical profile is **qualified** only when the applicable HQP evidence package and independent verifier result support that bounded claim.

No HQP result by itself establishes general availability, legal admissibility, regulatory compliance, complete observation, semantic truth, or qualification of untested hardware revisions.