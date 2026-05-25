# ETS Symbolic Verification

## Purpose

This document defines the ETS symbolic verification strategy.

ETS currently uses two major formal validation approaches:

| Validation Mode | Purpose |
|---|---|
| TLC | bounded explicit-state exploration |
| Apalache | SMT-backed symbolic analysis |

These approaches are complementary.

Neither currently constitutes universal theorem proof.

---

# 1. Why Symbolic Verification Matters

TLC is extremely valuable for executable state exploration.

However:

- explicit-state exploration can encounter state explosion;
- bounded exploration may miss classes of symbolic behaviors;
- liveness and fairness semantics become increasingly difficult at scale.

Symbolic verification helps address some of these limitations.

ETS therefore introduces:

> bounded symbolic validation as a complementary research discipline.

---

# 2. Current Symbolic Verification Scope

Current Sprint 14 symbolic support includes:

- Apalache execution workflow;
- symbolic target manifest;
- proof artifact publication;
- symbolic verification traceability.

Current symbolic verification remains:

> bounded and partial.

ETS does NOT currently claim:

- complete symbolic proof coverage;
- theorem completeness;
- mechanized proof correctness;
- universal liveness proof.

---

# 3. Initial Symbolic Verification Targets

| Model | Priority | Symbolic Status |
|---|---|---|
| ETSLog | high | targeted |
| ETSVerifierFederation | high | targeted |
| ETSAsyncTransport | high | targeted |
| ETSTemporalByzantineFederation | medium | deferred |
| ETSProbabilisticTrust | medium | deferred |
| ETSLivenessFederation | future | liveness-specialized |

The initial symbolic focus intentionally prioritizes:

- safety-oriented models;
- bounded state consistency;
- replay-order semantics;
- verifier conflict semantics.

---

# 4. Unsupported or Challenging Areas

The following areas may require:

- symbolic-safe refactoring;
- reduced abstractions;
- separate liveness models;
- bounded fairness simplifications.

## Known Difficult Areas

- temporal adversarial transitions;
- liveness fairness semantics;
- confidence-state explosion;
- replay-order combinatorics;
- topology-aware transport branching.

These limitations are expected.

---

# 5. TLC vs Apalache

ETS intentionally distinguishes between:

## TLC

Strengths:

- executable;
- concrete-state exploration;
- excellent debugging visibility;
- deterministic counterexamples.

Limitations:

- state explosion;
- bounded explicit exploration only.

---

## Apalache

Strengths:

- SMT-backed symbolic reasoning;
- symbolic invariant analysis;
- stronger bounded abstraction capabilities.

Limitations:

- unsupported TLA+ constructs;
- symbolic complexity;
- bounded symbolic assumptions;
- liveness complexity.

---

# 6. Proof Artifact Policy

ETS preserves:

- symbolic failures;
- parser failures;
- unsupported-model records;
- counterexample traces;
- proof manifests.

This is important.

Strong research preserves proof failures as evidence.

Weak research silently discards them.

---

# 7. Current Research Boundary

ETS currently supports:

- executable formal semantics;
- bounded symbolic scaffolding;
- reproducible CI validation;
- symbolic verification traceability.

ETS does NOT yet support:

- theorem-prover integration;
- mechanized correctness proofs;
- complete refinement verification;
- universal symbolic liveness guarantees.

These remain future research goals.

---

# 8. Strategic Importance

Symbolic verification is one of the most important transitions in the ETS research program.

Without symbolic reasoning:
- ETS remains primarily bounded executable formalism.

With symbolic reasoning:
- ETS increasingly enters advanced formal-methods research territory.

This transition materially strengthens:

- dissertation rigor;
- publication credibility;
- peer-review defensibility;
- and protocol research maturity.

---

# 9. Most Important Principle

The most important principle is:

> never confuse symbolic exploration with universal proof.

ETS becomes stronger whenever:

- assumptions remain explicit;
- proof boundaries remain documented;
- unsupported semantics remain visible;
- and symbolic limitations remain preserved.

That discipline is central to the scientific integrity of the project.
