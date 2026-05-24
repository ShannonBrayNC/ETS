# Metadata Redaction

ETS supports deterministic metadata redaction profiles before event hashing and
storage.

- `none`: store metadata as provided.
- `basic_pii`: redact exact sensitive keys such as `email`, `phone`, `ssn`,
  `password`, `token`, `access_token`, `refresh_token`, `secret`, and `api_key`.
- `strict`: redact those keys and compound keys containing those terms.

Redaction happens before the event hash is computed. Stored JSON and API
responses contain the redacted value `[REDACTED]`; the original sensitive value
is not stored by ETS.
