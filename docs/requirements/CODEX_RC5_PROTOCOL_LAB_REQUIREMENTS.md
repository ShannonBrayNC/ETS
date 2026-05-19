# Codex RC5 Protocol Lab Requirements

RC5 implements an executable protocol lab for ETS:

- deterministic canonicalization and evidence hashing
- append-only transparency log
- Merkle inclusion proofs
- simplified linear consistency proofs
- Ed25519 tree-head signing
- verifier quorum logic
- FastAPI protocol-lab compatibility endpoints
- fork and omission experiments
- benchmark artifact generation
- local Docker federation topology

RC5 does not claim proof of completeness. Omission detection reports findings
relative to an expected event set supplied by the caller or experiment.
