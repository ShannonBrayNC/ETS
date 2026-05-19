# Formal Theorems

## Theorem 1: Canonical Event Hash Determinism

For any JSON-native `EvidenceEvent`, canonical serialization is deterministic;
therefore SHA-256 over the hashable payload is deterministic.

## Theorem 2: Inclusion Soundness

Given a valid inclusion proof, recomputing the root from the leaf hash and audit
path yields the proof root.

## Theorem 3: Linear Consistency Soundness

Given a linear consistency proof, recomputing the previous root over the prefix
and the latest root over all supplied leaves verifies append-only extension
relative to those supplied leaves.

## Non-Theorem: Completeness

ETS does not prove that all real-world evidence was submitted. Omission
detection is relative to an expected event set.
