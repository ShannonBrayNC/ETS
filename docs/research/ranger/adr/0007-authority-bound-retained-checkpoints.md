# ADR 0007: Bind Retained Ranger Custody to Retained Key-Authority Heads

- **Status:** Accepted for R0.2 software reference
- **Date:** 2026-09-08
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

The static-key retained-checkpoint profile detects replay and truncation relative to verifier
state, while the key-authority profile establishes enrollment, boot-boundary rotation, and
revocation relative to a supplied authority history. Used independently, neither proves that the
Ranger key accepted for a custody checkpoint was evaluated against the latest authority history
already known to that verifier. A stale but valid authority prefix could hide a later revocation.

Changing `ets.ranger.retained-checkpoint.v1` in place would silently alter its verifier contract
and break versioned-source compatibility. Treating ETS Fleet state as an implicit key lookup would
also collapse operational authorization into evidence verification.

## Decision

Add two explicit R0.2 profiles:

- `ets.ranger.retained-key-authority-head.v1` is a registry-signed, predecessor-linked record of
  a verified authority event count and history head.
- `ets.ranger.authority-bound-retained-checkpoint.v1` binds an accepted Ranger custody head and
  resolved custody-key identity to the exact retained authority-head checkpoint used.

Retain authority state before evaluating custody. Reject authority rollback, equal-position forks,
non-prefix extension, unauthorized keys, same-boot key changes, Ranger truncation/forks, skipped
boots, and invalid prior-boot bindings. Permit distinct Ranger-only, authority-only, and combined
advancement records. Preserve the existing static-key profile unchanged.

Use the same configured registry signer for both chains in the software reference, while keeping
separate schemas and stores. Require independent verification to receive both retained chains,
the complete authority history, the Ranger custody chain, and out-of-band authority and registry
public keys.

ETS Core retains canonicalization and proof semantics. ETS Fleet remains the operational
authorization plane. Gateway remains outside the real-time safety loop.

## Consequences

- A verifier can reject a stale authority prefix and a correctly signed post-revocation Ranger
  boot without retroactively invalidating earlier evidence.
- Every accepted custody checkpoint identifies the precise retained authority view used to
  establish authority-relative key standing.
- A failed custody submission can still advance retained revocation state, preventing a retry
  under older authority history.
- The two SQLite commits are not cross-store atomic. The safe recovery state is authority ahead
  of composed custody; retry is idempotent, and receipt time cannot predate the bound authority
  head.
- Structural checkpoint verification intentionally does not claim source-custody or authority
  binding verification; the comprehensive verifier requires all source histories.
- Global currentness, Fleet authorization, administrative independence, trusted time, hardware
  identity, completeness, semantic truth, actuator response, and physical outcome remain
  unproven.
- Production requires authenticated administration, authority and registry key lifecycle,
  hardware-backed keys and anti-rollback state, encrypted storage, immutable replication, and
  reconciliation evidence.
