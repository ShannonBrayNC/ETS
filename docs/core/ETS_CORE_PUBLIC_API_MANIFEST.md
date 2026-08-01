# ETS Core Public API Manifest

Status: proposed for C1 implementation

Only names listed in this manifest are candidates for the supported C1 API. Existing imports not listed here remain compatibility or internal surfaces until separately approved.

## Stability classes

- `stable`: semantic compatibility required within the major version.
- `experimental`: may change in minor releases; explicit opt-in import path.
- `deprecated`: supported temporarily with warnings and migration guidance.
- `internal`: no compatibility promise.

## Stable public facade

Target import path:

```python
from ets.core.api import (
    CanonicalizationProfile,
    HashProfile,
    MerkleProfile,
    ProtocolProfile,
    EvidenceEvent,
    InclusionProof,
    ConsistencyProof,
    SignedTreeHead,
    EvidenceProofBundle,
    VerificationStatus,
    VerificationReason,
    VerificationResult,
    canonicalize,
    canonical_sha256,
    get_profile,
    list_profiles,
    merkle_root,
    generate_inclusion_proof,
    verify_inclusion_proof,
    generate_consistency_proof,
    verify_consistency_proof,
    verify_signed_tree_head,
    verify_bundle,
)
```

## Public contracts

### `canonicalize(value, *, profile=...) -> bytes`

Returns canonical bytes or raises `CanonicalizationError` when the caller supplies a value outside the profile domain.

### `canonical_sha256(value, *, profile=...) -> str`

Returns lowercase hexadecimal SHA-256 over canonical bytes.

### `get_profile(profile_id) -> ProtocolProfile`

Returns an immutable registered profile. Unknown identifiers raise `UnknownProfileError` for direct configuration use. Verification APIs convert unknown artifact profiles into structured `UNSUPPORTED_PROFILE` results.

### `list_profiles(*, production=True, verification=True) -> tuple[ProtocolProfile, ...]`

Returns profiles in stable identifier order.

### `merkle_root(leaves, *, profile=...) -> bytes`

Pure root construction over ordered leaf inputs.

### Proof generation

Generation APIs accept trusted, validated local data and may raise programmer/configuration exceptions. They SHALL emit explicit profile identifiers.

### Proof verification

Verification APIs accept untrusted portable material and return `VerificationResult`. Invalid proof material is a normal result, not an exception.

## Stable models

Public protocol models SHALL be immutable or treated as immutable, serializable without application services, and independent of Pydantic/FastAPI transport behavior at the public contract boundary.

## Excluded from the stable facade

The following SHALL NOT be exported by `ets.core.api` during C1:

- SQLite or in-memory stores;
- append-only log service implementations;
- artifact registry and raw-artifact convenience APIs;
- federation and quorum policy;
- external anchoring transports;
- report rendering;
- HTTP/API models;
- authentication and authorization;
- environment settings;
- Azure or hosted signer adapters;
- Edge capture and synchronization;
- portal or UI models;
- AI-derived analysis;
- Evidence Graph or trust-policy evaluation.

## Import compatibility

`ets.core.__init__` may retain transitional re-exports during C1, but:

1. it SHALL be documented as a compatibility facade;
2. new consumers SHALL use `ets.core.api`;
3. import-boundary tests SHALL freeze `ets.core.api.__all__`;
4. removal of compatibility exports requires deprecation and migration evidence; and
5. package import SHALL have no storage, network, environment, or logging side effects.

## Versioning

- Adding a backward-compatible stable function: minor version.
- Adding a new optional profile: minor version when no existing result changes.
- Changing canonical bytes, hash preimages, proof semantics, or result meanings: new protocol profile and normally a major version.
- Removing or renaming a stable symbol: major version after deprecation.
- Security disabling of a profile: security advisory plus explicit verification policy; historical verification requirements must be documented.
