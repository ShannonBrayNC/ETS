# ETS Application SDK v1 conformance vectors

This directory contains language-neutral golden vectors for implementations of
`ets.application.sdk.v1`.

A language binding MUST reproduce these bytes and digests exactly before it may
claim hashing compatibility with the ETS Python reference implementation.

Current vector families:

- `canonicalization/` — deterministic ETS JSON serialization and SHA-256.
- `event-hashing/` — canonical hashable `ets.event.v1` payloads.

The corpus is intentionally small in SDK-1. Before .NET or TypeScript performs
client-side ETS hashing, expand this corpus to cover Unicode edge cases, numeric
serialization, nested mappings, nulls, arrays, maximum-bound values, and rejected
non-finite numbers. Until those implementations pass the corpus, they should
submit protocol objects to Gateway and treat server-produced ETS hashes as
authoritative.
