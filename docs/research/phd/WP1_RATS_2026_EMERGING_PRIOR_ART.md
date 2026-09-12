# WP1 — 2026 Emerging RATS Prior Art Relevant to EXP-002

**Status:** prospective literature qualification / work-in-progress prior art  
**Date:** 2026-09-12  
**Scope:** EA-C001, EA-C003, EA-C005, EA-C006, EA-C007; EXP-002

## Research-integrity boundary

The sources below are active Internet-Drafts unless otherwise noted. They are not treated as settled standards or peer-reviewed proof. They matter because they materially narrow what can responsibly be claimed as original in Evidence Architecture and because they are unusually close to the current EXP-002 comparison surface.

## 1. Application-layer action evidence composed with RATS

**Source:** Anton Sokolov, *Composing Application-Layer Action Evidence with Remote Attestation Procedures*, draft-sokolov-rats-aep-composition-05, 18 Aug 2026.

The draft defines an application-layer Action Evidence Package (AEP) that reports an automated-system action, an authorising principal and an outcome, can hash-link to predecessor records, and is composed with platform Evidence under the RATS architecture. It explicitly preserves the limitation that self-reported action/outcome does not become independently observed fact merely because it is bound to attested platform state.

### Implication for ETS

This is direct emerging prior art against broad claims that ETS is novel because it:

- records an automated action;
- binds action evidence to authority information;
- records or hashes an outcome;
- composes application evidence with attested runtime/platform state;
- uses a Verifier/Relying Party split for machine-action evidence.

It also strongly reinforces an ETS boundary rather than defeating it: **self-report plus attestation is still not independent consequence observation**.

The remaining candidate space is therefore narrower: formal non-collapse across action stages and evidence classes; consequence custody; independent observation; explicit epistemic/nonclaim semantics; and empirical reduction of unsupported inference.

## 2. Behavioral evidence is conceptually distinct from remote attestation

**Source:** Tokachi Kamimura, *On the Relationship Between Remote Attestation and Behavioral Evidence Recording*, draft-kamimura-rats-behavioral-evidence-02, 21 Jul 2026.

The draft explicitly separates two questions:

- attestation: whether a system is in a trustworthy state;
- behavioral evidence: what the system actually did.

It also states that informal correlation between the two does not itself create a composed cryptographic proof and that behavioral-evidence mechanisms have independent security concerns, including selective omission and logging-infrastructure trust.

### Implication for ETS

ETS cannot claim novelty merely for observing that attestation and behavior evidence answer different questions. That distinction is now explicit in current RATS-related work.

Potential contribution must instead be tested in the specific semantics and architecture that connect these questions without overclaiming:

- what an independent verifier may conclude from each evidence class;
- how omission/unknown/unavailable states are represented;
- what additional evidence is required to move from reported action to observed consequence;
- how authority/standing and consequence are prevented from collapsing into attestation success.

## 3. Attested inference receipts for AI

**Source:** Borys Tsyrulnikov, *Attested Inference Receipt (AIR): A COSE/CWT Profile for Confidential AI Inference*, draft-tsyrulnikov-rats-attested-inference-receipt-02, 5 Jul 2026.

AIR binds model identity, input/output hashes, attestation-linked metadata and operational telemetry into a signed artifact for independent third-party verification of confidential AI inference. It explicitly separates receipt-local verification from appraisal of underlying platform attestation.

### Implication for ETS / AI Witness

EA-C005 must not claim novelty for:

- signed per-inference receipts;
- binding model identity to input/output hashes;
- attestation-linked AI inference provenance;
- separating receipt verification from platform attestation appraisal.

The surviving AI Witness hypothesis is about independently bounded evidence for consequential machine action, including authority, requested action, execution, external consequence, uncertainty and nonclaims—not merely inference provenance.

## 4. Current RATS architecture remains highly extensible

RFC 9334 already permits application Claims, Evidence appraisal, rich Attestation Results, Relying Party policy, freshness and trust assumptions. Current 2026 RATS work includes multi-verifier composition, interaction models, endorsements, event streams and richer attestation-result work.

### Implication for EXP-002

EXP-002 must continue to give Condition R the strongest reasonable architecture. A conclusion that RATS "cannot represent" an ETS distinction is not credible unless the comparison permits ordinary application-specific Claims and current multi-verifier/profile patterns.

## Revised thesis pressure

These sources increase pressure on primitive-level novelty for EA-C001/EA-C003/EA-C005. They strengthen the case that the dissertation should focus on one or more of the following only if experimentally and formally supported:

1. **formal non-collapse semantics** across identity, integrity, authority, standing, request, execution and result;
2. **first-class epistemic/nonclaim discipline** that measurably prevents unsupported inference;
3. **consequence custody** and explicit transition from authorized intent to independently evidenced external state;
4. **independent-verifier reconstruction utility** across distributed, AI and cyber-physical systems;
5. **failure envelopes** showing exactly when evidence is insufficient rather than silently promoting absence or self-report.

## External-review consequence

An independent RATS reviewer should be asked specifically to consider these 2026 drafts, not only RFC 9334. A review that ignores current action-evidence, behavioral-evidence and inference-receipt work would no longer be sufficiently adversarial.

## Sources

- RFC 9334, *Remote ATtestation procedureS (RATS) Architecture*, Jan 2023.
- A. Sokolov, *Composing Application-Layer Action Evidence with Remote Attestation Procedures*, draft-sokolov-rats-aep-composition-05, Aug 2026, work in progress.
- T. Kamimura, *On the Relationship Between Remote Attestation and Behavioral Evidence Recording*, draft-kamimura-rats-behavioral-evidence-02, Jul 2026, work in progress.
- B. Tsyrulnikov, *Attested Inference Receipt (AIR): A COSE/CWT Profile for Confidential AI Inference*, draft-tsyrulnikov-rats-attested-inference-receipt-02, Jul 2026, work in progress.
- IETF RATS Working Group current documents and charter, accessed 2026-09-12.
