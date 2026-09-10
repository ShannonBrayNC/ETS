# ADR 0011: Bind Retained Ranger Receipts to an External Publication Head

- **Status:** Accepted for R0.2 software reference
- **Date:** 2026-09-09
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

Ranger retained receipts now support configured governance and trusted-time composition, but a
presenter can still supply a valid stale prefix unless the verifier possesses a later head through
another channel. A single local SQLite store also cannot establish external custody or continued
availability.

## Decision

Define a strict, signed `ets.ranger.external-publication-receipt.v1` source structure and a
software-reference publisher. Each receipt binds an exact trusted-time-attested retained receipt,
its time-attestation digest, the originating registry, the publisher identity and key, sequence,
predecessor digest, and publisher-local timestamp.

Require verifiers to validate the complete chain and compare it with an expected head obtained
outside the presented chain. Composed verification must first establish the existing retained and
trusted-time claims, then require the latest publication receipt to bind those exact digests.
Registry and publisher identities and key material must be distinct.

Treat publication integrity, expected-head-relative freshness, continued custody, organizational
independence, and global currentness as separate claims.

## Consequences

- A stale prefix fails when the verifier has a later independently retained expected head.
- Deleted, inserted, reordered, duplicated, substituted, or tampered receipts fail closed.
- The reference structure can be emitted unchanged by a future real publisher adapter.
- No external service, immutable replication, hardware-backed key, continued custody, or global
  latest-state claim exists merely because the software-reference chain verifies.
- ETS Core, Fleet, Gateway, motion, actuator, and real-time safety behavior remain unchanged.

## Rejected alternatives

### Treat the registry's own latest receipt as external publication

Rejected because one authority restating its own head does not create a distinct custody or
rollback-detection boundary.

### Infer currentness from a valid publication signature

Rejected because a cryptographically valid historical prefix may still be stale.

### Claim external custody from the in-memory reference publisher

Rejected because code separation and distinct software keys do not prove operational,
organizational, or infrastructure independence or continued retention.

## Follow-on

Implement a separately administered immutable publication adapter, protect the publisher-key
lifecycle, retain expected heads with rollback resistance, and test independent retrieval and
availability without conflating those results with evidence truth or physical outcome.
