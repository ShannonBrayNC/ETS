"""Adapt ETS Ranger Decision Event v0.1 into Evidence Object v1.

The adapter preserves the complete Ranger event under a namespaced extension while
also projecting its claims, mission/decision context, policy references, source
dependencies, and event digest into generic Evidence Object v1 structures.

The adapter verifies the Ranger event digest before projection. It does not prove
sensor truth, identity truth, policy sufficiency, or signer authority.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from ets.evidence_object.models import (
    Claim,
    EvidenceContext,
    EvidenceIdentity,
    EvidenceObject,
    IntegrityBinding,
    Provenance,
    Relationship,
    RelationshipType,
)
from ets.ranger.decision_event import decision_event_digest

_RANGER_EVENT_SCHEMA = "ranger.decision-event.v0.1"
_RANGER_EXTENSION_NAMESPACE = "org.lanternprotocol.ranger.decision-event.v0.1"
_RANGER_INTEGRITY_PROFILE = "ets.ranger.decision-event.sha256.v0.1"


class RangerEvidenceObjectAdapterError(ValueError):
    """Raised when a Ranger decision event cannot be projected safely."""


def ranger_decision_event_to_evidence_object(
    event: Mapping[str, Any],
) -> EvidenceObject:
    """Project a Ranger Decision Event into an immutable Evidence Object v1.

    The complete source event is retained under ``extensions`` so generic ETS
    normalization does not erase Ranger-specific epistemic semantics.
    """

    payload = dict(event)
    if payload.get("schema_version") != _RANGER_EVENT_SCHEMA:
        raise RangerEvidenceObjectAdapterError(
            f"schema_version must be {_RANGER_EVENT_SCHEMA}"
        )

    event_digest = payload.get("event_digest")
    if not isinstance(event_digest, str) or not event_digest.startswith("sha256:"):
        raise RangerEvidenceObjectAdapterError("signed/sealed event_digest is required")
    if decision_event_digest(payload) != event_digest:
        raise RangerEvidenceObjectAdapterError("Ranger decision event digest mismatch")

    event_id = _required_string(payload, "event_id")
    mission_id = _required_string(payload, "mission_id")
    ranger_id = _required_string(payload, "ranger_id")
    occurred_at = _required_datetime(payload, "occurred_at")

    decision = payload.get("decision")
    if not isinstance(decision, Mapping):
        raise RangerEvidenceObjectAdapterError("decision must be an object")
    decision_id = _required_string(decision, "decision_id")
    policy_id = _required_string(decision, "policy_id")

    claims: list[Claim] = []
    relationships: list[Relationship] = []
    seen_relationship_ids: set[str] = set()

    subject_context = payload.get("subject_context")
    if not isinstance(subject_context, list):
        raise RangerEvidenceObjectAdapterError("subject_context must be an array")

    for subject in subject_context:
        if not isinstance(subject, Mapping):
            raise RangerEvidenceObjectAdapterError("subject_context entries must be objects")
        subject_id = _required_string(subject, "subject_id")
        subject_claims = subject.get("claims")
        if not isinstance(subject_claims, list):
            raise RangerEvidenceObjectAdapterError("subject claims must be an array")
        for source_claim in subject_claims:
            if not isinstance(source_claim, Mapping):
                raise RangerEvidenceObjectAdapterError("claim entries must be objects")
            claim_id = _required_string(source_claim, "claim_id")
            kind = _required_string(source_claim, "kind")
            state = _required_string(source_claim, "state")
            source_refs = source_claim.get("source_refs", [])
            if not isinstance(source_refs, list) or not all(
                isinstance(item, str) and item for item in source_refs
            ):
                raise RangerEvidenceObjectAdapterError("claim source_refs must be strings")

            # Preserve epistemic state as part of the claim value rather than
            # upgrading UNKNOWN/INDETERMINATE/etc. into an asserted fact.
            normalized_value = {
                "epistemic_state": state,
                "value": source_claim.get("value"),
                "threshold": source_claim.get("threshold"),
                "mechanism": source_claim.get("mechanism"),
                "reason": source_claim.get("reason"),
                "contradicts_claim_ids": source_claim.get("contradicts_claim_ids", []),
            }
            claims.append(
                Claim(
                    claim_id=claim_id,
                    subject=subject_id,
                    predicate=kind,
                    value=normalized_value,
                    confidence=source_claim.get("confidence"),
                    source_ref=source_refs[0] if len(source_refs) == 1 else None,
                )
            )

            for source_ref in source_refs:
                relationship_id = f"rel:{claim_id}:depends_on:{source_ref}"
                if relationship_id in seen_relationship_ids:
                    continue
                seen_relationship_ids.add(relationship_id)
                relationships.append(
                    Relationship(
                        relationship_id=relationship_id,
                        relationship_type=RelationshipType.DEPENDS_ON,
                        target_evidence_ref=source_ref,
                        observed=True,
                        confidence=None,
                    )
                )

    contexts = (
        EvidenceContext(
            context_type="ranger-mission",
            context_ref=mission_id,
            attributes={"ranger_id": ranger_id},
        ),
        EvidenceContext(
            context_type="ranger-decision",
            context_ref=decision_id,
            attributes={
                "selected_action": decision.get("selected_action"),
                "authorization_state": decision.get("authorization_state"),
                "participating_claim_ids": decision.get("participating_claim_ids", []),
                "excluded_claim_ids": decision.get("excluded_claim_ids", []),
                "previous_event_digest": payload.get("previous_event_digest"),
            },
        ),
    )

    return EvidenceObject(
        identity=EvidenceIdentity(
            evidence_id=event_id,
            version=1,
            namespace=f"urn:lantern:ranger:mission:{mission_id}",
            evidence_type="ranger-decision-event",
        ),
        created_at=occurred_at,
        claims=tuple(claims),
        provenance=Provenance(
            collected_by=ranger_id,
            source_system="ets-ranger",
            device_ref=ranger_id,
            workflow_ref=decision_id,
        ),
        contexts=contexts,
        relationships=tuple(relationships),
        integrity=(
            IntegrityBinding(
                digest=event_digest.removeprefix("sha256:"),
                scope="ranger-decision-event-preimage",
                profile=_RANGER_INTEGRITY_PROFILE,
            ),
        ),
        policy_refs=(policy_id,),
        extensions={
            _RANGER_EXTENSION_NAMESPACE: {
                "included_in_object_hash": True,
                "decision_event": payload,
            }
        },
    )


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerEvidenceObjectAdapterError(f"{field} must be a non-empty string")
    return result


def _required_datetime(value: Mapping[str, Any], field: str) -> datetime:
    raw = _required_string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RangerEvidenceObjectAdapterError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RangerEvidenceObjectAdapterError(f"{field} must be timezone-aware")
    return parsed


__all__ = [
    "RangerEvidenceObjectAdapterError",
    "ranger_decision_event_to_evidence_object",
]
