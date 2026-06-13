# ETS Dissertation Claim Audit

## Purpose

This audit converts the ETS research corpus into dissertation-safe claim
language. It is designed for advisor and committee review during Sprint 2.

The governing rule is:

> ETS may claim only what is supported by protocol definitions, formal models,
> executable code, tests, reproducible experiments, or explicitly bounded
> research assumptions.

## Claim Status Vocabulary

| Status | Meaning | Dissertation Use |
| --- | --- | --- |
| Implemented | Code and tests support the claim. | May appear as an implementation result. |
| Bounded model | Formal or deterministic model covers finite or scoped cases. | May appear as modeled evidence with assumptions. |
| Fairness-scoped | Liveness depends on weak fairness, eventual healing, or bounded adversarial pressure. | May appear only with assumptions stated nearby. |
| Statistical only | A limited statistical model supports the claim. | May appear as experimental inference, not proof of adversarial correctness. |
| Process model | Governance logic classifies cases or escalation paths. | May appear as workflow semantics, not legal sufficiency. |
| Pending | Artifact path exists or is planned but not complete enough to claim. | Must be framed as future work or Sprint 3-5 work. |
| Not claimed | ETS intentionally does not assert the property. | Must remain explicit in the dissertation. |

## Dissertation Claim Table

| Dissertation Claim | Current Evidence | Status | Safe Wording |
| --- | --- | --- | --- |
| ETS can deterministically hash supported evidence events. | `ets.core.canonical_json`; `tests/unit/test_canonical_json.py`; `tests/spec/test_vectors.py`; `docs/research/FORMAL_THEOREMS.md` | Implemented | ETS implements deterministic canonicalization and hashing for supported evidence-event structures. |
| ETS can verify inclusion of recorded evidence under a published root. | `ets.core.proofs`; `ets.core.merkle`; `tests/unit/test_inclusion_proofs.py` | Implemented | ETS verifies inclusion proofs for recorded artifacts under the proof rules implemented by the reference system. |
| ETS can model append-only log safety. | `formal/tla/ETSLog.tla`; `tests/unit/test_append_log.py`; `docs/research/FORMAL_TRACEABILITY_MATRIX.md` | Bounded model / implemented | ETS models and tests append-only log behavior for bounded research scenarios. |
| ETS can detect tampering, reordering, or replay mismatch within visible evidence. | Replay runner and experiment tests; `docs/dissertation/EVALUATION_AND_BENCHMARKS.md` | Implemented / reproducible experiment | ETS can detect replay mismatch for visible, canonicalized evidence under deterministic replay assumptions. |
| ETS can detect fork suspicion when conflicting roots become visible. | `ets.experiments.fork_simulation`; `tests/unit/test_experiments.py`; federation docs | Implemented | ETS can report fork suspicion when conflicting root observations are available to verifiers. |
| ETS can raise omission suspicion relative to an expected event set. | `ets.experiments.omission_detection`; `formal/alloy/ETSCausalModel.als`; `tests/unit/test_experiments.py` | Implemented / bounded model | ETS can report omission suspicion only when an external expectation model defines what should have appeared. |
| ETS can assess verifier root agreement under a threshold policy. | `ets.core.federation`; `tests/unit/test_federation.py`; `tests/integration/test_api.py` | Implemented | ETS can compute policy-bounded quorum or divergence assessments over finite verifier observations. |
| ETS can reason about asynchronous transport under bounded assumptions. | `formal/tla/ETSAsyncNetwork.tla`; `ets.experiments.async_network`; `tests/unit/test_async_network.py` | Bounded model | ETS evaluates transport delay, loss, and reordering in deterministic bounded scenarios, not arbitrary networks. |
| ETS can state liveness conditions for replay, propagation, recovery, and convergence. | `formal/tla/ETSLiveness.tla`; `ets.experiments.liveness`; `tests/unit/test_liveness.py` | Fairness-scoped | ETS states liveness only under explicit weak-fairness, bounded-pressure, and partition-healing assumptions. |
| ETS can update verifier reliability using a simple Bayesian model. | `ets.experiments.probabilistic`; `tests/unit/test_probabilistic.py` | Statistical only | ETS implements a Beta-Bernoulli reliability update; it is not a stochastic proof of federation convergence. |
| ETS can classify governance escalation cases. | `ets.governance.escalation`; `docs/governance/GOVERNANCE_SEMANTICS.md`; `tests/unit/test_governance.py` | Process model | ETS classifies governance signals and escalation states; it does not provide legal advice or institutional authority. |
| ETS provides a complete refinement proof from implementation to formal model. | Traceability matrix identifies future refinement needs. | Pending | ETS currently provides traceability, not a complete refinement proof. |
| ETS proves semantic truth of source events. | None; explicitly out of scope. | Not claimed | ETS verifies properties of recorded artifacts, not truth of the underlying real-world event. |
| ETS proves perfect completeness or universal omission detection. | None; omission requires expectation. | Not claimed | ETS cannot prove all relevant evidence was submitted without external completeness controls. |
| ETS implements full Byzantine consensus. | None; federation is root comparison and reporting. | Not claimed | ETS verifier federation is not a Byzantine consensus protocol. |
| ETS proves Internet-scale adversarial liveness. | None; bounded models only. | Not claimed | ETS does not claim liveness under permanent partition, total eclipse, arbitrary asynchronous adversaries, or unavailable verifiers. |

## Revised Thesis Boundary

Recommended dissertation language:

> Evidence Transparency Systems provide a bounded architecture for making
> recorded digital evidence independently verifiable, replayable, and
> governance-actionable under explicit canonicalization, cryptographic,
> visibility, verifier, and transport assumptions.

Language to avoid:

- ETS proves what happened.
- ETS guarantees complete evidence capture.
- ETS solves Byzantine consensus.
- ETS proves AI fairness or explanation correctness.
- ETS establishes legal chain-of-custody sufficiency.

## Advisor Review Questions

1. Are the implemented and bounded-model claims sufficient for a systems PhD
   contribution if paired with a stronger literature review?
2. Which pending claims must be completed before committee review?
3. Should the dissertation emphasize formal methods, systems implementation,
   AI governance, or reproducible evidence infrastructure as the primary
   contribution?
4. Which claims require publication before defense?
5. Which claims should be removed from the dissertation and reserved for
   future work?

