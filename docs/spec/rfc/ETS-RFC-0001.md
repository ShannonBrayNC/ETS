# ETS-RFC-0001: Protocol Overview

ETS is an evidence metadata transparency protocol. Events are canonicalized,
hashed, appended to a log, and committed into a Merkle tree. Verifiers can check
event hashes, inclusion proofs, consistency proofs, signed tree heads, and proof
bundles.

RC5 supports local and laboratory federation. It does not define production
governance for public roots of trust.
