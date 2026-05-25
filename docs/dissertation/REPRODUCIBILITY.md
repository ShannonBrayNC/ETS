# ETS Reproducibility Framework

## Purpose

This document defines the ETS reproducibility and experimental execution framework.

The purpose of this framework is not merely automation.

Its purpose is to ensure:

- experiments are replayable;
- assumptions are explicit;
- datasets are deterministic;
- benchmark outputs are reproducible;
- and CI validation remains inspectable.

This is a foundational requirement for dissertation-grade systems research.

---

# 1. Reproducibility Philosophy

ETS attempts to preserve a strict distinction between:

| Category | Meaning |
|---|---|
| Implemented | code exists |
| Executable | runnable from clean checkout |
| Reproducible | repeatable with deterministic assumptions |
| Validated | bounded checks pass |
| Proven | mathematically established under formal assumptions |

This distinction is essential.

Many systems projects accidentally treat:

```text
implemented
```

as equivalent to:

```text
scientifically validated.
```

ETS intentionally avoids this collapse.

---

# 2. Current Reproducibility Scope

The current ETS reproducibility layer supports:

- deterministic synthetic datasets;
- deterministic replay manifests;
- benchmark execution;
- experiment artifact generation;
- CI artifact publication;
- TLC formal execution.

The current framework does NOT yet include:

- Internet-scale replay simulation;
- probabilistic convergence mathematics;
- symbolic verification;
- stochastic network delay;
- real adversarial transport capture.

Those remain future work.

---

# 3. Experiment Structure

Current experiment assets are organized into:

```text
experiments/
  scenarios/

artifacts/
  benchmarks/
  experiments/
```

## Scenario Manifests

Scenario manifests define deterministic replay conditions.

Example:

```text
experiments/scenarios/sprint11-replay-manifest.json
```

Each manifest defines:

- deterministic seed;
- scenario identifiers;
- replay conditions;
- omission conditions;
- visibility degradation scenarios;
- expected bounded outcomes.

---

# 4. Deterministic Seeds

Deterministic seeds are mandatory for dissertation reproducibility.

Current baseline seed:

```text
20260524
```

This ensures:

- reproducible synthetic event ordering;
- reproducible benchmark generation;
- stable replay behavior.

## Important Boundary

Deterministic reproducibility does NOT imply:

- real-world transport realism;
- universal statistical representativeness.

It only guarantees:

> replayable bounded experimental state.

---

# 5. Synthetic Dataset Strategy

ETS currently uses synthetic non-PII datasets.

Primary generator:

```text
ets/experiments/dataset.py
```

This approach intentionally avoids:

- real customer data;
- privacy exposure;
- governance ambiguity.

The synthetic datasets are designed to support:

- replay testing;
- benchmark reproducibility;
- transport experiments;
- omission simulations.

---

# 6. Replay Experiment Harness

Primary runner:

```text
ets/experiments/replay_runner.py
```

Current scenarios include:

- federation baseline;
- replay visibility;
- omission suspicion;
- adversarial visibility degradation.

The current replay runner is intentionally lightweight.

It exists to establish:

> reproducible experimental discipline.

not:

> production-grade distributed simulation.

---

# 7. Benchmark Metrics

ETS currently standardizes the following metrics.

| Metric | Meaning |
|---|---|
| convergence latency | time required for bounded convergence |
| replay visibility rate | frequency of replay observation |
| omission suspicion rate | rate of missing expected observations |
| partition recovery timing | bounded recovery interval |
| confidence degradation | confidence reduction under adversarial conditions |
| transport asymmetry | observation imbalance across nodes |
| append latency | event insertion timing |
| proof generation latency | inclusion proof generation timing |

## Important Boundary

Current benchmark metrics are bounded engineering metrics.

They are NOT yet:

- statistically rigorous distributed systems benchmarks;
- probabilistic convergence proofs;
- Internet-scale measurements.

---

# 8. CI Artifact Publication

Current CI publishes:

- benchmark reports;
- experiment manifests;
- benchmark JSON outputs;
- benchmark markdown summaries;
- TLC execution summaries.

This creates:

> inspectable experimental evidence.

rather than merely:

> local execution claims.

---

# 9. Reproducibility Workflow

Current reproducibility workflow:

```text
clone repo
-> install dependencies
-> execute benchmarks
-> execute replay harness
-> execute TLC validation
-> inspect generated artifacts
```

This workflow is intentionally designed for:

- dissertation review;
- committee inspection;
- publication reproducibility;
- future artifact evaluation.

---

# 10. Scientific Boundaries

ETS currently supports:

- bounded reproducibility;
- bounded replay determinism;
- bounded experimental validation.

ETS does NOT yet support:

- formal probabilistic reproducibility;
- Internet-scale transport realism;
- stochastic adversarial scheduling;
- symbolic convergence proofs.

These limitations are intentional and explicitly documented.

---

# 11. Strategic Importance

The reproducibility layer changes ETS fundamentally.

Without reproducibility:

ETS risks becoming:

- conceptual protocol writing,
- untestable theory,
- or unverifiable implementation claims.

With reproducibility:

ETS becomes:

> inspectable systems research.

That transition is one of the most important milestones in the dissertation track.
