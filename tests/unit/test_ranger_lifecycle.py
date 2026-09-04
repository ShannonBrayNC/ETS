from datetime import UTC, datetime

import pytest

from ets.core.canonical_json import canonical_sha256
from ets.ranger.lifecycle import RangerLifecycleController, RangerLifecycleKind
from ets.ranger.mobility import (
    ClockQuality,
    MotionReason,
    MotionVector,
    RangerDriveCommand,
    RangerMobilityController,
    RangerMobilityPolicy,
    RangerSafetyInputError,
    SafetyMode,
)

NOW = datetime(2026, 9, 4, 7, 30, tzinfo=UTC)


def _controller() -> RangerLifecycleController:
    ctl = RangerMobilityController(
        vehicle_id="ets-ranger:r0-001",
        mission_id="mission-alpha",
        controller_id="operator-console-1",
        controller_session_id="session-1",
        boot_id="boot-1",
        policy=RangerMobilityPolicy(
            policy_id="ranger-r0-test",
            policy_version="1",
            max_linear_speed_mps=2.0,
            max_yaw_rate_rad_s=1.0,
            max_command_queue_age_ms=250,
            watchdog_timeout_ms=500,
            allow_reverse=True,
        ),
        local_clock_quality=ClockQuality.SYNCHRONIZED,
    )
    return RangerLifecycleController(ctl)


def _command(sequence: int = 1) -> RangerDriveCommand:
    return RangerDriveCommand(
        command_id=f"cmd-{sequence}",
        command_sequence=sequence,
        mission_id="mission-alpha",
        vehicle_id="ets-ranger:r0-001",
        controller_id="operator-console-1",
        controller_session_id="session-1",
        issued_at_utc=NOW,
        source_clock_quality=ClockQuality.SYNCHRONIZED,
        deadman_asserted=True,
        requested_motion=MotionVector(linear_speed_mps=1.0, yaw_rate_rad_s=0.0),
    )


def test_arm_and_disarm_are_first_class_evidence() -> None:
    lifecycle = _controller()
    armed = lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    disarmed = lifecycle.disarm(
        now_monotonic_ns=1_100_000_000,
        occurred_at_utc=NOW,
    )
    assert armed.lifecycle_kind is RangerLifecycleKind.ARM
    assert armed.mode_before is SafetyMode.DISARMED
    assert armed.mode_after is SafetyMode.ARMED
    assert armed.operator_rearm_required is False
    assert disarmed.lifecycle_kind is RangerLifecycleKind.DISARM
    assert disarmed.mode_after is SafetyMode.DISARMED
    assert disarmed.operator_rearm_required is True
    assert disarmed.lifecycle_sequence == armed.lifecycle_sequence + 1


def test_estop_assertion_links_lifecycle_to_mobility_event() -> None:
    lifecycle = _controller()
    lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    mobility, transition = lifecycle.authorize(
        _command(),
        received_monotonic_ns=1_010_000_000,
        evaluated_monotonic_ns=1_020_000_000,
        evaluated_at_utc=NOW,
        hardware_estop_asserted=True,
    )
    assert transition is not None
    assert transition.lifecycle_kind is RangerLifecycleKind.ESTOP_LATCH
    assert transition.mode_after is SafetyMode.ESTOP_LATCHED
    assert transition.reason_code is MotionReason.HARDWARE_ESTOP_ASSERTED
    assert transition.source_mobility_event_id == mobility.event_id
    assert transition.source_mobility_event_digest_sha256 == canonical_sha256(
        mobility.model_dump(mode="json")
    )
    assert transition.physical_estop_state_proven is False


def test_estop_reset_returns_to_disarmed_and_requires_rearm() -> None:
    lifecycle = _controller()
    lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=True,
    )
    reset = lifecycle.reset_estop(
        now_monotonic_ns=1_100_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    assert reset.lifecycle_kind is RangerLifecycleKind.ESTOP_RESET
    assert reset.mode_before is SafetyMode.ESTOP_LATCHED
    assert reset.mode_after is SafetyMode.DISARMED
    assert reset.operator_rearm_required is True


def test_estop_reset_fails_while_hardware_input_is_asserted() -> None:
    lifecycle = _controller()
    lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=True,
    )
    with pytest.raises(RangerSafetyInputError, match="released before reset"):
        lifecycle.reset_estop(
            now_monotonic_ns=1_100_000_000,
            occurred_at_utc=NOW,
            hardware_estop_asserted=True,
        )


def test_watchdog_timeout_is_first_class_transition_evidence() -> None:
    lifecycle = _controller()
    lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    mobility, transition = lifecycle.enforce_watchdog(
        now_monotonic_ns=1_500_000_000,
        observed_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    assert mobility is not None
    assert transition is not None
    assert transition.lifecycle_kind is RangerLifecycleKind.WATCHDOG_TIMEOUT
    assert transition.mode_after is SafetyMode.COMMAND_TIMEOUT
    assert transition.reason_code is MotionReason.WATCHDOG_TIMEOUT
    assert transition.operator_rearm_required is True
    assert transition.source_mobility_event_id == mobility.event_id


def test_timeout_recovery_requires_explicit_rearm_and_is_distinct() -> None:
    lifecycle = _controller()
    lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    lifecycle.enforce_watchdog(
        now_monotonic_ns=1_500_000_000,
        observed_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    recovery = lifecycle.arm(
        now_monotonic_ns=1_600_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    assert recovery.lifecycle_kind is RangerLifecycleKind.TIMEOUT_RECOVERY_REARM
    assert recovery.mode_before is SafetyMode.COMMAND_TIMEOUT
    assert recovery.mode_after is SafetyMode.ARMED
    assert recovery.operator_rearm_required is False


def test_no_lifecycle_event_when_watchdog_does_not_change_authority() -> None:
    lifecycle = _controller()
    lifecycle.arm(
        now_monotonic_ns=1_000_000_000,
        occurred_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    mobility, transition = lifecycle.enforce_watchdog(
        now_monotonic_ns=1_100_000_000,
        observed_at_utc=NOW,
        hardware_estop_asserted=False,
    )
    assert mobility is None
    assert transition is None


def test_lifecycle_wall_time_must_be_timezone_aware() -> None:
    lifecycle = _controller()
    with pytest.raises(RangerSafetyInputError, match="timezone-aware"):
        lifecycle.arm(
            now_monotonic_ns=1_000_000_000,
            occurred_at_utc=datetime(2026, 9, 4, 7, 30),
            hardware_estop_asserted=False,
        )
