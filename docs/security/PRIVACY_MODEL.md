# ETS Privacy Model

ETS separates proof material from raw content. Evidence events contain metadata
and content hashes; raw evidence bytes remain outside the transparency log.

Redaction profiles run before hashing and storage. Redacted metadata is the
canonical metadata that gets hashed, which means stored values and hash inputs
match exactly.

Fixtures and demos must use synthetic data only.
