from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from ets.ranger.decision_event import decision_event_digest
from ets.ranger.evidence_object_adapter import ranger_decision_event_to_evidence_object
from ets.ranger.mission_chain_verifier import verify_ranger_mission_chain

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs/research/ranger/examples/decision-event-unknown.json"


def _base_event() -> dict[str, object]:
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    value["event_digest"] = decision_event_digest(value)
    return value


def _event_from(
    previous: dict[str, object],
    *,
    event_id: str,
    decision_id: str,
    state: str,
    reason: str,
    selected_action: str,
) -> dict[str, object]:
    value = deepcopy(previous)
    value["event_id"] = event_id
    value["previous_event_digest"] = previous["event_digest"]
    decision = value["decision"]
    assert isinstance(decision, dict)
    decision["decision_id"] = decision_id
    decision["selected_action"] = selected_action
    subject_context = value["subject_context"]
    assert isinstance(subject_context, list)
    claims = subject_context[0]["claims"]
    assert isinstance(claims, list)
    identity = claims[1]
    assert isinstance(identity, dict)
    identity["state"] = state
    identity["reason"] = reason
    if state == "KNOWN":
        identity["value"] = "RANGER-USER-001"
        identity["confidence"] = 0.992
    else:
        identity.pop("value", None)
    value["event_digest"] = None
    value["signature"] = None
    value["event_digest"] = decision_event_digest(value)
    return value


def test_chain_reconstructs_epistemic_state_over_time() -> None:
    first = _base_event()
    second = _event_from(
        first,
        event_id="evt-ranger-0002",
        decision_id="decision-0002",
        state="INDETERMINATE",
        reason="A candidate match existed but did not exceed the active threshold.",
        selected_action="stop",
    )
    third = _event_from(
        second,
        event_id="evt-ranger-0003",
        decision_id="decision-0003",
        state="KNOWN",
        reason="Enrolled principal exceeded the active recognition threshold.",
        selected_action="continue",
    )

    result = verify_ranger_mission_chain(
        [
            ranger_decision_event_to_evidence_object(first),
            ranger_decision_event_to_evidence_object(second),
            ranger_decision_event_to_evidence_object(third),
        ]
    )

    assert result.valid_chain is True
    assert result.event_count == 3
    identity_transitions = [
        item
        for item in result.epistemic_transitions
        if item.predicate == "subject.registered_principal"
    ]
    assert [item.to_state for item in identity_transitions] == [
        "UNKNOWN",
        "INDETERMINATE",
        "KNOWN",
    ]
    assert [item.selected_action for item in identity_transitions] == [
        "maintain_distance",
        "stop",
        "continue",
    ]
    assert result.complete_capture_proven is False
    assert result.truth_claim_supported is False


def test_chain_rejects_broken_predecessor_link() -> None:
    first = _base_event()
    second = _event_from(
        first,
        event_id="evt-ranger-0002",
        decision_id="decision-0002",
        state="INDETERMINATE",
        reason="Candidate was below threshold.",
        selected_action="stop",
    )
    second["previous_event_digest"] = "sha256:" + "0" * 64
    second["event_digest"] = decision_event_digest(second)

    result = verify_ranger_mission_chain(
        [
            ranger_decision_event_to_evidence_object(first),
            ranger_decision_event_to_evidence_object(second),
        ]
    )

    assert result.valid_chain is False
    assert result.event_findings[1].predecessor_link_valid is False


def test_chain_rejects_cross_mission_splice() -> None:
    first = _base_event()
    second = _event_from(
        first,
        event_id="evt-ranger-0002",
        decision_id="decision-0002",
        state="KNOWN",
        reason="Identity known.",
        selected_action="continue",
    )
    second["mission_id"] = "mission-other"
    second["event_digest"] = decision_event_digest(second)

    result = verify_ranger_mission_chain(
        [
            ranger_decision_event_to_evidence_object(first),
            ranger_decision_event_to_evidence_object(second),
        ]
    )

    assert result.valid_chain is False
