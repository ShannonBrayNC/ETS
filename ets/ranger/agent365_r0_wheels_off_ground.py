"""Bounded wheels-off-ground qualification for the physical R0 bench profile."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from time import monotonic_ns, sleep
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.ranger.agent365_r0_bench_hardware import (
    DifferentialMotorBackend,
    NormallyClosedEstopBackend,
    RangeSensorBackend,
)

HARDWARE_PROFILE: Literal["r0-bench-pi-drv8833-dual-vl53l0x.v1"] = (
    "r0-bench-pi-drv8833-dual-vl53l0x.v1"
)


class StrictWheelsOffGroundModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class R0WheelsOffGroundConfigV1(StrictWheelsOffGroundModel):
    schema_version: Literal["ets.demo.agent365-r0.wheels-off-ground-config.v1"] = (
        "ets.demo.agent365-r0.wheels-off-ground-config.v1"
    )
    duty_cycle: float = Field(default=0.20, gt=0.0, le=0.35)
    pulse_seconds: float = Field(default=0.40, gt=0.0, le=1.0)
    poll_interval_seconds: float = Field(default=0.02, ge=0.01, le=0.10)
    settle_seconds: float = Field(default=0.15, ge=0.05, le=0.50)
    max_rear_translation_m: float = Field(default=0.03, gt=0.0, le=0.05)


class R0WheelsOffGroundResultV1(StrictWheelsOffGroundModel):
    schema_version: Literal["ets.demo.agent365-r0.wheels-off-ground-result.v1"] = (
        "ets.demo.agent365-r0.wheels-off-ground-result.v1"
    )
    profile: Literal["r0-bench-pi-drv8833-dual-vl53l0x.v1"] = HARDWARE_PROFILE
    gate: Literal["B_wheels_off_ground"] = "B_wheels_off_ground"
    observed_at: datetime
    duty_cycle: float
    pulse_seconds: float
    front_distance_before_m: float
    front_distance_after_m: float
    rear_distance_before_m: float
    rear_distance_after_m: float
    rear_translation_m: float
    max_rear_translation_m: float
    rear_translation_within_limit: bool
    estop_circuit_closed_before: bool
    estop_asserted_during_pulse: bool
    stop_command_completed_after: bool
    automated_checks_passed: bool
    controller_acknowledgement_proves_translation: Literal[False] = False
    wheel_direction_inferred: Literal[False] = False
    claim_boundary: Literal[
        "supported_chassis_bench_actuation_only_operator_must_confirm_wheel_direction"
    ] = "supported_chassis_bench_actuation_only_operator_must_confirm_wheel_direction"

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("wheels-off-ground observation time must be timezone-aware")
        return value.astimezone(UTC)


class R0WheelsOffGroundClock(Protocol):
    def now_utc(self) -> datetime: ...

    def monotonic_ns(self) -> int: ...

    def sleep(self, seconds: float) -> None: ...


class SystemR0WheelsOffGroundClock:
    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    def monotonic_ns(self) -> int:
        return monotonic_ns()

    def sleep(self, seconds: float) -> None:
        sleep(seconds)


class R0WheelsOffGroundError(RuntimeError):
    """Raised when the bounded bench pulse cannot be executed safely."""


def run_wheels_off_ground_pulse(
    *,
    motor: DifferentialMotorBackend,
    front_sensor: RangeSensorBackend,
    rear_sensor: RangeSensorBackend,
    estop: NormallyClosedEstopBackend,
    config: R0WheelsOffGroundConfigV1,
    clock: R0WheelsOffGroundClock | None = None,
) -> R0WheelsOffGroundResultV1:
    """Run one bounded motor pulse while the chassis is physically supported.

    The returned record never infers chassis motion or wheel direction from the motor command.
    """

    local_clock = clock or SystemR0WheelsOffGroundClock()
    if front_sensor.sensor_id == rear_sensor.sensor_id:
        raise R0WheelsOffGroundError("front and rear sensors must have distinct identities")

    motor.stop()
    estop_closed_before = _estop_closed(estop)
    if not estop_closed_before:
        raise R0WheelsOffGroundError(
            "normally-closed E-stop circuit is open/asserted before bench actuation"
        )

    front_before = _read_distance(front_sensor, "front")
    rear_before = _read_distance(rear_sensor, "rear")
    estop_asserted_during = False
    stop_completed = False

    start_ns = local_clock.monotonic_ns()
    deadline_ns = start_ns + int(config.pulse_seconds * 1_000_000_000)
    try:
        motor.drive_forward(config.duty_cycle)
        while local_clock.monotonic_ns() < deadline_ns:
            if not _estop_closed(estop):
                estop_asserted_during = True
                break
            local_clock.sleep(config.poll_interval_seconds)
    finally:
        motor.stop()
        stop_completed = True

    local_clock.sleep(config.settle_seconds)
    front_after = _read_distance(front_sensor, "front")
    rear_after = _read_distance(rear_sensor, "rear")
    rear_translation = abs(rear_after - rear_before)
    within_limit = rear_translation <= config.max_rear_translation_m
    automated_pass = (
        estop_closed_before
        and not estop_asserted_during
        and stop_completed
        and within_limit
    )

    return R0WheelsOffGroundResultV1(
        observed_at=local_clock.now_utc(),
        duty_cycle=config.duty_cycle,
        pulse_seconds=config.pulse_seconds,
        front_distance_before_m=front_before,
        front_distance_after_m=front_after,
        rear_distance_before_m=rear_before,
        rear_distance_after_m=rear_after,
        rear_translation_m=rear_translation,
        max_rear_translation_m=config.max_rear_translation_m,
        rear_translation_within_limit=within_limit,
        estop_circuit_closed_before=estop_closed_before,
        estop_asserted_during_pulse=estop_asserted_during,
        stop_command_completed_after=stop_completed,
        automated_checks_passed=automated_pass,
    )


def _estop_closed(estop: NormallyClosedEstopBackend) -> bool:
    try:
        return bool(estop.circuit_closed())
    except Exception:
        return False


def _read_distance(sensor: RangeSensorBackend, label: str) -> float:
    try:
        value = float(sensor.read_distance_m())
    except Exception as exc:
        raise R0WheelsOffGroundError(
            f"{label} range sensor could not provide a bench observation"
        ) from exc
    if not math.isfinite(value) or not 0.01 <= value <= 10.0:
        raise R0WheelsOffGroundError(f"{label} range sensor returned an invalid distance")
    return value


__all__ = [
    "R0WheelsOffGroundConfigV1",
    "R0WheelsOffGroundError",
    "R0WheelsOffGroundResultV1",
    "R0WheelsOffGroundClock",
    "SystemR0WheelsOffGroundClock",
    "run_wheels_off_ground_pulse",
]
