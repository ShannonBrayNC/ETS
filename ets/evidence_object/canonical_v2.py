"""Canonical identity serialization for Evidence Object v2."""

from __future__ import annotations

from typing import Any

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.evidence_object.models_v2 import EvidenceObjectV2

EVIDENCE_OBJECT_V2_HASH_PROFILE = "ets.evidence-object.identity.canonical-json.sha256.v2"
EVIDENCE_OBJECT_V2_IDENTITY_FIELDS = (
    "schema_id",
    "identity",
    "created_at",
    "bindings",
    "policies",
    "privacy",
    "extensions",
)


def identity_payload(evidence: EvidenceObjectV2) -> dict[str, Any]:
    """Return the normative identity preimage.

    Proof material is intentionally excluded. Verifiers must bind identity to
    verification semantics through a committed ``verification`` binding when
    those semantics are identity-relevant.
    """

    payload = evidence.model_dump(mode="json", exclude_none=True)
    return {field: payload[field] for field in EVIDENCE_OBJECT_V2_IDENTITY_FIELDS}


def canonical_identity_bytes(evidence: EvidenceObjectV2) -> bytes:
    return canonicalize(identity_payload(evidence))


def identity_hash(evidence: EvidenceObjectV2) -> str:
    return canonical_sha256(identity_payload(evidence))
