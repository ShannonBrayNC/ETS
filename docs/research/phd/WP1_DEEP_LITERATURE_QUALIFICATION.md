# WP1 Deep Literature Qualification — Evidence Object and Evidence Graph

**Status:** second-pass prior-art qualification  
**Date:** 2026-09-09  
**Contributions:** EA-C001, EA-C002  
**Record type:** retrospective literature qualification

## Research-integrity boundary

This document narrows candidate contribution claims. It does not promote either contribution. The purpose is to identify where Evidence Architecture overlaps established research and where a narrower hypothesis may still be testable.

## 1. Provenance semirings and database provenance

Green, Karvounarakis, and Tannen's provenance-semiring framework establishes strong prior art for algebraic provenance of relational query results. It unifies several prior provenance interpretations, including why-provenance and lineage, through semiring annotations and shows that provenance can be computed compositionally with query evaluation.

### Implication for EA-C001/EA-C002

Evidence Architecture must not claim novelty for:

- lineage of derived data;
- annotations that explain which inputs contributed to an output;
- algebraic composition of provenance;
- query-result provenance;
- dependency-aware derivation semantics generally.

The remaining candidate gap is not derivation lineage itself. It is whether evidentiary relationships that include derivation, authority, epistemic state, verification scope, standing, attempted action, execution, consequence, and resulting observation can be represented and independently evaluated without collapsing those categories into one provenance relation.

## 2. Scientific-workflow provenance and reproducibility

Scientific-workflow research already uses provenance traces to reconstruct executions, compare runs, identify divergence, and support reproducibility. Missier et al.'s PDIFF work is particularly relevant because it compares provenance traces and identifies where reproduced executions diverge.

### Implication

Evidence Architecture must not claim novelty for:

- workflow execution traces;
- provenance-based reproducibility;
- graph comparison of workflow runs;
- version-aware reconstruction of computational processes.

A narrower distinction remains plausible around consequence-stage decomposition and claim boundaries: reproduction of a workflow is not equivalent to establishing the standing of a consequential decision or proving that an intended external consequence actually occurred.

## 3. Authorization provenance

Authorization-provenance literature predates ETS. Hu et al. explicitly model provenance of authorization decisions in distributed settings. ACCESSPROV later tracks inputs used in access-control decisions so flaws can be detected at runtime.

### Implication

Evidence Architecture must not claim novelty for:

- provenance of access-control decisions;
- tracing policy inputs to authorization outcomes;
- delegation provenance;
- runtime provenance used to diagnose authorization flaws.

The candidate distinction is narrower: Evidence Architecture treats **standing** as a verification boundary that remains semantically distinct from identity, integrity, inclusion, and historical reconstruction, and then separately models whether a standing-qualified transition was permitted to bind into consequence.

This distinction still requires formal comparison against trust-management, authorization-logic, capability, and policy-provenance literature.

## 4. Claim/evidence and argumentation graphs

Structured claim-evidence systems are established prior art. Scientific-evidence models such as SEE and Micropublications represent claims, supporting evidence, argumentative relationships, attribution, and provenance as structured graphs.

### Implication

Evidence Architecture must not claim novelty for:

- representing claims as graph nodes;
- support/challenge relationships;
- attribution of claims;
- evidence-backed argument graphs;
- provenance of scientific claims.

A candidate distinction remains in treating operational relationships themselves as evidentiary claims with independent producer/provenance/verification state and in explicitly preserving contradiction, unknown, unavailable, shared-source dependence, and noncausality across operational decisions and consequences.

## 5. AI/ML provenance and lineage

AI provenance is now an active research area. Existing work covers model genealogy, training/deployment lineage, attestable ML pipelines, data/software supply-chain provenance, and machine-readable model records. These works materially narrow any claim that AI Witness is novel because it records model identity, data lineage, pipeline steps, or deployment provenance.

### Implication

Evidence Architecture must not claim novelty for:

- model lineage;
- model genealogy;
- training-data provenance;
- ML pipeline provenance;
- attestable model artifacts;
- machine-readable model records.

The remaining researchable question is whether machine-action evidence benefits from separating:

`input observation -> inference -> policy/authority -> decision -> tool/action request -> accepted/executed action -> consequence -> result observation`

while preserving uncertainty and unsupported claims and without asserting access to hidden model reasoning.

## 6. Cyber-physical provenance, runtime assurance, and safety cases

Cyber-physical security literature already includes provenance verification of control messages and enforcement decisions. Runtime assurance frameworks already separate advanced behavior from safety controllers and switching logic. Assurance-case research already structures claims, arguments, and evidence for safety-critical systems and manages evidence/trace links across the lifecycle.

### Implication

Evidence Architecture must not claim novelty for:

- runtime assurance generally;
- safety cases or assurance cases;
- structured safety evidence;
- control-message provenance;
- provenance-aware policy enforcement;
- safety-controller switching architectures.

The most defensible remaining candidate distinction is **consequence custody** as a specific evidentiary/architectural boundary: preserving and, for implementations that claim it, enforcing the link from historically valid standing through attempted transition to actual consequence, with an explicit rule that command evidence is not result evidence.

This remains a candidate contribution and must be compared against runtime-enforcement, reference-monitor, transactional, safety-interlock, assurance-case, and cyber-physical logging literature.

## 7. Revised novelty surface

The broad novelty surface is now substantially reduced.

### Explicitly excluded from novelty claims

- provenance records and graphs;
- lineage and derivation;
- claim/evidence graphs;
- workflow provenance and reproducibility;
- authorization provenance;
- policy-input tracing;
- secure/tamper-evident logs;
- attestation/verifier roles;
- ML model/data lineage;
- runtime assurance;
- safety and assurance cases;
- control-message provenance;
- chain of custody generally.

### Candidate differentiators still requiring proof

1. **Dimensional verification claim vectors** that prevent `verified` from silently implying truth, authority, completeness, standing, currentness, or consequence.
2. **First-class epistemic state and nonclaims** carried with evidence and relationships, including unknown, unavailable, indeterminate, contradicted, and not observed.
3. **Standing as a distinct verification boundary** separable from integrity, identity, inclusion, and reconstruction.
4. **Consequence-stage non-collapse**: decision, requested action, accepted/executed action, consequence, and result observation remain distinct evidentiary stages.
5. **Consequence custody** as a separately claimed and qualified enforcement/evidence boundary.
6. **Edge-as-claim semantics** in which relationships themselves can carry source, epistemic state, verification result, and dependency provenance.
7. **Shared-source dependence and inference provenance** used to prevent false corroboration.

None of these are yet established as original contributions.

## 8. Updated falsification rule

EA-C001 and EA-C002 should be further narrowed, revised, or refuted if prior work demonstrates substantially equivalent integrated semantics for the candidate differentiators above, especially if that work already combines:

- claim-bounded verification;
- explicit epistemic nonclaims;
- historical authorization/standing;
- transition/consequence separation;
- relationship-level verification;
- and independent reconstruction across digital and physical boundaries.

## 9. Implication for EXP-001

EXP-001 should no longer test whether Evidence Architecture has “more provenance.” That would be uninformative and confounded.

It should test whether the bounded semantics above reduce specific reconstruction errors relative to two baselines:

1. standard W3C PROV;
2. W3C PROV plus ordinary domain extensions that provide the same factual content but omit Evidence Architecture's bounded verification rules.

The experiment must therefore hold factual information constant and vary the **semantic discipline and verification structure**, not merely the amount of information presented.

## Sources qualified in this pass

- Green, Karvounarakis, Tannen — *Provenance Semirings*, PODS 2007.
- Missier et al. — *Provenance and data differencing for workflow reproducibility analysis*.
- Hu et al. — *Managing Authorization Provenance: A Modal Logic Based Approach*, ICTAI 2009.
- Capobianco, Skalka, Jaeger — *ACCESSPROV: Tracking the Provenance of Access Control Decisions*, TaPP 2017.
- SEE — structured representation of scientific claims, provenance, and argumentative support.
- Micropublications — semantic model for claims, evidence, arguments, and annotations.
- Atlas — ML lifecycle provenance/transparency framework.
- Unified Model Record / model provenance work for foundation-model genealogy.
- yProv4ML — ML provenance using PROV-JSON.
- Message Authentication and Provenance Verification for Industrial Control Systems.
- Ulgen runtime-assurance framework for cyber-physical systems.
- SACM/safety-evidence management and CPS assurance-case literature.

## Disposition

- **EA-C001:** remains `candidate`; novelty surface narrowed again.
- **EA-C002:** remains `candidate`; relation/claim semantics remain the primary research focus.
- **EXP-001:** proceed only after corpus, scoring rubric, evaluator protocol, and analysis plan are frozen prospectively.
