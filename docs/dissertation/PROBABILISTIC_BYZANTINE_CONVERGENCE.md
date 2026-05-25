# ETS Probabilistic Byzantine Convergence Mathematics

## Purpose

This document defines the ETS approach to probabilistic Byzantine convergence mathematics.

Probabilistic convergence is one of the hardest remaining research areas because Byzantine environments contain:

- incomplete visibility,
- adversarial behavior,
- replay asymmetry,
- scheduler uncertainty,
- and non-deterministic temporal progression.

ETS therefore adopts a bounded probabilistic approach.

---

# 1. Scientific Boundary

ETS does NOT currently claim:

- universal stochastic convergence;
- guaranteed probabilistic eventuality;
- arbitrary Byzantine inevitability;
- or omniscient adversarial visibility.

Instead ETS models:

> bounded convergence confidence under explicit probabilistic assumptions.

That distinction is critically important.

---

# 2. Why Probabilistic Convergence Matters

Deterministic convergence assumptions become fragile under Byzantine conditions.

Real distributed systems experience:

- message delay,
- replay,
- partial partitions,
- adversarial timing,
- and incomplete observation.

Probability therefore becomes necessary.

ETS increasingly studies:

- convergence confidence,
- expected adversarial contamination,
- probabilistic quorum correctness,
- and bounded epistemic certainty.

---

# 3. ETS Probabilistic Model

ETS now includes:

```text
ets/probability/byzantine_convergence.py
```

This model formalizes:

- honest-node fractions;
- Byzantine fractions;
- bounded convergence confidence;
- stochastic quorum assumptions.

The current implementation intentionally remains bounded and mathematically conservative.

---

# 4. Core Convergence Equation

Current ETS convergence confidence is modeled as:

```text
confidence = 1 - (1 - honest_fraction)^rounds
```

Interpretation:

- confidence increases geometrically as honest-majority observations accumulate across rounds;
- confidence remains probabilistic rather than deterministic;
- convergence remains bounded rather than universal.

This is scientifically honest.

---

# 5. Byzantine Contamination Fraction

ETS explicitly models:

```text
expected_byzantine_fraction = byzantine_nodes / total_nodes
```

This matters because:

- adversarial visibility contaminates convergence confidence;
- replay and asymmetry reduce certainty;
- and probabilistic confidence must remain bounded.

---

# 6. Why This Matters Philosophically

Traditional Byzantine systems often attempt:

- eventual agreement,
- deterministic convergence,
- or fault masking.

ETS increasingly attempts:

> bounded confidence regarding adversarially observed evidence.

That is a fundamentally different research direction.

---

# 7. Relationship to Prior ETS Layers

Probabilistic convergence now complements:

- temporal liveness;
- fairness semantics;
- Byzantine classification;
- replay visibility;
- mechanized theorem proofs.

Together these layers increasingly form:

> a bounded epistemic coordination theory.

---

# 8. Current Scientific Boundary

ETS currently supports:

- bounded convergence confidence;
- probabilistic adversarial fractions;
- stochastic confidence growth.

ETS does NOT currently support:

- Bayesian scheduler inference;
- stochastic temporal theorem completeness;
- infinite-state probabilistic proofs;
- Internet-scale probabilistic visibility mathematics.

These remain frontier research problems.

---

# 9. Most Important Principle

The most important principle is:

> ETS models probabilistic confidence, not probabilistic certainty.

That distinction is becoming one of the strongest scientific qualities of the project.
