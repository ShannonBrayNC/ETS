"""Hardware-facing execution adapter for the frozen Agent 365 + Ranger R0 mission.

This module sits below the existing evidence/state-machine boundary. It deliberately keeps
controller acknowledgement separate from independent physical observation: an actuator receipt
can prove only that a controller accepted a command, while the existing Ranger observation
models are required to support claims about motion, stop triggers, and the resulting state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic_ns
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.ranger.agent365_r0_boundary import (
    RangerR0BoundaryRecordV1,
    RangerR0MotionDirectiveV1,
    RangerR0MotionStartObservationV1,
    RangerR0ReceiptMotionBoundary,
    RangerR0ResultObservationV1,
    RangerR0StopDirectiveV1,
    RangerR0StopObservationV1,
)


class RangerR0PhysicalExecutionError(RuntimeError):
    """Raised when physical execution cannot safely complete the frozen R0 contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class RangerR0ActuatorReceiptV1(BaseModel):
    """Controller acknowledgement that is never promoted into sensor/result evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.actuator-receipt.v1"] = (
        "ets.demo.agent365-r0.actuator-receipt.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    actuator_id: str = Field(min_length=1, max_length=256)
    command_kind: Literal["motion", "stop", "fail_safe_stop"]
    accepted: bool
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    reason: str | None = Field(default=None, max_length=512)
    claim_boundary: Literal["controller_acknowledgement_not_physical_observation"] = (
        "controller_acknowledgement_not_physical_observation"
    )

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("actuator receipt time must be timezone-aware")
        return value.astimezone(UTC)


class RangerR0PhysicalRunResultV1(BaseModel):
    """Typed result from one completed physical execution through the seven-stage boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.physical-run.v1"] = (
        "ets.demo.agent365-r0.physical-run.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    boundary_records: tuple[RangerR0BoundaryRecordV1, ...]
    motion_directive: RangerR0MotionDirectiveV1
    motion_actuator_receipt: RangerR0ActuatorReceiptV1
    stop_directive: RangerR0StopDirectiveV1
    stop_actuator_receipt: RangerR0ActuatorReceiptV1
    independent_physical_result_observed: Literal[True] = True
    claim_boundary: Literal[
        "physical_run_contains_distinct_actuation_and_independent_observation_evidence"
    ] = "physical_run_contains_distinct_actuation_and_independent_observation_evidence"


class RangerR0PhysicalActuator(Protocol):
    """Vendor-neutral actuation boundary implemented by the actual R0 controller driver."""

    @property
    def actuator_id(self) -> str: ...

    def apply_motion(
        self,
        directive: RangerR0MotionDirectiveV1,
    ) -> RangerR0ActuatorReceiptV1: ...

    def apply_stop(
        self,
        directive: RangerR0StopDirectiveV1,
    ) -> RangerR0ActuatorReceiptV1: ...

    def fail_safe_stop(
        self,
        mission_id: str,
        *,
        reason: str,
    ) -> RangerR0ActuatorReceiptV1: ...


class RangerR0PhysicalSensors(Protocol):
    """Independent physical-observation boundary; must not proxy controller acknowledgements."""

    def hardware_estop_asserted(self) -> bool: ...

    def observe_motion_start(
        self,
        mission_id: str,
        directive: RangerR0MotionDirectiveV1,
    ) -> RangerR0MotionStartObservationV1: ...

    def observe_stop_condition(
        self,
        mission_id: str,
        directive: RangerR0MotionDirectiveV1,
    ) -> RangerR0StopObservationV1: ...

    def observe_result(
        self,
        mission_id: str,
        stop_directive: RangerR0StopDirectiveV1,
    ) -> RangerR0ResultObservationV1: ...


class RangerR0PhysicalClock(Protocol):
    """Local host clock used for robot-side policy decisions, separate from sensor timestamps."""

    def now_utc(self) -> datetime: ...

    def monotonic_ns(self) -> int: ...


class SystemRangerR0PhysicalClock:
    """Production local clock implementation."""

    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    def monotonic_ns(self) -> int:
        return monotonic_ns()


def execute_physical_r0_mission(
    boundary: RangerR0ReceiptMotionBoundary,
    mission_id: str,
    *,
    actuator: RangerR0PhysicalActuator,
    sensors: RangerR0PhysicalSensors,
    clock: RangerR0PhysicalClock | None = None,
    maximum_stop_observations: int = 10_000,
) -> RangerR0PhysicalRunResultV1:
    """Execute one already-received mission through real actuation and sensor observations.

    The caller must first pass the Gateway command through ``boundary.receive``. This function
    begins at local motion authorization and fails safe if physical observation disappears after
    motion is commanded.
    """

    if not mission_id:
        raise ValueError("mission_id must not be empty")
    if not 1 <= maximum_stop_observations <= 100_000:
        raise ValueError("maximum_stop_observations must be between 1 and 100000")
    local_clock = clock or SystemRangerR0PhysicalClock()

    if sensors.hardware_estop_asserted():
        raise RangerR0PhysicalExecutionError(
            "hardware_estop_asserted",
            "physical execution denied while the local hardware E-stop is asserted",
        )

    authorized = boundary.authorize_motion(
        mission_id,
        observed_at=local_clock.now_utc(),
        observed_monotonic_ns=local_clock.monotonic_ns(),
        hardware_estop_asserted=False,
    )
    motion_command_attempted = False
    try:
        motion_command_attempted = True
        motion_receipt = actuator.apply_motion(authorized.directive)
        _require_actuator_receipt(
            motion_receipt,
            mission_id=mission_id,
            actuator_id=actuator.actuator_id,
            command_kind="motion",
        )

        motion_observation = sensors.observe_motion_start(mission_id, authorized.directive)
        motion_started = boundary.record_motion_started(motion_observation)

        stop_observed: RangerR0BoundaryRecordV1 | None = None
        for _ in range(maximum_stop_observations):
            if sensors.hardware_estop_asserted():
                raise RangerR0PhysicalExecutionError(
                    "hardware_estop_asserted_during_motion",
                    "local E-stop asserted during motion; mission cannot claim normal completion",
                )
            stop_observation = sensors.observe_stop_condition(mission_id, authorized.directive)
            stop_observed = boundary.observe_stop_condition(stop_observation)
            if stop_observed is not None:
                break
        if stop_observed is None:
            raise RangerR0PhysicalExecutionError(
                "stop_observation_budget_exhausted",
                "no qualified stop condition was observed within the bounded sample budget",
            )

        stop_decided = boundary.decide_stop(
            mission_id,
            observed_at=local_clock.now_utc(),
            observed_monotonic_ns=local_clock.monotonic_ns(),
        )
        stop_authorized = boundary.actuate_stop(
            mission_id,
            observed_at=local_clock.now_utc(),
            observed_monotonic_ns=local_clock.monotonic_ns(),
        )
        stop_receipt = actuator.apply_stop(stop_authorized.directive)
        _require_actuator_receipt(
            stop_receipt,
            mission_id=mission_id,
            actuator_id=actuator.actuator_id,
            command_kind="stop",
        )

        result_observation = sensors.observe_result(mission_id, stop_authorized.directive)
        result_observed = boundary.record_result_observed(result_observation)
    except Exception:
        if motion_command_attempted:
            _fail_safe_stop(actuator, mission_id, "physical_execution_exception")
        raise

    return RangerR0PhysicalRunResultV1(
        mission_id=mission_id,
        boundary_records=(
            authorized.record,
            motion_started,
            stop_observed,
            stop_decided,
            stop_authorized.record,
            result_observed,
        ),
        motion_directive=authorized.directive,
        motion_actuator_receipt=motion_receipt,
        stop_directive=stop_authorized.directive,
        stop_actuator_receipt=stop_receipt,
    )


def _require_actuator_receipt(
    receipt: RangerR0ActuatorReceiptV1,
    *,
    mission_id: str,
    actuator_id: str,
    command_kind: Literal["motion", "stop"],
) -> None:
    if receipt.mission_id != mission_id:
        raise RangerR0PhysicalExecutionError(
            "actuator_mission_mismatch",
            "controller acknowledgement belongs to another mission_id",
        )
    if receipt.actuator_id != actuator_id:
        raise RangerR0PhysicalExecutionError(
            "actuator_identity_mismatch",
            "controller acknowledgement came from an unexpected actuator",
        )
    if receipt.command_kind != command_kind:
        raise RangerR0PhysicalExecutionError(
            "actuator_command_kind_mismatch",
            "controller acknowledgement does not match the issued command kind",
        )
    if not receipt.accepted:
        raise RangerR0PhysicalExecutionError(
            "actuator_command_rejected",
            "controller rejected the bounded R0 command",
        )


def _fail_safe_stop(
    actuator: RangerR0PhysicalActuator,
    mission_id: str,
    reason: str,
) -> None:
    try:
        receipt = actuator.fail_safe_stop(mission_id, reason=reason)
    except Exception as exc:
        raise RangerR0PhysicalExecutionError(
            "fail_safe_stop_failed",
            "physical execution failed and the local fail-safe stop path also failed",
        ) from exc
    if (
        receipt.mission_id != mission_id
        or receipt.actuator_id != actuator.actuator_id
        or receipt.command_kind != "fail_safe_stop"
        or not receipt.accepted
    ):
        raise RangerR0PhysicalExecutionError(
            "fail_safe_stop_not_acknowledged",
            "local fail-safe stop did not return a valid controller acknowledgement",
        )


__all__ = [
    "RangerR0ActuatorReceiptV1",
    "RangerR0PhysicalActuator",
    "RangerR0PhysicalClock",
    "RangerR0PhysicalExecutionError",
    "RangerR0PhysicalRunResultV1",
    "RangerR0PhysicalSensors",
    "SystemRangerR0PhysicalClock",
    "execute_physical_r0_mission",
]
