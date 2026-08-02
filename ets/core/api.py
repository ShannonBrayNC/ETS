"""Supported ETS Core public API.

This module is the stable C1.1 consumer facade. Product, storage, hosting,
reporting, federation, and policy concerns remain outside this boundary.
"""

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.core.models import EvidenceEvent
from ets.core.profiles import ProfileKind, ProtocolProfile, list_profiles, resolve_profile
from ets.core.results import (
    VerificationReason,
    VerificationResult,
    VerificationStatus,
    VerifiedComponent,
)

# Public terminology follows the specification while preserving the registry's
# implementation-level resolve_profile name for compatibility.
get_profile = resolve_profile

__all__ = [
    "EvidenceEvent",
    "ProfileKind",
    "ProtocolProfile",
    "VerificationReason",
    "VerificationResult",
    "VerificationStatus",
    "VerifiedComponent",
    "canonical_sha256",
    "canonicalize",
    "get_profile",
    "list_profiles",
    "resolve_profile",
]
