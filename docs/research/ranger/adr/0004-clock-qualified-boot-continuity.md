# ADR 0004: Link Boot Custody with Explicit Clock Quality

- Status: Accepted for R0.2 software reference
- Date: 2026-09-06
- Tracks: #605

## Context

Ranger custody chains are intentionally boot-scoped. A bare new `boot_id` cannot establish which
prior chain it follows, while a local UTC timestamp cannot by itself establish trusted time.
Treating either as sufficient would permit cross-boot ambiguity and overclaim temporal standing.

## Decision

The first custody record of each participating boot is an `ets.ranger.boot-checkpoint.v1` source
event. It binds a contiguous boot sequence, explicit clock source/quality/uncertainty, and—after
genesis—the preceding boot identifier and signed custody-head digest. Continuity verification
requires both chains to verify under the same expected Ed25519 key and signed key identifier.
Rotation is deferred until an authorized key-handoff contract exists.

## Consequences

- Independent verifiers can detect supplied cross-boot head substitution, identity mismatch,
  invalid adjacent boot-sequence transitions, wrong stable keys or key identifiers, and
  non-advancing recorded boot timestamps.
- Clock confidence is evidence data rather than an implicit trust claim.
- A later checkpoint makes prior suffix deletion detectable when the checkpoint is retained.
- Local checkpoints still do not prove complete capture, external witnessing, authenticated time,
  freshness of an otherwise valid pair, hardware identity, or the absence of an omitted boot.
