# Sprint 8 Defense Q&A

## Purpose

This document prepares advisor and committee discussion responses. It is not a
script to memorize. It is a bounded-claim defense guide.

## Core Answer Pattern

For every hard question:

1. State the boundary.
2. State what ETS does prove, model, test, or reproduce.
3. Point to the artifact.
4. State what remains future work.

## Likely Questions

### Is ETS just Certificate Transparency for evidence?

No. ETS inherits transparency-log lessons such as append-only roots and proof
artifacts, but its contribution is evidence-event semantics, replay,
federation, omission suspicion, governance interpretation, and claim discipline.

Artifacts:

- `LITERATURE_REVIEW.md`
- `RELATED_WORK_MATRIX.md`
- `PAPER_PIPELINE_ROADMAP.md`

### Does ETS prove what happened?

No. ETS verifies properties of recorded artifacts: canonical form, hashes,
proofs, roots, replay outputs, and verifier observations under explicit
assumptions. It does not prove semantic truth of source events.

Artifacts:

- `CLAIM_AUDIT.md`
- `PROSPECTUS.md`
- `DISSERTATION_ASSEMBLY_PLAN.md`

### Does ETS solve omission?

No. ETS can raise omission suspicion only relative to an external expectation
model. Without expected IDs, schedules, obligations, or monitoring constraints,
absence is ambiguous.

Artifacts:

- `CLAIM_AUDIT.md`
- `FORMAL_THEOREMS.md`
- `tests/unit/test_experiments.py`

### Is verifier federation Byzantine consensus?

No. ETS verifier federation compares roots, proof bundles, replay outputs, and
observations. It can report bounded disagreement, but it does not establish
global agreement under Byzantine faults.

Artifacts:

- `PROOF_STATUS_TABLE.md`
- `RELATED_WORK_MATRIX.md`
- `ETSVerifierFederation.tla`

### What is formally verified?

ETS has bounded TLA+ models, CI-backed TLC workflows, symbolic-safe Apalache
reduced model checks, and Lean-checked bounded lemmas. It does not claim
complete formal verification or implementation-to-model refinement proof.

Artifacts:

- `FORMAL_METHODS_AUDIT.md`
- `MODEL_CHECKING_COMMAND_LOG.md`
- `PROOF_STATUS_TABLE.md`

### What is reproducible?

Golden vectors, synthetic datasets, benchmark output shape, replay manifests,
fork/omission/federation/async/liveness/probabilistic tests, and artifact-record
behavior are reproducible in the reference implementation. Benchmark timings
are machine-dependent.

Artifacts:

- `IMPLEMENTATION_REPRODUCIBILITY_AUDIT.md`
- `EXPERIMENT_ARTIFACT_PLAN.md`
- `GOLDEN_VECTOR_COVERAGE.md`

### Why is this a PhD contribution?

The contribution is a bounded systems-research framework that unifies evidence
semantics, formal models, implementation traceability, reproducible artifacts,
and governance boundaries for independently verifiable recorded digital
evidence.

Artifacts:

- `CONTRIBUTIONS.md`
- `DISSERTATION_ASSEMBLY_PLAN.md`
- `PAPER_CLAIM_EVIDENCE_MAP.md`

### What remains before committee circulation?

Citation normalization, integrated chapter prose, figures, formal workflow run
artifacts, experiment result packages, advisor approval, and Missouri S&T
formatting.

Artifacts:

- `COMMITTEE_DRAFT_READINESS.md`
- `CHAPTER_INTEGRATION_CHECKLIST.md`
- `FIGURE_TABLE_PLAN.md`

