from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from ets.demos.agent365_r0_qualification_campaign import (
    R0QualificationPhase,
    R0QualificationPhaseState,
)
from ets.demos.agent365_r0_qualification_recorder import (
    R0QualificationRecorderError,
    append_phase,
    campaign_status,
    initialize_campaign,
    load_campaign,
)


def _write_json(path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _preflight_payload() -> dict[str, object]:
    return {
        "profile": "r0-bench-pi-drv8833-dual-vl53l0x.v1",
        "motion_authorized": False,
        "estop_circuit_closed": True,
        "actuator_outputs_forced_stopped": True,
        "claim_boundary": "preflight_only_no_motor_motion_or_physical_mission_claim",
    }


def _wheels_payload() -> dict[str, object]:
    return {
        "profile": "r0-bench-pi-drv8833-dual-vl53l0x.v1",
        "gate": "B_wheels_off_ground",
        "automated_checks_passed": True,
        "rear_translation_within_limit": True,
        "estop_circuit_closed_before": True,
        "estop_asserted_during_pulse": False,
        "stop_command_completed_after": True,
        "controller_acknowledgement_proves_translation": False,
        "wheel_direction_inferred": False,
    }


def test_recorder_requires_preflight_before_phase_b_pass(tmp_path) -> None:
    initialize_campaign(
        tmp_path,
        campaign_id="r0-test",
        code_sha="a" * 40,
    )
    wheels = tmp_path / "phase-b" / "wheels.json"
    _write_json(wheels, _wheels_payload())

    with pytest.raises(R0QualificationRecorderError, match="prerequisite PASS missing"):
        append_phase(
            tmp_path,
            phase=R0QualificationPhase.WHEELS_OFF_GROUND,
            state=R0QualificationPhaseState.PASS,
            artifact_paths=(wheels,),
            operator_observation="both_wheels_forward",
        )


def test_recorder_requires_machine_readable_phase_a_contract(tmp_path) -> None:
    initialize_campaign(
        tmp_path,
        campaign_id="r0-test",
        code_sha="a" * 40,
    )
    bad = tmp_path / "phase-a" / "bad.json"
    _write_json(bad, {"motion_authorized": True})

    with pytest.raises(R0QualificationRecorderError, match="no-motion preflight"):
        append_phase(
            tmp_path,
            phase=R0QualificationPhase.PREFLIGHT,
            state=R0QualificationPhaseState.PASS,
            artifact_paths=(bad,),
        )


def test_recorder_requires_operator_wheel_direction_observation(tmp_path) -> None:
    initialize_campaign(
        tmp_path,
        campaign_id="r0-test",
        code_sha="a" * 40,
    )
    preflight = tmp_path / "phase-a" / "preflight.json"
    wheels = tmp_path / "phase-b" / "wheels.json"
    _write_json(preflight, _preflight_payload())
    _write_json(wheels, _wheels_payload())

    append_phase(
        tmp_path,
        phase=R0QualificationPhase.PREFLIGHT,
        state=R0QualificationPhaseState.PASS,
        artifact_paths=(preflight,),
        recorded_at=datetime(2026, 9, 18, tzinfo=UTC),
    )

    with pytest.raises(R0QualificationRecorderError, match="both_wheels_forward"):
        append_phase(
            tmp_path,
            phase=R0QualificationPhase.WHEELS_OFF_GROUND,
            state=R0QualificationPhaseState.PASS,
            artifact_paths=(wheels,),
        )


def test_phase_a_and_b_pass_make_campaign_ready_for_live_mission(tmp_path) -> None:
    initialize_campaign(
        tmp_path,
        campaign_id="r0-test",
        code_sha="a" * 40,
    )
    preflight = tmp_path / "phase-a" / "preflight.json"
    wheels = tmp_path / "phase-b" / "wheels.json"
    _write_json(preflight, _preflight_payload())
    _write_json(wheels, _wheels_payload())

    append_phase(
        tmp_path,
        phase=R0QualificationPhase.PREFLIGHT,
        state=R0QualificationPhaseState.PASS,
        artifact_paths=(preflight,),
    )
    append_phase(
        tmp_path,
        phase=R0QualificationPhase.WHEELS_OFF_GROUND,
        state=R0QualificationPhaseState.PASS,
        artifact_paths=(wheels,),
        operator_observation="both_wheels_forward",
    )

    status = campaign_status(tmp_path)
    campaign = load_campaign(tmp_path)

    assert status["ready_for_phase_c_live_mission"] is True
    assert campaign.phase_state(R0QualificationPhase.PREFLIGHT) is R0QualificationPhaseState.PASS
    assert (
        campaign.phase_state(R0QualificationPhase.WHEELS_OFF_GROUND)
        is R0QualificationPhaseState.PASS
    )
    assert (tmp_path / "campaign.sha256").is_file()


def test_phase_records_are_append_only(tmp_path) -> None:
    initialize_campaign(
        tmp_path,
        campaign_id="r0-test",
        code_sha="a" * 40,
    )
    preflight = tmp_path / "phase-a" / "preflight.json"
    _write_json(preflight, _preflight_payload())
    append_phase(
        tmp_path,
        phase=R0QualificationPhase.PREFLIGHT,
        state=R0QualificationPhaseState.PASS,
        artifact_paths=(preflight,),
    )

    with pytest.raises(R0QualificationRecorderError, match="already retained and immutable"):
        append_phase(
            tmp_path,
            phase=R0QualificationPhase.PREFLIGHT,
            state=R0QualificationPhaseState.FAIL,
            artifact_paths=(preflight,),
        )
