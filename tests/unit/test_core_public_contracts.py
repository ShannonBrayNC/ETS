from __future__ import annotations

import importlib
import sys

from ets.core import api
from ets.core.profiles import EVENT_RFC6962_V1

EXPECTED_PUBLIC_API = [
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


def test_supported_api_manifest_is_exact() -> None:
    assert api.__all__ == EXPECTED_PUBLIC_API


def test_public_api_excludes_product_and_persistent_storage_symbols() -> None:
    prohibited = {
        "SQLiteEventStore",
        "ArtifactRegistry",
        "FederationPolicy",
        "QuorumPolicy",
    }
    assert prohibited.isdisjoint(api.__all__)


def test_profile_lookup_aliases_are_consistent() -> None:
    assert api.get_profile(EVENT_RFC6962_V1.id) is EVENT_RFC6962_V1
    assert api.resolve_profile(EVENT_RFC6962_V1.id) is EVENT_RFC6962_V1


def test_public_api_import_does_not_load_product_frameworks() -> None:
    before = set(sys.modules)
    importlib.reload(api)
    loaded = set(sys.modules) - before

    forbidden_roots = {"fastapi", "starlette", "uvicorn", "azure", "sqlalchemy"}
    assert not ({name.split(".", 1)[0] for name in loaded} & forbidden_roots)
