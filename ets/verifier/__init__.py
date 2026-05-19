"""SDK helpers for verifying ETS events and inclusion proofs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ets.core import (
    ConsistencyProof,
    EvidenceEvent,
    EvidenceProofBundle,
    InclusionProof,
    SignedTreeHead,
    VerificationResult,
    canonical_sha256,
)
from ets.core.proofs import verify_consistency_proof, verify_inclusion_proof


@dataclass(frozen=True)
class EventHashVerificationResult:
    """Result of comparing an event contract with an expected event hash."""

    valid: bool
    event_hash: str
    expected_event_hash: str
    reason: str


@dataclass(frozen=True)
class TreeHeadComparisonResult:
    """Result of comparing a previously trusted tree head with a newer one."""

    valid: bool
    reason: str
    log_id: str | None
    previous_tree_size: int
    latest_tree_size: int
    previous_root_hash: str
    latest_root_hash: str


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


def verify_consistency(
    proof: ConsistencyProof | Mapping[str, Any],
) -> VerificationResult:
    """Verify a self-contained ETS consistency proof."""

    parsed_proof = _parse_consistency_proof(proof)
    return verify_consistency_proof(parsed_proof)


def verify_bundle(bundle: EvidenceProofBundle | Mapping[str, Any]) -> VerificationResult:
    """Verify an ETS evidence proof bundle offline."""

    parsed_bundle = _parse_bundle(bundle)
    event_hash = compute_event_hash(parsed_bundle.event)
    if event_hash != parsed_bundle.event_hash:
        return VerificationResult(
            valid=False,
            reason="bundle event hash does not match event",
            root_hash=parsed_bundle.inclusion_proof.root_hash,
            leaf_hash=parsed_bundle.leaf_hash,
            tree_size=parsed_bundle.inclusion_proof.tree_size,
            verified_at_utc=parsed_bundle.verification_result.verified_at_utc,
        )
    proof_result = verify_inclusion_proof(parsed_bundle.inclusion_proof)
    if not proof_result.valid:
        return proof_result
    if parsed_bundle.tree_head.root_hash != parsed_bundle.inclusion_proof.root_hash:
        return VerificationResult(
            valid=False,
            reason="bundle tree head root does not match inclusion proof root",
            root_hash=parsed_bundle.tree_head.root_hash,
            leaf_hash=parsed_bundle.leaf_hash,
            tree_size=parsed_bundle.tree_head.tree_size,
            verified_at_utc=proof_result.verified_at_utc,
        )
    return proof_result


def compare_tree_heads(
    previous: SignedTreeHead | Mapping[str, Any],
    latest: SignedTreeHead | Mapping[str, Any],
) -> TreeHeadComparisonResult:
    """Compare tree heads for rollback, equivocation, and clock regressions.

    This is a local checkpoint sanity check. It does not replace a future
    cryptographic consistency proof for append-only growth between roots.
    """

    previous_head = _parse_tree_head(previous)
    latest_head = _parse_tree_head(latest)

    if previous_head.log_id != latest_head.log_id:
        return _tree_head_result(previous_head, latest_head, False, "log IDs do not match")

    if latest_head.tree_size < previous_head.tree_size:
        return _tree_head_result(previous_head, latest_head, False, "tree size regressed")

    if latest_head.created_at_utc < previous_head.created_at_utc:
        return _tree_head_result(previous_head, latest_head, False, "tree head timestamp regressed")

    if latest_head.tree_size == previous_head.tree_size:
        if latest_head.root_hash != previous_head.root_hash:
            return _tree_head_result(
                previous_head,
                latest_head,
                False,
                "same tree size has different roots",
            )
        return _tree_head_result(previous_head, latest_head, True, "ok")

    if latest_head.root_hash == previous_head.root_hash:
        return _tree_head_result(
            previous_head,
            latest_head,
            False,
            "tree size advanced without a root change",
        )

    return _tree_head_result(previous_head, latest_head, True, "tree size advanced")


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


def _parse_consistency_proof(
    proof: ConsistencyProof | Mapping[str, Any],
) -> ConsistencyProof:
    if isinstance(proof, ConsistencyProof):
        return proof
    try:
        return ConsistencyProof.model_validate(proof)
    except ValidationError:
        return ConsistencyProof.model_validate_json(json.dumps(proof))


def _parse_bundle(bundle: EvidenceProofBundle | Mapping[str, Any]) -> EvidenceProofBundle:
    if isinstance(bundle, EvidenceProofBundle):
        return bundle
    try:
        return EvidenceProofBundle.model_validate(bundle)
    except ValidationError:
        return EvidenceProofBundle.model_validate_json(json.dumps(bundle))


def _parse_tree_head(tree_head: SignedTreeHead | Mapping[str, Any]) -> SignedTreeHead:
    if isinstance(tree_head, SignedTreeHead):
        return tree_head
    try:
        return SignedTreeHead.model_validate(tree_head)
    except ValidationError:
        return SignedTreeHead.model_validate_json(json.dumps(tree_head))


def _tree_head_result(
    previous: SignedTreeHead,
    latest: SignedTreeHead,
    valid: bool,
    reason: str,
) -> TreeHeadComparisonResult:
    return TreeHeadComparisonResult(
        valid=valid,
        reason=reason,
        log_id=previous.log_id if previous.log_id == latest.log_id else None,
        previous_tree_size=previous.tree_size,
        latest_tree_size=latest.tree_size,
        previous_root_hash=previous.root_hash,
        latest_root_hash=latest.root_hash,
    )


__all__ = [
    "EventHashVerificationResult",
    "TreeHeadComparisonResult",
    "compare_tree_heads",
    "compute_event_hash",
    "verify_event_hash",
    "verify_consistency",
    "verify_bundle",
    "verify_inclusion",
]
