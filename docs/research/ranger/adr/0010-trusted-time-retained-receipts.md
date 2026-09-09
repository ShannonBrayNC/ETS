# ADR 0010: Add Trusted-Time Evidence to Retained Ranger Receipts

- **Status:** Accepted for R0.2 software reference
- **Date:** 2026-09-09
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

Ranger R0.2 already retains registry-signed authority-history heads and authority-bound custody
checkpoints. Those receipts intentionally carry `trusted_time_proven=false`. Their
`received_at_utc` fields are local registry observations and cannot establish independently signed
time evidence.

ADR 0008 introduced a separate configured trusted-time attestation primitive, and ADR 0009 composed
that primitive into governed authority acceptance. Retained receipts still need an additive stronger
verification path without changing their existing versioned schemas.

## Decision

Add verifier-side composition functions that require a valid configured trusted-time attestation
over the exact digest of the latest receipt in the complete presented retained chain.

For retained authority heads, the verifier must first establish registry-signature and structural
chain integrity. For authority-bound custody checkpoints, it must additionally require the existing
checkpoint-chain verifier to establish the retained authority binding.

Both profiles require configured registry identity/signing-key identity and configured time-source/
time-signing-key identity. The time attestation must target the exact retained receipt kind and
`checkpoint_digest_sha256`.

Keep the legacy retained receipt schemas unchanged and keep their local `received_at_utc` values
explicitly outside the trusted-time claim.

## Consequences

- A verifier can distinguish a locally timestamped retained receipt from one that also has
  separately signed configured trusted-time evidence.
- Receipt or subject substitution, registry-identity substitution, time-key substitution, and
  time-identity substitution fail closed.
- The time authority attests that the exact receipt digest existed within a bounded interval; it
  does not prove that the receipt's local receive timestamp is correct.
- Existing retained receipts do not automatically acquire stronger time claims.
- Registry-relative freshness remains registry-relative. The profile does not prove global latest
  state or independent external custody.
- Motion, actuator, Fleet, and Gateway behavior remain unchanged.

## Rejected alternatives

### Mark `received_at_utc` as trusted time

Rejected because a locally recorded timestamp does not establish an independent cryptographic time
claim.

### Add time fields to the existing retained receipt schemas

Rejected because that would change the meaning of versioned contracts already used by existing
retained evidence.

### Treat a valid time signature as proof of global UTC correctness

Rejected because the attestation proves only what the configured time-authority key signed, subject
to its stated uncertainty and trust boundary.

## Follow-on

The next R0.2 evidence-hardening step should add independent external publication/custody for
retained latest-head commitments so rollback resistance no longer depends only on one verifier's
local SQLite state. Publication should remain a separate claim from semantic truth, complete
capture, operational authorization, and global currentness.
