# Formal Theorems

This appendix states ETS proof obligations in restrained engineering terms.
The statements are intended for implementation review and formal-methods
expansion; they are not mathematical publication claims until mechanically
checked with the stated assumptions.

## Model Assumptions

- Events are represented as JSON-native `EvidenceEvent` values.
- Canonicalization is deterministic for supported JSON values.
- SHA-256 is collision-resistant for practical protocol purposes.
- Merkle proof verification uses the same hash-domain separation as proof
  generation.
- Tree-head signatures bind a root, tree size, log identifier, and timestamp to
  a configured public key.
- Omission detection receives an external expected-event set.
- Asynchronous network experiments use bounded delay/loss models and fixed
  seeds for reproducibility.
- Liveness properties depend on weak fairness for healing, replay,
  propagation, and recovery actions.
- Bayesian reliability experiments use a Beta-Bernoulli observation model.
- Governance escalation semantics are process classifications, not legal
  determinations.

## Theorem 1: Canonical Event Hash Determinism

For any supported `EvidenceEvent`, canonical serialization is deterministic.
Therefore SHA-256 over the hashable payload is deterministic.

Evidence in implementation:

- `ets.core.canonical_json`
- `tests/unit/test_canonical_json.py`
- `tests/spec/test_vectors.py`

## Theorem 2: Inclusion Soundness

Given a valid inclusion proof, recomputing the root from the leaf hash and audit
path yields the proof root. Modifying the leaf hash, path direction, sibling
hash, tree size, or expected root causes verification failure.

Evidence in implementation:

- `ets.core.proofs`
- `ets.core.merkle`
- `tests/unit/test_inclusion_proofs.py`

## Theorem 3: Linear Consistency Soundness

Given a linear consistency proof, recomputing the previous root over the prefix
and the latest root over all supplied leaves verifies append-only extension
relative to the supplied leaves.

Limitation: RC consistency proofs are not claimed to be compact RFC 6962
consistency proofs.

## Theorem 4: Quorum Threshold Correctness

For a finite set of verifier votes and a positive threshold, quorum acceptance
is true if and only if the number of valid votes is greater than or equal to
the threshold.

Evidence in implementation:

- `ets.core.quorum`
- `tests/unit/test_quorum.py`

## Theorem 5: Federation Root-Agreement Assessment

For a finite set of unique verifier observations and a positive threshold, ETS
reports quorum if and only if at least that many verifier IDs report the same
`(log_id, tree_size, root_hash)` tuple. ETS reports non-acceptance if a
same-log, same-size root conflict is also present.

Evidence in implementation:

- `ets.core.federation`
- `ets.experiments.federation_convergence`
- `tests/unit/test_federation.py`
- `tests/unit/test_experiments.py`
- `tests/integration/test_api.py`

Limitation: this is a deterministic laboratory assessment, not Byzantine
consensus or proof that any verifier is honest.

## Theorem 6: Fork Suspicion by Conflicting Roots

If two observed roots for the same logical federation view differ, a verifier
can report fork suspicion. This proves disagreement between observations, not
which node is honest.

Evidence in implementation:

- `ets.experiments.fork_simulation`
- `tests/unit/test_experiments.py`

## Theorem 7: Omission Suspicion Requires External Expectation

An omission finding is valid only relative to an expected-event set. If an
expected event ID is absent from the observed log IDs, ETS can report omission
suspicion for that ID.

Evidence in implementation:

- `ets.experiments.omission_detection`
- `formal/alloy/ETSCausalModel.als`
- `tests/unit/test_experiments.py`

## Theorem 8: Bounded Async Delivery Classification

For a fixed network seed, recipient set, delay bounds, packet-loss probability,
and partial-synchrony bound, the async-network experiment deterministically
classifies messages as delivered or lost, records delivery order, permits
packet reordering when configured, and reports convergence only when all
messages are delivered within the configured bound.

Evidence in implementation:

- `ets.experiments.async_network`
- `formal/tla/ETSAsyncNetwork.tla`
- `tests/unit/test_async_network.py`

Limitation: this is not a proof of partial synchrony for arbitrary networks and
does not establish liveness under an asynchronous adversary.

## Theorem 9: Fairness-Scoped Liveness

Under explicit weak-fairness assumptions and after partition/adversarial
pressure removal, the bounded liveness model states replay eventuality, witness
propagation completion, stale-state recovery, and convergence after adversarial
pressure.

Evidence in implementation:

- `formal/tla/ETSLiveness.tla`
- `ets.experiments.liveness`
- `tests/unit/test_liveness.py`

Limitation: this is not an unconditional liveness proof. If partitions do not
heal, adversarial pressure does not end, or fairness assumptions are not met,
ETS does not claim convergence.

## Theorem 10: Beta-Bernoulli Posterior Update

Given a Beta prior and Bernoulli success/failure counts, ETS computes the
posterior parameters by adding successes to alpha and failures to beta. The
reported mean and variance follow the standard Beta posterior formulas.

Evidence in implementation:

- `ets.experiments.probabilistic`
- `tests/unit/test_probabilistic.py`

Limitation: this models observed verifier reliability under a simple Bernoulli
assumption. It is not a stochastic-process convergence proof.

## Theorem 11: Governance Escalation Classification

Given a governance case with technical and policy signals, ETS deterministically
classifies the case as accepted only when quorum is accepted and no escalation
signals are present. Override, legal-hold, and multi-reviewer escalations
require arbitration.

Evidence in implementation:

- `ets.governance.escalation`
- `docs/governance/GOVERNANCE_SEMANTICS.md`
- `tests/unit/test_governance.py`

Limitation: this is a process model, not legal advice or a model of
organizational authority.

## Non-Theorems

ETS does not prove:

- that all real-world evidence was submitted;
- that an AI model's output is fair or semantically correct;
- that a private key was never compromised;
- that a log operator is honest;
- Byzantine consensus safety or liveness under asynchronous adversaries;
- Internet-scale federation convergence;
- symbolic model checking or refinement proof completion;
- that Bayesian verifier reliability implies adversarial correctness;
- that a legal chain of custody is sufficient for a court or regulator.

Those claims require external controls, policy definitions, operational review,
or legal analysis.
