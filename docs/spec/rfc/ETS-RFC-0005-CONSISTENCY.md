# ETS-RFC-0005: Consistency Proof Policy

RC6 keeps the implemented consistency proof as `ets.consistency_proof.v1`.
It is intentionally linear: the proof contains the latest leaf hashes and
verifies both the previous and latest roots from those leaves.

This is stronger than an unchecked tree-head comparison because it verifies
append-only growth against concrete leaves, but it is not a compact RFC 6962
consistency proof. A compact proof requires a tree algorithm and proof format
change that should not be smuggled into RC6 without new conformance vectors.

Decision:

- `ets.consistency_proof.v1` remains the RC proof format.
- The API and verifier must not claim compact consistency.
- Compact consistency is an RC7/v0.2 protocol candidate.
- Any future compact proof must ship with deterministic vectors, negative
  vectors, and third-party implementer documentation.
