"""Mission-chain verification for Ranger Decision Events carried by ETS Evidence Objects.

The chain verifier validates predecessor linkage and preserves epistemic state over time.
It proves ordering and integrity properties only; it does not prove sensor truth, identity
truth, policy correctness, or completeness of the mission record.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from ets.evidence_object.models import EvidenceObject
from ets.ranger.evidence_object_verifier import (
    RangerEvidenceObjectVerification,
    verify_ranger_evidence_object,
)


class RangerMissionChainError(ValueError):
    """Raised when a Ranger mission chain cannot be interpreted safely."""


class RangerEpistemicTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    subject: str
    predicate: str
    from_state: str | None
    to_state: str
    event_id: str
    decision_id: str
    selected_action: str


class RangerMissionEventFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    index: int
    event_id: str
    event_digest: str
    previous_event_digest: str | None
    predecessor_link_valid: bool
    event_verification: RangerEvidenceObjectVerification


class RangerMissionChainVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    valid_chain: bool
    mission_id: str
    ranger_id: str
    event_count: int
    first_event_digest: str
    head_event_digest: str
    event_findings: tuple[RangerMissionEventFinding, ...]
    epistemic_transitions: tuple[RangerEpistemicTransition, ...]
    complete_capture_proven: bool = False
    truth_claim_supported: bool = False
    claim_boundary: str = (
        "chain_integrity_and_epistemic_history_do_not_prove_complete_capture_or_semantic_truth"
    )


def verify_ranger_mission_chain(
    evidence_objects: Iterable[EvidenceObject],
    *,
    ranger_public_key_hex: str | None = None,
) -> RangerMissionChainVerification:
    """Verify an ordered sequence of Ranger-bearing Evidence Objects.

    The first event MUST have ``previous_event_digest`` equal to ``None``. Each later
    event MUST reference the immediately preceding event digest. All events MUST share
    the same mission and Ranger identity.
    """

    objects = list(evidence_objects)
    if not objects:
        raise RangerMissionChainError("mission chain must contain at least one event")

    findings: list[RangerMissionEventFinding] = []
    transitions: list[RangerEpistemicTransition] = []
    previous_digest: str | None = None
    mission_id: str | None = None
    ranger_id: str | None = None
    latest_states: dict[tuple[str, str], str] = {}
    valid_chain = True

    for index, evidence in enumerate(objects):
        verification = verify_ranger_evidence_object(
            evidence,
            ranger_public_key_hex=ranger_public_key_hex,
        )
        event = _embedded_event(evidence)
        event_id = _required_string(event, "event_id")
        event_digest = _required_string(event, "event_digest")
        predecessor = event.get("previous_event_digest")
        if predecessor is not None and not isinstance(predecessor, str):
            raise RangerMissionChainError("previous_event_digest must be string or null")

        if index == 0:
            predecessor_valid = predecessor is None
        else:
            predecessor_valid = predecessor == previous_digest

        if not predecessor_valid:
            valid_chain = False
        if (
            not verification.ranger_event_digest_valid
            or not verification.ranger_integrity_binding_valid
        ):
            valid_chain = False
        if ranger_public_key_hex is not None and verification.ranger_signature_status != "VALID":
            valid_chain = False

        if mission_id is None:
            mission_id = verification.mission_id
            ranger_id = verification.ranger_id
        elif verification.mission_id != mission_id or verification.ranger_id != ranger_id:
            valid_chain = False

        findings.append(
            RangerMissionEventFinding(
                index=index,
                event_id=event_id,
                event_digest=event_digest,
                previous_event_digest=predecessor,
                predecessor_link_valid=predecessor_valid,
                event_verification=verification,
            )
        )

        for claim in verification.claim_findings:
            key = (claim.subject, claim.predicate)
            prior = latest_states.get(key)
            if prior != claim.epistemic_state:
                transitions.append(
                    RangerEpistemicTransition(
                        subject=claim.subject,
                        predicate=claim.predicate,
                        from_state=prior,
                        to_state=claim.epistemic_state,
                        event_id=event_id,
                        decision_id=verification.decision_id,
                        selected_action=verification.selected_action,
                    )
                )
                latest_states[key] = claim.epistemic_state

        previous_digest = event_digest

    assert mission_id is not None and ranger_id is not None and previous_digest is not None
    return RangerMissionChainVerification(
        valid_chain=valid_chain,
        mission_id=mission_id,
        ranger_id=ranger_id,
        event_count=len(findings),
        first_event_digest=findings[0].event_digest,
        head_event_digest=previous_digest,
        event_findings=tuple(findings),
        epistemic_transitions=tuple(transitions),
    )


def _embedded_event(evidence: EvidenceObject) -> dict[str, object]:
    namespace = "org.lanternprotocol.ranger.decision-event.v0.1"
    extension = evidence.extensions.get(namespace)
    if not isinstance(extension, dict):
        raise RangerMissionChainError("Ranger decision-event extension is missing")
    event = extension.get("decision_event")
    if not isinstance(event, dict):
        raise RangerMissionChainError("Ranger decision_event extension is invalid")
    return event


def _required_string(value: dict[str, object], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerMissionChainError(f"{field} must be a non-empty string")
    return result


__all__ = [
    "RangerEpistemicTransition",
    "RangerMissionChainError",
    "RangerMissionChainVerification",
    "RangerMissionEventFinding",
    "verify_ranger_mission_chain",
]
