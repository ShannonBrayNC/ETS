# ADR 0013: Preserve Historical Publication-Key Standing Without Granting Current Authority

- **Status:** Accepted for R0.2 software reference
- **Date:** 2026-09-10
- **Decision owners:** Ranger R0 / ETS Evidence Architecture research
- **Tracks:** #605

## Context

ADR 0012 adds separate publisher and custodian signatures, a logically append-only archive, and
expected-head-relative retrieval audits. A cryptographically valid source signature remains valid
after a normal key rotation or a key-compromise revocation, but it is unsafe to infer that the old
key is still currently authorized. Conversely, discarding all records signed by an old key would
destroy useful historical reconstruction evidence.

The source record timestamps are not trusted-time evidence. A lifecycle implementation must not
use them to claim the source signed before a later lifecycle change.

## Decision

Add a separate authority-signed lifecycle history for `publisher` and `custodian` roles. Require:

- enrollment possession proof from the proposed source key;
- dual old/new possession proofs for rotation;
- bounded, authority-only revocation;
- role-specific active-key transition checks;
- global rejection of reused source-key IDs or public keys across the two roles;
- identity, key, and public-key separation from the lifecycle authority; and
- a signed source-key-standing record naming an exact authority-history prefix and source digest.

Verifier output must report historical authority-relative standing separately from current status
relative to the full history presented. Mixed-key publication-chain verification resolves each
receipt with its own historical standing. All source-time, trusted-time, global-currentness,
operational authorization, WORM, independence, truth, and physical-outcome claims remain false.

## Consequences

- A source record signed by an old key can remain historically verifiable after rotation/revocation.
- A later full history reports that old key as non-current instead of silently treating it as valid
  present authorization.
- Verifiers reject malformed, reordered, forked, duplicate, substituted, cross-role-reused, or
  proof-invalid lifecycle evidence.
- Source signature time relative to a lifecycle event remains unknown absent a separate
  trusted-time composition.
- ETS Core canonicalization remains unchanged; Gateway, Fleet, motion behavior, and the real-time
  safety loop remain outside this profile.

## Rejected alternatives

### Pin one perpetual publisher/custodian public key

Rejected because normal maintenance and compromise response require lifecycle changes, while a
single pinned key either breaks historical verification or leaves the old key implicitly current.

### Treat any valid old signature as current authority

Rejected because signature validity, historical key standing, and current authorization are
different propositions.

### Infer ordering from receipt or audit timestamps

Rejected because those timestamps lack a configured trusted-time binding and can be manipulated or
misconfigured.

### Reuse custody-key authority history unchanged

Rejected because physical Ranger boot-scoped custody and external publication/custodian roles have
different scope, identity, and source semantics. A separate additive profile avoids conflating
them.

## Follow-on

Compose the lifecycle profile with a separately administered immutable publication backend and
independently retained latest-head custody. Add hardware-backed key attestation, administrative
policy evidence, trusted-time bindings, backend configuration evidence, replication, retrieval
availability observations, and deletion-negative tests before making stronger custody claims.
