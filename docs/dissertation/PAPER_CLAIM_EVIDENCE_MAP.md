# Paper Claim Evidence Map

## Purpose

This map ensures each proposed paper claim is supported by existing ETS
artifacts or clearly marked as pending. It is the Sprint 6 publication
counterpart to the Sprint 2 claim audit.

## Claim Evidence Matrix

| Paper | Claim | Evidence | Status |
| --- | --- | --- | --- |
| Paper 1 | ETS represents recorded evidence as canonical, hash-bound artifacts. | `GOLDEN_VECTOR_COVERAGE.md`; `tests/spec/test_vectors.py`; `ets/spec/test-vectors/v0.1/event-vectors.json` | Supported for covered vectors. |
| Paper 1 | ETS supports append-only proof semantics. | `FORMAL_METHODS_AUDIT.md`; `ETSLog.tla`; Merkle vectors; `FORMAL_THEOREMS.md` | Bounded / covered examples. |
| Paper 1 | ETS does not prove semantic truth or completeness. | `CLAIM_AUDIT.md`; `PROSPECTUS.md` | Explicit non-claim. |
| Paper 2 | Verifier federation can detect bounded root conflicts. | `ETSVerifierFederation.tla`; `test_federation.py`; `test_experiments.py` | Supported in bounded tests/models. |
| Paper 2 | Federation is not Byzantine consensus. | `CLAIM_AUDIT.md`; `PROOF_STATUS_TABLE.md`; `RELATED_WORK_MATRIX.md` | Explicit non-claim. |
| Paper 3 | ETS experiments are replayable from manifests. | `EXPERIMENT_ARTIFACT_PLAN.md`; `replay_runner.py`; `sprint11-replay-manifest.json` | Supported in harness; final artifact bundle pending. |
| Paper 3 | Benchmark outputs are JSON/Markdown. | `run_benchmarks.py`; `test_benchmarks.py`; `REPRODUCIBILITY_APPENDIX.md` | Supported. |
| Paper 3 | Benchmark timings are not universal throughput. | `IMPLEMENTATION_REPRODUCIBILITY_AUDIT.md`; `SPRINT_5_READINESS_REPORT.md` | Explicit boundary. |
| Paper 4 | TLA+ models provide bounded formal validation. | `.github/workflows/tla.yml`; `MODEL_CHECKING_COMMAND_LOG.md`; `PROOF_STATUS_TABLE.md` | CI-backed when workflow runs successfully. |
| Paper 4 | Apalache checks are symbolic-safe and reduced. | `.github/workflows/apalache.yml`; `formal/apalache/README.md`; `FORMAL_TRACEABILITY_MATRIX.md` | Bounded symbolic-safe, not complete verification. |
| Paper 4 | Lean mechanizes bounded temporal/fairness/classification lemmas. | `.github/workflows/lean-proofs.yml`; `formal/lean/src/ETSProofs/` | CI-backed when workflow runs successfully. |
| Paper 5 | ETS can support AI governance evidence artifacts. | `EVIDENCE_THEORY.md`; `LITERATURE_REVIEW.md`; `CLAIM_AUDIT.md` | Conceptual; needs case-study artifact. |
| Paper 5 | ETS does not prove fairness, explanation correctness, or complete inference capture. | `LITERATURE_REVIEW.md`; `CLAIM_AUDIT.md` | Explicit non-claim. |

## Publication Readiness Gate

No paper should be submitted until:

1. each major claim maps to at least one artifact;
2. limitations are present in the abstract or early framing;
3. reproduction commands pass or the failure is documented;
4. source citations are normalized;
5. advisor approves the primary venue family;
6. artifact availability statement is drafted.

