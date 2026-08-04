"""Deterministic checks for the published ETS Core C1.5 vector set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.core.merkle import merkle_root
from ets.core.results import VerificationReason, VerificationStatus

VECTOR_FILE = Path(__file__).resolve().parents[2] / "vectors/core/v1/c1_5_vectors.json"


def _vectors() -> dict[str, object]:
    return json.loads(VECTOR_FILE.read_text(encoding="utf-8"))


def test_vector_metadata_is_versioned() -> None:
    vectors = _vectors()
    assert vectors["schema_version"] == "ets.conformance.v1"
    assert vectors["vector_set"] == "ets-core-c1.5-2026.1"
    assert vectors["source_profile"] == "ets.protocol.event.v1.rfc6962-sha256"


def test_canonicalization_vectors_are_byte_exact() -> None:
    for vector in _vectors()["canonicalization"]:
        canonical = canonicalize(vector["input"])
        assert canonical.hex() == vector["canonical_hex"], vector["id"]
        assert canonical_sha256(vector["input"]) == vector["sha256"], vector["id"]


def test_event_hash_vector_is_byte_exact() -> None:
    for vector in _vectors()["event_hashes"]:
        canonical = canonicalize(vector["payload"])
        assert canonical.hex() == vector["canonical_hex"], vector["id"]
        assert hashlib.sha256(canonical).hexdigest() == vector["event_hash"], vector["id"]


def test_rfc6962_root_vectors_match_reference_implementation() -> None:
    for vector in _vectors()["merkle_roots"]:
        assert len(vector["leaf_hashes"]) == vector["tree_size"]
        assert merkle_root(vector["leaf_hashes"]) == vector["root_hash"]


def test_negative_vectors_use_closed_status_and_reason_sets() -> None:
    allowed_statuses = {status.value for status in VerificationStatus}
    allowed_reasons = {reason.value for reason in VerificationReason}
    identifiers: set[str] = set()

    for vector in _vectors()["negative"]:
        assert vector["id"] not in identifiers
        identifiers.add(vector["id"])
        assert vector["expected_status"] in allowed_statuses
        assert vector["expected_reason"] in allowed_reasons


def test_legacy_and_consistency_claims_are_bounded() -> None:
    compatibility = _vectors()["compatibility"]
    legacy = compatibility["legacy_alpha"]
    consistency = compatibility["consistency_proof"]

    assert legacy["verification_allowed"] is True
    assert legacy["generation_allowed"] is False
    assert consistency == {
        "follow_up_issue": 194,
        "rfc6962_compact": False,
        "status": "alpha-linear-witness",
    }
