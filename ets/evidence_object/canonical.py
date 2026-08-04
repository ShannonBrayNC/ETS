"""Canonical serialization and hashing for Evidence Object v1."""

from __future__ import annotations

from typing import Any

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.evidence_object.models import EvidenceObject

EVIDENCE_OBJECT_HASH_PROFILE = "ets.evidence-object.canonical-json.sha256.v1"


def hashable_payload(evidence: EvidenceObject) -> dict[str, Any]:
    """Return the normative Evidence Object hash preimage.

    The object hash excludes no normative fields in v1. Transport envelopes,
    server receipts, Merkle proofs, and registry metadata must remain outside
    the EvidenceObject model and therefore outside this preimage.
    """

    return evidence.model_dump(mode="json", exclude_none=True)


def canonical_bytes(evidence: EvidenceObject) -> bytes:
    """Return deterministic UTF-8 JSON bytes for an Evidence Object."""

    return canonicalize(hashable_payload(evidence))


def object_hash(evidence: EvidenceObject) -> str:
    """Return the SHA-256 digest for the canonical Evidence Object payload."""

    return canonical_sha256(hashable_payload(evidence))
