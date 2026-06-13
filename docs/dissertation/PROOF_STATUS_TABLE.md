# ETS Proof Status Table

## Purpose

This table is the Sprint 4 proof-maturity snapshot. It should be used by the
advisor to decide which formal claims are dissertation-ready, which require
Sprint 4 follow-up, and which should remain future work.

## Status Legend

| Status | Meaning |
| --- | --- |
| Implemented | Executable code and tests support the behavior. |
| TLA Modeled | TLA+ model and configuration exist. |
| TLC CI | GitHub Actions executes TLC for the model. |
| Apalache CI | GitHub Actions executes symbolic-safe Apalache checks. |
| Lean CI | GitHub Actions executes Lean theorem files. |
| Traceability | Claim is mapped to artifacts, but not proved by refinement. |
| Pending | Artifact path exists or work is planned but not complete enough to claim. |
| Not claimed | ETS intentionally does not assert this property. |

## Proof-Maturity Matrix

| Claim Family | Main Artifacts | Current Status | Dissertation Wording |
| --- | --- | --- | --- |
| Append-only log safety | `ETSLog.tla`, `ETSLog.cfg`, `test_append_log.py`, `FORMAL_TRACEABILITY_MATRIX.md` | TLA Modeled; TLC CI; implemented trace | ETS models and tests append-only safety for bounded log configurations. |
| Missing-event suspicion requires expectation | `ETSLog.tla`, Alloy causal model, omission experiments | TLA Modeled; implemented trace | ETS can raise omission suspicion only relative to an external expected-event set. |
| Verifier federation quorum | `ETSVerifierFederation.tla`, `ETSVerifierFederation.cfg`, federation tests | TLA Modeled; TLC CI; implemented trace | ETS models finite verifier root agreement and conflict visibility under policy thresholds. |
| Temporal Byzantine classification | `ETSTemporalByzantineFederation.tla`, `ByzantineTemporal.lean` | TLA Modeled; TLC CI; Lean CI | ETS models and mechanizes bounded adversarial classification, not Byzantine consensus. |
| Discretized trust semantics | `ETSProbabilisticTrust.tla`, probabilistic tests | TLA Modeled; TLC CI; implemented statistical primitive | ETS models bounded confidence states and separately implements Beta-Bernoulli updates; it does not prove stochastic convergence. |
| Fairness-scoped liveness federation | `ETSLivenessFederation.tla`, `ETSLivenessFederation.cfg` | TLA Modeled; TLC CI | ETS states convergence/progress only under explicit fairness and healing assumptions. |
| Async transport safety | `ETSAsyncTransport.tla`, `ETSAsyncTransport.cfg`, async tests | TLA Modeled; TLC CI; implemented trace | ETS models bounded topology-aware delivery and replay visibility. |
| Temporal liveness theorem model | `ETSTemporalLivenessTheorems.tla`, `ETSTemporalLivenessTheorems.cfg` | TLA Modeled; TLC CI | ETS models terminal classification and pending-state resolution under bounded assumptions. |
| Universal temporal liveness model | `ETSUniversalTemporalLiveness.tla` | TLA Modeled; TLC CI with temporal theorem config | ETS frames universal liveness as conditional bounded eventual classification, not unconditional liveness. |
| Symbolic-safe append log | `formal/apalache/models/ETSLogSymbolic.tla` | Apalache CI | ETS has bounded symbolic-safe validation for a reduced log model. |
| Symbolic-safe federation | `formal/apalache/models/ETSVerifierFederationSymbolic.tla` | Apalache CI | ETS has bounded symbolic-safe validation for a reduced federation model. |
| Symbolic-safe transport | `formal/apalache/models/ETSAsyncTransportSymbolic.tla` | Apalache CI | ETS has bounded symbolic-safe validation for reduced replay/delivery semantics. |
| Symbolic bounded liveness progress | `formal/apalache/models/ETSLivenessProgressSymbolic.tla` | Apalache CI | ETS has bounded symbolic progress checking, not universal temporal proof. |
| Lean temporal progress | `TemporalLiveness.lean` | Lean CI | ETS mechanizes bounded terminal-state and classification lemmas. |
| Lean fairness progress | `Fairness.lean` | Lean CI | ETS mechanizes consequences of supplied fairness assumptions. |
| Lean Byzantine temporal classification | `ByzantineTemporal.lean` | Lean CI | ETS mechanizes bounded adversarial classification consequences. |
| Implementation-to-model refinement proof | `REFINEMENT_MODEL.md`, `IMPLEMENTATION_TRACEABILITY.md` | Traceability / pending | ETS has traceability and a refinement plan, not a completed implementation-to-model refinement proof. |
| Cryptographic primitive proofs | SHA-256, Ed25519, Merkle assumptions | Not claimed | ETS relies on standard cryptographic assumptions rather than proving primitives. |
| Full Byzantine consensus | None | Not claimed | ETS verifier federation is not a Byzantine consensus protocol. |
| Internet-scale liveness | None | Not claimed | ETS does not claim liveness under arbitrary Internet-scale adversarial networks. |

## Committee-Ready Formal Claims

The following are likely defensible for advisor review:

- bounded TLA+ model suite exists;
- CI executes TLC for selected formal models;
- CI executes Lean theorem files for bounded temporal/fairness/classification
  lemmas;
- Apalache symbolic-safe workflow exists for reduced models;
- formal limitations are explicitly documented.

The following should remain Sprint 4/Sprint 5 follow-up unless advisor says
otherwise:

- retained CI artifact outputs for TLC/Apalache/Lean;
- full implementation-to-model refinement proof;
- cross-validation between TLA+, Alloy, Lean, and implementation traces;
- cryptographic theorem proof;
- stronger probabilistic or stochastic convergence theory.
