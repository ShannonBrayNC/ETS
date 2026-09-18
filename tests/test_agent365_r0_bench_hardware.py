from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.ranger.agent365_r0_bench_hardware import (
    Drv8833R0Actuator,
    DualRangeR0PhysicalSensors,
    R0BenchCalibrationV1,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0MotionDirectiveV1,
    RangerR0StopDirectiveV1,
    RangerR0StopReason,
)

MISSION_ID = "11111111-1111-4111-8111-111111111111"


class FakeClock:
    def __init__(self) -> None:
        self.ns = 0
        self.base = datetime(2026, 9, 17, tzinfo=UTC)

    def now_utc(self) -> datetime:
        return self.base + timedelta(seconds=self.ns / 1_000_000_000)

    def monotonic_ns(self) -> int:
        return self.ns

    def sleep(self, seconds: float) -> None:
        self.ns += int(seconds * 1_000_000_000)


class FakeMotorBackend:
    def __init__(self) -> None:
        self.forward_calls: list[float] = []
        self.stop_calls = 0

    def drive_forward(self, duty_cycle: float) -> None:
        self.forward_calls.append(duty_cycle)

    def stop(self) -> None:
        self.stop_calls += 1


class FakeRangeSensor:
    def __init__(self, sensor_id: str, values: list[float]) -> None:
        self._sensor_id = sensor_id
        self._values = list(values)
        self._last = self._values[-1]

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    def read_distance_m(self) -> float:
        if self._values:
            self._last = self._values.pop(0)
        return self._last


class FakeEstop:
    def __init__(self, *, closed: bool = True) -> None:
        self.closed = closed

    def circuit_closed(self) -> bool:
        return self.closed


def _calibration() -> R0BenchCalibrationV1:
    return R0BenchCalibrationV1(
        calibrated_max_speed_mps=0.25,
        max_duty_cycle=0.80,
        motion_start_delta_m=0.02,
        motion_start_timeout_s=1.0,
        sample_interval_s=0.05,
        stationary_window_s=0.30,
    )


def _motion(speed: float = 0.10) -> RangerR0MotionDirectiveV1:
    return RangerR0MotionDirectiveV1(
        mission_id=MISSION_ID,
        delivery_id="delivery-1",
        vehicle_id="ets-ranger:r0-demo",
        controller_id="ranger-controller:r0",
        issued_at=datetime(2026, 9, 17, tzinfo=UTC),
        issued_monotonic_ns=1,
        linear_speed_mps=speed,
        max_distance_m=1.0,
        max_duration_s=10,
        stop_distance_m=0.45,
    )


def _stop() -> RangerR0StopDirectiveV1:
    return RangerR0StopDirectiveV1(
        mission_id=MISSION_ID,
        vehicle_id="ets-ranger:r0-demo",
        controller_id="ranger-controller:r0",
        stop_reason=RangerR0StopReason.OBSTACLE_WITHIN_STOP_DISTANCE,
        issued_at=datetime(2026, 9, 17, tzinfo=UTC),
        issued_monotonic_ns=2,
    )


def test_drv8833_actuator_maps_authorized_speed_to_bounded_duty_cycle() -> None:
    clock = FakeClock()
    backend = FakeMotorBackend()
    actuator = Drv8833R0Actuator(backend, _calibration(), clock=clock)

    receipt = actuator.apply_motion(_motion(0.10))

    assert receipt.accepted is True
    assert receipt.command_kind == "motion"
    assert backend.forward_calls == [pytest.approx(0.32)]


def test_drv8833_actuator_rejects_speed_above_frozen_calibration() -> None:
    backend = FakeMotorBackend()
    calibration = R0BenchCalibrationV1(
        calibrated_max_speed_mps=0.15,
        max_duty_cycle=0.75,
    )
    actuator = Drv8833R0Actuator(backend, calibration, clock=FakeClock())

    receipt = actuator.apply_motion(_motion(0.20))

    assert receipt.accepted is False
    assert "calibration ceiling" in (receipt.reason or "")
    assert backend.forward_calls == []


def test_drv8833_stop_and_fail_safe_are_controller_acknowledgements_only() -> None:
    backend = FakeMotorBackend()
    actuator = Drv8833R0Actuator(backend, _calibration(), clock=FakeClock())

    stop_receipt = actuator.apply_stop(_stop())
    fail_safe_receipt = actuator.fail_safe_stop(MISSION_ID, reason="test")

    assert stop_receipt.accepted is True
    assert stop_receipt.claim_boundary == "controller_acknowledgement_not_physical_observation"
    assert fail_safe_receipt.command_kind == "fail_safe_stop"
    assert backend.stop_calls == 2


def test_open_normally_closed_estop_fails_closed_before_motion() -> None:
    sensors = DualRangeR0PhysicalSensors(
        front_sensor=FakeRangeSensor("front", [1.0]),
        rear_sensor=FakeRangeSensor("rear", [1.0]),
        estop=FakeEstop(closed=False),
        calibration=_calibration(),
        clock=FakeClock(),
    )

    assert sensors.hardware_estop_asserted() is True


def test_dual_range_suite_observes_motion_obstacle_and_stopped_result() -> None:
    clock = FakeClock()
    sensors = DualRangeR0PhysicalSensors(
        front_sensor=FakeRangeSensor("front", [0.40]),
        rear_sensor=FakeRangeSensor(
            "rear",
            [1.000, 1.005, 1.030, 1.100, 1.100, 1.101],
        ),
        estop=FakeEstop(),
        calibration=_calibration(),
        clock=clock,
    )

    assert sensors.hardware_estop_asserted() is False
    started = sensors.observe_motion_start(MISSION_ID, _motion())
    stop_observation = sensors.observe_stop_condition(MISSION_ID, _motion())
    result = sensors.observe_result(MISSION_ID, _stop())

    assert started.distance_travelled_m == pytest.approx(0.03)
    assert started.source_kind == "independent_motion_sensor"
    assert stop_observation.obstacle_distance_m == pytest.approx(0.40)
    assert stop_observation.distance_travelled_m == pytest.approx(0.10)
    assert stop_observation.source_kind == "independent_stop_sensor"
    assert result.speed_mps < 0.02
    assert result.stationary_duration_ms >= 250
    assert result.distance_travelled_m == pytest.approx(0.101)
    assert result.source_kind == "independent_result_sensor"


def test_dual_range_suite_rejects_duplicate_sensor_identity() -> None:
    with pytest.raises(ValueError, match="distinct sensor IDs"):
        DualRangeR0PhysicalSensors(
            front_sensor=FakeRangeSensor("same", [1.0]),
            rear_sensor=FakeRangeSensor("same", [1.0]),
            estop=FakeEstop(),
            calibration=_calibration(),
            clock=FakeClock(),
        )
