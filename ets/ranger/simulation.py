"""Deterministic Ranger R0.1 mobility simulation and evidence-shaped records.

The simulator accepts only a complete mobility event emitted by the fail-closed safety
boundary.  Its outputs describe a simulated adapter response and a derived kinematic
result; they are not observations of physical hardware or the external world.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.ranger.mobility import ClockQuality, MotionVector, RangerMobilityEvent


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class ExecutionEnvironment(StrEnum):
    SIMULATION = "simulation"


class SimulationValueClass(StrEnum):
    DERIVED_VALUE = "derived_value"


class ActuatorResponseStatus(StrEnum):
    APPLIED = "applied"


class SimulatedPose2D(StrictModel):
    x_m: float = Field(ge=-1_000_000.0, le=1_000_000.0)
    y_m: float = Field(ge=-1_000_000.0, le=1_000_000.0)
    heading_rad: float = Field(ge=-math.pi, le=math.pi)


class SimulatedVehicleState(StrictModel):
    pose: SimulatedPose2D
    linear_speed_mps: float = Field(ge=-20.0, le=20.0)
    yaw_rate_rad_s: float = Field(ge=-20.0, le=20.0)

    @classmethod
    def stopped_at(cls, pose: SimulatedPose2D) -> SimulatedVehicleState:
        return cls(pose=pose, linear_speed_mps=0.0, yaw_rate_rad_s=0.0)


class RangerSimulationConfig(StrictModel):
    schema_version: Literal["ets.ranger.simulation-config.v1"] = "ets.ranger.simulation-config.v1"
    model_id: Literal["ets.ranger.planar-kinematic-euler.v1"] = (
        "ets.ranger.planar-kinematic-euler.v1"
    )
    model_version: Literal["1"] = "1"
    max_step_duration_ms: int = Field(default=1_000, ge=1, le=5_000)
    initial_pose: SimulatedPose2D = Field(
        default_factory=lambda: SimulatedPose2D(x_m=0.0, y_m=0.0, heading_rad=0.0)
    )


class RangerActuatorResponse(StrictModel):
    """Response observed at the simulated drive-adapter interface."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/actuator-response/v1"
        },
    )

    schema_version: Literal["ets.ranger.actuator-response.v1"] = "ets.ranger.actuator-response.v1"
    classification: Literal["actuator_response"] = "actuator_response"
    response_id: str = Field(min_length=1, max_length=256)
    response_sequence: int = Field(ge=1, le=2**63 - 1)
    source_mobility_event_id: str = Field(min_length=1, max_length=256)
    source_mobility_event_sequence: int = Field(ge=1, le=2**63 - 1)
    source_mobility_event_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vehicle_id: str = Field(min_length=12, max_length=160)
    mission_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    producer_id: str = Field(min_length=1, max_length=160)
    simulation_session_id: str = Field(min_length=1, max_length=128)
    execution_environment: Literal[ExecutionEnvironment.SIMULATION] = (
        ExecutionEnvironment.SIMULATION
    )
    responded_at_utc: datetime
    responded_monotonic_ns: int = Field(ge=0)
    local_clock_quality: ClockQuality
    commanded_motion: MotionVector
    applied_motion: MotionVector
    response_status: Literal[ActuatorResponseStatus.APPLIED] = ActuatorResponseStatus.APPLIED
    physical_actuator_observed: Literal[False] = False
    claim_boundary: Literal["simulated_adapter_response_not_physical_actuator"] = (
        "simulated_adapter_response_not_physical_actuator"
    )

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("responded_at_utc")
    @classmethod
    def normalize_responded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("responded_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_ideal_adapter_application(self) -> Self:
        if self.applied_motion != self.commanded_motion:
            raise ValueError("the ideal simulator must apply the commanded motion exactly")
        return self


class RangerSimulatedResult(StrictModel):
    """Derived simulator state shaped as a result record without a physical claim."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/simulated-result/v1"
        },
    )

    schema_version: Literal["ets.ranger.simulated-result.v1"] = "ets.ranger.simulated-result.v1"
    classification: Literal[SimulationValueClass.DERIVED_VALUE] = SimulationValueClass.DERIVED_VALUE
    record_role: Literal["simulated_observed_result"] = "simulated_observed_result"
    result_id: str = Field(min_length=1, max_length=256)
    result_sequence: int = Field(ge=1, le=2**63 - 1)
    source_mobility_event_id: str = Field(min_length=1, max_length=256)
    source_mobility_event_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_actuator_response_id: str = Field(min_length=1, max_length=256)
    source_actuator_response_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vehicle_id: str = Field(min_length=12, max_length=160)
    mission_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    producer_id: str = Field(min_length=1, max_length=160)
    simulation_session_id: str = Field(min_length=1, max_length=128)
    execution_environment: Literal[ExecutionEnvironment.SIMULATION] = (
        ExecutionEnvironment.SIMULATION
    )
    model_id: str = Field(min_length=1, max_length=256)
    model_version: str = Field(min_length=1, max_length=64)
    model_config_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    simulated_at_utc: datetime
    simulated_monotonic_ns: int = Field(ge=0)
    local_clock_quality: ClockQuality
    step_duration_ms: int = Field(ge=1, le=5_000)
    state_before: SimulatedVehicleState
    state_after: SimulatedVehicleState
    physical_outcome_observed: Literal[False] = False
    claim_boundary: Literal["derived_simulation_state_not_physical_or_sensor_observation"] = (
        "derived_simulation_state_not_physical_or_sensor_observation"
    )

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("simulated_at_utc")
    @classmethod
    def normalize_simulated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("simulated_at_utc must be timezone-aware")
        return value.astimezone(UTC)


def _normalize_heading(value: float) -> float:
    normalized = (value + math.pi) % (2.0 * math.pi) - math.pi
    return 0.0 if normalized == 0.0 else normalized


def _integrate_state(
    state: SimulatedVehicleState,
    motion: MotionVector,
    step_duration_ms: int,
) -> SimulatedVehicleState:
    duration_s = step_duration_ms / 1_000.0
    distance_m = motion.linear_speed_mps * duration_s
    pose = SimulatedPose2D(
        x_m=state.pose.x_m + distance_m * math.cos(state.pose.heading_rad),
        y_m=state.pose.y_m + distance_m * math.sin(state.pose.heading_rad),
        heading_rad=_normalize_heading(state.pose.heading_rad + motion.yaw_rate_rad_s * duration_s),
    )
    return SimulatedVehicleState(
        pose=pose,
        linear_speed_mps=motion.linear_speed_mps,
        yaw_rate_rad_s=motion.yaw_rate_rad_s,
    )


class RangerSimulationStep(StrictModel):
    """Self-validating linkage across command, adapter response, and simulated result."""

    schema_version: Literal["ets.ranger.simulation-step.v1"] = "ets.ranger.simulation-step.v1"
    source_mobility_event: RangerMobilityEvent
    simulation_config: RangerSimulationConfig
    actuator_response: RangerActuatorResponse
    simulated_result: RangerSimulatedResult

    @model_validator(mode="after")
    def require_linkage_and_deterministic_result(self) -> Self:
        event = self.source_mobility_event
        config = self.simulation_config
        response = self.actuator_response
        result = self.simulated_result
        event_digest = canonical_sha256(event.model_dump(mode="json"))
        config_digest = canonical_sha256(config.model_dump(mode="json"))
        response_digest = canonical_sha256(response.model_dump(mode="json"))

        if response.source_mobility_event_id != event.event_id:
            raise ValueError("actuator response must link to the mobility event")
        if response.source_mobility_event_sequence != event.event_sequence:
            raise ValueError("actuator response must preserve the mobility event sequence")
        if response.source_mobility_event_digest_sha256 != event_digest:
            raise ValueError("actuator response mobility-event digest mismatch")
        if response.commanded_motion != event.actuator_command.motion:
            raise ValueError("simulator response must consume the authorized actuator command")
        if response.responded_at_utc != event.evaluated_at_utc:
            raise ValueError("actuator response wall time must match safety-boundary release")
        if response.responded_monotonic_ns != event.evaluated_monotonic_ns:
            raise ValueError("actuator response monotonic time must match safety-boundary release")
        if response.local_clock_quality is not event.local_clock_quality:
            raise ValueError("actuator response must preserve safety-boundary clock quality")
        expected_response_id = "rar:" + canonical_sha256(
            {
                "simulation_session_id": response.simulation_session_id,
                "response_sequence": response.response_sequence,
                "source_mobility_event_digest_sha256": event_digest,
            }
        )
        if response.response_id != expected_response_id:
            raise ValueError("actuator response identifier mismatch")
        if result.source_mobility_event_id != event.event_id:
            raise ValueError("simulated result must link to the mobility event")
        if result.source_mobility_event_digest_sha256 != event_digest:
            raise ValueError("simulated result mobility-event digest mismatch")
        if result.source_actuator_response_id != response.response_id:
            raise ValueError("simulated result must link to the actuator response")
        if result.source_actuator_response_digest_sha256 != response_digest:
            raise ValueError("simulated result actuator-response digest mismatch")
        if result.result_sequence != response.response_sequence:
            raise ValueError("response and result sequences must match")
        if result.model_id != config.model_id or result.model_version != config.model_version:
            raise ValueError("simulated result model identity mismatch")
        if result.model_config_digest_sha256 != config_digest:
            raise ValueError("simulated result configuration digest mismatch")
        if result.step_duration_ms > config.max_step_duration_ms:
            raise ValueError("simulated result exceeds configured step duration")
        if result.simulated_monotonic_ns != (
            response.responded_monotonic_ns + result.step_duration_ms * 1_000_000
        ):
            raise ValueError("simulated monotonic time must follow the configured step")
        if result.simulated_at_utc != response.responded_at_utc + timedelta(
            milliseconds=result.step_duration_ms
        ):
            raise ValueError("simulated wall time must follow the configured step")
        expected_state = _integrate_state(
            result.state_before,
            response.applied_motion,
            result.step_duration_ms,
        )
        if result.state_after != expected_state:
            raise ValueError("simulated result does not match deterministic model output")
        expected_result_id = "rsr:" + canonical_sha256(
            {
                "simulation_session_id": result.simulation_session_id,
                "result_sequence": result.result_sequence,
                "source_actuator_response_digest_sha256": response_digest,
            }
        )
        if result.result_id != expected_result_id:
            raise ValueError("simulated result identifier mismatch")

        identity_sets = (
            (event.vehicle_id, response.vehicle_id, result.vehicle_id),
            (event.mission_id, response.mission_id, result.mission_id),
            (event.boot_id, response.boot_id, result.boot_id),
            (
                response.simulation_session_id,
                result.simulation_session_id,
                result.simulation_session_id,
            ),
            (response.producer_id, result.producer_id, result.producer_id),
        )
        if any(len(set(values)) != 1 for values in identity_sets):
            raise ValueError("simulation step identity linkage mismatch")
        return self


class RangerSimulationInputError(ValueError):
    """Raised when the simulation ingress contract fails closed."""


class RangerMobilitySimulator:
    """Deterministic planar simulator downstream of the mobility safety boundary."""

    def __init__(
        self,
        *,
        vehicle_id: str,
        mission_id: str,
        boot_id: str,
        producer_id: str,
        simulation_session_id: str,
        config: RangerSimulationConfig | None = None,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerSimulationInputError("vehicle_id must use the ets-ranger: namespace")
        for name, value, maximum in (
            ("mission_id", mission_id, 128),
            ("boot_id", boot_id, 128),
            ("producer_id", producer_id, 160),
            ("simulation_session_id", simulation_session_id, 128),
        ):
            if not value or len(value) > maximum:
                raise RangerSimulationInputError(f"{name} must contain 1-{maximum} characters")

        self.vehicle_id = vehicle_id
        self.mission_id = mission_id
        self.boot_id = boot_id
        self.producer_id = producer_id
        self.simulation_session_id = simulation_session_id
        self.config = RangerSimulationConfig.model_validate(
            (config or RangerSimulationConfig()).model_dump()
        )
        self._config_digest = canonical_sha256(self.config.model_dump(mode="json"))
        self._state = SimulatedVehicleState.stopped_at(self.config.initial_pose)
        self._last_mobility_event_sequence = 0
        self._step_sequence = 0
        self._last_simulated_monotonic_ns: int | None = None

    @property
    def state(self) -> SimulatedVehicleState:
        return self._state

    @property
    def config_digest_sha256(self) -> str:
        return self._config_digest

    def apply(
        self,
        event: RangerMobilityEvent,
        *,
        step_duration_ms: int,
    ) -> RangerSimulationStep:
        event = RangerMobilityEvent.model_validate(event.model_dump())
        if not 1 <= step_duration_ms <= self.config.max_step_duration_ms:
            raise RangerSimulationInputError(
                f"step_duration_ms must contain 1-{self.config.max_step_duration_ms}"
            )
        if (
            event.vehicle_id != self.vehicle_id
            or event.mission_id != self.mission_id
            or event.boot_id != self.boot_id
        ):
            raise RangerSimulationInputError("mobility event identity mismatch")
        expected_event_sequence = self._last_mobility_event_sequence + 1
        if event.event_sequence != expected_event_sequence:
            raise RangerSimulationInputError(
                "mobility event sequence must be contiguous; "
                f"expected {expected_event_sequence}, received {event.event_sequence}"
            )
        if (
            self._last_simulated_monotonic_ns is not None
            and event.evaluated_monotonic_ns < self._last_simulated_monotonic_ns
        ):
            raise RangerSimulationInputError("mobility event precedes the prior simulated result")

        step_sequence = self._step_sequence + 1
        event_payload = event.model_dump(mode="json")
        event_digest = canonical_sha256(event_payload)
        response_id = "rar:" + canonical_sha256(
            {
                "simulation_session_id": self.simulation_session_id,
                "response_sequence": step_sequence,
                "source_mobility_event_digest_sha256": event_digest,
            }
        )
        response = RangerActuatorResponse(
            response_id=response_id,
            response_sequence=step_sequence,
            source_mobility_event_id=event.event_id,
            source_mobility_event_sequence=event.event_sequence,
            source_mobility_event_digest_sha256=event_digest,
            vehicle_id=self.vehicle_id,
            mission_id=self.mission_id,
            boot_id=self.boot_id,
            producer_id=self.producer_id,
            simulation_session_id=self.simulation_session_id,
            responded_at_utc=event.evaluated_at_utc,
            responded_monotonic_ns=event.evaluated_monotonic_ns,
            local_clock_quality=event.local_clock_quality,
            commanded_motion=event.actuator_command.motion,
            applied_motion=event.actuator_command.motion,
        )
        response_digest = canonical_sha256(response.model_dump(mode="json"))
        next_state = _integrate_state(
            self._state,
            response.applied_motion,
            step_duration_ms,
        )
        simulated_monotonic_ns = event.evaluated_monotonic_ns + step_duration_ms * 1_000_000
        simulated_at_utc = event.evaluated_at_utc + timedelta(milliseconds=step_duration_ms)
        result_id = "rsr:" + canonical_sha256(
            {
                "simulation_session_id": self.simulation_session_id,
                "result_sequence": step_sequence,
                "source_actuator_response_digest_sha256": response_digest,
            }
        )
        result = RangerSimulatedResult(
            result_id=result_id,
            result_sequence=step_sequence,
            source_mobility_event_id=event.event_id,
            source_mobility_event_digest_sha256=event_digest,
            source_actuator_response_id=response.response_id,
            source_actuator_response_digest_sha256=response_digest,
            vehicle_id=self.vehicle_id,
            mission_id=self.mission_id,
            boot_id=self.boot_id,
            producer_id=self.producer_id,
            simulation_session_id=self.simulation_session_id,
            model_id=self.config.model_id,
            model_version=self.config.model_version,
            model_config_digest_sha256=self.config_digest_sha256,
            simulated_at_utc=simulated_at_utc,
            simulated_monotonic_ns=simulated_monotonic_ns,
            local_clock_quality=event.local_clock_quality,
            step_duration_ms=step_duration_ms,
            state_before=self._state,
            state_after=next_state,
        )
        step = RangerSimulationStep(
            source_mobility_event=event,
            simulation_config=self.config,
            actuator_response=response,
            simulated_result=result,
        )

        self._state = next_state
        self._last_mobility_event_sequence = event.event_sequence
        self._step_sequence = step_sequence
        self._last_simulated_monotonic_ns = simulated_monotonic_ns
        return step
