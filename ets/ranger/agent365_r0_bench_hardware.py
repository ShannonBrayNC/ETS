"""Concrete bench-hardware adapters for the frozen Agent 365 + Ranger R0 demo.

The bench profile keeps the motor-controller acknowledgement separate from independent physical
observation. The DRV8833 adapter can only report controller-side command acceptance. Motion,
stop conditions, and the final stopped state are derived from a separate dual-range-sensor suite
plus a normally-closed hardware E-stop input.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from importlib import import_module
from time import monotonic_ns, sleep
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ets.ranger.agent365_r0_boundary import (
    RangerR0MotionDirectiveV1,
    RangerR0MotionStartObservationV1,
    RangerR0ResultObservationV1,
    RangerR0StopDirectiveV1,
    RangerR0StopObservationV1,
)
from ets.ranger.agent365_r0_physical import (
    RangerR0ActuatorReceiptV1,
    RangerR0PhysicalExecutionError,
)


class StrictBenchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class R0BenchCalibrationV1(StrictBenchModel):
    """Frozen motor/sampling limits for one bench qualification profile."""

    schema_version: str = "ets.demo.agent365-r0.bench-calibration.v1"
    calibrated_max_speed_mps: float = Field(gt=0.0, le=0.25)
    max_duty_cycle: float = Field(gt=0.0, le=1.0)
    motion_start_delta_m: float = Field(default=0.02, gt=0.0, le=0.25)
    motion_start_timeout_s: float = Field(default=1.5, gt=0.0, le=5.0)
    sample_interval_s: float = Field(default=0.05, ge=0.01, le=0.5)
    stationary_window_s: float = Field(default=0.30, ge=0.25, le=2.0)


class DifferentialMotorBackend(Protocol):
    """Low-level motor backend. It must not create physical-state evidence."""

    def drive_forward(self, duty_cycle: float) -> None: ...

    def stop(self) -> None: ...


class RangeSensorBackend(Protocol):
    """Independent distance source used for physical-state observations."""

    @property
    def sensor_id(self) -> str: ...

    def read_distance_m(self) -> float: ...


class NormallyClosedEstopBackend(Protocol):
    """Normally-closed E-stop circuit; False/open is treated as asserted."""

    def circuit_closed(self) -> bool: ...


class R0BenchSampleClock(Protocol):
    def now_utc(self) -> datetime: ...

    def monotonic_ns(self) -> int: ...

    def sleep(self, seconds: float) -> None: ...


class SystemR0BenchSampleClock:
    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    def monotonic_ns(self) -> int:
        return monotonic_ns()

    def sleep(self, seconds: float) -> None:
        sleep(seconds)


class Drv8833R0Actuator:
    """Bounded forward/stop actuator for a two-motor DRV8833 bench platform."""

    def __init__(
        self,
        backend: DifferentialMotorBackend,
        calibration: R0BenchCalibrationV1,
        *,
        actuator_id: str = "r0-bench:drv8833",
        clock: R0BenchSampleClock | None = None,
    ) -> None:
        if not actuator_id:
            raise ValueError("actuator_id must not be empty")
        self._backend = backend
        self._calibration = calibration
        self._actuator_id = actuator_id
        self._clock = clock or SystemR0BenchSampleClock()

    @property
    def actuator_id(self) -> str:
        return self._actuator_id

    def apply_motion(
        self,
        directive: RangerR0MotionDirectiveV1,
    ) -> RangerR0ActuatorReceiptV1:
        if directive.linear_speed_mps > self._calibration.calibrated_max_speed_mps:
            return self._receipt(
                directive.mission_id,
                command_kind="motion",
                accepted=False,
                reason="requested speed exceeds the frozen bench calibration ceiling",
            )

        duty_cycle = (
            directive.linear_speed_mps
            / self._calibration.calibrated_max_speed_mps
            * self._calibration.max_duty_cycle
        )
        duty_cycle = max(0.0, min(duty_cycle, self._calibration.max_duty_cycle))
        try:
            self._backend.drive_forward(duty_cycle)
        except Exception as exc:
            raise RangerR0PhysicalExecutionError(
                "motor_backend_motion_failed",
                "DRV8833 backend failed while applying the authorized forward command",
            ) from exc

        return self._receipt(
            directive.mission_id,
            command_kind="motion",
            accepted=True,
            reason=f"forward duty cycle {duty_cycle:.4f}",
        )

    def apply_stop(
        self,
        directive: RangerR0StopDirectiveV1,
    ) -> RangerR0ActuatorReceiptV1:
        try:
            self._backend.stop()
        except Exception as exc:
            raise RangerR0PhysicalExecutionError(
                "motor_backend_stop_failed",
                "DRV8833 backend failed while applying the stop command",
            ) from exc
        return self._receipt(
            directive.mission_id,
            command_kind="stop",
            accepted=True,
            reason=directive.stop_reason.value,
        )

    def fail_safe_stop(
        self,
        mission_id: str,
        *,
        reason: str,
    ) -> RangerR0ActuatorReceiptV1:
        try:
            self._backend.stop()
        except Exception as exc:
            raise RangerR0PhysicalExecutionError(
                "motor_backend_fail_safe_stop_failed",
                "DRV8833 backend failed while applying the local fail-safe stop",
            ) from exc
        return self._receipt(
            mission_id,
            command_kind="fail_safe_stop",
            accepted=True,
            reason=reason,
        )

    def _receipt(
        self,
        mission_id: str,
        *,
        command_kind: Literal["motion", "stop", "fail_safe_stop"],
        accepted: bool,
        reason: str | None,
    ) -> RangerR0ActuatorReceiptV1:
        return RangerR0ActuatorReceiptV1(
            mission_id=mission_id,
            actuator_id=self.actuator_id,
            command_kind=command_kind,
            accepted=accepted,
            observed_at=self._clock.now_utc(),
            observed_monotonic_ns=self._clock.monotonic_ns(),
            reason=reason,
        )


class DualRangeR0PhysicalSensors:
    """Independent physical observer using rear travel range + front obstacle range."""

    def __init__(
        self,
        *,
        front_sensor: RangeSensorBackend,
        rear_sensor: RangeSensorBackend,
        estop: NormallyClosedEstopBackend,
        calibration: R0BenchCalibrationV1,
        observer_id: str = "r0-bench:dual-vl53l0x",
        clock: R0BenchSampleClock | None = None,
    ) -> None:
        if not observer_id:
            raise ValueError("observer_id must not be empty")
        if front_sensor.sensor_id == rear_sensor.sensor_id:
            raise ValueError("front and rear range sensors must have distinct sensor IDs")
        self._front = front_sensor
        self._rear = rear_sensor
        self._estop = estop
        self._calibration = calibration
        self._observer_id = observer_id
        self._clock = clock or SystemR0BenchSampleClock()
        self._baseline_rear_m: float | None = None
        self._mission_id: str | None = None
        self._motion_start_ns: int | None = None

    @property
    def observer_id(self) -> str:
        return self._observer_id

    def hardware_estop_asserted(self) -> bool:
        try:
            closed = self._estop.circuit_closed()
        except Exception:
            return True
        if not closed:
            return True
        if self._baseline_rear_m is None:
            self._baseline_rear_m = self._read_range(self._rear, "rear")
        return False

    def observe_motion_start(
        self,
        mission_id: str,
        directive: RangerR0MotionDirectiveV1,
    ) -> RangerR0MotionStartObservationV1:
        baseline = self._require_baseline()
        start_ns = self._clock.monotonic_ns()
        deadline_ns = start_ns + int(self._calibration.motion_start_timeout_s * 1_000_000_000)

        while self._clock.monotonic_ns() <= deadline_ns:
            if self.hardware_estop_asserted():
                raise RangerR0PhysicalExecutionError(
                    "hardware_estop_asserted_during_motion_start",
                    "hardware E-stop opened while waiting for independent motion observation",
                )
            now_ns = self._clock.monotonic_ns()
            rear_m = self._read_range(self._rear, "rear")
            travelled_m = max(0.0, rear_m - baseline)
            elapsed_s = max(
                (now_ns - start_ns) / 1_000_000_000,
                self._calibration.sample_interval_s,
            )
            if travelled_m >= self._calibration.motion_start_delta_m:
                self._mission_id = mission_id
                self._motion_start_ns = start_ns
                return RangerR0MotionStartObservationV1(
                    mission_id=mission_id,
                    observer_id=self.observer_id,
                    observed_at=self._clock.now_utc(),
                    observed_monotonic_ns=now_ns,
                    speed_mps=travelled_m / elapsed_s,
                    distance_travelled_m=travelled_m,
                )
            self._clock.sleep(self._calibration.sample_interval_s)

        raise RangerR0PhysicalExecutionError(
            "motion_not_independently_observed",
            "rear range witness did not observe the required forward displacement",
        )

    def observe_stop_condition(
        self,
        mission_id: str,
        directive: RangerR0MotionDirectiveV1,
    ) -> RangerR0StopObservationV1:
        self._require_active_mission(mission_id)
        baseline = self._require_baseline()
        start_ns = self._require_motion_start_ns()
        now_ns = self._clock.monotonic_ns()
        rear_m = self._read_range(self._rear, "rear")
        front_m = self._read_range(self._front, "front")
        return RangerR0StopObservationV1(
            mission_id=mission_id,
            observer_id=self.observer_id,
            observed_at=self._clock.now_utc(),
            observed_monotonic_ns=now_ns,
            distance_travelled_m=max(0.0, rear_m - baseline),
            elapsed_s=max(0.0, (now_ns - start_ns) / 1_000_000_000),
            obstacle_distance_m=front_m,
            hardware_estop_asserted=self.hardware_estop_asserted(),
        )

    def observe_result(
        self,
        mission_id: str,
        stop_directive: RangerR0StopDirectiveV1,
    ) -> RangerR0ResultObservationV1:
        self._require_active_mission(mission_id)
        baseline = self._require_baseline()
        first_m = self._read_range(self._rear, "rear")
        first_ns = self._clock.monotonic_ns()
        self._clock.sleep(self._calibration.stationary_window_s)
        second_m = self._read_range(self._rear, "rear")
        second_ns = self._clock.monotonic_ns()
        elapsed_s = max(
            (second_ns - first_ns) / 1_000_000_000,
            self._calibration.stationary_window_s,
        )
        speed_mps = abs(second_m - first_m) / elapsed_s
        return RangerR0ResultObservationV1(
            mission_id=mission_id,
            observer_id=self.observer_id,
            observed_at=self._clock.now_utc(),
            observed_monotonic_ns=second_ns,
            speed_mps=speed_mps,
            distance_travelled_m=max(0.0, second_m - baseline),
            stationary_duration_ms=int(elapsed_s * 1000),
        )

    def _require_baseline(self) -> float:
        if self._baseline_rear_m is None:
            raise RangerR0PhysicalExecutionError(
                "rear_range_baseline_missing",
                "rear range baseline was not captured before physical motion",
            )
        return self._baseline_rear_m

    def _require_active_mission(self, mission_id: str) -> None:
        if self._mission_id != mission_id:
            raise RangerR0PhysicalExecutionError(
                "sensor_mission_mismatch",
                "physical sensor suite is not armed for this mission_id",
            )

    def _require_motion_start_ns(self) -> int:
        if self._motion_start_ns is None:
            raise RangerR0PhysicalExecutionError(
                "motion_start_time_missing",
                "physical sensor suite has no independent motion-start timestamp",
            )
        return self._motion_start_ns

    @staticmethod
    def _read_range(sensor: RangeSensorBackend, label: str) -> float:
        try:
            value = float(sensor.read_distance_m())
        except Exception as exc:
            raise RangerR0PhysicalExecutionError(
                f"{label}_range_sensor_failed",
                f"{label} range sensor could not provide an independent observation",
            ) from exc
        if not math.isfinite(value) or not 0.01 <= value <= 10.0:
            raise RangerR0PhysicalExecutionError(
                f"{label}_range_sensor_invalid",
                f"{label} range sensor returned an invalid distance",
            )
        return value


class GpioZeroDrv8833Backend:
    """Raspberry Pi gpiozero binding for DRV8833 AIN1/AIN2/BIN1/BIN2."""

    def __init__(
        self,
        *,
        left_in1_pin: int,
        left_in2_pin: int,
        right_in1_pin: int,
        right_in2_pin: int,
        frequency_hz: int = 1000,
    ) -> None:
        try:
            gpiozero = import_module("gpiozero")
        except ImportError as exc:
            raise RuntimeError(
                "gpiozero is required for the Raspberry Pi DRV8833 backend"
            ) from exc
        pwm_output_device = vars(gpiozero)["PWMOutputDevice"]

        self._left_in1 = pwm_output_device(left_in1_pin, frequency=frequency_hz)
        self._left_in2 = pwm_output_device(left_in2_pin, frequency=frequency_hz)
        self._right_in1 = pwm_output_device(right_in1_pin, frequency=frequency_hz)
        self._right_in2 = pwm_output_device(right_in2_pin, frequency=frequency_hz)
        self.stop()

    def drive_forward(self, duty_cycle: float) -> None:
        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError("duty_cycle must be in [0, 1]")
        self._left_in2.value = 0.0
        self._right_in2.value = 0.0
        self._left_in1.value = duty_cycle
        self._right_in1.value = duty_cycle

    def stop(self) -> None:
        self._left_in1.value = 0.0
        self._left_in2.value = 0.0
        self._right_in1.value = 0.0
        self._right_in2.value = 0.0

    def close(self) -> None:
        self.stop()
        for device in (
            self._left_in1,
            self._left_in2,
            self._right_in1,
            self._right_in2,
        ):
            device.close()


class GpioZeroNormallyClosedEstop:
    """Normally-closed E-stop binding.

    Wire the NC circuit between the configured GPIO input and ground. The internal pull-up means
    a healthy closed circuit reads low. Opening the E-stop circuit, unplugging the wire, or losing
    the ground path reads high and therefore fails closed.
    """

    def __init__(self, pin: int, *, bounce_time_s: float = 0.02) -> None:
        try:
            gpiozero = import_module("gpiozero")
        except ImportError as exc:
            raise RuntimeError("gpiozero is required for the Raspberry Pi E-stop backend") from exc
        digital_input_device = vars(gpiozero)["DigitalInputDevice"]
        self._input = digital_input_device(pin, pull_up=True, bounce_time=bounce_time_s)

    def circuit_closed(self) -> bool:
        return not bool(self._input.value)

    def close(self) -> None:
        self._input.close()


class AdafruitVL53L0XRangeBackend:
    """Adapter for one configured Adafruit CircuitPython VL53L0X object."""

    def __init__(self, sensor_id: str, sensor: Any, *, keepalive: tuple[Any, ...] = ()) -> None:
        if not sensor_id:
            raise ValueError("sensor_id must not be empty")
        self._sensor_id = sensor_id
        self._sensor = sensor
        self._keepalive = keepalive

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    def read_distance_m(self) -> float:
        distance_mm = float(self._sensor.range)
        return distance_mm / 1000.0


def create_dual_vl53l0x_backends(
    *,
    front_xshut_pin: int,
    rear_xshut_pin: int,
    front_address: int = 0x30,
    rear_address: int = 0x31,
) -> tuple[AdafruitVL53L0XRangeBackend, AdafruitVL53L0XRangeBackend]:
    """Bring up two VL53L0X sensors with separate I2C addresses using XSHUT pins."""

    if front_address == rear_address or front_address == 0x29 or rear_address == 0x29:
        raise ValueError("front/rear addresses must be distinct and must not remain at 0x29")
    try:
        adafruit_vl53l0x = import_module("adafruit_vl53l0x")
        board = import_module("board")
        gpiozero = import_module("gpiozero")
    except ImportError as exc:
        raise RuntimeError(
            "adafruit-circuitpython-vl53l0x, Adafruit-Blinka, and gpiozero are required"
        ) from exc
    digital_output_device = vars(gpiozero)["DigitalOutputDevice"]
    vl53l0x_type = vars(adafruit_vl53l0x)["VL53L0X"]
    i2c_factory = vars(board)["I2C"]

    front_gate = digital_output_device(front_xshut_pin, initial_value=False)
    rear_gate = digital_output_device(rear_xshut_pin, initial_value=False)
    sleep(0.05)
    i2c = i2c_factory()

    front_gate.on()
    sleep(0.05)
    front_sensor = vl53l0x_type(i2c)
    front_sensor.set_address(front_address)

    rear_gate.on()
    sleep(0.05)
    rear_sensor = vl53l0x_type(i2c)
    rear_sensor.set_address(rear_address)

    keepalive = (front_gate, rear_gate, i2c)
    return (
        AdafruitVL53L0XRangeBackend(
            "r0-bench:vl53l0x:front",
            front_sensor,
            keepalive=keepalive,
        ),
        AdafruitVL53L0XRangeBackend(
            "r0-bench:vl53l0x:rear",
            rear_sensor,
            keepalive=keepalive,
        ),
    )


__all__ = [
    "AdafruitVL53L0XRangeBackend",
    "DifferentialMotorBackend",
    "Drv8833R0Actuator",
    "DualRangeR0PhysicalSensors",
    "GpioZeroDrv8833Backend",
    "GpioZeroNormallyClosedEstop",
    "NormallyClosedEstopBackend",
    "R0BenchCalibrationV1",
    "R0BenchSampleClock",
    "RangeSensorBackend",
    "SystemR0BenchSampleClock",
    "create_dual_vl53l0x_backends",
]
