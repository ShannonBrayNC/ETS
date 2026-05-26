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

CI may validate syntax or artifact presence when model checkers are not
installed. A full paper artifact must state whether TLC or Alloy Analyzer was
executed and with which bounds.

## Symbolic Verification Status

Apalache and refinement proofs are tracked in `formal/apalache/README.md`.
They are not currently part of the reproducibility baseline. Publications must
describe symbolic verification as pending until a pinned checker version,
commands, and outputs are committed.

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
