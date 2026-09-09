# ETS Doctoral Contribution Ledger

This ledger records candidate contributions to knowledge. A contribution is not established merely because code or documentation exists.

## Contribution record schema

Each contribution should use this structure:

```text
ID: EA-C###
Title:
Status: candidate | supported | revised | refuted | retired
Record type: prospective | retrospective
Research questions:
Claim:
Problem addressed:
Prior art / related work:
Identified gap:
Difference from prior art:
Formal definition/model:
Methodology:
Implementation evidence:
Experiment IDs:
Results:
Negative results / counterexamples:
Assumptions:
Limitations:
Public artifacts:
Publication target/status:
Independent validation:
Impact evidence:
Authorship/contribution:
First documented:
Last reviewed:
```

## Candidate contribution inventory

The entries below are **candidate** contributions. They require literature review and evidence qualification before they may be described as original contributions to knowledge.

### EA-C001 — Evidence Object model

- **Status:** candidate
- **Record type:** retrospective
- **Research questions:** RQ1, RQ3
- **Candidate claim:** ETS provides a bounded Evidence Object model for independently evaluating identity, integrity, provenance, custody, and declared verification context while separating those properties from semantic truth.
- **Existing evidence:** protocol contracts, canonicalization/hash implementation, verifier tests, formal traceability matrix.
- **Prior-art qualification:** first-pass WP1 comparison completed in `WP1_EVIDENCE_OBJECT_GRAPH_PRIOR_ART.md`; broad novelty claims around provenance records, signed metadata, transparency logs, event histories, and attester/verifier separation are explicitly excluded.
- **Provisional research gap:** domain-neutral composition of independently inspectable assurance dimensions with explicit epistemic/nonclaim semantics, historical standing context, and consequence/result evidence remains a candidate gap requiring deeper literature review and evaluation.
- **Primary gaps:** peer-reviewed systematic prior-art review; minimum-sufficiency argument; independent implementation/reproduction; evaluation of the narrowed differentiators.

### EA-C002 — Evidence Graph model

- **Status:** candidate
- **Record type:** retrospective
- **Research questions:** RQ2, RQ3
- **Candidate claim:** typed graph relationships can make derivation, custody, authority, observation, decision, action, and consequence claims separately inspectable and verifiable without asserting truth merely from graph membership.
- **Existing evidence:** existing architecture/research corpus; Ranger relationship modeling.
- **Prior-art qualification:** first-pass WP1 comparison completed in `WP1_EVIDENCE_OBJECT_GRAPH_PRIOR_ART.md`; W3C PROV is the primary baseline and prevents any broad novelty claim for typed provenance graphs.
- **Provisional research gap:** edges as separately attributable evidentiary claims combined with epistemic/contradiction state, authority/policy dependencies, consequence custody, shared-source dependency, and explicit noncausality remains a candidate gap requiring formal mapping and evaluation.
- **Primary gaps:** relation-by-relation mapping to W3C PROV; peer-reviewed prior-art review; canonical graph semantics; empirical/formal evaluation.

### EA-C003 — Explicit trust and claim-boundary decomposition

- **Status:** candidate
- **Record type:** retrospective
- **Research questions:** RQ3, RQ7
- **Candidate claim:** verification outputs can preserve useful cryptographic/procedural guarantees while explicitly retaining unsupported external assumptions instead of collapsing integrity into truth.
- **Existing evidence:** conservative claim boundaries in research documentation and formal traceability matrix.
- **Primary gaps:** formal taxonomy; comparison with trust/attestation literature; user/verifier evaluation criteria.

### EA-C004 — Offline/asynchronous evidence continuity

- **Status:** candidate
- **Record type:** retrospective
- **Research questions:** RQ4
- **Candidate claim:** bounded evidence provenance can remain independently verifiable through asynchronous transport, reordering, partition, and later synchronization under explicit fairness and healing assumptions.
- **Existing evidence:** `ETSAsyncNetwork.tla`, liveness model, async network implementation/tests, reproducibility work.
- **Primary gaps:** refinement mapping; wider adversarial evaluation; publication-grade experiments.

### EA-C005 — AI Witness / machine-action provenance

- **Status:** candidate
- **Record type:** retrospective
- **Research questions:** RQ5, RQ7
- **Candidate claim:** consequential AI actions can be evidenced through externally inspectable inputs, model/runtime identity, policy, declared decisions, authority, actions, and results without claiming access to or fidelity of hidden internal reasoning.
- **Existing evidence:** ETS architecture and AI Witness research/case studies.
- **Primary gaps:** literature review; stable experimental protocol; independent observer evaluation; nondeterministic replication study.

### EA-C006 — Cyber-physical decision provenance

- **Status:** candidate
- **Record type:** retrospective for concept; prospective for future Ranger experiments
- **Research questions:** RQ6, RQ8
- **Candidate claim:** a cyber-physical evidence chain can distinguish observation, inference, decision, authority, command, actuator behavior, and resulting physical state such that an independent verifier can identify which boundaries are evidenced and which remain asserted.
- **Existing evidence:** Ranger research program and verifier composition work.
- **Primary gaps:** physical experimental data; sensor/actuator independent observation; controlled fault injection; external reproduction.

### EA-C007 — Consequence custody

- **Status:** candidate
- **Record type:** retrospective for concept; prospective for future experiments
- **Research questions:** RQ6, RQ8
- **Candidate claim:** post-action resulting-state evidence requires a custody/provenance treatment distinct from command evidence and can be modeled without inferring consequence from intent.
- **Existing evidence:** Ranger and Evidence Architecture research expansion.
- **Primary gaps:** formal definition; prior-art comparison; experimental evaluation across digital and physical consequences.

### EA-C008 — Evidence-aware adversarial qualification

- **Status:** candidate
- **Record type:** prospective
- **Research questions:** RQ7
- **Candidate claim:** security qualification can treat evidence invariants and the provenance of the qualification itself as first-class research objects, enabling reproducible analysis of where ETS claims survive or fail.
- **Existing evidence:** ETS Adversarial Qualification research program.
- **Primary gaps:** executed experiment series; quantitative outcome criteria; external comparison and reproduction.

## Promotion rule

A candidate contribution should not become `supported` until, at minimum:

1. relevant prior art is documented;
2. the claimed gap is defensible;
3. a method is explicit;
4. supporting evidence is linked;
5. limitations and counterexamples are recorded;
6. authorship is clear; and
7. the contribution can be explained independently of product marketing.
