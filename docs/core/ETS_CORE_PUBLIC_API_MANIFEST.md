# ETS Core Public API Manifest

Status: C1.1 implementation contract

This manifest freezes the first supported `ets.core.api` facade. Symbols not listed here are compatibility, implementation, experimental, or product surfaces unless separately approved.

## Stable public facade

```python
from ets.core.api import (
    EvidenceEvent,
    ProfileKind,
    ProtocolProfile,
    VerificationReason,
    VerificationResult,
    VerificationStatus,
    VerifiedComponent,
    canonical_sha256,
    canonicalize,
    get_profile,
    list_profiles,
    resolve_profile,
)
```

The exact ordered `__all__` value is:

```text
EvidenceEvent
ProfileKind
ProtocolProfile
VerificationReason
VerificationResult
VerificationStatus
VerifiedComponent
canonical_sha256
canonicalize
get_profile
list_profiles
resolve_profile
```

## Contract behavior

### Canonicalization

- `canonicalize(value) -> bytes` returns deterministic UTF-8 JSON bytes for supported JSON-native values.
- `canonical_sha256(value) -> str` returns a lowercase SHA-256 hexadecimal digest over those bytes.

### Profiles

- `get_profile(profile_id)` is the specification-facing lookup name.
- `resolve_profile(profile_id, *, allow_verification_only=True)` remains available as the explicit implementation-facing lookup.
- `list_profiles(...)` returns immutable profile records in stable identifier order.
- Unknown profiles raise `UnknownProfileError` in direct configuration use.
- Verification-only profiles cannot be used for production generation when `allow_verification_only=False`.

### Verification results

`VerificationStatus`, `VerificationReason`, `VerifiedComponent`, and `VerificationResult` are immutable machine-readable contracts. Normal invalidity is represented as data rather than an exception.

## Deferred public contracts

The following remain required by later C1 work packages but are not exported by C1.1 until their pure, profile-aware contracts and structured verification behavior are implemented and independently reviewed:

- inclusion and consistency proof models;
- Merkle root and proof-generation functions;
- signed tree-head verification;
- portable evidence-proof bundle verification.

Their absence from C1.1 is deliberate and does not authorize consumers to import internal implementations.

## Excluded from the stable facade

The facade must not export:

- SQLite or in-memory stores;
- append-only log service implementations;
- artifact registries;
- federation or quorum policy;
- anchoring transports;
- reports and templates;
- FastAPI or transport models;
- authentication or authorization;
- environment settings;
- Azure adapters;
- Edge or Cloud runtime behavior;
- portals, billing, AI, or trust-policy evaluation.

## Compatibility and versioning

- `ets.core.__init__` remains a transitional compatibility facade.
- New consumers use `ets.core.api`.
- The exact ordered `ets.core.api.__all__` is CI-enforced.
- Adding a backward-compatible stable symbol requires a minor release and manifest update.
- Removing or renaming a stable symbol requires a major release after deprecation.
- Changing canonical bytes, profile semantics, proof semantics, or result meanings requires a new versioned protocol contract.
