# ETS Mechanized Fairness Proofs

## Purpose

This document defines the ETS approach to mechanized fairness reasoning.

Fairness is one of the most dangerous concepts in distributed systems research.

Many systems implicitly assume fairness without:

- defining it,
- constraining it,
- or proving consequences separately from assumptions.

ETS intentionally separates:

- fairness assumptions,
from:
- fairness consequences.

That distinction is critically important.

---

# 1. Why Fairness Is Difficult

Fairness attempts to answer questions such as:

> If an action remains enabled forever, will it eventually execute?

This becomes difficult because:

- schedulers may indefinitely delay actions;
- adversaries may starve progress;
- partitions may persist;
- visibility may remain incomplete.

Without fairness assumptions:

many temporal liveness claims collapse.

---

# 2. ETS Fairness Philosophy

ETS does NOT attempt to prove:

- that arbitrary real-world schedulers are fair;
- that Byzantine adversaries eventually cooperate;
- or that progress occurs without assumptions.

Instead ETS proves:

> the consequences of explicitly supplied fairness assumptions.

That is a profoundly important scientific distinction.

---

# 3. Mechanized Fairness Framework

ETS now includes:

```text
formal/lean/src/ETSProofs/Fairness.lean
```

This module mechanizes:

- fairness-constrained progress;
- timeout classification;
- terminal-state consequences;
- fairness-derived execution semantics.

---

# 4. Core Mechanized Fairness Theorems

## Theorem A — fairEnabledProgressTerminates

Meaning:

If:

- fairness assumptions are supplied,
- and an action remains enabled,

then:

- the resulting state reaches terminal classification.

This theorem proves:

> fairness assumptions produce bounded terminal progress.

It does NOT prove:

> that arbitrary schedulers are fair.

That distinction matters enormously.

---

## Theorem B — timeoutIsClassified

Meaning:

Timeout classification is itself valid epistemic evidence.

This theorem reinforces a central ETS principle:

> unresolved uncertainty should become explicitly classified uncertainty.

---

## Theorem C — executedImpliesFairEvidence

Meaning:

Observed execution constitutes explicit evidence of fair progress.

This theorem connects:

- execution,
- fairness,
- and evidence semantics.

---

## Theorem D — terminalStateHasFairClassification

Meaning:

Valid terminal states cannot silently remain unresolved.

This theorem formalizes:

> terminal epistemic accountability.

---

# 5. Relationship to Temporal Liveness

Fairness and liveness are deeply connected.

Without fairness assumptions:

- liveness often becomes impossible.

ETS therefore models:

- fairness assumptions explicitly;
- temporal eventuality conditionally;
- timeout semantics formally.

This transforms:

- impossible universal eventuality

into:

- bounded fairness-constrained progress.

---

# 6. Relationship to FLP Impossibility

The FLP impossibility result demonstrates that deterministic consensus cannot simultaneously guarantee both safety and liveness in fully asynchronous systems with faults.

ETS does not attempt to escape this limitation.

Instead ETS:

- constrains assumptions;
- bounds temporal progression;
- introduces timeout classification;
- and models fairness consequences explicitly.

This is scientifically honest.

---

# 7. Why Mechanized Fairness Matters

Mechanized fairness proofs strengthen ETS because they:

- reduce informal reasoning drift;
- expose hidden assumptions;
- separate fairness premises from theorem conclusions;
- improve dissertation rigor;
- improve peer-review defensibility.

This is especially important in adversarial distributed systems research.

---

# 8. Current Scientific Boundary

ETS currently supports:

- bounded mechanized fairness consequences;
- fairness-constrained terminal progress;
- timeout-classification reasoning;
- theorem-checked fairness semantics.

ETS does NOT currently support:

- arbitrary scheduler fairness proofs;
- Byzantine fairness inevitability;
- stochastic fairness mathematics;
- infinite-state fairness completeness.

Those remain frontier research problems.

---

# 9. Most Important Principle

The most important principle is:

> ETS mechanizes what fairness assumptions imply, not whether reality guarantees fairness.

That distinction is one of the strongest scientific qualities of the project.
