"""Supported ETS Core public API.

This facade is intentionally small. Existing imports from ``ets.core`` remain a
compatibility surface until the C4 package transition.
"""

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.core.errors import (
    CanonicalizationError,
    DuplicateKeyError,
    ETSError,
    InternalInvariantError,
    NonFiniteNumberError,
    ProfileConflictError,
    ProfileError,
    ProtocolModelError,
    ResourceLimitError,
    SignatureBackendError,
    UnknownProfileError,
    UnsupportedValueError,
    VerificationOnlyProfileError,
)
from ets.core.models import EvidenceEvent
from ets.core.profiles import (
    ALPHA_UNPREFIXED_MERKLE_V1,
    CANONICAL_JSON_V1,
    ED25519_V1,
    EVENT_ALPHA_UNPREFIXED_V1,
    EVENT_RFC6962_V1,
    PROFILES,
    RFC6962_MERKLE_V1,
    SHA256_V1,
    ProfileKind,
    ProtocolProfile,
    resolve_profile,
)
from ets.core.results import (
    VerificationReason,
    VerificationResult,
    VerificationStatus,
    VerifiedComponent,
)

__all__ = [
    "ALPHA_UNPREFIXED_MERKLE_V1",
    "CANONICAL_JSON_V1",
    "CanonicalizationError",
    "DuplicateKeyError",
    "ED25519_V1",
    "ETSError",
    "EVENT_ALPHA_UNPREFIXED_V1",
    "EVENT_RFC6962_V1",
    "EvidenceEvent",
    "InternalInvariantError",
    "NonFiniteNumberError",
    "PROFILES",
    "ProfileConflictError",
    "ProfileError",
    "ProfileKind",
    "ProtocolModelError",
    "ProtocolProfile",
    "RFC6962_MERKLE_V1",
    "ResourceLimitError",
    "SHA256_V1",
    "SignatureBackendError",
    "UnknownProfileError",
    "UnsupportedValueError",
    "VerificationOnlyProfileError",
    "VerificationReason",
    "VerificationResult",
    "VerificationStatus",
    "VerifiedComponent",
    "canonical_sha256",
    "canonicalize",
    "resolve_profile",
]
