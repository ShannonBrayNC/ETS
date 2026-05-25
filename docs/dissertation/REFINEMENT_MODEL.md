# ETS Refinement Architecture

## Purpose

This document defines the refinement structure connecting:

- conceptual dissertation claims,
- formal protocol models,
- executable validation,
- implementation behavior,
- and future symbolic verification.

The goal is not to claim universal proof.

The goal is:

> disciplined correspondence between abstraction layers.

---

# 1. Why Refinement Matters

Distributed systems research frequently fails at one of two extremes.

## Failure Mode A

The work contains:
- elegant mathematics,
- but no executable implementation relationship.

## Failure Mode B

The work contains:
- extensive code,
- but no formal correspondence to protocol claims.

ETS attempts to avoid both failures.

Refinement architecture is the bridge.

---

# 2. ETS Refinement Hierarchy

ETS currently operates across six abstraction layers.

| Layer | Description |
|---|---|
| L0 | Dissertation and evidence theory concepts |
| L1 | Formal protocol semantics |
| L2 | Executable TLA+ models |
| L3 | Symbolic verification layer |
| L4 | Implementation behavior |
| L5 | Experimental and benchmark outputs |

The dissertation must continuously distinguish these layers.

---

# 3. L0 — Conceptual Layer

This layer contains:

- evidence theory;
- epistemic coordination concepts;
- visibility semantics;
- confidence semantics;
- omission suspicion.

This layer defines:

> what ETS is attempting to reason about.

It does NOT itself constitute proof.

---

# 4. L1 — Formal Semantics Layer

This layer defines:

- state machines;
- invariants;
- liveness properties;
- fairness assumptions;
- adversarial semantics.

Examples:

- verifier federation semantics;
- replay-order semantics;
- transport visibility semantics.

This layer defines:

> formal protocol behavior.

---

# 5. L2 — Executable Formal Models

This layer contains:

- executable TLA+ specifications;
- TLC configurations;
- bounded state exploration.

This layer validates:

- explicit-state bounded behaviors.

It does NOT prove:

- universal correctness;
- unbounded liveness;
- or complete protocol safety.

---

# 6. L3 — Symbolic Verification Layer

This layer introduces:

- SMT-backed symbolic exploration;
- symbolic invariant analysis;
- symbolic safety checks.

Current Sprint 12 work establishes:

- Apalache scaffolding;
- symbolic-validation workflow structure;
- proof-index integration.

This layer strengthens:

> confidence in bounded semantics.

It still does NOT constitute universal theorem proof.

---

# 7. L4 — Implementation Layer

This layer contains:

- canonicalization code;
- inclusion proof APIs;
- federation logic;
- benchmark engines;
- replay experiment harnesses.

This layer defines:

> operational realization of protocol semantics.

Implementation correctness remains partially dependent on:

- testing;
- CI validation;
- reproducibility;
- and future traceability mapping.

---

# 8. L5 — Experimental Layer

This layer contains:

- benchmark artifacts;
- replay scenarios;
- deterministic datasets;
- reproducible experiment outputs.

This layer validates:

> observable bounded behavior.

Experimental reproducibility is not identical to theorem proof.

ETS intentionally preserves this distinction.

---

# 9. Refinement Boundaries

The following transitions are currently strongest.

| Transition | Current Status |
|---|---|
| Conceptual -> Formal | strong |
| Formal -> Executable | strong |
| Executable -> CI validation | strong |
| Executable -> Symbolic | emerging |
| Formal -> Implementation | partial |
| Implementation -> Mathematical proof | weak |

This table should evolve over time.

---

# 10. Important Scientific Boundary

ETS currently supports:

- executable bounded semantics;
- partial symbolic scaffolding;
- reproducible experimentation.

ETS does NOT yet support:

- complete refinement proofs;
- mechanically verified implementation correctness;
- universal theorem-level guarantees.

Those remain future research goals.

---

# 11. Strategic Importance

Refinement architecture is one of the most important concepts in dissertation-grade systems research.

Without refinement:
- theory and implementation drift apart.

With refinement:
- protocol claims become traceable,
- assumptions become inspectable,
- and validation becomes scientifically defensible.

This is essential for ETS to mature from:
- interesting architecture

into:
- rigorous distributed systems research.
