# ADR 0008: Additive Ranger Governance and Trusted-Time Evidence

- **Status:** Accepted for R0.2 software reference
- **Date:** 2026-09-08
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

Ranger R0.2 now has signed local custody, cross-boot continuity, verifier-retained latest heads,
authority-relative custody-key lifecycle, and authority-bound retained checkpoints. Those profiles
intentionally do not prove that a key-lifecycle request was approved by an authenticated
administrator or that event/receipt timestamps are backed by a separately signed trusted-time
source.

Changing the existing `ets.ranger.key-binding-request.v1`, `ets.ranger.key-authority-event.v1`, or
retained-checkpoint schemas in place would silently strengthen old contracts and blur the claim
boundary of already retained evidence.

## Decision

Add two independent, versioned evidence primitives:

- `ets.ranger.administrative-approval.v1` signs the canonical digest of the complete existing key
  binding request with a configured administrator key and binds event kind plus Ranger scope.
- `ets.ranger.trusted-time-attestation.v1` signs an exact subject digest, subject kind, UTC
  observation, bounded uncertainty, and configured time-authority identity.

Compose those primitives in a verifier that can prove configured-key administrative approval and
configured-time-authority evidence for a request while keeping authority acceptance as a separate
claim. Permit trusted-time attestations to target retained authority-head and authority-bound
custody-checkpoint digests so later receipt profiles can distinguish local timestamps from
separately signed time evidence.

Do not modify motion authorization, Fleet authorization, Gateway placement, or legacy v1 evidence
contracts in this increment.

## Consequences

- Request substitution, scope substitution, administrator-key substitution, approval tampering,
  time-key substitution, and subject-digest substitution fail closed.
- A valid administrative approval proves control of the configured administrator key, not human
  identity or administrative independence.
- A valid trusted-time attestation proves the configured time authority made the bounded interval
  claim, not global UTC correctness or independent consensus.
- Existing authority events and retained receipts do not automatically gain these stronger claims.
- The next governed-authority profile must require these proofs before claiming authenticated
  administration or trusted time and must preserve legacy verification semantics separately.
- Production still requires hardware-backed key custody, administrator/time key lifecycle,
  anti-rollback state, encrypted storage, external immutable replication, and Fleet composition.

## Rejected alternatives

### Modify the existing authority-event schema in place

Rejected because it would change the meaning of a versioned evidence contract and create ambiguity
for already retained histories.

### Treat local recorded timestamps as trusted time

Rejected because clock quality metadata and a wall-clock value do not prove an independent signed
time assertion.

### Treat administrator identity strings as authentication

Rejected because identity labels without possession of a configured signing key do not establish
cryptographic administrative authentication.
