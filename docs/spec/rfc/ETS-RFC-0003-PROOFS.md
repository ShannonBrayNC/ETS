# ETS-RFC-0003: Proofs

RC5 proof types:

- Inclusion proof: leaf hash, audit path, root, and tree size.
- Consistency proof: previous size, latest size, previous root, latest root, and
  linear leaf hashes.
- Proof bundle: event, event hash, leaf hash, tree head, inclusion proof, and
  verification result.

All v1 proof types are bound to `ets.merkle.rfc6962_sha256.v1`: leaf hashes use
the `0x00` domain byte, internal nodes use the `0x01` domain byte, hash inputs
are raw digest bytes rather than hexadecimal text, and odd tree sizes use the
RFC 6962 power-of-two split without node duplication.

Linear consistency proofs are not compact. They are suitable for executable
research and deterministic validation of the current Merkle construction.
