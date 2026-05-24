# ETS-RFC-0003: Proofs

RC5 proof types:

- Inclusion proof: leaf hash, audit path, root, and tree size.
- Consistency proof: previous size, latest size, previous root, latest root, and
  linear leaf hashes.
- Proof bundle: event, event hash, leaf hash, tree head, inclusion proof, and
  verification result.

Linear consistency proofs are not compact. They are suitable for executable
research and deterministic validation of the current Merkle construction.
