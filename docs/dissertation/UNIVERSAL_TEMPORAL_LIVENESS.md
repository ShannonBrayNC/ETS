# ETS Universal Temporal Liveness

## Purpose

This document studies the strongest temporal liveness claim ETS can responsibly make.

This is one of the most difficult and dangerous areas in distributed systems research.

The risk is overclaiming.

Many systems implicitly suggest:

- eventual convergence;
- eventual consistency;
- eventual agreement;
- or eventual visibility

without carefully defining:

- scheduler assumptions;
- adversarial limits;
- transport guarantees;
- fairness conditions;
- and temporal bounds.

ETS intentionally avoids that mistake.

---

# 1. Fundamental Research Boundary

ETS does NOT currently claim:

- unconditional universal liveness;
- universal asynchronous convergence;
- arbitrary Byzantine eventual agreement;
- or omnipotent temporal guarantees.

Those claims are not scientifically defensible under unrestricted adversarial scheduling.

Instead ETS introduces:

> conditional universal temporal liveness under explicit bounded assumptions.

That distinction is critically important.

---

# 2. Why Universal Liveness Is Difficult

Universal temporal liveness asks:

> Will every pending state eventually reach a terminal classification?

This becomes difficult because:

- schedulers may delay forever;
- partitions may persist indefinitely;
- adversaries may starve progress;
- fairness may fail;
- observations may remain incomplete forever.

Without assumptions, universal liveness often becomes impossible.

---

# 3. Relationship to FLP Impossibility

ETS should explicitly acknowledge the broader impossibility landscape.

The FLP result demonstrates:

> deterministic consensus cannot guarantee both safety and liveness in a fully asynchronous system with even one faulty process.

ETS does not attempt to bypass this limitation.

Instead ETS explicitly constrains:

- temporal assumptions;
- fairness assumptions;
- timeout semantics;
- bounded scheduling.

This transforms:

- impossible universal liveness

into:

- conditional bounded temporal progress.

That is scientifically honest.

---

# 4. ETS Liveness Philosophy

ETS treats temporal liveness as:

> eventual bounded classification under explicit assumptions.

Importantly:

terminal outcomes include:

- successful resolution;
- conflict classification;
- timeout classification.

Conflict is not treated as protocol failure.

Conflict itself is evidence.

That is philosophically central to ETS.

---

# 5. Universal Temporal Model

ETS now includes:

```text
formal/tla/ETSUniversalTemporalLiveness.tla
```

This model defines:

- bounded time;
- eventual timeout classification;
- weak fairness assumptions;
- eventual terminal outcomes.

The theorem structure is intentionally conditional.

---

# 6. Conditional Universal Theorem

The strongest theorem ETS currently supports is approximately:

> Given bounded temporal progression, enabled timeout classification, and weak fairness assumptions for progress actions, every pending evidence state eventually reaches a terminal classification state.

This is NOT equivalent to:

- universal asynchronous liveness;
- Byzantine inevitability;
- or arbitrary convergence proof.

The distinction matters enormously.

---

# 7. Core Temporal Properties

## Property A — EventualTerminalClassification

Definition:

```text
<>(terminal)
```

Meaning:

Every execution eventually reaches a terminal state.

---

## Property B — EveryPendingStateEventuallyClassifies

Definition:

```text
[](pending => <>terminal)
```

Meaning:

Any pending state eventually transitions into a terminal classification.

This is the closest ETS currently comes to universal temporal liveness.

---

## Property C — EveryExecutionEventuallyHasOutcome

Definition:

```text
<>(outcome # "None")
```

Meaning:

Every bounded execution eventually receives a classified outcome.

Again:

classification may represent:

- resolution,
- conflict,
- or timeout.

This is intentional.

---

# 8. Why Timeout Matters

Timeout semantics are essential.

Without timeout classification:

- pending states may remain unresolved indefinitely;
- liveness collapses under adversarial delay.

Timeout transforms:

- infinite unresolved uncertainty

into:

- bounded classified uncertainty.

That transformation is one of the deepest conceptual ideas emerging in ETS.

---

# 9. Fairness Assumptions

ETS universal temporal liveness depends on:

- weak fairness assumptions;
- enabled progress execution;
- bounded temporal progression.

Without fairness assumptions:

an adversarial scheduler can indefinitely prevent progress.

ETS intentionally documents this limitation.

---

# 10. Scientific Importance

Most systems research focuses on:

- agreement;
- replication;
- consensus;
- fault tolerance.

ETS increasingly focuses on:

- bounded eventual classification;
- defensible temporal conclusions;
- unresolved evidence states;
- replay persistence;
- epistemic uncertainty.

That is a much deeper framing.

---

# 11. Remaining Research Gaps

Still missing:

- stochastic temporal convergence mathematics;
- probabilistic scheduler modeling;
- adaptive adversarial temporal topology;
- mechanized liveness theorem proofs;
- Internet-scale temporal visibility analysis.

These remain frontier research problems.

---

# 12. Most Important Principle

The most important principle is:

> ETS never claims more temporal certainty than its assumptions justify.

That discipline is becoming one of the strongest scientific qualities of the entire project.
