# ETS Doctoral Gap Analysis

**Status:** preliminary; originality not established.

This document intentionally distinguishes **rejected broad novelty claims** from **narrow candidate contributions**. Each candidate contribution remains subject to systematic prior-art review, formalization, experiment, external critique and possible retirement.

## EA-C001 — Evidence Object

### Broad claim rejected

`A signed object carrying provenance and verification metadata is novel.`

This claim is not defensible. C2PA manifests, in-toto link metadata, SLSA attestations, transparency-log entries, remote-attestation evidence and established forensic evidence handling overlap materially.

### Narrow candidate contribution

A domain-general Evidence Object may be research-worthy if it can demonstrate a combination not already provided by prior work:

1. deterministic evidence identity/integrity binding;
2. typed claim classes rather than generic provenance assertions;
3. explicit verification context and trust dependencies;
4. custody/provenance relationships;
5. preservation of unsupported assumptions in verifier output;
6. refusal to infer semantic/real-world truth from cryptographic integrity;
7. composability across software, AI, distributed and cyber-physical domains.

### Evidence needed

- formal object schema and invariants;
- minimum-sufficiency argument;
- nearest-neighbor comparison with C2PA, in-toto/SLSA, secure logging, attestation, forensic custody and provenance models;
- verifier semantics for verified / asserted / contradicted / unknown / externally dependent properties;
- controlled experiments showing that the additional distinctions change verifier conclusions;
- independent reproduction or critique.

### Falsification condition

If prior work already provides materially equivalent domain-general claim typing, verification-state semantics, custody/provenance composition and unsupported-assumption retention, `EA-C001` must be narrowed, merged or retired.

---

## EA-C002 — Evidence Graph

### Broad claim rejected

`A graph representing evidence provenance is novel.`

This is not defensible. W3C PROV directly establishes graph-oriented provenance representation; database provenance, C2PA, in-toto, SLSA and other systems encode lineage and transformation relationships.

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
- experiments spanning at least digital and cyber-physical scenarios.

### Falsification condition

If prior literature already supplies materially equivalent typed evidence-edge semantics and certainty/trust propagation across observation → inference → authority → action → consequence, `EA-C002` must be narrowed or retired.

---

## EA-C003 — Explicit trust and claim-boundary decomposition

### Broad claim rejected

`Separating trust assumptions from cryptographic guarantees is novel.`

This is too broad. Security protocols, attestation systems, formal assurance, threat modeling and assurance cases already distinguish assumptions, roots of trust and guaranteed properties.

### Narrow candidate contribution

A verifier-oriented decomposition may be research-worthy if ETS provides a domain-neutral semantics in which every conclusion exposes:

- the evidence directly verified;
- the mechanism that supports the conclusion;
- unresolved external assumptions;
- dependencies on identity, hardware, policy, sensors, institutions or independent observers;
- epistemic state such as verified, asserted, contradicted, unknown or unverifiable.

The intended contribution is not merely documenting assumptions; it is preventing stronger evidentiary state from propagating across unsupported dependencies.

### Evidence needed

- formal trust/claim taxonomy;
- mapping to attestation and assurance-case literature;
- explicit propagation rules and counterexamples;
- user/verifier evaluation showing that the decomposition prevents false-confidence conclusions.

### Falsification condition

If established assurance or evidence frameworks already provide materially equivalent machine-verifiable claim-state propagation and unsupported-assumption retention across the ETS domains, `EA-C003` should be reframed as implementation/application rather than original theory.

---

## EA-C004 — Offline/asynchronous evidence continuity

### Broad claim rejected

`Maintaining integrity through offline operation and later synchronization is novel.`

This is not defensible. Secure logging, distributed databases, replicated logs, offline protocols and synchronization systems already address integrity and reconciliation under disconnection.

### Narrow candidate contribution

Research value may exist in preserving **bounded evidentiary meaning** rather than merely synchronizing records. The candidate question is whether an independent verifier can reconstruct provenance, ordering constraints and custody after delay/reordering/partition while explicitly reporting what cannot be known globally.

### Evidence needed

- formal assumptions concerning fairness, healing, clocks and identities;
- refinement mapping between formal models and implementation;
- prospective partition/reorder/duplicate/replay/omission experiments;
- tests that distinguish local evidence continuity from unsupported global-completeness claims.

### Falsification condition

If existing secure distributed-log or provenance systems already provide equivalent independent-verifier semantics under disconnection and reconciliation, narrow `EA-C004` to the integration of those mechanisms with the broader Evidence Architecture.

---

## EA-C005 — AI Witness / machine-action provenance

### Broad claim rejected

`Logging AI inputs, model identity, outputs and actions for accountability is novel.`

This is increasingly well-covered by responsible-AI observability, ML lifecycle logging and recent LLM audit-trail work.

### Narrow candidate contribution

The candidate gap is action-level evidentiary reconstruction under origin distrust:

- externally inspectable input/context evidence;
- model/runtime identity;
- policy and authority state;
- declared decision output;
- tool/action invocation;
- externally observed result;
- explicit disagreement/omission handling;
- no requirement to disclose hidden chain-of-thought.

The core question is whether an independent verifier can evaluate a consequential machine action without treating the AI system's own narrative as authoritative.

### Evidence needed

- closest-work comparison with AI audit-trail and ML observability literature;
- stable prospective protocol;
- nondeterministic replication studies;
- origin-log omission/manipulation experiments;
- independent observer experiments;
- privacy/security analysis for captured context.

### Falsification condition

If existing AI-accountability frameworks already provide equivalent independent action-level reconstruction with authority, execution and externally observed consequence under an origin-distrust threat model, `EA-C005` must be narrowed or retired.

---

## EA-C006 — Cyber-physical decision provenance

### Broad claim rejected

`Recording sensor input, decisions and actuator commands in a robot is novel.`

This is plainly not defensible. Robotics, autonomous-system assurance and flight/vehicle logging already record such information.

### Narrow candidate contribution

The candidate gap is an evidence semantics that separates:

`Observation -> Inference -> Decision -> Authority -> Command -> Actuator Execution -> Resulting State`

and permits each boundary to carry its own source, integrity, trust and verification state so that an independent verifier can determine which transitions are evidenced and which remain asserted.

### Evidence needed

- mapping against autonomy/runtime-assurance and cyber-physical forensics literature;
- formal event/relation model;
- Ranger prospective experiments;
- independent sensor/actuator observation;
- controlled faults including stale sensors, rejected commands, non-executing actuators and contradictory observers;
- cross-domain comparison showing that the same semantics also apply to digital machine actions.

### Falsification condition

If existing CPS/autonomy provenance or forensic frameworks already provide materially equivalent independent, trust-bounded reconstruction across these boundaries, `EA-C006` must be narrowed to a specific missing property.

---

## EA-C007 — Consequence custody

### Broad claim rejected

`Recording the result of an action is novel.`

This is not defensible.

### Narrow candidate contribution

The research question is whether **post-action resulting-state evidence requires a distinct custody/provenance treatment** because intent, command issuance and even actuator execution do not logically establish the external consequence.

Candidate consequence custody includes:

- independent resulting-state observations;
- observer identity and trust state;
- temporal relationship to the action;
- chain of custody for the observation;
- contradictory-result observations;
- uncertainty and coverage limitations.

### Evidence needed

- prior-art comparison with digital forensics, CPS forensics, event outcome monitoring and assurance;
- formal definition distinguishing action evidence from consequence evidence;
- digital and physical experiments;
- counterexamples where command/action logs produce a false conclusion about resulting state.

### Falsification condition

If an established framework already formalizes result evidence with equivalent custody, independent observation, contradiction and uncertainty semantics across digital and physical systems, `EA-C007` should be reframed or retired.

---

## EA-C008 — Evidence-aware adversarial qualification

### Broad claim rejected

`Using fault injection or penetration testing to evaluate evidence systems is novel.`

It is not. Fault injection, red teaming, adversarial testing and reproducible security evaluation are mature practices.

### Narrow candidate contribution

The candidate gap is treating the **evidence generated about the qualification itself** as a first-class object and evaluating failures in terms of specific evidentiary invariants:

- which claims remain sound;
- which degrade to unknown/unsupported;
- which become contradicted;
- which fail silently;
- whether the qualification can itself be independently reconstructed.

### Evidence needed

- explicit attacker/fault model;
- quantitative invariant-based outcome criteria;
- prospective adversarial series;
- reproducibility package;
- independent replication/challenge;
- negative-result ledger.

### Falsification condition

If existing security-assurance frameworks already provide equivalent evidence-of-evaluation provenance plus machine-verifiable evidentiary degradation semantics, `EA-C008` must be narrowed.

---

## Cross-cutting thesis gap under investigation

A possible higher-level ETS contribution is not a new primitive but a **verification discipline**:

> Independently verifiable evidence systems should separate integrity, provenance, identity, authority, policy, observation, inference, action, custody and consequence claims, and should preserve unsupported assumptions rather than allowing cryptographic validity, graph connectivity or origin-system logging to promote those assumptions into semantic truth.

The stronger cross-domain proposition is:

> The same bounded evidentiary semantics may apply to distributed software, AI-mediated action and cyber-physical action, even though the sensors, actuators, trust roots and consequences differ.

Both statements remain research hypotheses.

## Current status

| Contribution | Prior-art pass | Gap formulation | Formalization | Experiments | External validation | Status |
|---|---|---|---|---|---|---|
| EA-C001 Evidence Object | seed/first pass | narrowed | partial | engineering evidence; doctoral protocol pending | missing | candidate |
| EA-C002 Evidence Graph | seed/first pass | narrowed | partial | architecture/Ranger evidence; controlled comparison pending | missing | candidate |
| EA-C003 Trust decomposition | seed | narrowed | partial | protocol pending | missing | candidate |
| EA-C004 Offline continuity | seed | narrowed | partial/TLA+ | engineering tests exist; prospective protocol pending | missing | candidate |
| EA-C005 AI Witness | seed/current literature started | narrowed | partial | case studies/engineering evidence; prospective protocol pending | missing | candidate |
| EA-C006 Cyber-physical provenance | seed/current assurance literature started | narrowed | partial | Ranger prospective physical experiments pending | missing | candidate |
| EA-C007 Consequence custody | seed | narrowed | needed | prospective digital/physical experiments pending | missing | candidate |
| EA-C008 Adversarial qualification | seed | narrowed | needed | prospective series pending | missing | candidate |

## Highest-risk novelty questions

The following could materially narrow the thesis and should be attacked first:

1. Does provenance/assurance literature already formalize evidence-edge certainty and trust-state propagation in a domain-general way?
2. Does CPS forensics already distinguish command, actuator execution and independently observed result with explicit custody semantics?
3. Do current AI audit-trail systems support independent reconstruction under a malicious/omissive origin threat model?
4. Do attestation/assurance frameworks already provide the equivalent of ETS verification-state decomposition?
5. Can the cross-domain digital/AI/CPS synthesis be defended as more than a taxonomy or engineering integration?

## Promotion rule

No contribution moves from `candidate` to `supported` until:

1. relevant closest prior art is documented;
2. the gap remains defensible after negative searching;
3. the claim is formally or operationally precise;
4. a prospective method exists where practical;
5. supporting and negative evidence are linked;
6. limitations and trust assumptions are explicit;
7. authorship is clear; and
8. independent scholarly criticism or reproduction has been sought.
