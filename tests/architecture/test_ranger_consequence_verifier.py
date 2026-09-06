from __future__ import annotations

from copy import deepcopy

from ets.ranger.consequence_verifier import verify_ranger_consequence
from ets.ranger.decision_event import decision_event_digest
from ets.ranger.evidence_object_adapter import ranger_decision_event_to_evidence_object


def _event() -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": "ranger.decision-event.v0.1",
        "event_id": "event-001",
        "mission_id": "mission-001",
        "ranger_id": "ranger-001",
        "occurred_at": "2026-09-06T10:00:00+00:00",
        "subject_context": [
            {
                "subject_id": "SUBJECT-A921",
                "subject_scope": "MISSION_PSEUDONYM",
                "claims": [
                    {
                        "claim_id": "claim-human",
                        "kind": "human_detected",
                        "value": True,
                        "state": "KNOWN",
                        "confidence": 0.998,
                        "threshold": 0.95,
                        "mechanism": "vision",
                        "source_refs": ["measurement-human"],
                        "reason": None,
                        "contradicts_claim_ids": [],
                    }
                ],
            }
        ],
        "decision": {
            "decision_id": "decision-001",
            "policy_id": "policy-safe-stop-v1",
            "candidate_actions": ["continue", "stop"],
            "selected_action": "stop",
            "authorization_state": "AUTHORIZED",
            "participating_claim_ids": ["claim-human"],
            "excluded_claim_ids": [],
            "decision_reason": "human detected ahead",
        },
        "cyber_physical_state": {
            "schema_version": "ranger.cyber-physical-state.v0.1",
            "captured_at": "2026-09-06T10:00:00+00:00",
            "clock": {
                "source": "ptp",
                "synchronized": True,
                "offset_ms": 0.2,
                "uncertainty_ms": 0.5,
                "state": "KNOWN",
                "reason": None,
            },
            "capabilities": [
                {"capability_id": "camera", "source_id": "camera-01", "state": "AVAILABLE", "reason": None, "health_ref": "health-camera", "calibration_ref": "cal-camera"},
                {"capability_id": "lidar", "source_id": "lidar-01", "state": "AVAILABLE", "reason": None, "health_ref": "health-lidar", "calibration_ref": "cal-lidar"},
            ],
            "measurements": [
                {
                    "measurement_id": "measurement-stop",
                    "property": "vehicle_speed",
                    "value": 0.0,
                    "unit": "m/s",
                    "state": "KNOWN",
                    "source_id": "wheel-encoder",
                    "method": "encoder",
                    "captured_at": "2026-09-06T10:00:00.500+00:00",
                    "freshness_ms": 0,
                    "uncertainty": 0.02,
                    "confidence": 0.99,
                    "coordinate_frame": "vehicle-local",
                    "calibration_ref": "cal-encoder",
                    "health_ref": "health-encoder",
                    "dependency_refs": [],
                    "reason": None,
                }
            ],
            "system_state": [],
            "actuation": {
                "selected_action": {"state": "KNOWN", "value": "stop", "source_refs": ["decision-001"], "observed_at": "2026-09-06T10:00:00.100+00:00", "reason": None},
                "issued_command": {"state": "KNOWN", "value": {"velocity_mps": 0.0}, "source_refs": ["controller-command-001"], "observed_at": "2026-09-06T10:00:00.150+00:00", "reason": None},
                "command_acknowledgement": {"state": "KNOWN", "value": "accepted", "source_refs": ["motor-controller-ack-001"], "observed_at": "2026-09-06T10:00:00.170+00:00", "reason": None},
                "actuator_response": {"state": "KNOWN", "value": {"wheel_speed_mps": 0.0}, "source_refs": ["motor-response-001"], "observed_at": "2026-09-06T10:00:00.400+00:00", "reason": None},
            },
            "consequence": {
                "state": "KNOWN",
                "claim": "vehicle stopped",
                "value": True,
                "observed_at": "2026-09-06T10:00:00.500+00:00",
                "supporting_measurement_refs": ["measurement-stop"],
                "contradicting_measurement_refs": [],
                "reason": None,
            },
        },
        "evidence": [
            {
                "evidence_id": "measurement-human",
                "evidence_type": "camera-observation",
                "source_id": "camera-01",
                "captured_at": "2026-09-06T10:00:00+00:00",
                "digest": "sha256:" + "1" * 64,
                "uri": None,
            }
        ],
        "previous_event_digest": None,
        "event_digest": None,
        "signature": None,
    }
    event["event_digest"] = decision_event_digest(event)
    return event


def _evidence(event: dict[str, object] | None = None):
    return ranger_decision_event_to_evidence_object(event or _event())


def test_fully_supported_consequence_chain_is_supported() -> None:
    result = verify_ranger_consequence(_evidence())
    assert result.overall_status == "SUPPORTED"
    assert result.consequence_claim_supported is True
    assert result.truth_claim_supported is False
    assert all(stage.status == "SUPPORTED" for stage in result.stage_findings)
    assert result.supporting_measurement_refs == ("measurement-stop",)


def test_contradicting_measurement_forces_contradicted_result() -> None:
    event = deepcopy(_event())
    cps = event["cyber_physical_state"]
    assert isinstance(cps, dict)
    consequence = cps["consequence"]
    assert isinstance(consequence, dict)
    consequence["contradicting_measurement_refs"] = ["measurement-moving"]
    event["event_digest"] = decision_event_digest(event)

    result = verify_ranger_consequence(_evidence(event))
    assert result.overall_status == "CONTRADICTED"
    assert result.consequence_claim_supported is False
    assert result.contradicting_measurement_refs == ("measurement-moving",)


def test_missing_actuation_evidence_is_not_observed() -> None:
    event = deepcopy(_event())
    cps = event["cyber_physical_state"]
    assert isinstance(cps, dict)
    cps["actuation"] = None
    event["event_digest"] = decision_event_digest(event)

    result = verify_ranger_consequence(_evidence(event))
    assert result.overall_status == "NOT_OBSERVED"
    assert any(stage.stage == "actuation" and stage.status == "NOT_OBSERVED" for stage in result.stage_findings)


def test_selected_action_mismatch_is_contradicted() -> None:
    event = deepcopy(_event())
    cps = event["cyber_physical_state"]
    assert isinstance(cps, dict)
    actuation = cps["actuation"]
    assert isinstance(actuation, dict)
    selected = actuation["selected_action"]
    assert isinstance(selected, dict)
    selected["value"] = "continue"
    event["event_digest"] = decision_event_digest(event)

    result = verify_ranger_consequence(_evidence(event))
    assert result.overall_status == "CONTRADICTED"
    assert any(stage.stage == "selected_action" and stage.status == "CONTRADICTED" for stage in result.stage_findings)


def test_degraded_capability_is_reported_without_promoting_truth() -> None:
    event = deepcopy(_event())
    cps = event["cyber_physical_state"]
    assert isinstance(cps, dict)
    capabilities = cps["capabilities"]
    assert isinstance(capabilities, list)
    capabilities.append(
        {
            "capability_id": "gnss",
            "source_id": "gnss-01",
            "state": "DEGRADED",
            "reason": "multipath",
            "health_ref": "health-gnss",
            "calibration_ref": None,
        }
    )
    event["event_digest"] = decision_event_digest(event)

    result = verify_ranger_consequence(_evidence(event))
    assert "gnss:DEGRADED:multipath" in result.capability_limitations
    assert result.truth_claim_supported is False
