# ETS Formal Proof Index

## Purpose

This document indexes ETS theorem families, invariants, symbolic validation status, executable validation coverage, and known proof limitations.

The purpose of this document is not to exaggerate formal guarantees.

Its purpose is to maintain:

- scientific accountability;
- proof traceability;
- validation transparency;
- and explicit assumption tracking.

---

# Validation Categories

ETS distinguishes between the following categories.

| Category | Meaning |
|---|---|
| Implemented | operational code exists |
| Formally Modeled | TLA+ specification exists |
| Executably Validated | TLC exploration executes successfully |
| Symbolically Validated | Apalache or SMT-backed analysis exists |
| Refinement Mapped | correspondence relationship documented |
| Theorem Proven | mechanically verified proof exists |
| Hypothetical | future research only |

Maintaining these distinctions is one of the most important scientific responsibilities of the ETS project.

---

# Model Registry

## ETSLog

| Property | Status |
|---|---|
| Implemented | yes |
| Formally Modeled | yes |
| TLC Validation | yes |
| Symbolic Validation | scaffolded |
| Refinement Mapping | partial |
| Mechanized Proof | no |

### Core Claims
- append-only semantics;
- bounded evidence integrity.

### Important Boundaries
- no cryptographic proof theorem;
- no universal completeness proof.

---

## ETSVerifierFederation

| Property | Status |
|---|---|
| Implemented | partial |
| Formally Modeled | yes |
| TLC Validation | yes |
| Symbolic Validation | scaffolded |
| Refinement Mapping | partial |
| Mechanized Proof | no |

### Core Claims
- quorum semantics;
- bounded conflict visibility;
- verifier disagreement handling.

### Important Boundaries
- no Byzantine consensus proof;
- no dynamic governance proof.

---

## ETSTemporalByzantineFederation

| Property | Status |
|---|---|
| Implemented | partial |
| Formally Modeled | yes |
| TLC Validation | yes |
| Symbolic Validation | future work |
| Refinement Mapping | weak |
| Mechanized Proof | no |

### Core Claims
- freshness semantics;
- stale quorum handling;
- bounded adversarial visibility.

### Important Boundaries
- no asynchronous Byzantine liveness proof.

---

## ETSProbabilisticTrust

| Property | Status |
|---|---|
| Implemented | partial |
| Formally Modeled | yes |
| TLC Validation | yes |
| Symbolic Validation | future work |
| Refinement Mapping | weak |
| Mechanized Proof | no |

### Core Claims
- discretized confidence semantics;
- bounded trust degradation.

### Important Boundaries
- not Bayesian mathematics;
- not stochastic theorem proof.

---

## ETSLivenessFederation

| Property | Status |
|---|---|
| Implemented | partial |
| Formally Modeled | yes |
| TLC Validation | yes |
| Symbolic Validation | future work |
| Refinement Mapping | weak |
| Mechanized Proof | no |

### Core Claims
- bounded progress under fairness assumptions.

### Important Boundaries
- fairness assumptions required;
- no universal liveness proof.

---

## ETSAsyncTransport

| Property | Status |
|---|---|
| Implemented | partial |
| Formally Modeled | yes |
| TLC Validation | yes |
| Symbolic Validation | scaffolded |
| Refinement Mapping | partial |
| Mechanized Proof | no |

### Core Claims
- replay visibility;
- delayed transport semantics;
- topology-aware delivery.

### Important Boundaries
- no stochastic transport mathematics;
- no Internet-scale network proof.

---

# Symbolic Verification Status

## Sprint 12 Status

Sprint 12 establishes:

- Apalache configuration;
- symbolic validation workflow structure;
- proof-index traceability;
- symbolic verification boundaries.

Current symbolic support remains:

> bounded and experimental.

Future work should:

- create symbolic-safe model variants;
- add symbolic liveness analysis;
- integrate SMT artifact publication;
- strengthen refinement correspondence.

---

# Current Strongest Research Areas

ETS is currently strongest in:

- bounded executable semantics;
- conflict visibility;
- evidence theory;
- replay visibility semantics;
- uncertainty preservation;
- reproducibility discipline.

---

# Current Weakest Research Areas

ETS remains weakest in:

- theorem-level proof completeness;
- probabilistic mathematics;
- implementation refinement proofs;
- symbolic liveness proofing;
- large-scale adversarial simulation.

These weaknesses are intentionally documented rather than hidden.

---

# Dissertation Guidance

The dissertation should consistently preserve the distinction between:

- evidence;
- assumptions;
- executable validation;
- symbolic validation;
- and theorem proof.

ETS becomes weaker whenever these categories are blurred.

ETS becomes stronger whenever those boundaries remain explicit.
