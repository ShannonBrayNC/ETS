from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib

from ets.ranger.decision_event import decision_event_digest
from ets.ranger.evidence_object_adapter import ranger_decision_event_to_evidence_object
from ets.ranger.mission_consequence_verifier import verify_ranger_mission_consequences


def _artifact_bytes(event_id: str) -> bytes:
    return f"camera-artifact:{event_id}".encode("utf-8")


def _artifact_digest(event_id: str) -> str:
    return "sha256:" + hashlib.sha256(_artifact_bytes(event_id)).hexdigest()


def _event(event_id: str, previous: str | None, state: str, action: str, consequence_state: str = "KNOWN") -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": "ranger.decision-event.v0.1",
        "event_id": event_id,
        "mission_id": "mission-1",
        "ranger_id": "ranger-1",
        "occurred_at": datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "subject_context": [
            {
                "subject_id": "SUBJECT-1",
                "subject_scope": "MISSION_PSEUDONYM",
                "claims": [
                    {
                        "claim_id": f"identity-{event_id}",
                        "kind": "identity",
                        "state": state,
                        "source_refs": [f"camera-{event_id}"],
                        **({"value": "registered-user-1"} if state == "KNOWN" else {"reason": f"identity state is {state}"}),
                    }
                ],
            }
        ],
        "decision": {
            "decision_id": f"decision-{event_id}",
            "policy_id": "policy-1",
            "selected_action": action,
            "participating_claim_ids": [f"identity-{event_id}"],
        },
        "cyber_physical_state": {
            "schema_version": "ranger.cyber-physical-state.v0.1",
            "captured_at": datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "capabilities": [{"capability_id": "camera", "state": "AVAILABLE"}],
            "measurements": [
                {
                    "measurement_id": f"speed-{event_id}",
                    "property": "vehicle_speed",
                    "value": 0.0,
                    "unit": "m/s",
                    "state": "KNOWN",
                    "source_id": "encoder-1",
                    "captured_at": datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                }
            ],
            "actuation": {
                "selected_action": {"state": "KNOWN", "value": action},
                "issued_command": {"state": "KNOWN", "value": {"target": action}},
                "command_acknowledgement": {"state": "KNOWN", "value": "accepted"},
                "actuator_response": {"state": "KNOWN", "value": "executed"},
            },
            "consequence": {
                "state": consequence_state,
                "claim": "vehicle response observed",
                "supporting_measurement_refs": [f"speed-{event_id}"] if consequence_state == "KNOWN" else [],
                "contradicting_measurement_refs": [],
                **({"reason": "consequence unavailable"} if consequence_state != "KNOWN" else {}),
            },
        },
        "evidence": [
            {
                "evidence_id": f"camera-{event_id}",
                "evidence_type": "camera-observation",
                "source_id": "camera-1",
                "digest": _artifact_digest(event_id),
            }
        ],
        "previous_event_digest": previous,
        "event_digest": None,
        "signature": None,
    }
    event["event_digest"] = decision_event_digest(event)
    return event


def _chain() -> list[dict[str, object]]:
    first = _event("e1", None, "UNKNOWN", "maintain_distance")
    second = _event("e2", first["event_digest"], "INDETERMINATE", "stop")
    third = _event("e3", second["event_digest"], "KNOWN", "continue")
    return [first, second, third]


def _all_artifacts() -> dict[str, bytes]:
    return {f"camera-{event_id}": _artifact_bytes(event_id) for event_id in ("e1", "e2", "e3")}


def test_mission_consequence_verifier_supports_complete_chain() -> None:
    objects = [ranger_decision_event_to_evidence_object(event) for event in _chain()]
    result = verify_ranger_mission_consequences(objects)
    assert result.valid_chain is True
    assert result.overall_status == "SUPPORTED"
    assert result.first_problem_event_index is None
    assert result.source_evidence_verification_requested is False
    assert [finding.source_evidence_status for finding in result.event_findings] == ["NOT_REQUESTED"] * 3
    assert result.temporal_epistemic_conservation_preserved is True
    assert [finding.consequence_status for finding in result.event_findings] == ["SUPPORTED", "SUPPORTED", "SUPPORTED"]
    transitions = result.chain_verification.epistemic_transitions
    assert [transition.to_state for transition in transitions] == ["UNKNOWN", "INDETERMINATE", "KNOWN"]


def test_source_aware_mission_verifies_all_referenced_artifacts() -> None:
    objects = [ranger_decision_event_to_evidence_object(event) for event in _chain()]
    result = verify_ranger_mission_consequences(objects, artifacts=_all_artifacts())
    assert result.overall_status == "SUPPORTED"
    assert result.source_evidence_verification_requested is True
    assert result.source_verified_event_count == 3
    assert result.source_incomplete_event_count == 0
    assert result.source_digest_mismatch_event_count == 0
    assert [finding.source_evidence_status for finding in result.event_findings] == ["VERIFIED"] * 3


def test_missing_source_artifact_marks_earliest_dependent_event_incomplete() -> None:
    objects = [ranger_decision_event_to_evidence_object(event) for event in _chain()]
    artifacts = _all_artifacts()
    del artifacts["camera-e2"]
    result = verify_ranger_mission_consequences(objects, artifacts=artifacts)
    assert result.valid_chain is True
    assert result.overall_status == "INCOMPLETE"
    assert result.first_problem_event_index == 1
    assert result.first_problem_event_id == "e2"
    assert result.source_incomplete_event_count == 1
    finding = result.event_findings[1]
    assert finding.consequence_status == "SUPPORTED"
    assert finding.source_evidence_status == "INCOMPLETE"
    assert finding.source_evidence is not None
    assert finding.source_evidence.missing_count == 1


def test_digest_invalid_source_marks_mission_digest_mismatch_without_erasing_consequence() -> None:
    objects = [ranger_decision_event_to_evidence_object(event) for event in _chain()]
    artifacts = _all_artifacts()
    artifacts["camera-e2"] = b"tampered-camera-artifact"
    result = verify_ranger_mission_consequences(objects, artifacts=artifacts)
    assert result.valid_chain is True
    assert result.overall_status == "DIGEST_MISMATCH"
    assert result.first_problem_event_id == "e2"
    assert result.source_digest_mismatch_event_count == 1
    finding = result.event_findings[1]
    assert finding.consequence_status == "SUPPORTED"
    assert finding.source_evidence_status == "DIGEST_MISMATCH"


def test_first_contradicted_consequence_is_reported() -> None:
    events = _chain()
    broken = deepcopy(events[1])
    cps = broken["cyber_physical_state"]
    assert isinstance(cps, dict)
    consequence = cps["consequence"]
    assert isinstance(consequence, dict)
    consequence["state"] = "CONTRADICTED"
    consequence["supporting_measurement_refs"] = []
    consequence["contradicting_measurement_refs"] = ["speed-e2"]
    consequence["reason"] = "encoder evidence contradicts claimed consequence"
    broken["event_digest"] = decision_event_digest(broken)
    events[1] = broken
    events[2]["previous_event_digest"] = broken["event_digest"]
    events[2]["event_digest"] = decision_event_digest(events[2])
    objects = [ranger_decision_event_to_evidence_object(event) for event in events]
    result = verify_ranger_mission_consequences(objects)
    assert result.valid_chain is True
    assert result.overall_status == "CONTRADICTED"
    assert result.first_problem_event_index == 1
    assert result.first_problem_event_id == "e2"


def test_missing_consequence_makes_mission_incomplete() -> None:
    events = _chain()
    cps = events[1]["cyber_physical_state"]
    assert isinstance(cps, dict)
    cps["consequence"] = None
    events[1]["event_digest"] = decision_event_digest(events[1])
    events[2]["previous_event_digest"] = events[1]["event_digest"]
    events[2]["event_digest"] = decision_event_digest(events[2])
    objects = [ranger_decision_event_to_evidence_object(event) for event in events]
    result = verify_ranger_mission_consequences(objects)
    assert result.overall_status == "INCOMPLETE"
    assert result.first_problem_event_id == "e2"


def test_broken_chain_dominates_consequence_and_source_support() -> None:
    events = _chain()
    events[2]["previous_event_digest"] = "sha256:" + "f" * 64
    events[2]["event_digest"] = decision_event_digest(events[2])
    objects = [ranger_decision_event_to_evidence_object(event) for event in events]
    result = verify_ranger_mission_consequences(objects, artifacts=_all_artifacts())
    assert result.valid_chain is False
    assert result.overall_status == "CHAIN_INVALID"
    assert result.first_problem_event_index == 2


def test_later_known_identity_does_not_rewrite_earlier_unknown_state() -> None:
    objects = [ranger_decision_event_to_evidence_object(event) for event in _chain()]
    result = verify_ranger_mission_consequences(objects, artifacts=_all_artifacts())
    first_states = result.event_findings[0].epistemic_states
    last_states = result.event_findings[-1].epistemic_states
    assert first_states == ("UNKNOWN",)
    assert last_states == ("KNOWN",)
    assert result.temporal_epistemic_conservation_preserved is True
