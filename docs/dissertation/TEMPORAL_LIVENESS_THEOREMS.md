# ETS Temporal Liveness Theorems

## Purpose

This document defines the ETS approach to temporal liveness reasoning.

Temporal liveness is one of the most difficult areas in distributed systems research.

It becomes especially difficult under:

- adversarial scheduling;
- partial visibility;
- asynchronous delivery;
- network partitions;
- and bounded observation.

ETS therefore adopts a bounded theorem-oriented approach.

---

# 1. Scientific Boundary

ETS currently supports:

- bounded temporal liveness models;
- fairness-constrained liveness semantics;
- bounded progress classification;
- replayable liveness experiments.

ETS does NOT currently claim:

- universal asynchronous liveness;
- Byzantine eventual consistency proofs;
- Internet-scale temporal guarantees;
- arbitrary scheduler fairness.

This distinction is critically important.

---

# 2. Why Liveness Is Difficult

Safety and liveness are fundamentally different.

## Safety

Safety asks:

> Can a bad thing happen?

Examples:

- duplicate delivery;
- invalid quorum acceptance;
- append-only violation.

Safety violations are often finite and observable.

---

## Liveness

Liveness asks:

> Will a good thing eventually happen?

Examples:

- eventual classification;
- eventual delivery;
- eventual convergence;
- eventual replay visibility.

Liveness becomes difficult because:

- infinite execution paths exist;
- scheduler assumptions matter;
- fairness assumptions matter;
- and delayed systems may remain indefinitely unresolved.

---

# 3. ETS Liveness Philosophy

ETS intentionally avoids claiming:

- universal eventual convergence;
- guaranteed asynchronous completion;
- perfect temporal coordination.

Instead ETS focuses on:

> bounded defensible temporal progress under explicit assumptions.

That distinction is one of the strongest scientific qualities of the project.

---

# 4. Temporal Liveness Model

ETS now includes:

```text
formal/tla/ETSTemporalLivenessTheorems.tla
```

This model formalizes:

- bounded delay;
- partition healing;
- timeout classification;
- eventual terminal state transition;
- fairness-constrained progress.

---

# 5. Core Temporal Properties

## Property A — PendingEventuallyEnds

Definition:

```text
<>(~pending)
```

Meaning:

A pending evidence state eventually reaches:

- resolution,
- conflict classification,
- or timeout completion.

This is a bounded eventual-progress property.

---

## Property B — PartitionEventuallyHealsOrTerminal

Definition:

```text
<>(~partitioned \/ ~pending)
```

Meaning:

A partitioned state eventually either:

- heals,
- or transitions into a terminal classification state.

This avoids indefinite unresolved execution under bounded assumptions.

---

## Property C — ResolutionEventuallyClassified

Definition:

```text
<>(resolved \/ conflicted)
```

Meaning:

An evidence state eventually receives a terminal classification.

This may be:

- successful resolution,
- or conflict identification.

Importantly:

conflict remains a valid terminal outcome.

That is philosophically important for ETS.

---

# 6. Fairness Assumptions

ETS liveness currently depends on fairness assumptions.

Current fairness constraints include:

- eventual healing opportunities;
- eventual enabled-resolution execution;
- eventual timeout classification.

Without fairness assumptions:

many distributed systems cannot prove liveness properties.

ETS intentionally documents this dependency.

---

# 7. Why This Matters

Most distributed systems research focuses heavily on:

- safety,
- replication,
- consensus,
- integrity.

ETS additionally studies:

- unresolved evidence states;
- bounded temporal uncertainty;
- replay persistence;
- conflict classification;
- and defensible temporal conclusions.

This is a deeper and more epistemically focused framing.

---

# 8. Current Research Limits

ETS temporal liveness remains bounded.

Still missing:

- stochastic temporal convergence mathematics;
- probabilistic scheduler modeling;
- adaptive Byzantine topology evolution;
- symbolic liveness theorem completeness;
- mechanized temporal proof systems.

These remain future research directions.

---

# 9. Strategic Importance

Temporal liveness reasoning is one of the most important transitions in the ETS research program.

Without liveness reasoning:
- ETS remains primarily a safety-oriented evidence architecture.

With temporal liveness reasoning:
- ETS increasingly becomes a theory of bounded evidentiary progress under adversarial observation conditions.

That transition materially strengthens:

- dissertation rigor;
- publication credibility;
- and the long-term scientific identity of ETS.
