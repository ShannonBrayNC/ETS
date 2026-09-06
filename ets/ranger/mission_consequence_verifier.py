"""Mission-wide Ranger consequence reconstruction.

Combines mission-chain integrity/epistemic history with per-event cyber-physical
consequence verification. The result identifies the earliest event where the supplied
mission record becomes unsupported, contradicted, degraded, or incomplete without
retroactively rewriting earlier epistemic state.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from ets.evidence_object.models import EvidenceObject
from ets.ranger.consequence_verifier import (
    RangerConsequenceVerification,
    verify_ranger_consequence,
)
from ets.ranger.mission_chain_verifier import (
    RangerMissionChainVerification,
    verify_ranger_mission_chain,
)


class RangerMissionConsequenceError(ValueError):
    """Raised when mission consequence evidence cannot be reconstructed safely."""


class RangerMissionConsequenceEventFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    index: int
    event_id: str
    decision_id: str
    selected_action: str
    predecessor_link_valid: bool
    event_integrity_valid: bool
    consequence_status: str
    capability_limitations: tuple[str, ...]
    epistemic_states: tuple[str, ...]
    consequence: RangerConsequenceVerification


class RangerMissionConsequenceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mission_id: str
    ranger_id: str
    event_count: int
    valid_chain: bool
    overall_status: str
    first_problem_event_index: int | None
    first_problem_event_id: str | None
    event_findings: tuple[RangerMissionConsequenceEventFinding, ...]
    chain_verification: RangerMissionChainVerification
    complete_capture_proven: bool = False
    truth_claim_supported: bool = False
    temporal_epistemic_conservation_preserved: bool = True
    claim_boundary: str = (
        "mission_reconstruction_supports_only_the_supplied_evidence_chain_and_does_not_prove_complete_capture_or_external_truth"
    )


def verify_ranger_mission_consequences(
    evidence_objects: Iterable[EvidenceObject],
    *,
    ranger_public_key_hex: str | None = None,
) -> RangerMissionConsequenceVerification:
    """Verify mission ordering, epistemic state, and physical consequence per event."""

    objects = list(evidence_objects)
    if not objects:
        raise RangerMissionConsequenceError("mission must contain at least one Ranger Evidence Object")

    chain = verify_ranger_mission_chain(
        objects,
        ranger_public_key_hex=ranger_public_key_hex,
    )

    findings: list[RangerMissionConsequenceEventFinding] = []
    first_problem_index: int | None = None
    first_problem_event_id: str | None = None
    statuses: list[str] = []

    for chain_finding, evidence in zip(chain.event_findings, objects, strict=True):
        consequence = verify_ranger_consequence(evidence)
        statuses.append(consequence.overall_status)
        integrity_valid = (
            chain_finding.event_verification.ranger_event_digest_valid
            and chain_finding.event_verification.ranger_integrity_binding_valid
        )
        epistemic_states = tuple(
            finding.epistemic_state
            for finding in chain_finding.event_verification.claim_findings
        )
        finding = RangerMissionConsequenceEventFinding(
            index=chain_finding.index,
            event_id=chain_finding.event_id,
            decision_id=chain_finding.event_verification.decision_id,
            selected_action=chain_finding.event_verification.selected_action,
            predecessor_link_valid=chain_finding.predecessor_link_valid,
            event_integrity_valid=integrity_valid,
            consequence_status=consequence.overall_status,
            capability_limitations=consequence.capability_limitations,
            epistemic_states=epistemic_states,
            consequence=consequence,
        )
        findings.append(finding)

        event_problem = (
            not chain_finding.predecessor_link_valid
            or not integrity_valid
            or consequence.overall_status != "SUPPORTED"
        )
        if event_problem and first_problem_index is None:
            first_problem_index = chain_finding.index
            first_problem_event_id = chain_finding.event_id

    if not chain.valid_chain:
        overall = "CHAIN_INVALID"
    elif any(status == "CONTRADICTED" for status in statuses):
        overall = "CONTRADICTED"
    elif any(status == "INDETERMINATE" for status in statuses):
        overall = "INDETERMINATE"
    elif any(status in {"NOT_OBSERVED", "NOT_AVAILABLE"} for status in statuses):
        overall = "INCOMPLETE"
    elif statuses and all(status == "SUPPORTED" for status in statuses):
        overall = "SUPPORTED"
    else:
        overall = "INDETERMINATE"

    return RangerMissionConsequenceVerification(
        mission_id=chain.mission_id,
        ranger_id=chain.ranger_id,
        event_count=chain.event_count,
        valid_chain=chain.valid_chain,
        overall_status=overall,
        first_problem_event_index=first_problem_index,
        first_problem_event_id=first_problem_event_id,
        event_findings=tuple(findings),
        chain_verification=chain,
    )


__all__ = [
    "RangerMissionConsequenceError",
    "RangerMissionConsequenceEventFinding",
    "RangerMissionConsequenceVerification",
    "verify_ranger_mission_consequences",
]
