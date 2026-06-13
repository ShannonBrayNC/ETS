# Sprint 4 Readiness Report

## Sprint Goal

Sprint 4 hardens the formal-methods layer:

- audit existing formal artifacts;
- document proof status and validation categories;
- record model-checking commands and local tool limitations;
- tech-edit formal claims for dissertation-safe wording;
- add tests for Sprint 4 deliverables;
- stage the work in the repository.

## Completed Deliverables

| Deliverable | Status | Artifact |
| --- | --- | --- |
| Formal-methods audit | Complete | `docs/dissertation/FORMAL_METHODS_AUDIT.md` |
| Proof-status table | Complete | `docs/dissertation/PROOF_STATUS_TABLE.md` |
| Model-checking command log | Complete | `docs/dissertation/MODEL_CHECKING_COMMAND_LOG.md` |
| Sprint 4 readiness report | Complete | `docs/dissertation/SPRINT_4_READINESS_REPORT.md` |
| Apalache README technical edit | Complete | `formal/apalache/README.md` |
| TLA validation documentation technical edit | Complete | `docs/research/TLA_EXECUTION_AND_VALIDATION.md` |
| Tests for Sprint 4 formal deliverables | Complete | `tests/unit/test_dissertation_deliverables.py` |

## Current Formal Posture

ETS is ready for advisor review as a bounded formal-methods research program.
It is not yet ready to claim complete formal verification, implementation
refinement, cryptographic proof, universal liveness, or Byzantine consensus.

The strongest Sprint 4 formal claim is:

> ETS contains a bounded formal model suite with CI-backed TLC execution,
> symbolic-safe Apalache checks for reduced models, Lean-checked bounded
> temporal/fairness/classification lemmas, and explicit traceability/non-claim
> documentation.

## Local Verification Result

Local formal execution was blocked because the shell environment does not expose
`java`, `tlc2.TLC`, `apalache-mc`, or `lake`.

Local verification performed in Sprint 4:

- repository formal artifact audit;
- workflow command audit;
- dissertation document tests;
- DOCX structural checks from prior packet generation.

## Formal Claims Ready For Advisor Review

- Bounded append-only log safety modeling.
- Bounded verifier federation and conflict visibility.
- Bounded temporal Byzantine classification.
- Bounded transport and replay visibility semantics.
- Fairness-scoped liveness assumptions.
- Symbolic-safe Apalache workflow for reduced models.
- Lean mechanized lemmas for bounded temporal/fairness/classification
  properties.
- Traceability from claims to models, code, tests, and proof-index documents.

## Formal Claims Not Ready Or Not Claimed

| Claim | Status | Next Action |
| --- | --- | --- |
| Full implementation-to-model refinement proof | Pending | Sprint 4 follow-up or Sprint 7 appendix planning. |
| Retained CI output package for committee review | Pending | Capture GitHub Actions URLs/artifacts after push. |
| Complete symbolic verification suite | Pending | Expand Apalache target coverage and retain outputs. |
| Cryptographic theorem proof | Not claimed | Keep as standard cryptographic assumptions. |
| Full Byzantine consensus | Not claimed | Preserve verifier-federation distinction. |
| Internet-scale adversarial liveness | Not claimed | Keep bounded/fairness-scoped wording. |
| Stochastic convergence proof | Not claimed | Keep probabilistic work statistical/experimental. |

## Sprint 5 Handoff

Sprint 5 should connect formal claims to implementation and reproducibility:

1. Golden vectors for canonicalization and proof bundles.
2. Replay/fork/omission/transport experiment packages.
3. Result tables tied to formal claim families.
4. Artifact bundles that include command, environment, seed, output, and
   interpretation.
5. If possible, implementation-to-formal trace examples for one narrow claim.

## Advisor Questions

1. Is the formal-methods contribution strong enough if framed as bounded model
   checking plus Lean snippets rather than complete refinement proof?
2. Which formal claims must be promoted from appendix support to chapter-level
   evidence?
3. Should the dissertation require Apalache artifacts or only TLC/Lean outputs?
4. Would a narrow refinement proof for append-only log state be expected?
5. Should universal temporal liveness remain a future-work direction?
