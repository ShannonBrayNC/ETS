# ETS Publication Strategy

## Purpose

This document defines the publication decomposition strategy for ETS.

The goal is not to publish a single oversized paper.

The goal is:

> a coherent sequence of bounded, defensible, and incrementally reviewable research contributions.

---

# 1. Publication Philosophy

ETS should avoid:

- sweeping universal claims;
- overloaded mega-papers;
- unsupported cryptographic claims;
- vague “AI trust” narratives.

ETS publications should instead emphasize:

- bounded formalism;
- executable validation;
- evidence theory;
- replayable experiments;
- explicit limitations.

---

# 2. Recommended Publication Sequence

## Paper 1 — ETS Core Transparency Semantics

### Focus

- append-only evidence coordination;
- evidence representation;
- inclusion semantics;
- bounded transparency guarantees.

### Key Contribution

Distinguishing evidence preservation from claims of completeness.

### Recommended Venues

- IEEE Secure Development
- IEEE Cloud
- ACM middleware workshops

---

## Paper 2 — Verifier Federation and Conflict Visibility

### Focus

- quorum semantics;
- verifier disagreement;
- equivocation suspicion;
- conflict preservation.

### Key Contribution

Treating disagreement as observable protocol evidence.

### Recommended Venues

- DSN workshops
- middleware conferences
- distributed systems workshops

---

## Paper 3 — Temporal and Adversarial Evidence Coordination

### Focus

- stale visibility;
- replay-order semantics;
- transport asymmetry;
- confidence degradation.

### Key Contribution

Integrating transport visibility and adversarial observation into evidence coordination.

### Recommended Venues

- IEEE CNS workshops
- ACSAC workshops
- formal methods workshops

---

## Paper 4 — Computationally Bounded Epistemic Coordination

### Focus

- evidence theory;
- trust vs certainty;
- omission suspicion;
- epistemic degradation;
- defensible conclusions under bounded observation.

### Key Contribution

A formal architecture for reasoning about distributed evidence under incomplete and adversarial visibility.

### Recommended Venues

- interdisciplinary systems venues
- trustworthy AI workshops
- governance and systems conferences

---

# 3. Dissertation-to-Publication Mapping

| Dissertation Chapter | Publication Relationship |
|---|---|
| Chapters 1-2 | shared introduction/background |
| Chapter 3 | Paper 4 |
| Chapter 4 | Paper 1 |
| Chapter 5 | Papers 1-3 |
| Chapter 6 | implementation appendix material |
| Chapter 7 | evaluation material across papers |
| Chapters 8-10 | dissertation-only synthesis |

---

# 4. Formatting Standards

## IEEE Standards

Use:

- IEEEtran formatting;
- theorem environments;
- numbered figures;
- bounded abstract lengths;
- explicit limitation sections.

---

## ACM Standards

Use:

- ACM SIG proceedings templates;
- artifact availability statements;
- reproducibility sections;
- formal methods appendices.

---

# 5. Figure Standards

Figures should prioritize:

- layered architecture diagrams;
- verifier federation flows;
- transport visibility diagrams;
- replay-order timelines;
- confidence degradation illustrations.

Avoid:

- marketing diagrams;
- oversized decorative graphics;
- exaggerated security claims.

---

# 6. Bibliography Standards

ETS should maintain:

- BibTeX source files;
- citation consistency;
- theorem references;
- reproducibility references;
- formal-methods references.

Related work should explicitly include:

- Certificate Transparency;
- Trillian;
- Sigsum;
- TLA+;
- Apalache;
- Byzantine fault tolerance;
- epistemic logic;
- distributed observability systems.

---

# 7. Artifact Publication Strategy

Every paper should ideally include:

- executable models;
- benchmark manifests;
- deterministic seeds;
- CI validation references;
- replayable artifacts.

This significantly improves publication credibility.

---

# 8. Strategic Publication Principle

ETS becomes strongest when every paper contributes:

- one bounded claim,
- one reproducible artifact,
- one explicit limitation section,
- and one clearly traceable formal contribution.

That discipline will make the dissertation substantially stronger over time.
