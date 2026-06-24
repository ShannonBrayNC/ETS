# Publication Sprint Plan

## Purpose

This plan starts the ETS publication lane with two bounded papers:

1. Paper Candidate 1: core evidence transparency semantics.
2. Paper Candidate 3: reproducible experiments and artifact packaging.

The sequence prioritizes a defensible core contribution first, then follows
with artifact-backed reproducibility evidence.

## Paper Candidate 1

### Working Title

Evidence Transparency Systems: Bounded Semantics for Verifiable Digital
Evidence

### Central Claim

ETS can represent recorded digital evidence as canonical, hash-bound,
append-only, independently verifiable artifacts without claiming semantic truth
or perfect completeness.

### Contribution

The paper contributes a protocol architecture for canonical evidence events,
append-only logs, Merkle-style proof semantics, signed roots, and proof-carrying
audit artifacts.

### Required Evidence

- `docs/dissertation/EVIDENCE_THEORY.md`
- `docs/dissertation/FORMAL_ARCHITECTURE.md`
- `docs/research/FORMAL_THEOREMS.md`
- `docs/research/FORMAL_TRACEABILITY_MATRIX.md`
- `tests/spec/test_vectors.py`
- `tests/unit/test_verifier_golden.py`
- `tests/unit/test_artifacts.py`

### Paper 1 Outline

1. Problem: evidence preservation is often conflated with truth.
2. Background: transparency logs, Merkle proofs, formal methods, and audit systems.
3. ETS model: evidence events, canonicalization, append-only state, proofs.
4. Verification boundary: integrity and inclusion, not semantic completeness.
5. Implementation trace: reference Python package and verifier behavior.
6. Evaluation: golden vectors, verifier tests, and bounded formal model status.
7. Limitations: no legal sufficiency, no production certification, no universal completeness.

## Paper Candidate 3

### Working Title

Reproducible Evidence Transparency Experiments: Replay, Omission Suspicion,
Transport Visibility, and Artifact Packaging

### Central Claim

ETS can package bounded experiments as replayable artifacts with deterministic
seeds, synthetic non-PII data, JSON/Markdown outputs, and explicit
interpretation boundaries.

### Contribution

The paper contributes an artifact discipline for evidence transparency systems:
deterministic replay manifests, benchmark outputs, experiment runners, and
validation matrices that separate reproducibility from universal proof.

### Required Evidence

- `docs/dissertation/REPRODUCIBILITY.md`
- `docs/research/REPRODUCIBILITY_APPENDIX.md`
- `experiments/scenarios/sprint11-replay-manifest.json`
- `ets/experiments/replay_runner.py`
- `ets/benchmarks/run_benchmarks.py`
- `tests/unit/test_benchmarks.py`
- `tests/research/test_research_platform_artifacts.py`
- GitHub Actions benchmark artifacts: `benchmark-results`, `experiment-results`

### Paper 3 Outline

1. Problem: systems research often lacks replayable evidence artifacts.
2. ETS artifact model: manifests, seeds, synthetic data, and output bundles.
3. Replay scenarios: federation, transport replay, omission suspicion, visibility degradation.
4. Benchmark outputs: deterministic shape, machine-dependent timings.
5. Validation: tests, workflow artifacts, and reproduction commands.
6. Interpretation boundaries: synthetic scenarios, no production throughput claim.
7. Artifact availability plan: commit SHA, workflow run URLs, and retained outputs.

## Venue Families

| Paper | Venue Families |
| --- | --- |
| Paper 1 | IEEE Secure Development, IEEE Cloud workshops, ACM/IEEE systems security workshops, trustworthy systems workshops. |
| Paper 3 | ACM artifact-evaluation-friendly workshops, systems reproducibility workshops, software engineering workshops, trustworthy systems workshops. |

## Submission Gate

Neither paper is submission-ready until:

- advisor approves author list, target venue, and paper sequence;
- citations are normalized;
- figures and tables are created;
- evidence run URLs and artifact bundles are captured;
- limitations are reviewed for overclaiming;
- institutional or advisor formatting expectations are met.

## Next Executable Slice

The next publication slice is Paper 1 extended abstract plus Figure 1 and the
formal/implementation evidence table. Paper 3 should follow after the benchmark
and replay artifacts have passing workflow URLs attached.
