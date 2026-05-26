import pytest

from ets.governance import GovernanceCase, GovernanceSignal, evaluate_governance_case


def test_evaluate_governance_case_accepts_clean_case() -> None:
    decision = evaluate_governance_case(
        GovernanceCase(
            case_id="case-001",
            signals=frozenset({GovernanceSignal.PROOF_VALID}),
            quorum_accepted=True,
            reviewer_count=1,
        )
    )

    assert decision.status == "accepted"
    assert decision.escalation_required is False
    assert decision.arbitration_required is False
    assert decision.reasons == ["no governance escalation required"]


def test_evaluate_governance_case_escalates_invalid_proof() -> None:
    decision = evaluate_governance_case(
        GovernanceCase(
            case_id="case-002",
            signals=frozenset({GovernanceSignal.PROOF_INVALID}),
            quorum_accepted=True,
            reviewer_count=1,
        )
    )

    assert decision.status == "escalated"
    assert decision.escalation_required is True
    assert decision.arbitration_required is False
    assert decision.reasons == ["proof validation failed"]


def test_evaluate_governance_case_requires_arbitration_for_override() -> None:
    decision = evaluate_governance_case(
        GovernanceCase(
            case_id="case-003",
            signals=frozenset(
                {
                    GovernanceSignal.OMISSION_SUSPECTED,
                    GovernanceSignal.POLICY_OVERRIDE_REQUESTED,
                }
            ),
            quorum_accepted=False,
            reviewer_count=2,
        )
    )

    assert decision.status == "escalated"
    assert decision.arbitration_required is True
    assert "policy override requested" in decision.reasons
    assert "verifier quorum was not accepted" in decision.reasons


def test_evaluate_governance_case_rejects_invalid_case() -> None:
    with pytest.raises(ValueError):
        evaluate_governance_case(
            GovernanceCase(
                case_id="",
                signals=frozenset(),
                quorum_accepted=True,
                reviewer_count=1,
            )
        )
    with pytest.raises(ValueError):
        evaluate_governance_case(
            GovernanceCase(
                case_id="case-004",
                signals=frozenset(),
                quorum_accepted=True,
                reviewer_count=-1,
            )
        )
