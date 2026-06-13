# ETS Research Artifact Map

## Purpose

This map identifies where Sprint 2 dissertation claims are supported inside the
ETS repository. It is not a proof of correctness. It is a navigation and
traceability document for advisor review, committee planning, and future
publication work.

## Primary Dissertation Artifacts

| Artifact | Role |
| --- | --- |
| `docs/dissertation/ETS_PHD_DISSERTATION_ROUGH_DRAFT.md` | Rough dissertation manuscript synthesized from the ETS research corpus. |
| `docs/dissertation/MST_ADVISOR_REVIEW_PACKET.md` | Advisor-facing return-to-PhD packet. |
| `docs/dissertation/CLAIM_AUDIT.md` | Sprint 2 claim discipline and safe wording. |
| `docs/dissertation/SPRINT_2_READINESS_REPORT.md` | Sprint 2 completion status, risks, and next-sprint handoff. |
| `docs/dissertation/PROSPECTUS.md` | Prior prospectus and thesis framing. |
| `docs/dissertation/DISSERTATION_STRUCTURE.md` | Dissertation argument flow and chapter structure. |
| `docs/dissertation/LITERATURE_REVIEW.md` | Existing literature review base to harden in Sprint 3. |
| `docs/dissertation/FORMAL_FOUNDATIONS.md` | Formal vocabulary for evidence, observation, proof, replay, suspicion, and federation. |
| `docs/dissertation/EVALUATION_AND_BENCHMARKS.md` | Evaluation questions, benchmark areas, and reproducibility requirements. |
| `docs/dissertation/IMPLEMENTATION_TRACEABILITY.md` | Dissertation-level correspondence between claims, models, code, and experiments. |

## Research and Formal Evidence Artifacts

| Artifact | Supports |
| --- | --- |
| `docs/research/RESEARCH_PROGRAM.md` | Scope, research tracks, limitations, and publication deliverables. |
| `docs/research/ETS_RESEARCH_PAPER_RC1.md` | Initial research paper framing. |
| `docs/research/ETS_RESEARCH_PAPER_RC2_ADVANCED.md` | Formal system model, invariants, threat model, and complexity framing. |
| `docs/research/ETS_RC3_EXECUTABLE_RESEARCH_PLAN.md` | Executable research-plan direction. |
| `docs/research/FORMAL_THEOREMS.md` | Theorem statements, assumptions, evidence paths, and non-theorems. |
| `docs/research/FORMAL_TRACEABILITY_MATRIX.md` | Claim-to-model/code/test matrix and claim discipline. |
| `docs/research/REPRODUCIBILITY_APPENDIX.md` | Reproducibility requirements and artifact expectations. |
| `docs/research/ASYNC_TRANSPORT_RESEARCH.md` | Bounded transport research and constraints. |
| `docs/research/RESEARCH_NOTE_VERIFIER_FEDERATION_AND_CONVERGENCE.md` | Federation and convergence framing. |
| `docs/research/RESEARCH_NOTE_TEMPORAL_AND_BYZANTINE_SEMANTICS.md` | Temporal and adversarial semantics. |
| `docs/research/RESEARCH_NOTE_PROBABILISTIC_TRUST_AND_ADAPTIVE_ADVERSARIES.md` | Probabilistic trust boundaries. |

## Formal Model Families

| Area | Representative Artifacts | Sprint 2 Status |
| --- | --- | --- |
| Append-only logs | `formal/tla/ETSLog.tla` | Bounded model / implemented trace. |
| Verifier federation | `formal/tla/ETSVerifierFederation.tla` | Bounded model / implementation trace. |
| Async transport | `formal/tla/ETSAsyncNetwork.tla`, `formal/tla/ETSAsyncTransport.tla` | Bounded model; not arbitrary-network proof. |
| Temporal liveness | `formal/tla/ETSLiveness.tla`, `formal/tla/ETSLivenessFederation.tla` | Fairness-scoped. |
| Universal temporal liveness | `formal/tla/ETSUniversalTemporalLiveness.tla` | Research extension; requires proof-status review. |
| Probabilistic trust | `formal/tla/ETSProbabilisticTrust.tla` | Model/research extension; statistical implementation only. |
| Mechanized proofs | `formal/lean/src/ETSProofs/` | Proof-development track; completion must be audited before final claims. |

## Implementation and Test Evidence

| Area | Representative Tests | Claim Supported |
| --- | --- | --- |
| Canonicalization | `tests/unit/test_canonical_json.py`, `tests/spec/test_vectors.py` | Deterministic hash inputs for supported structures. |
| Append-only behavior | `tests/unit/test_append_log.py` | Append-only log safety in implementation. |
| Inclusion proofs | `tests/unit/test_inclusion_proofs.py` | Inclusion verification behavior. |
| Quorum and federation | `tests/unit/test_quorum.py`, `tests/unit/test_federation.py`, `tests/integration/test_api.py` | Root agreement, quorum, and divergence assessment. |
| Experiments | `tests/unit/test_experiments.py` | Fork, omission, and replay experiment behavior. |
| Async network | `tests/unit/test_async_network.py` | Bounded delay/loss/reordering classification. |
| Liveness | `tests/unit/test_liveness.py` | Fairness-scoped liveness experiment behavior. |
| Probabilistic updates | `tests/unit/test_probabilistic.py` | Beta-Bernoulli update behavior. |
| Governance | `tests/unit/test_governance.py` | Process classification and escalation semantics. |
| Dissertation deliverables | `tests/unit/test_dissertation_deliverables.py` | Required dissertation documents and bounded claim language. |

## Sprint 2 Technical Editing Notes

- Use "verifies recorded artifacts" rather than "proves events."
- Use "omission suspicion" rather than "omission proof" unless an external
  expectation model is explicitly present.
- Use "verifier federation" rather than "consensus."
- Use "fairness-scoped liveness" rather than "guaranteed liveness."
- Use "statistical reliability update" rather than "probabilistic safety."
- Use "traceability" rather than "refinement proof" until a refinement proof is
  actually completed.

