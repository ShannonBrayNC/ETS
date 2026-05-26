# Contribution Claims

## Primary Claim

ETS contributes a bounded protocol architecture for independently verifiable digital evidence. It improves integrity verification, replayability, provenance visibility, and governance review without claiming universal truth, perfect completeness, or full Byzantine consensus.

## Theoretical Contributions

- Formal separation of semantic truth, recorded evidence integrity, and completeness.
- Omission suspicion as a bounded epistemic state.
- Confidence semantics for verifier observations under partial visibility.
- Evidence transparency framing for AI, civic, and enterprise governance systems.

## Formal Methods Contributions

- TLA+ models for append-only logs, verifier federation, liveness, asynchronous transport, and Byzantine-adjacent behavior.
- Alloy artifacts for structural causality and evidence constraints.
- A refinement ladder from dissertation definitions to executable tests.
- Explicit proof/assumption boundaries.

## Systems Contributions

- Reference implementation of canonical evidence events.
- Append-only log, Merkle proof, consistency proof, signed root, and verifier interfaces.
- API, CLI, SDK, Explorer, and certificate/report surfaces.
- Deterministic Phase 2 and Phase 3 demos for hosted and federation-oriented validation.

## Evaluation Contributions

- Reproducible benchmark and experiment plan.
- Fork simulation, omission detection, replay, probabilistic trust, and federation checks.
- Golden proof fixtures and tamper demonstrations.
- CI-checkable validation path.

## Governance Contributions

- Human-readable proof certificates.
- AI and software provenance scenarios.
- Consent and disclosure alignment through Lantern stack integration.
- Audit artifacts suitable for enterprise, civic, and research review.

## Existing Artifact Mapping

| Claim | Repo artifacts |
| --- | --- |
| Canonical evidence events | `ets/core/models.py`, `ets/core/canonical_json.py`, `tests/unit/test_evidence_event.py` |
| Append-only verification | `ets/core/log.py`, `ets/core/hash_chain.py`, `tests/unit/test_hash_chain.py` |
| Merkle proofs | `ets/core/proofs.py`, `tests/unit/test_inclusion_proofs.py` |
| Signed roots | `ets/core/signing.py`, `docs/security/TREE_HEAD_SIGNING.md` |
| Federation | `ets/core/federation.py`, `ets/runtime/distributed_verifier.py`, `tests/unit/test_federation.py` |
| Replay and experiments | `ets/experiments`, `tests/unit/test_experiments.py` |
| Governance outputs | `ets/reports/certificate.py`, `docs/scenarios` |
| Formal models | `formal/tla`, `formal/alloy`, `formal/apalache` |

## Boundaries

The contribution is not a cryptocurrency, not a token economy, not a universal oracle, and not a complete replacement for consensus protocols. ETS is a verifiable evidence layer that can complement existing systems.
