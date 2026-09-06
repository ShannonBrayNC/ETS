"""Mission-wide Ranger consequence reconstruction.

Combines mission-chain integrity/epistemic history, per-event cyber-physical consequence
verification, and optional source-artifact digest resolution. Source verification is kept
separate from consequence support so missing bytes do not erase what the remaining record
can establish, while the mission result still surfaces the earliest evidentiary gap.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

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
from ets.ranger.source_evidence_verifier import (
    RangerSourceEvidenceVerification,
    verify_ranger_source_evidence,
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
    source_evidence_status: str
    capability_limitations: tuple[str, ...]
    epistemic_states: tuple[str, ...]
    consequence: RangerConsequenceVerification
    source_evidence: RangerSourceEvidenceVerification | None = None


class RangerMissionConsequenceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mission_id: str
    ranger_id: str
    event_count: int
    valid_chain: bool
    overall_status: str
    first_problem_event_index: int | None
    first_problem_event_id: str | None
    source_evidence_verification_requested: bool
    source_verified_event_count: int
    source_incomplete_event_count: int
    source_digest_mismatch_event_count: int
    event_findings: tuple[RangerMissionConsequenceEventFinding, ...]
    chain_verification: RangerMissionChainVerification
    complete_capture_proven: bool = False
    truth_claim_supported: bool = False
    temporal_epistemic_conservation_preserved: bool = True
    claim_boundary: str = (
        "mission_reconstruction_supports_only_the_supplied_evidence_chain_and_source_bytes_and_does_not_prove_complete_capture_or_external_truth"
    )


def verify_ranger_mission_consequences(
    evidence_objects: Iterable[EvidenceObject],
    *,
    ranger_public_key_hex: str | None = None,
    artifacts: Mapping[str, bytes] | None = None,
) -> RangerMissionConsequenceVerification:
    """Verify mission ordering, epistemic state, physical consequence, and optional sources.

    When ``artifacts`` is supplied, every event's declared source-evidence references are
    resolved independently by evidence ID. A digest mismatch is stronger than a missing
    artifact and is surfaced at mission level. Missing source bytes make verification
    incomplete; they are never interpreted as proof that the underlying observation did
    not occur. Omitting ``artifacts`` leaves source verification ``NOT_REQUESTED`` and
    preserves the pre-existing chain/consequence-only behavior.
    """

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
    consequence_statuses: list[str] = []
    source_statuses: list[str] = []

    for chain_finding, evidence in zip(chain.event_findings, objects, strict=True):
        consequence = verify_ranger_consequence(evidence)
        consequence_statuses.append(consequence.overall_status)
        integrity_valid = (
            chain_finding.event_verification.ranger_event_digest_valid
            and chain_finding.event_verification.ranger_integrity_binding_valid
        )
        epistemic_states = tuple(
            finding.epistemic_state
            for finding in chain_finding.event_verification.claim_findings
        )

        source_evidence: RangerSourceEvidenceVerification | None = None
        if artifacts is None:
            source_status = "NOT_REQUESTED"
        else:
            source_evidence = verify_ranger_source_evidence(evidence, artifacts=artifacts)
            source_status = source_evidence.overall_status
            source_statuses.append(source_status)

        finding = RangerMissionConsequenceEventFinding(
            index=chain_finding.index,
            event_id=chain_finding.event_id,
            decision_id=chain_finding.event_verification.decision_id,
            selected_action=chain_finding.event_verification.selected_action,
            predecessor_link_valid=chain_finding.predecessor_link_valid,
            event_integrity_valid=integrity_valid,
            consequence_status=consequence.overall_status,
            source_evidence_status=source_status,
            capability_limitations=consequence.capability_limitations,
            epistemic_states=epistemic_states,
            consequence=consequence,
            source_evidence=source_evidence,
        )
        findings.append(finding)

        source_problem = source_status not in {"NOT_REQUESTED", "VERIFIED"}
        event_problem = (
            not chain_finding.predecessor_link_valid
            or not integrity_valid
            or consequence.overall_status != "SUPPORTED"
            or source_problem
        )
        if event_problem and first_problem_index is None:
            first_problem_index = chain_finding.index
            first_problem_event_id = chain_finding.event_id

    if not chain.valid_chain:
        overall = "CHAIN_INVALID"
    elif "DIGEST_MISMATCH" in source_statuses:
        overall = "DIGEST_MISMATCH"
    elif any(status == "CONTRADICTED" for status in consequence_statuses):
        overall = "CONTRADICTED"
    elif any(status == "INDETERMINATE" for status in consequence_statuses):
        overall = "INDETERMINATE"
    elif "INDETERMINATE" in source_statuses:
        overall = "INDETERMINATE"
    elif any(status in {"NOT_OBSERVED", "NOT_AVAILABLE"} for status in consequence_statuses):
        overall = "INCOMPLETE"
    elif "INCOMPLETE" in source_statuses:
        overall = "INCOMPLETE"
    elif consequence_statuses and all(status == "SUPPORTED" for status in consequence_statuses):
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
        source_evidence_verification_requested=artifacts is not None,
        source_verified_event_count=sum(status == "VERIFIED" for status in source_statuses),
        source_incomplete_event_count=sum(status == "INCOMPLETE" for status in source_statuses),
        source_digest_mismatch_event_count=sum(status == "DIGEST_MISMATCH" for status in source_statuses),
        event_findings=tuple(findings),
        chain_verification=chain,
    )


__all__ = [
    "RangerMissionConsequenceError",
    "RangerMissionConsequenceEventFinding",
    "RangerMissionConsequenceVerification",
    "verify_ranger_mission_consequences",
]
