# ETS Proof Artifact Archive

## Purpose

This directory stores symbolic verification and proof-oriented artifacts generated during ETS research execution.

The purpose is:

- reproducibility;
- auditability;
- symbolic trace preservation;
- counterexample retention;
- and scientific accountability.

---

# 1. Why Preserve Proof Artifacts

Formal verification research frequently produces:

- parser failures;
- unsupported semantic constructs;
- counterexamples;
- fairness violations;
- symbolic deadlocks;
- incomplete proof attempts.

ETS intentionally preserves these outputs.

This is important.

Strong research treats proof failures as evidence.

Weak research silently removes them.

---

# 2. Expected Artifact Types

| Artifact | Purpose |
|---|---|
| symbolic traces | replayable symbolic execution paths |
| counterexamples | invariant or property violations |
| parser failures | unsupported specification records |
| execution manifests | proof configuration tracking |
| CI summaries | workflow execution evidence |
| unsupported-model notes | explicit boundary documentation |

---

# 3. Retention Policy

ETS should preserve:

- successful proof traces;
- failed proof traces;
- unsupported-model records;
- symbolic configuration manifests;
- benchmark-linked symbolic artifacts.

Artifacts should remain reproducible whenever possible.

---

# 4. Scientific Boundary

Stored artifacts do NOT automatically imply:

- theorem completeness;
- universal correctness;
- or production certification.

Artifacts represent:

> bounded evidence regarding protocol behavior under explicit assumptions.

This distinction is essential.

---

# 5. Future Expansion

Future research may add:

- Apalache symbolic traces;
- theorem-prover outputs;
- mechanized proof artifacts;
- stochastic convergence traces;
- multi-node federation simulation outputs.

---

# 6. Strategic Importance

Proof-artifact preservation strengthens:

- dissertation rigor;
- peer-review defensibility;
- reproducibility;
- and scientific transparency.

It also reinforces one of the central philosophical principles of ETS:

> disagreement, failure, replay, and uncertainty are themselves valuable evidence.
