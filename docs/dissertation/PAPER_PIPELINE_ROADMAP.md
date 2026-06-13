# Sprint 6 Paper Pipeline Roadmap

## Purpose

This roadmap converts the ETS dissertation work into publishable paper targets.
It does not mark any paper as submission-ready. It defines paper candidates,
bounded claims, required evidence, and next actions.

## Publication Strategy

ETS should become a sequence of bounded papers rather than one oversized paper.
Each paper should contain:

- one central research claim;
- one technical contribution;
- one reproducible artifact package;
- one formal or empirical evidence map;
- one explicit limitations section.

## Paper Candidate 1: ETS Core Evidence Transparency Semantics

### Working Title

Evidence Transparency Systems: Bounded Transparency Semantics for Verifiable
Digital Evidence

### Central Claim

ETS can represent recorded digital evidence as canonical, hash-bound,
append-only, independently verifiable artifacts without claiming semantic truth
or perfect completeness.

### Primary Contribution

A protocol architecture for canonical evidence events, append-only logs,
Merkle-style proof semantics, signed roots, and proof-carrying audit artifacts.

### Evidence Required

- `docs/dissertation/CLAIM_AUDIT.md`
- `docs/dissertation/LITERATURE_REVIEW.md`
- `docs/dissertation/GOLDEN_VECTOR_COVERAGE.md`
- `tests/spec/test_vectors.py`
- `tests/unit/test_artifacts.py`
- `docs/research/FORMAL_THEOREMS.md`

### Likely Venue Families

- IEEE Secure Development;
- IEEE Cloud workshops;
- ACM/IEEE systems security workshops;
- software supply-chain or transparency workshops.

## Paper Candidate 2: Verifier Federation And Conflict Visibility

### Working Title

Verifier Federation for Evidence Transparency: Root Agreement, Fork Suspicion,
and Bounded Conflict Visibility

### Central Claim

Independent verifiers can compare roots, observations, and replay artifacts to
detect bounded disagreement and fork suspicion without becoming a Byzantine
consensus protocol.

### Primary Contribution

A finite verifier-federation model and implementation trace for quorum
assessment, root conflict visibility, and divergence reporting.

### Evidence Required

- `formal/tla/ETSVerifierFederation.tla`
- `formal/tla/ETSTemporalByzantineFederation.tla`
- `ets/experiments/federation_convergence.py`
- `ets/experiments/fork_simulation.py`
- `tests/unit/test_federation.py`
- `tests/unit/test_experiments.py`
- `docs/dissertation/PROOF_STATUS_TABLE.md`

### Likely Venue Families

- DSN workshops;
- middleware workshops;
- distributed systems workshops;
- applied formal methods workshops.

## Paper Candidate 3: Reproducible Experiments For Evidence Transparency

### Working Title

Reproducible Evidence Transparency Experiments: Replay, Omission Suspicion,
Transport Visibility, and Artifact Packaging

### Central Claim

ETS can package bounded experiments as replayable artifacts with deterministic
seeds, synthetic non-PII datasets, JSON/Markdown outputs, and explicit
interpretation boundaries.

### Primary Contribution

A reproducible systems artifact suite for replay, omission, fork, federation,
async-network, liveness, probabilistic, and benchmark scenarios.

### Evidence Required

- `docs/dissertation/IMPLEMENTATION_REPRODUCIBILITY_AUDIT.md`
- `docs/dissertation/EXPERIMENT_ARTIFACT_PLAN.md`
- `docs/research/REPRODUCIBILITY_APPENDIX.md`
- `experiments/scenarios/sprint11-replay-manifest.json`
- `ets/experiments/replay_runner.py`
- `ets/benchmarks/run_benchmarks.py`
- Sprint 5 test set.

### Likely Venue Families

- ACM artifact-evaluation-friendly workshops;
- systems reproducibility workshops;
- IEEE/ACM software engineering workshops;
- trustworthy systems workshops.

## Paper Candidate 4: Bounded Formal Models For Evidence Coordination

### Working Title

Bounded Formal Models for Evidence Transparency: Append-Only Safety,
Fairness-Scoped Liveness, and Adversarial Classification

### Central Claim

ETS formalizes selected evidence-coordination properties with bounded TLA+
models, symbolic-safe Apalache checks, and Lean-checked classification lemmas
while explicitly avoiding universal correctness claims.

### Primary Contribution

A formal-methods case study in maintaining proof-status discipline across
TLA+, Apalache, Lean, implementation tests, and dissertation traceability.

### Evidence Required

- `docs/dissertation/FORMAL_METHODS_AUDIT.md`
- `docs/dissertation/PROOF_STATUS_TABLE.md`
- `docs/dissertation/MODEL_CHECKING_COMMAND_LOG.md`
- `.github/workflows/tla.yml`
- `.github/workflows/apalache.yml`
- `.github/workflows/lean-proofs.yml`
- `formal/tla/`
- `formal/apalache/`
- `formal/lean/`

### Likely Venue Families

- formal methods workshops;
- TLA+/FM practitioner venues;
- trustworthy systems workshops;
- software engineering artifact venues.

## Paper Candidate 5: Evidence Theory For AI Governance

### Working Title

Evidence Transparency for AI Governance: Verifiable Audit Artifacts Without
Truth Overclaiming

### Central Claim

ETS can make selected AI governance artifacts independently verifiable without
claiming model fairness, explanation correctness, or complete inference
capture.

### Primary Contribution

A governance-facing evidence theory that separates recorded artifact integrity
from semantic truth, fairness, compliance approval, and legal sufficiency.

### Evidence Required

- `docs/dissertation/EVIDENCE_THEORY.md`
- `docs/dissertation/CLAIM_AUDIT.md`
- `docs/dissertation/LITERATURE_REVIEW.md`
- `docs/dissertation/RELATED_WORK_MATRIX.md`
- `docs/dissertation/SPRINT_5_READINESS_REPORT.md`

### Likely Venue Families

- AI governance workshops;
- trustworthy AI workshops;
- information systems governance venues;
- interdisciplinary systems and policy workshops.

## Recommended Submission Order

1. Paper Candidate 1: core evidence transparency semantics.
2. Paper Candidate 3: reproducible experiments and artifact package.
3. Paper Candidate 4: formal model/proof-status case study.
4. Paper Candidate 2: verifier federation and conflict visibility.
5. Paper Candidate 5: AI governance specialization.

This order starts with the most general ETS contribution and builds toward
specialized or higher-risk venues.

