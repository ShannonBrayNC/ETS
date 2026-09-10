# WP1 — Evidence Graph ↔ W3C PROV Mapping and Deeper Prior-Art Review

**Status:** second-pass doctoral qualification work  
**Date:** 2026-09-09  
**Contributions:** EA-C001, EA-C002  
**Record type:** retrospective qualification of candidate contributions

## Research-integrity boundary

This document narrows the candidate novelty surface. It does not promote EA-C001 or EA-C002.

W3C PROV is the primary provenance baseline because it already provides domain-neutral `Entity`, `Activity`, and `Agent` concepts plus typed relations such as generation, use, derivation, attribution, association, delegation, revision, specialization, primary source, and invalidation. PROV explicitly supports domain-specific specialization. Therefore, an ETS relationship that can be represented faithfully as an ordinary or qualified PROV relation is not novel merely because ETS gives it a domain-specific name.

The doctoral question is narrower:

> Does Evidence Architecture contribute independently useful semantics for bounded evidentiary claims that remain materially distinct from ordinary provenance description, especially where standing, epistemic state, verification dimensions, and consequence formation must remain separately inspectable?

## Deeper prior-art findings

### Database provenance

Buneman, Khanna, and Tan's 2001 work distinguishes why-provenance from where-provenance and formalizes how database outputs depend on source data.

Implication for ETS:

- derivation lineage is mature prior art;
- source-dependency graphs are not novel;
- tracing which inputs influenced an output is not itself novel;
- EA-C002 must not rely on inference lineage alone as a contribution.

The remaining question is whether Evidence Architecture adds useful semantics by combining inference lineage with independently attributable claim edges, epistemic state, standing, contradiction, and consequence boundaries.

### Secure and forward-integrity audit logging

Schneier and Kelsey established secure audit-log designs intended to detect undetectable modification or destruction of pre-compromise log entries even after a logging system is compromised.

Implication for ETS:

- tamper-evident or forward-secure logging is prior art;
- compromise-resistant audit history is not novel as a general goal;
- Evidence Objects and retained checkpoints must be evaluated as compositions of established cryptographic mechanisms plus bounded evidence semantics, not as novelty in secure logging itself.

### Digital-forensics chain of custody

Digital-forensics literature contains substantial chain-of-custody models, including integrity, authenticity, auditability, transfer history, and blockchain-based preservation approaches.

Implication for ETS:

- chain of custody is mature prior art;
- digitally signed custody transfers are not novel;
- graph-based custody lineage is not novel;
- candidate differentiation must instead focus on the relationship among custody, standing, claim boundaries, and independently verified consequence evidence.

### RATS attestation architecture

RFC 9334 already separates Attester, Evidence, Verifier, Attestation Result, Relying Party, Reference Values, Endorsements, and appraisal policies. Evidence is explicitly treated as claims rather than automatic truth.

Implication for ETS:

- Evidence → Verifier → Result architecture is not novel;
- appraisal policy is not novel;
- claim-oriented attestation is not novel;
- EA-C001 must be distinguished by semantics beyond generic evidence/appraisal roles.

## W3C PROV relation mapping

The table below classifies common Evidence Architecture relationships against PROV. “Direct” means a close semantic equivalent exists. “Specialization” means PROV can represent the relation through a domain-specific subproperty or qualified relation without loss of the core provenance meaning. “Extension” means the Evidence Architecture semantics include a normative distinction not carried by the base PROV relation alone and require an additional profile or model rule.

| Evidence Architecture relation/concept | Closest W3C PROV concept | Classification | Qualification |
|---|---|---|---|
| artifact produced by process | `prov:wasGeneratedBy` | Direct | Ordinary generation semantics. |
| process consumed artifact | `prov:used` | Direct | Ordinary usage semantics. |
| artifact derived from artifact | `prov:wasDerivedFrom` | Direct | Prior art; not novel. |
| artifact originated from source | `prov:hadPrimarySource` | Direct | Prior art. |
| revision / correction lineage | `prov:wasRevisionOf` | Direct | Append-only correction policies may add constraints, but revision relation itself is prior art. |
| actor responsible for artifact | `prov:wasAttributedTo` | Direct | Identity assurance remains outside the bare relation. |
| actor participated in process | `prov:wasAssociatedWith` | Direct | Authorization/standing is not implied by association. |
| delegated actor relationship | `prov:actedOnBehalfOf` | Direct | Historical scope, expiry, revocation, and jurisdiction require separate standing evidence. |
| process informed by process | `prov:wasInformedBy` | Direct | Does not itself establish causality. |
| entity invalidated by process | `prov:wasInvalidatedBy` | Direct | Useful for revocation/supersession, but policy standing semantics remain additional. |
| version/specific state of entity | `prov:specializationOf` | Direct | Useful for historical state/version modeling. |
| equivalent alternate representation | `prov:alternateOf` | Direct | No novelty. |
| member in evidence collection/pack | `prov:hadMember` | Direct | Inclusion semantics alone are prior art. |
| source observation produced observation artifact | `prov:wasGeneratedBy` + qualified generation | Specialization | Evidence Architecture adds sensor/capability/quality semantics as profile data. |
| inference used source observations | `prov:used` + `prov:wasDerivedFrom` | Specialization | Model/version/threshold/uncertainty can be represented through qualified activities/entities. |
| inferred claim depends on upstream claim | `prov:wasDerivedFrom` | Specialization | Shared-source detection is graph analysis over provenance, not automatically novel. |
| policy governed decision/process | qualified association / domain property | Specialization | PROV can express policy entity used by activity; EA adds policy-in-force and standing rules. |
| authority justified action | association/delegation + policy entity | Extension | PROV describes responsibility/delegation but does not by itself define the EA Standing Boundary. |
| standing evaluation justified bind | activity using authority/policy/state entities | Extension | The graph can be encoded in PROV, but EA's normative claim is that standing remains distinct from integrity/inclusion/reconstruction. |
| decision produced requested command | generation/derivation/activity chain | Specialization | PROV can encode the chain. EA requires that decision and command remain distinct propositions. |
| requested command accepted/executed | activity/entity sequence | Specialization | PROV can encode transitions; EA makes non-collapse a verification rule. |
| actuator output led to physical-state observation | generation/use/derivation chain | Extension | Encoding is possible in PROV; EA's candidate distinction is bounded consequence semantics and refusal to infer physical outcome from command evidence. |
| observed result supports consequence claim | derivation plus observation activity | Extension | EA requires consequence evidence to remain distinct from intent, command, acknowledgement, and standing. |
| contradiction between claims | no single canonical starting-point relation | Extension/profile | Can be modeled with domain-specific properties or entities; contradiction semantics must be independently defined. |
| epistemic state `UNKNOWN` / `NOT_AVAILABLE` / `INDETERMINATE` | domain attributes/entities | Extension/profile | PROV can carry attributes, but EA treats these states as first-class claim semantics rather than absence of triples. |
| claim edge has its own producer/signature/verifier result | qualified influence/bundle or reification patterns | Extension/profile | PROV can describe provenance of the relation representation; EA must demonstrate measurable value from mandatory edge-as-claim treatment. |
| verifier result decomposed by dimension | provenance of verification activity/result entity | Extension/profile | PROV can model the activity/result, but does not prescribe EA's integrity/identity/custody/freshness/standing/completeness/consequence vector. |

## What this mapping eliminates as novelty

EA-C002 must not claim novelty for any of the following:

- entity/activity/agent graph structure;
- typed provenance relations;
- derivation or dependency graphs;
- agent attribution or delegation;
- revision lineage;
- provenance of provenance;
- source-dependency analysis;
- event/process chains;
- domain-specific specialization of a provenance ontology.

These are already squarely covered by PROV and related provenance research.

## Candidate semantics that remain researchable

The mapping leaves a smaller set of potentially defensible contributions, subject to deeper literature review and evaluation.

### 1. Standing as a distinct verification boundary

Evidence Architecture explicitly separates:

- reconstruction: what evidence supports what happened;
- standing: whether material authorization/policy predicates held at the relevant time;
- consequence custody: whether a standing-qualified transition was permitted to bind.

PROV can represent the entities and activities involved, but the EA contribution claim is not the graph encoding. It is the normative separation of these guarantees and the verification consequences of that separation.

### 2. Command/result non-collapse

A provenance graph can represent decision, command, execution, and result. Evidence Architecture makes a stronger semantic requirement:

> evidence of a decision is not evidence of a command; evidence of a command is not evidence of execution; evidence of execution is not evidence of the resulting physical or external state.

The candidate contribution is this bounded-claim discipline plus verifiable transition semantics, not the existence of a path in a graph.

### 3. First-class epistemic state

PROV can carry attributes and domain extensions. Evidence Architecture proposes explicit semantics for states such as:

- `NOT_OBSERVED`;
- `NOT_AVAILABLE`;
- `UNKNOWN`;
- `INDETERMINATE`;
- `CONTRADICTED`.

The research question is whether making these states mandatory and machine-verifiable reduces false inference relative to ordinary missing or unqualified provenance information.

### 4. Edge-as-claim verification

PROV supports qualification and provenance descriptions about provenance. The remaining EA-C002 hypothesis must therefore be more specific:

> Does requiring consequential relationships themselves to have attributable evidence, verification status, epistemic status, and explicit nonclaims improve reconstruction accuracy or reduce unsupported inference?

This is testable and falsifiable.

### 5. Verification claim vectors

RATS and other verification architectures already produce appraisal results. Evidence Architecture proposes decomposing verification into dimensions such as:

- schema/canonicalization;
- digest/signature;
- signer or producer identity under a trust model;
- custody continuity;
- retained-state freshness;
- policy standing;
- scoped completeness;
- consequence linkage;
- explicit nonclaims.

The contribution, if any, lies in the compositional semantics and empirical benefit of preserving dimensions instead of emitting a generic `verified` state.

## Proposed formal research hypotheses

### H-C001-A — Bounded object verification

A verifier using a dimensional Evidence Object result will make fewer unsupported semantic inferences than a verifier given an otherwise equivalent binary verification result.

### H-C002-A — Edge-as-claim reconstruction

For consequential event graphs, requiring independently attributable relationship evidence will improve reconstruction precision compared with topology-only or unqualified provenance graphs.

### H-C002-B — Epistemic-state preservation

Explicit `UNKNOWN`/`NOT_AVAILABLE`/`INDETERMINATE`/`CONTRADICTED` states will reduce false negative/false positive conclusions compared with treating missing evidence as false or absent.

### H-C002-C — Consequence decomposition

Explicit decision → requested command → accepted/executed action → resulting-state observation decomposition will reduce incorrect outcome attribution compared with models that collapse one or more of those stages.

These remain hypotheses and require prospective experimental protocols.

## Proposed evaluation design

A future experiment should construct matched evidence packages for the same scenario using:

1. a baseline PROV representation;
2. a PROV representation with domain extensions but no EA verification rules;
3. an Evidence Architecture representation with bounded claim vectors, epistemic states, and consequence-stage separation.

Independent evaluators should answer a fixed set of reconstruction questions. Measure:

- supported-claim precision;
- unsupported-inference rate;
- missed-contradiction rate;
- false completeness assumptions;
- command/result confusion rate;
- standing/integrity confusion rate;
- reconstruction time;
- inter-rater agreement.

If EA does not materially improve one or more predeclared metrics, the contribution should be narrowed or refuted.

## Current disposition

- **EA-C001:** remains `candidate`. The Evidence Object must be defended as a bounded verification composition, not as a novel provenance record or signed envelope.
- **EA-C002:** remains `candidate`. The Evidence Graph must be defended through specific semantics and evaluation outcomes, not as a novel typed provenance graph.

## Primary references for this pass

- W3C, *PROV-O: The PROV Ontology*, W3C Recommendation, 2013: https://www.w3.org/TR/prov-o/
- W3C, *PROV-DM: The PROV Data Model*, W3C Recommendation, 2013: https://www.w3.org/TR/prov-dm/
- Buneman, Khanna, Tan, *Why and Where: A Characterization of Data Provenance*, ICDT 2001, DOI 10.1007/3-540-44503-X_20.
- Schneier and Kelsey, *Secure Audit Logs to Support Computer Forensics*, ACM TISSEC, 1999.
- IETF RFC 9334, *Remote ATtestation procedureS (RATS) Architecture*, 2023.
- Lone and Mir, *Forensic-chain: Blockchain based digital forensics chain of custody with PoC in Hyperledger Composer*, Digital Investigation 28, 2019, DOI 10.1016/j.diin.2019.01.002.

## Next WP1 slice

1. provenance semirings and scientific-workflow provenance;
2. authorization/trust-management provenance;
3. claim/evidence graph and argumentation literature;
4. AI provenance/model lineage;
5. cyber-physical provenance, safety cases, and runtime assurance;
6. formalize the prospective experiment above in `EXPERIMENT_LEDGER.md` without executing or backdating it.
