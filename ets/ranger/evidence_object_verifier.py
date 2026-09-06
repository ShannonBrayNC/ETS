"""Reverse verification for Ranger-bearing ETS Evidence Object v1 records.

This verifier keeps cryptographic validity, epistemic state, decision-policy
participation, and semantic truth as separate result dimensions. A valid digest
or signature proves integrity/authenticity properties only; it does not prove
sensor truth, human identity, location truth, or policy sufficiency.
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from ets.evidence_object.canonical import object_hash
from ets.evidence_object.models import EvidenceObject
from ets.ranger.decision_event import decision_event_digest, verify_decision_event

_RANGER_EXTENSION_NAMESPACE = "org.lanternprotocol.ranger.decision-event.v0.1"
_RANGER_INTEGRITY_SCOPE = "ranger-decision-event-preimage"
_RANGER_INTEGRITY_PROFILE = "ets.ranger.decision-event.sha256.v0.1"


class RangerEvidenceVerificationError(ValueError):
    """Raised when an object cannot be interpreted as a Ranger Evidence Object."""


class RangerClaimFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    claim_id: str
    subject: str
    predicate: str
    epistemic_state: str
    participating: bool
    excluded: bool
    reason: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class RangerEvidenceObjectVerification(BaseModel):
    """Separated verification findings for one Ranger-bearing Evidence Object."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    ranger_event_present: bool
    ranger_event_digest_valid: bool
    ranger_integrity_binding_valid: bool
    ranger_signature_status: str
    outer_object_hash: str
    outer_object_hash_valid: bool | None
    mission_id: str
    ranger_id: str
    decision_id: str
    policy_id: str
    selected_action: str
    authorization_state: str | None = None
    participating_claim_ids: tuple[str, ...]
    excluded_claim_ids: tuple[str, ...]
    claim_findings: tuple[RangerClaimFinding, ...]
    truth_claim_supported: bool = False
    truth_claim_boundary: str = (
        "integrity_and_signature_verification_do_not_prove_sensor_identity_location_or_policy_truth"
    )


def verify_ranger_evidence_object(
    evidence: EvidenceObject,
    *,
    ranger_public_key_hex: str | None = None,
    expected_object_hash: str | None = None,
) -> RangerEvidenceObjectVerification:
    """Verify the embedded Ranger event and its outer ETS Evidence Object.

    ``expected_object_hash`` is optional because Evidence Object v1 does not store
    its own recursive hash inside the object. When supplied, it is compared with
    the independently recomputed outer object hash.

    ``ranger_public_key_hex`` is optional. If omitted, a present Ranger signature
    is reported as ``UNVERIFIED_NO_TRUSTED_KEY`` rather than accepted or rejected.
    """

    extension = evidence.extensions.get(_RANGER_EXTENSION_NAMESPACE)
    if not isinstance(extension, Mapping):
        raise RangerEvidenceVerificationError("Ranger decision-event extension is missing")
    event = extension.get("decision_event")
    if not isinstance(event, Mapping):
        raise RangerEvidenceVerificationError("Ranger decision_event extension is invalid")

    stored_digest = event.get("event_digest")
    digest_valid = isinstance(stored_digest, str) and decision_event_digest(event) == stored_digest

    binding = next(
        (
            item
            for item in evidence.integrity
            if item.scope == _RANGER_INTEGRITY_SCOPE
            and item.profile == _RANGER_INTEGRITY_PROFILE
        ),
        None,
    )
    binding_valid = bool(
        binding is not None
        and isinstance(stored_digest, str)
        and stored_digest.startswith("sha256:")
        and binding.digest == stored_digest.removeprefix("sha256:")
        and digest_valid
    )

    signature = event.get("signature")
    if signature is None:
        signature_status = "ABSENT"
    elif ranger_public_key_hex is None:
        signature_status = "UNVERIFIED_NO_TRUSTED_KEY"
    else:
        signature_status = (
            "VALID"
            if verify_decision_event(event, public_key_hex=ranger_public_key_hex)
            else "INVALID"
        )

    outer_hash = object_hash(evidence)
    outer_hash_valid = None if expected_object_hash is None else outer_hash == expected_object_hash

    decision = event.get("decision")
    if not isinstance(decision, Mapping):
        raise RangerEvidenceVerificationError("embedded Ranger decision is invalid")
    participating = _string_tuple(decision.get("participating_claim_ids", []), "participating_claim_ids")
    excluded = _string_tuple(decision.get("excluded_claim_ids", []), "excluded_claim_ids")

    findings: list[RangerClaimFinding] = []
    subjects = event.get("subject_context")
    if not isinstance(subjects, list):
        raise RangerEvidenceVerificationError("embedded subject_context is invalid")
    for subject in subjects:
        if not isinstance(subject, Mapping):
            raise RangerEvidenceVerificationError("embedded subject_context entry is invalid")
        subject_id = _required_string(subject, "subject_id")
        claims = subject.get("claims")
        if not isinstance(claims, list):
            raise RangerEvidenceVerificationError("embedded claims are invalid")
        for claim in claims:
            if not isinstance(claim, Mapping):
                raise RangerEvidenceVerificationError("embedded claim is invalid")
            claim_id = _required_string(claim, "claim_id")
            confidence = claim.get("confidence")
            if confidence is not None and not isinstance(confidence, int | float):
                raise RangerEvidenceVerificationError("claim confidence must be numeric or null")
            findings.append(
                RangerClaimFinding(
                    claim_id=claim_id,
                    subject=subject_id,
                    predicate=_required_string(claim, "kind"),
                    epistemic_state=_required_string(claim, "state"),
                    participating=claim_id in participating,
                    excluded=claim_id in excluded,
                    reason=claim.get("reason") if isinstance(claim.get("reason"), str) else None,
                    confidence=float(confidence) if confidence is not None else None,
                )
            )

    return RangerEvidenceObjectVerification(
        ranger_event_present=True,
        ranger_event_digest_valid=digest_valid,
        ranger_integrity_binding_valid=binding_valid,
        ranger_signature_status=signature_status,
        outer_object_hash=outer_hash,
        outer_object_hash_valid=outer_hash_valid,
        mission_id=_required_string(event, "mission_id"),
        ranger_id=_required_string(event, "ranger_id"),
        decision_id=_required_string(decision, "decision_id"),
        policy_id=_required_string(decision, "policy_id"),
        selected_action=_required_string(decision, "selected_action"),
        authorization_state=(
            decision.get("authorization_state")
            if isinstance(decision.get("authorization_state"), str)
            else None
        ),
        participating_claim_ids=participating,
        excluded_claim_ids=excluded,
        claim_findings=tuple(findings),
    )


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerEvidenceVerificationError(f"{field} must be a non-empty string")
    return result


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise RangerEvidenceVerificationError(f"{field} must be an array of strings")
    return tuple(value)


__all__ = [
    "RangerClaimFinding",
    "RangerEvidenceObjectVerification",
    "RangerEvidenceVerificationError",
    "verify_ranger_evidence_object",
]
