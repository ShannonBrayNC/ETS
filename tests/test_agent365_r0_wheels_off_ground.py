from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.ranger.agent365_r0_wheels_off_ground import (
    R0WheelsOffGroundConfigV1,
    R0WheelsOffGroundError,
    run_wheels_off_ground_pulse,
)


class FakeClock:
    def __init__(self) -> None:
        self.ns = 0
        self.base = datetime(2026, 9, 18, tzinfo=UTC)

    def now_utc(self) -> datetime:
        return self.base + timedelta(seconds=self.ns / 1_000_000_000)

    def monotonic_ns(self) -> int:
        return self.ns

    def sleep(self, seconds: float) -> None:
        self.ns += int(seconds * 1_000_000_000)


class FakeMotor:
    def __init__(self) -> None:
        self.drive_calls: list[float] = []
        self.stop_calls = 0

    def drive_forward(self, duty_cycle: float) -> None:
        self.drive_calls.append(duty_cycle)

    def stop(self) -> None:
        self.stop_calls += 1


class FakeRange:
    def __init__(self, sensor_id: str, values: list[float]) -> None:
        self._sensor_id = sensor_id
        self._values = list(values)

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    def read_distance_m(self) -> float:
        if len(self._values) > 1:
            return self._values.pop(0)
        return self._values[0]


class FakeEstop:
    def __init__(self, states: list[bool]) -> None:
        self._states = list(states)

    def circuit_closed(self) -> bool:
        if len(self._states) > 1:
            return self._states.pop(0)
        return self._states[0]


def test_wheels_off_ground_pulse_passes_without_translation() -> None:
    motor = FakeMotor()
    result = run_wheels_off_ground_pulse(
        motor=motor,
        front_sensor=FakeRange("front", [0.8, 0.8]),
        rear_sensor=FakeRange("rear", [1.0, 1.01]),
        estop=FakeEstop([True]),
        config=R0WheelsOffGroundConfigV1(
            duty_cycle=0.20,
            pulse_seconds=0.10,
            poll_interval_seconds=0.02,
            settle_seconds=0.05,
            max_rear_translation_m=0.03,
        ),
        clock=FakeClock(),
    )

    assert result.automated_checks_passed is True
    assert result.rear_translation_within_limit is True
    assert result.controller_acknowledgement_proves_translation is False
    assert result.wheel_direction_inferred is False
    assert motor.drive_calls == [0.20]
    assert motor.stop_calls >= 2


def test_wheels_off_ground_pulse_fails_closed_on_estop_open() -> None:
    motor = FakeMotor()
    result = run_wheels_off_ground_pulse(
        motor=motor,
        front_sensor=FakeRange("front", [0.8, 0.8]),
        rear_sensor=FakeRange("rear", [1.0, 1.0]),
        estop=FakeEstop([True, True, False]),
        config=R0WheelsOffGroundConfigV1(
            duty_cycle=0.20,
            pulse_seconds=0.20,
            poll_interval_seconds=0.02,
            settle_seconds=0.05,
        ),
        clock=FakeClock(),
    )

    assert result.estop_asserted_during_pulse is True
    assert result.automated_checks_passed is False
    assert motor.stop_calls >= 2


def test_wheels_off_ground_rejects_open_estop_before_actuation() -> None:
    motor = FakeMotor()

    with pytest.raises(R0WheelsOffGroundError, match="open/asserted"):
        run_wheels_off_ground_pulse(
            motor=motor,
            front_sensor=FakeRange("front", [0.8]),
            rear_sensor=FakeRange("rear", [1.0]),
            estop=FakeEstop([False]),
            config=R0WheelsOffGroundConfigV1(),
            clock=FakeClock(),
        )

    assert motor.drive_calls == []
    assert motor.stop_calls == 1


def test_wheels_off_ground_reports_translation_instead_of_hiding_it() -> None:
    result = run_wheels_off_ground_pulse(
        motor=FakeMotor(),
        front_sensor=FakeRange("front", [0.8, 0.8]),
        rear_sensor=FakeRange("rear", [1.0, 1.08]),
        estop=FakeEstop([True]),
        config=R0WheelsOffGroundConfigV1(
            pulse_seconds=0.10,
            settle_seconds=0.05,
            max_rear_translation_m=0.03,
        ),
        clock=FakeClock(),
    )

    assert result.rear_translation_within_limit is False
    assert result.automated_checks_passed is False
    assert result.rear_translation_m == pytest.approx(0.08)
