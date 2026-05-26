"""Deterministic human-governance escalation semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GovernanceSignal(StrEnum):
    PROOF_VALID = "proof_valid"
    PROOF_INVALID = "proof_invalid"
    FORK_SUSPECTED = "fork_suspected"
    OMISSION_SUSPECTED = "omission_suspected"
    POLICY_OVERRIDE_REQUESTED = "policy_override_requested"
    LEGAL_HOLD = "legal_hold"


@dataclass(frozen=True)
class GovernanceCase:
    case_id: str
    signals: frozenset[GovernanceSignal]
    quorum_accepted: bool
    reviewer_count: int


@dataclass(frozen=True)
class GovernanceDecision:
    case_id: str
    status: str
    escalation_required: bool
    arbitration_required: bool
    reasons: list[str]


def evaluate_governance_case(case: GovernanceCase) -> GovernanceDecision:
    """Classify a disputed ETS case for human escalation.

    This function models process semantics only. It does not decide legal
    sufficiency, organizational accountability, or truth of an external event.
    """

    if not case.case_id:
        raise ValueError("case_id is required")
    if case.reviewer_count < 0:
        raise ValueError("reviewer_count must be non-negative")

    reasons: list[str] = []
    if GovernanceSignal.PROOF_INVALID in case.signals:
        reasons.append("proof validation failed")
    if GovernanceSignal.FORK_SUSPECTED in case.signals:
        reasons.append("fork suspicion requires trust-boundary review")
    if GovernanceSignal.OMISSION_SUSPECTED in case.signals:
        reasons.append("omission suspicion requires expectation-source review")
    if GovernanceSignal.POLICY_OVERRIDE_REQUESTED in case.signals:
        reasons.append("policy override requested")
    if GovernanceSignal.LEGAL_HOLD in case.signals:
        reasons.append("legal hold requires organizational handling")
    if not case.quorum_accepted:
        reasons.append("verifier quorum was not accepted")

    escalation_required = bool(reasons)
    arbitration_required = (
        GovernanceSignal.POLICY_OVERRIDE_REQUESTED in case.signals
        or GovernanceSignal.LEGAL_HOLD in case.signals
        or case.reviewer_count > 1
    ) and escalation_required
    status = "accepted" if not escalation_required else "escalated"

    return GovernanceDecision(
        case_id=case.case_id,
        status=status,
        escalation_required=escalation_required,
        arbitration_required=arbitration_required,
        reasons=reasons or ["no governance escalation required"],
    )
