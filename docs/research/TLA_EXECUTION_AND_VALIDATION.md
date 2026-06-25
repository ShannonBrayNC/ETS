# TLA+ Execution and Validation Strategy

## Purpose

This document defines how ETS formal models are executed and validated
within continuous integration.

The objective is to ensure the formal layer remains:

- executable,
- bounded,
- reproducible,
- artifact-backed,
- and scientifically honest.

## Important Distinction

A formal specification file existing in a repository is NOT equivalent to:

- a validated model,
- a checked invariant,
- a reproducible formal result,
- or a citable evidence artifact.

ETS therefore executes TLC directly in CI and retains per-model evidence artifacts.

This transition is extremely important.

The formal layer has moved from:

```text
research-oriented specification drafting
```

into:

```text
machine-executed bounded verification with retained evidence artifacts
```

## Executed Models

The CI workflow currently executes:

- ETSLog
- ETSVerifierFederation
- ETSTemporalByzantineFederation
- ETSProbabilisticTrust
- ETSLivenessFederation
- ETSAsyncTransport
- ETSTemporalLivenessTheorems
- ETSUniversalTemporalLiveness

Each model includes:

- a bounded configuration;
- explicit invariants;
- executable state transitions;
- TLC validation semantics;
- and retained log output when executed through the evidence capture runner.

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

## Evidence Capture Gates

ETS now separates pull-request smoke validation from full evidence capture.

### Pull-request smoke gate

The `Formal Specs` workflow executes `scripts/run-tlc-models.sh` with a bounded
per-model timeout and uploads `tlc-evidence-artifacts` on success or failure.

The artifact contains:

- `summary.md`;
- `results.json`;
- one TLC log per configured model.

Timeouts in this gate are treated as deferred evidence, not proof of model
success. Non-timeout TLC failures remain workflow failures.

### Full TLC evidence gate

The `Full TLC Evidence Capture` workflow is manually dispatched from the default
branch. It runs the same model set with a longer per-model timeout and uploads
`full-tlc-evidence-artifacts`.

This workflow is the expected execution path for issue `#70`.

A dissertation or publication claim may cite full TLC evidence only when it
includes the workflow run ID, commit SHA, timeout policy, artifact name, target
set, and per-model result.

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

The GitHub Actions workflow treats:

- invariant violations,
- parser failures,
- TLC execution failures,
- and malformed configurations

as CI failures.

This creates an enforceable boundary between:

- aspirational formalism,
- and executable formal verification.

A formal failure with retained logs is not a CI infrastructure failure. It is a
formal evidence result that must be remediated or marked pending.

## Current Limitations

The current formal CI still does NOT establish:

- universal liveness proofs;
- temporal fairness proofs beyond the configured model boundaries;
- probabilistic theorem proving;
- Byzantine transport verification;
- PlusCal refinement;
- Alloy/TLA+ cross-validation.

Those remain future work unless a retained workflow artifact proves the specific
claim under stated bounds.

## Next Recommended Formal Directions

1. Run the manual full TLC evidence gate and retain the artifact bundle.
2. Add automatic invariant coverage reporting.
3. Add liveness properties with explicit fairness assumptions.
4. Add partition-healing semantics.
5. Add bounded replay-order verification.
6. Add message queue modeling.
7. Add selective visibility adversary scenarios.
8. Add formal state refinement proofs.
9. Cross-reference Apalache and TLC artifacts by model target.
10. Cross-reference Lean proof artifacts by theorem family.

## Conclusion

The ETS formal layer is materially stronger when formal execution is paired with
retained evidence artifacts.

The project no longer merely:

- stores formal specifications.

It now:

- executes them,
- validates invariants,
- records model/proof failures as explicit evidence,
- and integrates bounded formal verification into CI.

That is a significant transition in research maturity.
