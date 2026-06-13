# ETS Experiment Artifact Plan

## Purpose

This Sprint 5 plan defines the artifact package that should be generated before
committee review or publication submission. It follows artifact-evaluation
practice: every result should have a command, environment, manifest, output,
and interpretation.

## Recommended Artifact Package Layout

```text
artifacts/dissertation/sprint5/
  README.md
  environment.json
  commands.txt
  test-summary.txt
  golden-vectors/
    event-vector-summary.md
    merkle-vector-summary.md
  benchmarks/
    benchmark-results.json
    benchmark-results.md
    interpretation.md
  experiments/
    manifest.json
    experiment-results.json
    experiment-results.md
    interpretation.md
  fork/
    command.txt
    result.json
    interpretation.md
  omission/
    command.txt
    result.json
    interpretation.md
  federation/
    command.txt
    result.json
    interpretation.md
  async-network/
    command.txt
    result.json
    interpretation.md
  liveness/
    command.txt
    result.json
    interpretation.md
  probabilistic/
    command.txt
    result.json
    interpretation.md
```

## Baseline Commands

From a clean checkout:

```text
python -m pytest tests/spec/test_vectors.py -q
python -m pytest tests/unit/test_benchmarks.py tests/unit/test_experiments.py -q
python -m pytest tests/unit/test_async_network.py tests/unit/test_liveness.py tests/unit/test_probabilistic.py -q
python -m pytest tests/unit/test_artifacts.py -q
python -m ets.benchmarks.run_benchmarks
python -m ets.experiments.replay_runner
python -m ets.experiments.run_fork_simulation
python -m ets.experiments.run_omission_detection
```

## Existing Scenario Manifest

Primary manifest:

```text
experiments/scenarios/sprint11-replay-manifest.json
```

Current scenario IDs:

- `federation-baseline`
- `transport-replay-baseline`
- `omission-suspicion-baseline`
- `adversarial-visibility-baseline`

The manifest uses seed `20260524` and synthetic non-PII data.

## Result Interpretation Rules

| Result Type | Interpretation |
| --- | --- |
| Golden vector pass | Supports deterministic canonicalization and basic Merkle conformance. |
| Benchmark JSON shape | Supports reproducible artifact generation and event/proof counts. |
| Benchmark timing | Machine-dependent engineering measurement, not universal performance. |
| Fork result | Demonstrates visible conflicting-root suspicion. |
| Omission result | Demonstrates missing expected ID suspicion, not universal completeness. |
| Federation result | Demonstrates finite policy threshold behavior, not Byzantine consensus. |
| Async-network result | Demonstrates bounded seeded transport behavior, not arbitrary-network liveness. |
| Liveness result | Demonstrates fairness-scoped progress under bounded assumptions. |
| Probabilistic result | Demonstrates Beta-Bernoulli update math, not stochastic safety. |

## Sprint 5 Non-Claims

- No production benchmark claims.
- No Internet-scale deployment claims.
- No legal admissibility or legal chain-of-custody sufficiency.
- This package is not legal sufficiency evidence by itself.
- No complete external verifier federation deployment.
- No stochastic convergence proof.
- No proof that unrecorded real-world events did not occur.
