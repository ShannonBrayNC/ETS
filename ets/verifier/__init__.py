"""SDK helpers for verifying ETS events and inclusion proofs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ets.core import EvidenceEvent, InclusionProof, VerificationResult, canonical_sha256
from ets.core.proofs import verify_inclusion_proof


@dataclass(frozen=True)
class EventHashVerificationResult:
    """Result of comparing an event contract with an expected event hash."""

    valid: bool
    event_hash: str
    expected_event_hash: str
    reason: str


def compute_event_hash(event: EvidenceEvent | Mapping[str, Any]) -> str:
    """Return the canonical ETS event hash for an event object or JSON mapping."""

    parsed_event = _parse_event(event)
    return canonical_sha256(parsed_event.hashable_payload())


def verify_event_hash(
    event: EvidenceEvent | Mapping[str, Any],
    expected_event_hash: str,
) -> EventHashVerificationResult:
    """Verify that an event matches an expected canonical SHA-256 event hash."""

    event_hash = compute_event_hash(event)
    valid = event_hash == expected_event_hash
    return EventHashVerificationResult(
        valid=valid,
        event_hash=event_hash,
        expected_event_hash=expected_event_hash,
        reason="ok" if valid else "event hash does not match expected hash",
    )


def verify_inclusion(
    proof: InclusionProof | Mapping[str, Any],
) -> VerificationResult:
    """Verify a self-contained ETS inclusion proof."""

    parsed_proof = _parse_proof(proof)
    return verify_inclusion_proof(parsed_proof)


def _parse_event(event: EvidenceEvent | Mapping[str, Any]) -> EvidenceEvent:
    if isinstance(event, EvidenceEvent):
        return event
    try:
        return EvidenceEvent.model_validate(event)
    except ValidationError:
        return EvidenceEvent.model_validate_json(json.dumps(event))


def _parse_proof(proof: InclusionProof | Mapping[str, Any]) -> InclusionProof:
    if isinstance(proof, InclusionProof):
        return proof
    try:
        return InclusionProof.model_validate(proof)
    except ValidationError:
        return InclusionProof.model_validate_json(json.dumps(proof))


__all__ = [
    "EventHashVerificationResult",
    "compute_event_hash",
    "verify_event_hash",
    "verify_inclusion",
]
