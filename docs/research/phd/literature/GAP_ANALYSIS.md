# ETS Doctoral Gap Analysis

Status: preliminary; originality not established.

## EA-C001 — Evidence Object

### Broad claim rejected

`A signed object carrying provenance and verification metadata is novel.`

This claim is not defensible. C2PA manifests, in-toto link metadata, SLSA attestations, transparency-log entries, and established forensic evidence handling all overlap materially.

### Narrow candidate contribution

A domain-general Evidence Object may be research-worthy if it can demonstrate a combination not already provided by prior work:

1. deterministic evidence identity/integrity binding;
2. typed claim classes rather than generic provenance assertions;
3. explicit verification context and trust dependencies;
4. custody/provenance relationships;
5. preservation of unsupported assumptions in verifier output;
6. refusal to infer semantic/real-world truth from cryptographic integrity;
7. composability across software, AI, distributed, and cyber-physical domains.

### Evidence needed

- formal object schema and invariants;
- minimum-sufficiency argument showing why each field/relationship exists;
- nearest-neighbor comparison with C2PA, in-toto/SLSA, secure logging, attestation, forensic custody, and provenance models;
- verifier semantics for verified / asserted / unknown / externally dependent properties;
- controlled experiments showing that the additional distinctions change verifier conclusions in meaningful cases;
- independent reproduction or critique.

### Falsification condition

If prior work already provides materially equivalent domain-general claim typing, verification-state semantics, custody/provenance composition, and unsupported-assumption retention, `EA-C001` must be narrowed, merged into another contribution, or retired.

## EA-C002 — Evidence Graph

### Broad claim rejected

`A graph representing evidence provenance is novel.`

This is not defensible. W3C PROV directly establishes graph-oriented provenance representation; C2PA, in-toto, SLSA, and other provenance systems also encode lineage and transformation relationships.

### Narrow candidate contribution

A typed Evidence Graph may be research-worthy if ETS can demonstrate a relation model in which these edge families remain semantically and verifiably distinct:

- observation;
- derivation;
- inference;
- attribution/identity;
- authority/authorization;
- decision;
- command/action;
- custody;
- resulting state/consequence.

The graph must preserve the rule that connectivity does not imply truth: a verified hash/link can coexist with an unverified semantic assertion, and verifier state must not silently propagate stronger certainty across that boundary.

### Evidence needed

- canonical relation algebra;
- formal edge semantics and admissible compositions;
- explicit verifier-state propagation rules;
- mapping to/from W3C PROV where possible;
- counterexamples showing where generic provenance representation is insufficient for ETS verification goals;
- experiments spanning at least digital and cyber-physical scenarios;
- external review of whether the distinctions are technically meaningful and non-duplicative.

### Falsification condition

If prior literature already supplies materially equivalent typed evidence-edge semantics and certainty/trust propagation across observation → inference → authority → action → consequence, `EA-C002` must be narrowed or retired.

## Cross-cutting thesis gap under investigation

A possible higher-level ETS contribution is not a new primitive but a **verification discipline**:

> Independently verifiable evidence systems should separate integrity, provenance, authority, observation, inference, action, custody, and consequence claims, and should preserve unsupported assumptions rather than allowing cryptographic validity or graph connectivity to promote those assumptions into semantic truth.

This statement is currently a research hypothesis, not an established original contribution.

## Current status

| Contribution | Prior-art pass | Gap formulation | Formalization | Experiments | External validation | Status |
|---|---|---|---|---|---|---|
| EA-C001 | seed primary-source pass complete | narrowed | partial | engineering evidence exists; doctoral protocol pending | missing | candidate |
| EA-C002 | seed primary-source pass complete | narrowed | partial/needed | Ranger/architecture evidence exists; controlled comparison pending | missing | candidate |

## Next decision gate

Do not promote either contribution until the systematic scholarly expansion has searched the nearest academic literature in data provenance, secure logging, remote attestation, digital custody, provenance graphs, and cyber-physical assurance.