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

## Theorem 5: Fork Suspicion by Conflicting Roots

If two observed roots for the same logical federation view differ, a verifier
can report fork suspicion. This proves disagreement between observations, not
which node is honest.

Evidence in implementation:

- `ets.experiments.fork_simulation`
- `tests/unit/test_experiments.py`

## Theorem 6: Omission Suspicion Requires External Expectation

An omission finding is valid only relative to an expected-event set. If an
expected event ID is absent from the observed log IDs, ETS can report omission
suspicion for that ID.

Evidence in implementation:

- `ets.experiments.omission_detection`
- `formal/alloy/ETSCausalModel.als`
- `tests/unit/test_experiments.py`

## Non-Theorems

ETS does not prove:

- that all real-world evidence was submitted;
- that an AI model's output is fair or semantically correct;
- that a private key was never compromised;
- that a log operator is honest;
- that a legal chain of custody is sufficient for a court or regulator.

Those claims require external controls, policy definitions, operational review,
or legal analysis.
