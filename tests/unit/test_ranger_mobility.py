from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.ranger import (
    AuthorizationResult,
    ClockQuality,
    MotionReason,
    MotionVector,
    RangerDriveCommand,
    RangerMobilityController,
    RangerMobilityEvent,
    RangerMobilityPolicy,
    RangerSafetyInputError,
    SafetyMode,
)

NOW = datetime(2026, 9, 4, 6, 0, tzinfo=UTC)


def policy() -> RangerMobilityPolicy:
    return RangerMobilityPolicy(
        policy_id="policy:ranger:r0.1:test-course",
        policy_version="1",
        max_linear_speed_mps=2.0,
        max_yaw_rate_rad_s=1.0,
        max_command_queue_age_ms=100,
        watchdog_timeout_ms=250,
    )


def controller() -> RangerMobilityController:
    return RangerMobilityController(
        vehicle_id="ets-ranger:r0-sim-001",
        mission_id="mission:test-course-001",
        controller_id="operator:shannon",
        controller_session_id="session:teleop-001",
        boot_id="boot-001",
        policy=policy(),
        local_clock_quality=ClockQuality.SYNCHRONIZED,
    )


def command(
    sequence: int = 1,
    *,
    motion: MotionVector | None = None,
    deadman_asserted: bool = True,
    issued_at_utc: datetime = NOW,
    vehicle_id: str = "ets-ranger:r0-sim-001",
    mission_id: str = "mission:test-course-001",
    controller_id: str = "operator:shannon",
    controller_session_id: str = "session:teleop-001",
) -> RangerDriveCommand:
    return RangerDriveCommand(
        command_id=f"cmd-{sequence}",
        command_sequence=sequence,
        mission_id=mission_id,
        vehicle_id=vehicle_id,
        controller_id=controller_id,
        controller_session_id=controller_session_id,
        issued_at_utc=issued_at_utc,
        source_clock_quality=ClockQuality.SYNCHRONIZED,
        deadman_asserted=deadman_asserted,
        requested_motion=motion or MotionVector(linear_speed_mps=1.0, yaw_rate_rad_s=0.2),
    )


def authorize(
    ctl: RangerMobilityController,
    item: RangerDriveCommand,
    *,
    received_ns: int = 1_000_000_000,
    evaluated_ns: int = 1_010_000_000,
    estop: bool = False,
) -> RangerMobilityEvent:
    return ctl.authorize(
        item,
        received_monotonic_ns=received_ns,
        evaluated_monotonic_ns=evaluated_ns,
        evaluated_at_utc=NOW,
        hardware_estop_asserted=estop,
    )


def test_controller_starts_disarmed_and_denies_motion_with_explicit_evidence() -> None:
    ctl = controller()
    event = authorize(ctl, command())

    assert event.policy_evaluation.authorization_result is AuthorizationResult.DENIED
    assert event.policy_evaluation.reason_codes == (MotionReason.NOT_ARMED,)
    assert event.actuator_command.motion.is_stopped
    assert ctl.applied_motion.is_stopped
    assert event.observed_facts.classification == "observed_fact"
    assert event.derived_values.classification == "derived_value"
    assert event.policy_evaluation.classification == "policy_evaluation"
    assert event.actuator_command.classification == "actuator_command"
    assert event.observed_result is None
    assert event.claim_boundary == "authorization_only_no_actuator_or_physical_outcome"


def test_armed_fresh_bounded_command_is_allowed_deterministically() -> None:
    first = controller()
    second = controller()
    for ctl in (first, second):
        mode = ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)
        assert mode is SafetyMode.ARMED

    event_a = authorize(first, command())
    event_b = authorize(second, command())

    assert event_a == event_b
    assert event_a.policy_evaluation.authorization_result is AuthorizationResult.ALLOWED
    assert event_a.policy_evaluation.reason_codes == ()
    assert event_a.actuator_command.motion == command().requested_motion
    assert event_a.policy_evaluation.policy_digest_sha256 == first.policy_digest_sha256
    assert event_a.derived_values.command_queue_age_ms == 10


@pytest.mark.parametrize(
    ("motion", "reason"),
    [
        (MotionVector(linear_speed_mps=2.1, yaw_rate_rad_s=0.0), MotionReason.LINEAR_SPEED_LIMIT),
        (MotionVector(linear_speed_mps=0.0, yaw_rate_rad_s=1.1), MotionReason.YAW_RATE_LIMIT),
    ],
)
def test_out_of_policy_motion_is_denied_not_silently_clamped(
    motion: MotionVector,
    reason: MotionReason,
) -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)

    event = authorize(ctl, command(motion=motion))

    assert event.policy_evaluation.authorization_result is AuthorizationResult.DENIED
    assert reason in event.policy_evaluation.reason_codes
    assert event.actuator_command.motion.is_stopped


def test_deadman_release_denies_motion() -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)

    event = authorize(ctl, command(deadman_asserted=False))

    assert event.policy_evaluation.reason_codes == (MotionReason.DEADMAN_RELEASED,)
    assert event.actuator_command.motion.is_stopped


def test_estop_is_latched_until_release_reset_and_explicit_rearm() -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)

    asserted = authorize(ctl, command(), estop=True)
    assert asserted.mode_after is SafetyMode.ESTOP_LATCHED
    assert MotionReason.HARDWARE_ESTOP_ASSERTED in asserted.policy_evaluation.reason_codes

    released_only = authorize(
        ctl,
        command(2),
        received_ns=1_020_000_000,
        evaluated_ns=1_030_000_000,
    )
    assert released_only.mode_after is SafetyMode.ESTOP_LATCHED
    assert MotionReason.ESTOP_LATCHED in released_only.policy_evaluation.reason_codes

    assert (
        ctl.reset_estop(
            now_monotonic_ns=1_040_000_000,
            hardware_estop_asserted=False,
        )
        is SafetyMode.DISARMED
    )
    assert (
        ctl.arm(
            now_monotonic_ns=1_050_000_000,
            hardware_estop_asserted=False,
        )
        is SafetyMode.ARMED
    )
    allowed = authorize(
        ctl,
        command(3),
        received_ns=1_060_000_000,
        evaluated_ns=1_070_000_000,
    )
    assert allowed.policy_evaluation.authorization_result is AuthorizationResult.ALLOWED


def test_stale_local_queue_command_is_denied_and_remote_wall_clock_is_not_safety_clock() -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)
    future_remote_time = NOW + timedelta(days=365)

    event = authorize(
        ctl,
        command(issued_at_utc=future_remote_time),
        received_ns=1_000_000_000,
        evaluated_ns=1_101_000_000,
    )

    assert MotionReason.STALE_COMMAND in event.policy_evaluation.reason_codes
    assert event.derived_values.command_queue_age_ms == 101
    assert event.actuator_command.motion.is_stopped


def test_duplicate_or_out_of_order_sequence_is_rejected() -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)
    first = authorize(ctl, command(2))
    assert first.policy_evaluation.authorization_result is AuthorizationResult.ALLOWED

    replay = authorize(
        ctl,
        command(2),
        received_ns=1_020_000_000,
        evaluated_ns=1_030_000_000,
    )

    assert MotionReason.NON_MONOTONIC_COMMAND in replay.policy_evaluation.reason_codes
    assert replay.actuator_command.motion.is_stopped


@pytest.mark.parametrize(
    "overrides",
    [
        {"vehicle_id": "ets-ranger:other"},
        {"mission_id": "mission:other"},
        {"controller_id": "operator:other"},
        {"controller_session_id": "session:other"},
    ],
)
def test_identity_mismatch_fails_closed(overrides: dict[str, str]) -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)

    event = authorize(ctl, command(**overrides))

    assert MotionReason.IDENTITY_MISMATCH in event.policy_evaluation.reason_codes
    assert event.actuator_command.motion.is_stopped


def test_loss_of_command_watchdog_stops_and_requires_explicit_rearm() -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)
    allowed = authorize(ctl, command())
    assert not allowed.actuator_command.motion.is_stopped

    timeout = ctl.enforce_watchdog(
        now_monotonic_ns=1_260_000_000,
        observed_at_utc=NOW,
        hardware_estop_asserted=False,
    )

    assert timeout is not None
    assert timeout.operator_command is None
    assert timeout.policy_evaluation.reason_codes == (MotionReason.WATCHDOG_TIMEOUT,)
    assert timeout.mode_after is SafetyMode.COMMAND_TIMEOUT
    assert timeout.actuator_command.motion.is_stopped
    assert timeout.derived_values.watchdog_elapsed_ms == 250

    denied = authorize(
        ctl,
        command(2),
        received_ns=1_270_000_000,
        evaluated_ns=1_280_000_000,
    )
    assert MotionReason.COMMAND_TIMEOUT_LATCHED in denied.policy_evaluation.reason_codes
    assert (
        ctl.arm(
            now_monotonic_ns=1_290_000_000,
            hardware_estop_asserted=False,
        )
        is SafetyMode.ARMED
    )


def test_invalid_monotonic_order_fails_closed() -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)

    event = authorize(
        ctl,
        command(),
        received_ns=1_100_000_000,
        evaluated_ns=1_000_000_000,
    )

    assert MotionReason.INVALID_MONOTONIC_ORDER in event.policy_evaluation.reason_codes
    assert event.mode_after is SafetyMode.COMMAND_TIMEOUT
    assert event.actuator_command.motion.is_stopped


def test_policy_prevents_watchdog_shorter_than_queue_age() -> None:
    with pytest.raises(ValidationError, match="watchdog_timeout_ms"):
        RangerMobilityPolicy(
            policy_id="policy:test",
            policy_version="1",
            max_linear_speed_mps=1.0,
            max_yaw_rate_rad_s=1.0,
            max_command_queue_age_ms=500,
            watchdog_timeout_ms=100,
        )


def test_contract_is_strict_and_exposes_stable_schema_identity() -> None:
    ctl = controller()
    event = authorize(ctl, command())
    payload = event.model_dump(mode="json")
    payload["unobserved_physical_result"] = "invented"

    with pytest.raises(ValidationError):
        RangerMobilityEvent.model_validate(payload)

    schema = RangerMobilityEvent.model_json_schema()
    assert schema["$id"] == "https://lanternprotocol.org/schemas/ets/ranger/mobility-event/v1"
    assert schema["additionalProperties"] is False


def test_forged_allowed_event_without_positive_standing_is_rejected() -> None:
    ctl = controller()
    ctl.arm(now_monotonic_ns=900_000_000, hardware_estop_asserted=False)
    event = authorize(ctl, command())
    payload = event.model_dump()
    payload["observed_facts"] = event.observed_facts.model_copy(
        update={"controller_identity_match": False}
    )

    with pytest.raises(ValidationError, match="positive standing"):
        RangerMobilityEvent.model_validate(payload)


def test_estop_reset_cannot_override_asserted_hardware_signal() -> None:
    ctl = controller()
    assert (
        ctl.arm(
            now_monotonic_ns=1,
            hardware_estop_asserted=True,
        )
        is SafetyMode.ESTOP_LATCHED
    )

    with pytest.raises(RangerSafetyInputError, match="must be released"):
        ctl.reset_estop(now_monotonic_ns=2, hardware_estop_asserted=True)

    assert ctl.mode is SafetyMode.ESTOP_LATCHED
    assert ctl.applied_motion.is_stopped
