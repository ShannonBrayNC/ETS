# ADR 0006: Authority-Relative Ranger Custody-Key History

- **Status:** Accepted for R0 software reference
- **Date:** 2026-09-08
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

Ranger custody records identify and verify an Ed25519 key, but a valid signature does not imply
that the key was authorized. Cross-boot verification originally required one stable key and
therefore had no evidence-backed way to accept planned rotation or reject a revoked key while
preserving historical evidence.

ETS Fleet already owns operational device enrollment and authorization. Reimplementing that
control plane inside Ranger would create competing semantics, while treating Fleet state or a
signature as self-proving standing would collapse architecture boundaries.

## Decision

Create a separate append-only `ets.ranger.key-authority-event.v1` history for custody-verification
key standing. Each event is canonically hashed, predecessor-linked, and signed by a key distinct
from the Ranger custody key.

- Enrollment requires proof of possession from the proposed Ranger key.
- Rotation requires possession proofs from both the current and replacement keys and takes effect
  at a strictly later boot sequence.
- Revocation is authority-only, reason-coded, effective at a declared boot sequence, and terminal
  in R0.
- Historical verification resolves the correct key by boot sequence and does not retroactively
  invalidate custody records from before a later rotation or revocation.
- The SQLite implementation is a crash-consistent software reference and makes no hardware,
  administrative-independence, operational-authorization, or global-currentness claim.

ETS Core retains canonicalization and digest semantics. Fleet remains the operational device
authorization plane. Gateway remains outside Ranger's real-time safety loop.

## Consequences

The new profile closes the verifier gap between signature integrity and authority-relative key
standing, and allows independently verified custody continuity across a planned key change. A
correctly signed boot at or after revocation now fails key-standing verification.

R0 deliberately has no overlap window or emergency authority-only rotation: rotation happens at a
boot boundary and needs the old key. [ADR 0007](0007-authority-bound-retained-checkpoints.md) now
composes this history with separately retained authority heads and a new custody-checkpoint
profile; the original static-key checkpoint contract remains unchanged. Whole-registry rollback
still requires immutable replication or an externally retained latest checkpoint. Production also
requires Fleet composition, authenticated administration, hardware key custody, anti-rollback
state, encryption, and authority/registry key lifecycle governance.
