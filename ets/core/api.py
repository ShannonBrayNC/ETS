"""Supported ETS Core public API.

This module is the stable consumer facade. Product, storage, hosting,
reporting, federation, and policy concerns remain outside this boundary.
"""

from ets.core.bundle import EvidenceProofBundle
from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.core.log import (
    DuplicateEventError,
    EventNotFoundError,
    InMemoryAppendOnlyLog,
    LogEntry,
)
from ets.core.merkle import leaf_hash_for_event_hash, merkle_root
from ets.core.models import EvidenceEvent
from ets.core.profiles import ProfileKind, ProtocolProfile, list_profiles, resolve_profile
from ets.core.proofs import (
    InclusionProof,
    generate_inclusion_proof,
    verify_inclusion_proof,
)
from ets.core.results import (
    VerificationReason,
    VerificationResult,
    VerificationStatus,
    VerifiedComponent,
)
from ets.core.tree_head import SignedTreeHead

# Public terminology follows the specification while preserving the registry's
# implementation-level resolve_profile name for compatibility.
get_profile = resolve_profile

__all__ = [
    "DuplicateEventError",
    "EventNotFoundError",
    "EvidenceEvent",
    "EvidenceProofBundle",
    "InMemoryAppendOnlyLog",
    "InclusionProof",
    "LogEntry",
    "ProfileKind",
    "ProtocolProfile",
    "SignedTreeHead",
    "VerificationReason",
    "VerificationResult",
    "VerificationStatus",
    "VerifiedComponent",
    "canonical_sha256",
    "canonicalize",
    "generate_inclusion_proof",
    "get_profile",
    "leaf_hash_for_event_hash",
    "list_profiles",
    "merkle_root",
    "resolve_profile",
    "verify_inclusion_proof",
]
