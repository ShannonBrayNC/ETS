# ADR 0005: Retain Ranger Latest Heads Outside Vehicle Custody

- Status: Accepted for R0.2 software reference
- Date: 2026-09-07
- Tracks: #605

## Context

A Ranger custody chain can be internally valid and still be stale. Pairwise boot-continuity
verification cannot detect replay of an older valid pair when the verifier has no separately
retained latest state. The vehicle must not be the sole authority for what its latest known head
was.

## Decision

Add `ets.ranger.retained-checkpoint.v1` and a verifier-side registry. The registry verifies a
complete Ranger custody chain under an out-of-band vehicle key, compares it with durable retained
state, and signs the accepted boot sequence, record count, and custody head under a distinct
registry key. Same-boot updates prove prefix extension; new boots must be adjacent and bind the
retained boot and head. Offline presentation verification requires an exact match with the
separately supplied latest checkpoint.

The first accepted state is explicitly a baseline. The profile claims freshness only relative to
the supplied registry history and cannot claim global currency, independent physical custody,
trusted time, completeness, standing, semantic truth, or physical outcome.

## Consequences

- A verifier holding the latest checkpoint can reject an older valid boot or a truncated current
  chain and distinguish those cases from a fork or uncheckpointed newer state.
- Vehicle and registry signatures are purpose-separated under distinct expected keys.
- Registry rollback remains possible when the entire software store is replaced with an earlier
  valid copy; replicated immutable publication or quorum witnesses are follow-on work.
- Authorized Ranger and registry key rotation/revocation, authenticated time, hardware-backed
  custody, and fleet enrollment remain outside this increment.

