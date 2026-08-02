# ETS Core Protocol Profile Registry

Status: C1 registry contract aligned to the merged implementation

## Registry rules

Every normative artifact must identify the profiles needed to reproduce or verify it. Profile identifiers are lowercase ASCII strings, immutable after publication, and never reassigned.

The C1 `ProtocolProfile` value contains:

- `id`
- `kind`
- `version`
- `production`
- `verification_only`
- `description`

Profiles are frozen values held in an immutable registry.

## Registered C1 profiles

### `ets.protocol.event.v1.rfc6962-sha256`

- Kind: `event`
- Version: `1`
- Production: allowed
- Verification-only: false

### `ets.protocol.event.v1.alpha-unprefixed`

- Kind: `event`
- Version: `1`
- Production: prohibited
- Verification-only: true

### `ets.canonical.json.v1`

- Kind: `canonicalization`
- Version: `1`
- Production: allowed
- Deterministic UTF-8 JSON serialization

### `ets.hash.sha256.v1`

- Kind: `hash`
- Version: `1`
- Production: allowed
- SHA-256 digest profile

### `ets.merkle.rfc6962-sha256.v1`

- Kind: `merkle`
- Version: `1`
- Production: allowed
- Leaf: `SHA256(0x00 || leaf_input)`
- Node: `SHA256(0x01 || left || right)`

### `ets.merkle.alpha-unprefixed-sha256.v1`

- Kind: `merkle`
- Version: `1`
- Production: prohibited
- Verification-only: true
- Legacy unprefixed leaf/node behavior

### `ets.signature.ed25519.v1`

- Kind: `signature`
- Version: `1`
- Production: allowed
- Signature validity does not establish key authorization or trust

## Lookup behavior

- `resolve_profile(profile_id)` returns the registered immutable value.
- `get_profile(profile_id)` is the public-facade alias for `resolve_profile`.
- `list_profiles()` returns profiles in stable identifier order.
- Unknown identifiers raise `UnknownProfileError` in direct configuration use.
- `resolve_profile(..., allow_verification_only=False)` raises `VerificationOnlyProfileError` for legacy verification-only profiles.
- Implementations must not guess a profile from digest values, proof shape, or payload structure.

## Extension process

A new profile requires:

1. an ADR or normative specification;
2. security analysis;
3. positive, negative, and downgrade vectors;
4. implementation and conformance tests;
5. compatibility and production-permission statements;
6. independent review; and
7. a registry and public-documentation update in the same release.
