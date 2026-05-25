# ETS Dissertation Structure

## Working Title

**Evidence Transparency Systems: A Formal Architecture for Computationally Bounded Evidentiary Coordination Under Adversarial and Incomplete Observation Conditions**

## Purpose

This document defines the dissertation narrative architecture for ETS.

The dissertation must not read as:

- a product manual;
- a protocol brochure;
- a blockchain alternative pitch;
- or a collection of unrelated formal models.

It must read as a coherent academic argument.

The central claim is:

> Modern distributed systems need formal mechanisms for coordinating evidence, visibility, confidence, disagreement, and uncertainty under adversarial and incomplete observation conditions.

ETS is proposed as one such architecture.

---

# 1. Dissertation Argument Flow

The dissertation should follow a five-part research arc.

## Part I — Problem Formation

Modern systems increasingly make decisions from distributed evidence, yet they frequently collapse distinct concepts:

- evidence;
- observation;
- trust;
- confidence;
- visibility;
- certainty.

This collapse creates weak foundations for:

- AI governance;
- forensic reconstruction;
- auditability;
- distributed observability;
- adversarial transparency;
- institutional accountability.

## Part II — Theory

ETS introduces an evidence theory for distributed systems.

It separates:

- evidence from truth;
- observation from certainty;
- confidence from proof;
- omission suspicion from completeness;
- disagreement from failure.

## Part III — Formal Architecture

ETS formalizes evidence coordination through layered models:

- append-only evidence state;
- verifier federation;
- temporal freshness;
- adversarial visibility;
- bounded trust;
- liveness and fairness;
- asynchronous transport.

## Part IV — Implementation and Reproducibility

ETS implements a reference research platform with:

- executable TLA+ models;
- CI validation;
- reproducible experiments;
- benchmark artifacts;
- implementation traceability.

## Part V — Implications and Limits

ETS does not claim universal truth or perfect completeness.

Instead, it contributes a bounded framework for determining what conclusions remain defensible under explicit assumptions.

---

# 2. Proposed Chapter Structure

## Chapter 1 — Introduction

Purpose:

- introduce the problem;
- define the thesis;
- state contributions;
- establish research scope.

Key thesis statement:

> ETS is a formal architecture for computationally bounded evidentiary coordination under adversarial and incomplete observation conditions.

Must include:

- motivation;
- problem statement;
- research questions;
- contribution summary;
- dissertation roadmap.

---

## Chapter 2 — Background and Literature Review

Purpose:

- situate ETS in prior research;
- distinguish it from related systems.

Areas:

- append-only logs;
- Certificate Transparency;
- Merkle proof systems;
- distributed consensus;
- Byzantine fault tolerance;
- formal methods;
- computational trust;
- epistemic logic;
- observability and SIEM systems.

Important boundary:

ETS should be framed as synthesis and extension, not invention from nothing.

---

## Chapter 3 — Evidence Theory for Distributed Systems

Purpose:

- define the intellectual core of ETS.

Concepts:

- evidence;
- observation;
- visibility;
- trust;
- confidence;
- certainty;
- disagreement;
- omission suspicion;
- replay visibility;
- epistemic degradation.

This chapter is likely the dissertation's most distinctive theoretical contribution.

---

## Chapter 4 — ETS Protocol Architecture

Purpose:

- define ETS as a layered protocol architecture.

Layers:

1. evidence object layer;
2. integrity layer;
3. transparency log layer;
4. verifier federation layer;
5. temporal/adversarial layer;
6. transport visibility layer;
7. epistemic coordination layer.

Deliverables referenced:

- `FORMAL_ARCHITECTURE.md`;
- RFC drafts;
- protocol diagrams.

---

## Chapter 5 — Formal Models and Verification

Purpose:

- present formal models and validation methods.

Models:

- ETSLog;
- ETSVerifierFederation;
- ETSTemporalByzantineFederation;
- ETSProbabilisticTrust;
- ETSLivenessFederation;
- ETSAsyncTransport.

Validation modes:

- TLC bounded exploration;
- symbolic verification scaffolding;
- proof indexing;
- refinement mapping.

Boundary:

Formal models validate bounded semantics, not universal correctness.

---

## Chapter 6 — Reference Implementation

Purpose:

- describe the implementation as research artifact.

Topics:

- canonicalization;
- hashing;
- inclusion proofs;
- append-only log behavior;
- federation logic;
- reproducibility harness;
- CI validation.

Boundary:

Implementation is a reference research platform, not a production-certified system.

---

## Chapter 7 — Experimental Evaluation and Reproducibility

Purpose:

- demonstrate replayable research methodology.

Topics:

- deterministic replay manifests;
- benchmark artifacts;
- synthetic non-PII datasets;
- transport scenarios;
- replay visibility;
- omission suspicion;
- artifact publication.

Boundary:

Experiments are bounded and synthetic, not universal workload benchmarks.

---

## Chapter 8 — Discussion

Purpose:

- analyze implications.

Topics:

- AI governance;
- forensic systems;
- institutional accountability;
- distributed observability;
- computational trust;
- epistemic integrity.

---

## Chapter 9 — Limitations and Future Work

Purpose:

- preserve scientific honesty.

Limitations:

- no perfect completeness;
- no universal truth proof;
- no full Byzantine consensus;
- no stochastic convergence mathematics yet;
- symbolic verification incomplete;
- refinement proofs incomplete;
- implementation not production certified.

---

## Chapter 10 — Conclusion

Purpose:

- restate the thesis;
- summarize contributions;
- identify the path forward.

Closing frame:

ETS contributes a formal architecture for distinguishing what is evidenced, what is observed, what is trusted, what is uncertain, and what remains defensible under bounded and adversarial conditions.

---

# 3. Contribution Mapping

| Contribution | Chapter | Supporting Artifacts |
|---|---|---|
| Evidence theory | 3 | `EVIDENCE_THEORY.md`, `GLOSSARY.md` |
| Layered ETS architecture | 4 | `FORMAL_ARCHITECTURE.md`, RFC docs |
| Formal model suite | 5 | TLA+ models, TLC CI |
| Symbolic verification path | 5 | `formal/apalache/`, `FORMAL_PROOF_INDEX.md` |
| Reference implementation | 6 | Python package, APIs, benchmark code |
| Reproducibility framework | 7 | `REPRODUCIBILITY.md`, benchmark workflow |
| Research boundary discipline | 9 | proof index, traceability matrix |

---

# 4. Theorem Placement

| Theorem Family | Best Chapter |
|---|---|
| Evidence integrity | Chapter 5 |
| Append-only safety | Chapter 5 |
| Quorum validity | Chapter 5 |
| Conflict visibility | Chapter 5 |
| Liveness under fairness | Chapter 5 |
| Replay visibility | Chapter 5 |
| Omission suspicion boundaries | Chapter 3 or 5 |

---

# 5. Evaluation Placement

Evaluation should appear after formal and implementation chapters.

Recommended flow:

1. define theoretical claim;
2. present formal model;
3. connect implementation;
4. execute reproducible experiment;
5. document limitation.

This prevents the dissertation from over-relying on either pure theory or pure engineering.

---

# 6. Limitation Framing

Limitations should not be hidden.

They should be presented as part of the contribution.

ETS is strongest when it explicitly states:

- what can be evidenced;
- what can be observed;
- what can be suspected;
- what can be bounded;
- what cannot yet be proven.

This is not weakness.

It is the core discipline of the research.
