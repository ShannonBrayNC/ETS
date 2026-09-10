# ADR 0012: Retain Publication Chains Behind a Distinct Custodian Boundary

- **Status:** Accepted for R0.2 software reference
- **Date:** 2026-09-10
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

ADR 0011 defines signed external publication receipts and expected-head-relative verification, but
its publisher is in memory. A later verifier needs evidence that a separate custody boundary
retained the chain and could retrieve the expected head. Calling a local database "immutable"
would overstate the available evidence.

## Decision

Add a separately keyed archive boundary that verifies the complete publisher chain, transactionally
appends only an exact new suffix, detects recovery behind a caller-retained expected head, and emits
signed retrieval-audit evidence. Require custodian identities, key IDs, and public-key material to
be distinct from publisher and registry roles.

Classify SQLite WAL/FULL persistence as a logical append-only software reference. Keep physical
WORM storage, independent administration, hardware anti-rollback, continued availability, truth,
and physical outcome explicitly false.

## Consequences

- Valid stale copies fail when checked against a later separately retained head.
- Forked, duplicated, reordered, malformed, key-substituted, or index-tampered data fails closed.
- Retrieval success, head mismatch, and empty archive become signed source observations.
- A production object-lock/WORM adapter can preserve the versioned receipt and audit semantics.
- The reference cannot claim immutable media or organizational independence from software behavior
  and distinct keys alone.
- ETS Core canonicalization remains authoritative; Fleet, Gateway, motion, and authorization are
  unchanged.

## Rejected alternatives

### Label SQLite as immutable storage

Rejected because privileged file or database access can replace or alter it. The implementation
enforces and verifies logical append-only behavior only.

### Treat a successful write as continued custody

Rejected because acceptance does not establish later availability. Retrieval is a separate signed
observation with its own expected-head comparison.

### Reuse the publisher key for archive audits

Rejected because it collapses publication and custody into one authority and weakens substitution
detection.

## Follow-on

Add publisher/custodian key lifecycle evidence, then qualify a real WORM/object-lock backend with
independent administration, retention-policy evidence, replication, deletion-negative tests, and
availability observations.
