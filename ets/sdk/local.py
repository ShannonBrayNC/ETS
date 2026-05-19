"""Small local SDK facade over the canonical ETS core."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from ets.core import (
    EventStore,
    EvidenceEvent,
    InclusionProof,
    LogEntry,
    VerificationResult,
    canonical_sha256,
    generate_inclusion_proof,
)
from ets.core.proofs import verify_inclusion_proof as core_verify_inclusion_proof
from ets.verifier import EventHashVerificationResult, verify_event_hash


def create_evidence(data: EvidenceEvent | Mapping[str, Any]) -> EvidenceEvent:
    """Create a validated EvidenceEvent from a model or JSON-native mapping."""

    if isinstance(data, EvidenceEvent):
        return data
    normalized = dict(data)
    if "created_at_utc" not in normalized:
        normalized["created_at_utc"] = datetime.now(UTC)
    return EvidenceEvent.model_validate(normalized)


def hash_evidence(evidence: EvidenceEvent | Mapping[str, Any]) -> str:
    """Return the canonical ETS event hash."""

    event = create_evidence(evidence)
    return canonical_sha256(event.hashable_payload())


def verify_evidence(
    evidence: EvidenceEvent | Mapping[str, Any],
    expected_event_hash: str,
) -> EventHashVerificationResult:
    """Verify evidence against an expected canonical event hash."""

    return verify_event_hash(create_evidence(evidence), expected_event_hash)


def append_evidence(store: EventStore, evidence: EvidenceEvent | Mapping[str, Any]) -> LogEntry:
    """Append evidence through a configured ETS event store."""

    return store.append(create_evidence(evidence))


def get_inclusion_proof(store: EventStore, event_id: str) -> InclusionProof:
    """Fetch a self-contained inclusion proof for an event in a local store."""

    entry = store.get_by_event_id(event_id)
    return generate_inclusion_proof(store.list_entries(), entry.log_index)


def verify_inclusion_proof(proof: InclusionProof | Mapping[str, Any]) -> VerificationResult:
    """Verify an inclusion proof without an API connection."""

    parsed = proof if isinstance(proof, InclusionProof) else InclusionProof.model_validate(proof)
    return core_verify_inclusion_proof(parsed)
