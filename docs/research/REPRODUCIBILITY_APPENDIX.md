# Reproducibility Appendix

This appendix records how to reproduce ETS RC research artifacts from a clean
checkout.

## Environment

- Python 3.12
- Node.js 22 for Explorer UI builds
- Docker only for federation deployment checks
- No external secrets
- No real PII

## Local Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```

## Benchmark Reproduction

```powershell
.\.venv\Scripts\python.exe -m ets.benchmarks.run_benchmarks
```

Expected artifacts:

- `artifacts/benchmarks/benchmark-results.json`
- `artifacts/benchmarks/benchmark-results.md`

Benchmark timings are machine-dependent. Event counts, tree size, and output
shape are deterministic.

## Golden Vector Reproduction

```powershell
.\.venv\Scripts\python.exe -m pytest tests/spec/test_vectors.py -q
```

Current golden vectors are:

- `ets/spec/test-vectors/v0.1/event-vectors.json`
- `ets/spec/test-vectors/merkle-vectors.json`

These vectors support deterministic canonical JSON, event-hash, leaf-hash, and
small Merkle-root checks. They do not yet cover proof bundles, signed tree
heads, redaction profiles, or cross-language implementation outputs.

## Experiment Reproduction

```powershell
.\.venv\Scripts\python.exe -m ets.experiments.run_fork_simulation
.\.venv\Scripts\python.exe -m ets.experiments.run_omission_detection
```

Fork simulations should report divergent roots. Omission experiments should
report findings only for expected event IDs that are absent from the observed
log.

The federation convergence experiment is exercised by:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_experiments.py
```

It uses fixed synthetic tree heads to measure quorum acceptance and conflict
rejection without relying on wall-clock network convergence.

Async-network and Bayesian reliability primitives are exercised by:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_async_network.py tests/unit/test_liveness.py tests/unit/test_probabilistic.py
```

The async-network experiment records deterministic seeded delivery/loss
outcomes under bounded delay settings. The Bayesian primitive performs
Beta-Bernoulli posterior updates for observed verifier behavior. Neither test
suite establishes BFT consensus or stochastic convergence.

The manifest-driven replay harness is:

```powershell
.\.venv\Scripts\python.exe -m ets.experiments.replay_runner
```

Primary manifest:

- `experiments/scenarios/sprint11-replay-manifest.json`

Expected generated artifacts:

- `artifacts/experiments/experiment-results.json`
- `artifacts/experiments/experiment-results.md`

## Federation API Reproduction

The federation quorum/fork primitive is tested through both unit tests and the
FastAPI integration suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_federation.py tests/integration/test_api.py
```

The route `POST /api/v1/federation/assess` is deterministic for a fixed set of
tree-head observations. It does not contact external verifiers or discover
public keys.

## Formal Model Reproduction

TLA+ validation is represented by:

- `formal/tla/ETSLog.tla`
- `formal/tla/ETSLog.cfg`
- `formal/tla/ETSAsyncNetwork.tla`
- `formal/tla/ETSAsyncNetwork.cfg`
- `formal/tla/ETSLiveness.tla`
- `formal/tla/ETSLiveness.cfg`

Alloy causal modeling is represented by:

- `formal/alloy/ETSCausalModel.als`

The formal CI workflow executes bounded TLC checks for selected TLA+ models.
A full paper artifact must state the workflow run URL, checker version, commit
SHA, and configured bounds.

## Symbolic Verification Status

Apalache symbolic-safe reduced model checks are tracked in
`formal/apalache/README.md` and `.github/workflows/apalache.yml`.
Publications must distinguish bounded symbolic-safe workflow results from
complete symbolic verification or implementation refinement proof.

## Dissertation Artifact Package

Sprint 5 proposes a committee-facing artifact package in:

- `docs/dissertation/EXPERIMENT_ARTIFACT_PLAN.md`

The recommended package records:

- environment summary;
- commands;
- test summary;
- golden-vector summaries;
- benchmark JSON/Markdown;
- experiment manifest and outputs;
- interpretation notes;
- known non-claims.

## Docker Federation

```powershell
docker compose up --build
.\scripts\validate-docker-federation.ps1
```

Docker validation is environment-dependent. A release candidate must document
whether Docker was available locally and whether all health endpoints passed.

## Result Interpretation

ETS benchmark and experiment outputs support reproducibility of the reference
implementation. They do not establish production throughput, legal sufficiency,
or proof of real-world completeness.
