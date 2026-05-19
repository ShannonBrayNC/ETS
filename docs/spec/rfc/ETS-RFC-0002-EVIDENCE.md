# ETS-RFC-0002: Evidence Events

An `EvidenceEvent` contains tenant, workspace, evidence identifiers, a
`sha256` content hash, metadata, and a UTC creation timestamp. Raw evidence
bytes are never stored by ETS.

`content_hash_alg` is `sha256` in RC5. Unsupported hash algorithms are rejected.
