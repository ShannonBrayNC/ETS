# ETS Core Protocol Profile Registry

Status: proposed registry for C1

## Registry rules

Every normative artifact SHALL identify all profiles needed to reproduce or verify it. Identifiers are lowercase ASCII, immutable after publication, and never reassigned.

A profile record contains:

- `profile_id`
- `kind`
- `status`
- `protocol_version`
- `canonicalization_profile`
- `content_hash_profile`
- `merkle_profile`
- `signature_profile`, when applicable
- production/verification permissions
- supersession information

Statuses are `active`, `verification_only`, `experimental`, `deprecated`, and `disabled`.

## C1 registry

### `ets.protocol.event.v1.rfc6962-sha256`

- Kind: composite protocol
- Status: active
- Production: allowed
- Verification: allowed
- Event schema: `ets.event.v1`
- Canonicalization: `ets.canonical.json.v1`
- Content/event digest: `ets.hash.sha256.v1`
- Merkle: `ets.merkle.rfc6962-sha256.v1`
- Tree-head payload: `ets.tree-head.v1`

### `ets.protocol.event.v1.alpha-unprefixed`

- Kind: composite protocol
- Status: verification-only
- Production: prohibited
- Verification: allowed only when explicitly identified
- Event schema: `ets.event.v1`
- Canonicalization: `ets.canonical.json.v1`
- Content/event digest: `ets.hash.sha256.v1`
- Merkle: `ets.merkle.alpha-unprefixed-sha256.v1`

### `ets.canonical.json.v1`

- UTF-8
- deterministic key ordering
- no insignificant whitespace
- arrays preserve order
- finite supported numbers only
- no implicit Unicode normalization

### `ets.hash.sha256.v1`

- Algorithm: SHA-256
- Digest representation at interchange boundaries: lowercase hexadecimal unless a schema specifies raw bytes/base64
- Digest length: 32 bytes / 64 hexadecimal characters

### `ets.merkle.rfc6962-sha256.v1`

- Leaf: `SHA256(0x00 || leaf_input)`
- Node: `SHA256(0x01 || left || right)`
- Status: active

### `ets.merkle.alpha-unprefixed-sha256.v1`

- Legacy leaf/node hashing without RFC 6962 domain prefixes
- Status: verification-only
- No new production artifacts

### `ets.signature.ed25519.v1`

- Signature algorithm: Ed25519
- Signs canonical `ets.tree-head.v1` payload bytes
- Key trust and revocation remain external policy inputs

## Resolution behavior

- Direct configuration with an unknown profile raises `UnknownProfileError`.
- Verification of an artifact naming an unknown profile returns `UNSUPPORTED / UNSUPPORTED_PROFILE`.
- Missing profile where required returns `UNKNOWN / PROFILE_REQUIRED` or `MALFORMED / PROFILE_REQUIRED`, according to the artifact schema.
- Conflicting nested profiles return `INVALID / PROFILE_CONFLICT`.
- Implementations SHALL NOT guess profiles from digest values or proof shape.

## Extension process

A new profile requires:

1. ADR or normative specification;
2. security analysis;
3. positive, negative, and downgrade vectors;
4. implementation and conformance tests;
5. compatibility statement;
6. independent review; and
7. registry update in the same release.
