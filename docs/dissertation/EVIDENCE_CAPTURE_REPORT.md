# Evidence Capture Report

## Purpose

This report captures the current formal, test, benchmark, and reproducibility
evidence for ETS. It distinguishes local validation, GitHub Actions evidence,
and blockers that must be resolved before committee-facing or publication
claims can cite the evidence as passing.

## Branch And Baseline

| Field | Value |
| --- | --- |
| Sprint branch | `codex/dissertation-evidence-publication-gate` |
| Default branch baseline | `origin/main` |
| Baseline SHA | `1122204f87af0b0867132e2f786010b896f07e99` |
| Local Python validation target | Python 3.12 |
| Resolved FastAPI version | `0.136.3` |
| Resolved Starlette version | `1.3.1` |
| Latest PR evidence SHA | `58e96ccd0893df733f47b84a643fde54ad4de8cf` |

## Local Validation Captured

| Evidence | Command | Result |
| --- | --- | --- |
| Golden vectors | `py -3.12 -m pytest tests/spec/test_vectors.py` | Passed as part of focused evidence suite. |
| Verifier golden coverage | `py -3.12 -m pytest tests/unit/test_verifier_golden.py` | Passed as part of focused evidence suite. |
| Benchmark artifact test | `py -3.12 -m pytest tests/unit/test_benchmarks.py` | Passed as part of focused evidence suite. |
| Research artifact tests | `py -3.12 -m pytest tests/research/test_research_platform_artifacts.py` | Passed as part of focused evidence suite. |
| Focused evidence suite | `py -3.12 -m pytest tests/spec/test_vectors.py tests/unit/test_verifier_golden.py tests/unit/test_benchmarks.py tests/research/test_research_platform_artifacts.py` | `19 passed`. |
| Full unit/integration suite | `py -3.12 -m pytest` | `283 passed`, 1 Starlette/httpx deprecation warning. |
| Lint | `py -3.12 -m ruff check .` | Passed. |
| Type check | `py -3.12 -m mypy` | Passed. |
| Dependency audit | `pip-audit` | No known vulnerabilities found; local editable package `ets` is skipped because it is not on PyPI. |
| Benchmark runner | `py -3.12 -m ets.benchmarks.run_benchmarks` | Produced deterministic output shape for 100 events. |
| Replay runner | `py -3.12 -m ets.experiments.replay_runner` | Produced 4 seeded scenarios with seed `20260524`. |

Benchmark and experiment timing values are machine-dependent. They should be
cited as reproducible artifact shape and bounded local execution, not as
production throughput.

## Current GitHub Actions Evidence

| Workflow | Latest URL Reviewed | Result | Evidence Interpretation |
| --- | --- | --- | --- |
| CI | <https://github.com/ShannonBrayNC/ETS/actions/runs/27479858656> | Passed | Python tests, lint, type check, and dependency audit passed on the PR branch. |
| Formal Specs / TLC | <https://github.com/ShannonBrayNC/ETS/actions/runs/27479858667> | Running at capture time | PR-gate TLC now uses bounded runtime protection. Full unbounded TLC evidence is tracked in issue `#70`. |
| Apalache | <https://github.com/ShannonBrayNC/ETS/actions/runs/27479858674> | Passed | Symbolic-safe ETSLog, federation, transport, and bounded liveness models passed and retain `symbolic-proof-artifacts`. |
| Lean proofs | <https://github.com/ShannonBrayNC/ETS/actions/runs/27479858651> | Passed | Lean proof files passed after timeout and Byzantine suspicion proof simplification. |
| Benchmarks | <https://github.com/ShannonBrayNC/ETS/actions/runs/27479858659> | Passed | Benchmark and replay artifact workflow succeeded for the PR branch. |

## Formal Tool Status

| Tool | Current Status | Next Evidence Requirement |
| --- | --- | --- |
| TLC | PR workflow is bounded so CI cannot hang indefinitely. Local `java` is unavailable. | Complete issue `#70` for full unbounded TLC evidence capture in a configured formal-validation environment. |
| Apalache | Latest PR workflow passed and uploads `symbolic-proof-artifacts`. Local `apalache-mc` is unavailable. | Retain the passing PR run URL and artifact bundle for dissertation evidence. |
| Lean | Latest PR workflow passed. Local `lean` is unavailable. | Retain the passing PR run URL for mechanized proof evidence. |
| Python tests | Local Python 3.12 full suite passed. | Preserve the `283 passed` result and rerun before merge if the branch changes. |
| Benchmarks | Local benchmark and replay commands executed; latest workflow passed. | Attach or cite workflow artifact names: `benchmark-results`, `experiment-results`. |

## Artifact Locations

| Artifact | Path Or Workflow Artifact |
| --- | --- |
| Benchmark JSON | `artifacts/benchmarks/benchmark-results.json` |
| Benchmark Markdown | `artifacts/benchmarks/benchmark-results.md` |
| Replay manifest | `experiments/scenarios/sprint11-replay-manifest.json` |
| Benchmark workflow artifact | `benchmark-results` |
| Replay workflow artifact | `experiment-results` |
| Apalache proof artifact | `symbolic-proof-artifacts` |
| TLC summary | GitHub Actions step summary from `tla.yml` |
| Lean summary | GitHub Actions step summary from `lean-proofs.yml` |

Generated benchmark outputs under `artifacts/benchmarks/` are ignored by Git and
should be regenerated or cited from workflow artifacts.

## Claim Boundaries

The current evidence supports:

- deterministic event vectors;
- verifier golden behavior;
- local benchmark/replay execution;
- documented formal model workflows;
- bounded formal and mechanized proof targets.

The current evidence does not yet support:

- universal theorem proof;
- universal liveness;
- Byzantine consensus;
- production throughput claims;
- legal sufficiency;
- real-world completeness.

Related tracking issues: `#67`, `#70`.
