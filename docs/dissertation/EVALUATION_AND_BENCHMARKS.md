# Evaluation And Benchmarks

## Purpose

This document defines the dissertation evaluation framework for ETS. The goal is reproducible systems evidence, not marketing benchmarks.

## Evaluation Questions

1. How quickly can verifier federation detect root divergence?
2. How reliably can replay detect tampered or reordered evidence?
3. How does omission suspicion behave under delayed or partially visible events?
4. How do proof sizes and verification cost scale with log size?
5. How do asynchronous transport scenarios affect confidence and convergence?
6. How reproducible are benchmark results across machines and CI runs?

## Benchmark Areas

### Federation Convergence

Measure time and observation count required for verifier nodes to converge on a shared root or report divergence.

Metrics:

- convergence latency,
- root agreement rate,
- divergent root detection time,
- stale root frequency.

### Replay Order

Evaluate deterministic replay over canonical event sequences, reordered inputs, missing entries, and tampered payloads.

Metrics:

- replay success rate,
- replay mismatch count,
- failed event index,
- reconstruction latency.

### Omission Detection

Simulate expected event ranges, missing ranges, delayed delivery, and selective visibility.

Metrics:

- omission suspicion rate,
- false suspicion rate under delay,
- time to suspicion,
- time to resolution.

### Transport Asymmetry

Evaluate partitions, delayed roots, one-way visibility, and verifier eclipse scenarios.

Metrics:

- propagation delay,
- partition recovery time,
- asymmetric observation count,
- confidence degradation.

### Adversarial Visibility

Inject forks, invalid signatures, stale roots, conflicting roots, and tampered proofs.

Metrics:

- detection rate,
- detection latency,
- report completeness,
- proof preservation rate.

## Reproducibility Requirements

Every experiment should record:

- code commit,
- Python version,
- dependency lock or environment summary,
- random seed,
- scenario manifest,
- input dataset,
- output report,
- command used,
- known limitations.

## Existing Artifacts

Current ETS evaluation artifacts include:

- `ets/benchmarks/run_benchmarks.py`,
- `ets/experiments/run_fork_simulation.py`,
- `ets/experiments/run_omission_detection.py`,
- `ets/experiments/replay_runner.py`,
- `experiments/scenarios/sprint11-replay-manifest.json`,
- `tests/unit/test_benchmarks.py`,
- `tests/unit/test_experiments.py`,
- `tests/unit/test_federation.py`,
- `tests/unit/test_probabilistic.py`,
- `docs/research/REPRODUCIBILITY_APPENDIX.md`.

## CI Execution

CI should run deterministic tests on every change. Longer benchmark sweeps may run on schedule or before dissertation artifact publication.

Minimum dissertation validation command:

```text
python -m pytest -q
```

Optional targeted checks:

```text
python -m pytest tests/unit/test_benchmarks.py tests/unit/test_experiments.py -q
python -m pytest tests/unit/test_federation.py tests/unit/test_probabilistic.py -q
```

## Result Traceability

Published result tables must point to:

- exact test or script,
- source commit,
- input manifest,
- generated artifact path,
- interpretation notes.

## Limitations

Local deterministic experiments do not prove Internet-scale behavior. Small federation simulations do not establish full Byzantine consensus. Benchmark results should be presented as evidence about the reference implementation and model scope, not universal performance guarantees.

## Publication-Ready Output Pattern

Each benchmark package should include:

```text
benchmark-name/
  README.md
  scenario.json
  command.txt
  environment.json
  results.json
  interpretation.md
```

This pattern supports reproducible artifact evaluation for committee review, conference review, and future independent replication.
