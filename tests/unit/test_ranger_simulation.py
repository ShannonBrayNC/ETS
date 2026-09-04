from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.ranger import (
    AuthorizationResult,
    ClockQuality,
    MotionVector,
    RangerDriveCommand,
    RangerMobilityController,
    RangerMobilityEvent,
    RangerMobilityPolicy,
    RangerMobilitySimulator,
    RangerSimulationConfig,
    RangerSimulationInputError,
    RangerSimulationStep,
    SimulatedPose2D,
    SimulationValueClass,
)

NOW = datetime(2026, 9, 4, 7, 0, tzinfo=UTC)


def controller() -> RangerMobilityController:
    return RangerMobilityController(
        vehicle_id="ets-ranger:r0-sim-001",
        mission_id="mission:test-course-001",
        controller_id="operator:shannon",
        controller_session_id="session:teleop-001",
        boot_id="boot-001",
        policy=RangerMobilityPolicy(
            policy_id="policy:ranger:r0.1:test-course",
            policy_version="1",
            max_linear_speed_mps=2.0,
            max_yaw_rate_rad_s=1.0,
            max_command_queue_age_ms=100,
            watchdog_timeout_ms=250,
        ),
        local_clock_quality=ClockQuality.SYNCHRONIZED,
    )


def simulator(*, mission_id: str = "mission:test-course-001") -> RangerMobilitySimulator:
    return RangerMobilitySimulator(
        vehicle_id="ets-ranger:r0-sim-001",
        mission_id=mission_id,
        boot_id="boot-001",
        producer_id="simulator:ranger-planar-001",
        simulation_session_id="simulation:session-001",
    )


def command(sequence: int, motion: MotionVector | None = None) -> RangerDriveCommand:
    return RangerDriveCommand(
        command_id=f"cmd-{sequence}",
        command_sequence=sequence,
        mission_id="mission:test-course-001",
        vehicle_id="ets-ranger:r0-sim-001",
        controller_id="operator:shannon",
        controller_session_id="session:teleop-001",
        issued_at_utc=NOW,
        source_clock_quality=ClockQuality.SYNCHRONIZED,
        deadman_asserted=True,
        requested_motion=motion or MotionVector(linear_speed_mps=1.0, yaw_rate_rad_s=0.2),
    )


def mobility_event(
    ctl: RangerMobilityController,
    sequence: int,
    *,
    evaluated_ns: int,
    motion: MotionVector | None = None,
) -> RangerMobilityEvent:
    return ctl.authorize(
        command(sequence, motion),
        received_monotonic_ns=evaluated_ns - 10_000_000,
        evaluated_monotonic_ns=evaluated_ns,
        evaluated_at_utc=NOW,
        hardware_estop_asserted=False,
    )


def armed_controller() -> RangerMobilityController:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)
    return ctl


def test_simulator_consumes_safety_event_and_separates_claim_classes() -> None:
    event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)
    step = simulator().apply(event, step_duration_ms=500)

    assert event.policy_evaluation.authorization_result is AuthorizationResult.ALLOWED
    assert step.actuator_response.commanded_motion == event.actuator_command.motion
    assert step.actuator_response.applied_motion == event.actuator_command.motion
    assert step.actuator_response.classification == "actuator_response"
    assert step.actuator_response.physical_actuator_observed is False
    assert (
        step.actuator_response.claim_boundary == "simulated_adapter_response_not_physical_actuator"
    )
    assert step.simulated_result.classification is SimulationValueClass.DERIVED_VALUE
    assert step.simulated_result.record_role == "simulated_observed_result"
    assert step.simulated_result.physical_outcome_observed is False
    assert (
        step.simulated_result.claim_boundary
        == "derived_simulation_state_not_physical_or_sensor_observation"
    )


def test_planar_result_is_deterministic_and_binds_model_configuration() -> None:
    first_event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)
    second_event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)
    first = simulator().apply(first_event, step_duration_ms=500)
    second = simulator().apply(second_event, step_duration_ms=500)

    assert first == second
    assert first.simulated_result.state_after.pose.x_m == pytest.approx(0.5)
    assert first.simulated_result.state_after.pose.y_m == pytest.approx(0.0)
    assert first.simulated_result.state_after.pose.heading_rad == pytest.approx(0.1)
    assert first.simulated_result.model_id == "ets.ranger.planar-kinematic-euler.v1"
    assert first.simulated_result.model_config_digest_sha256 == simulator().config_digest_sha256


def test_denied_zero_command_is_applied_without_recovering_requested_motion() -> None:
    ctl = controller()
    event = mobility_event(
        ctl,
        1,
        evaluated_ns=1_000_000_000,
        motion=MotionVector(linear_speed_mps=1.5, yaw_rate_rad_s=0.0),
    )
    step = simulator().apply(event, step_duration_ms=500)

    assert event.policy_evaluation.authorization_result is AuthorizationResult.DENIED
    assert event.actuator_command.motion.is_stopped
    assert step.actuator_response.commanded_motion.is_stopped
    assert step.simulated_result.state_after.pose == SimulatedPose2D(
        x_m=0.0,
        y_m=0.0,
        heading_rad=0.0,
    )


def test_simulator_rejects_identity_confusion_before_mutating_state() -> None:
    event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)
    sim = simulator(mission_id="mission:other")

    with pytest.raises(RangerSimulationInputError, match="identity mismatch"):
        sim.apply(event, step_duration_ms=500)

    assert sim.state.pose.x_m == 0.0


def test_simulator_rejects_duplicate_and_missing_event_sequences() -> None:
    ctl = armed_controller()
    first = mobility_event(ctl, 1, evaluated_ns=1_000_000_000)
    second = mobility_event(ctl, 2, evaluated_ns=1_600_000_000)
    sim = simulator()
    sim.apply(first, step_duration_ms=500)

    with pytest.raises(RangerSimulationInputError, match="expected 2, received 1"):
        sim.apply(first, step_duration_ms=500)

    payload = second.model_dump()
    payload["event_sequence"] = 3
    missing = RangerMobilityEvent.model_validate(payload)
    with pytest.raises(RangerSimulationInputError, match="expected 2, received 3"):
        sim.apply(missing, step_duration_ms=500)


def test_simulator_rejects_event_before_prior_result_time() -> None:
    ctl = armed_controller()
    first = mobility_event(ctl, 1, evaluated_ns=1_000_000_000)
    second = mobility_event(ctl, 2, evaluated_ns=1_100_000_000)
    sim = simulator()
    sim.apply(first, step_duration_ms=500)

    with pytest.raises(RangerSimulationInputError, match="precedes the prior"):
        sim.apply(second, step_duration_ms=100)


def test_bundle_rejects_corrupted_event_without_updated_link_digests() -> None:
    event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)
    step = simulator().apply(event, step_duration_ms=500)
    payload = step.model_dump()
    payload["source_mobility_event"]["evaluated_monotonic_ns"] = 1_000_000_001

    with pytest.raises(ValidationError, match="mobility-event digest mismatch"):
        RangerSimulationStep.model_validate(payload)


def test_bundle_rejects_tampered_derived_result() -> None:
    event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)
    step = simulator().apply(event, step_duration_ms=500)
    payload = step.model_dump()
    payload["simulated_result"]["state_after"]["pose"]["x_m"] = 99.0

    with pytest.raises(ValidationError, match="deterministic model output"):
        RangerSimulationStep.model_validate(payload)


def test_step_duration_is_bounded_by_committed_config() -> None:
    config = RangerSimulationConfig(max_step_duration_ms=250)
    sim = RangerMobilitySimulator(
        vehicle_id="ets-ranger:r0-sim-001",
        mission_id="mission:test-course-001",
        boot_id="boot-001",
        producer_id="simulator:ranger-planar-001",
        simulation_session_id="simulation:session-001",
        config=config,
    )
    event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)

    with pytest.raises(RangerSimulationInputError, match="1-250"):
        sim.apply(event, step_duration_ms=251)


def test_response_and_result_contracts_are_strict_and_versioned() -> None:
    event = mobility_event(armed_controller(), 1, evaluated_ns=1_000_000_000)
    step = simulator().apply(event, step_duration_ms=500)
    response_schema = step.actuator_response.model_json_schema()
    result_schema = step.simulated_result.model_json_schema()

    assert response_schema["$id"].endswith("/ranger/actuator-response/v1")
    assert result_schema["$id"].endswith("/ranger/simulated-result/v1")
    assert response_schema["additionalProperties"] is False
    assert result_schema["additionalProperties"] is False

    payload = step.simulated_result.model_dump()
    payload["physical_outcome"] = "invented"
    with pytest.raises(ValidationError):
        type(step.simulated_result).model_validate(payload)
