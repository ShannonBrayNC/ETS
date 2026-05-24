# TLA+ Execution and Validation Strategy

## Purpose

This document defines how ETS formal models are executed and validated
within continuous integration.

The objective is to ensure the formal layer remains:

- executable,
- bounded,
- reproducible,
- and scientifically honest.

## Important Distinction

A formal specification file existing in a repository is NOT equivalent to:

- a validated model,
- a checked invariant,
- or a reproducible formal result.

ETS therefore now executes TLC directly in CI.

This transition is extremely important.

The formal layer has moved from:

```text
research-oriented specification drafting
```

into:

```text
machine-executed bounded verification
```

## Executed Models

The CI workflow currently executes:

- ETSLog
- ETSVerifierFederation
- ETSTemporalByzantineFederation
- ETSProbabilisticTrust

Each model includes:

- a bounded configuration;
- explicit invariants;
- executable state transitions;
- and TLC validation semantics.

## Scientific Boundary

TLC execution does NOT prove:

- universal correctness;
- Internet-scale convergence;
- cryptographic security;
- asynchronous Byzantine safety;
- probabilistic completeness.

Instead, TLC validates:

- bounded state-space exploration;
- invariant preservation;
- reachable-state consistency;
- protocol transition correctness within configured limits.

This distinction is essential.

## Important Design Adjustment

During CI hardening, the original probabilistic trust model was revised.

The earlier version attempted weighted trust aggregation through:

```text
Sum(...)
```

over set comprehensions.

That design risked TLC incompatibility and unnecessary state-space complexity.

The executable version now uses:

```text
discretized visible support counts
```

instead of arbitrary weighted aggregation.

This significantly improves:

- TLC executability;
- model interpretability;
- bounded-state exploration;
- and formal reproducibility.

Importantly:

The documentation continues to explicitly state:

- the model represents bounded confidence semantics,
- not mathematically rigorous probabilistic inference.

That distinction improves scientific accuracy.

## CI Failure Semantics

The GitHub Actions workflow now treats:

- invariant violations,
- parser failures,
- TLC execution failures,
- and malformed configurations

as CI failures.

This creates an enforceable boundary between:

- aspirational formalism,
- and executable formal verification.

## Current Limitations

The current formal CI still does NOT include:

- liveness proofs;
- temporal fairness proofs;
- probabilistic theorem proving;
- asynchronous network simulation;
- Byzantine transport verification;
- Apalache model checking;
- PlusCal refinement;
- Alloy/TLA+ cross-validation.

Those remain future work.

## Next Recommended Formal Directions

1. Add liveness properties.
2. Add fairness constraints.
3. Add Apalache symbolic checking.
4. Add bounded replay-order verification.
5. Add partition-healing semantics.
6. Add message queue modeling.
7. Add selective visibility adversary scenarios.
8. Add formal state refinement proofs.
9. Add model execution artifacts to CI.
10. Add automatic invariant coverage reporting.

## Conclusion

The ETS formal layer is now materially stronger.

The project no longer merely:

- stores formal specifications.

It now:

- executes them,
- validates invariants,
- and integrates bounded formal verification into CI.

That is a significant transition in research maturity.
