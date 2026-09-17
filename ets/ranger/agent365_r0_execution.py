"""Mission-scoped Ranger R0 execution boundary for the frozen Agent 365 P0 demo.

This module starts where the Gateway authorization boundary ends. It preserves the exact
``mission_id`` through command receipt, local mobility authorization, observed motion start,
stop-condition observation, stop decision, stop actuation command, and resulting-state
observation.

The module intentionally distinguishes commands and policy decisions from physical
observations. A stop command is not proof that the robot stopped; the resulting state must be
observed separately.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.demos.agent365_r0_mission import MISSION_SCENARIO_ID
from ets.gateway.agent365_r0_mission import (
    MISSION_POLICY_VERSION,
    MissionCorrelationEnvelopeV1,
    RangerR0GatewayCommandV1,
)
from ets.ranger.mobility import (
    AuthorizationResult,
    ClockQuality,
    MotionVector,
    RangerDriveCommand,
    RangerMobilityController,
    RangerMobilityEvent,
    RangerMobilityPolicy,
    SafetyMode,
)

RANGER_R0_EXECUTION_SCHEMA_VERSION: Final = "ets.demo.agent365-r0.ranger-execution.v1"
STOPPED_SPEED_TOLERANCE_MPS: Final = 0.02
START_YAW_TOLERANCE_RAD_S: Final = 0.05


class RangerR0ExecutionError(ValueError):
    """Raised when the frozen Ranger R0 execution chain must fail closed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerR0ExecutionPhase(StrEnum):
    CREATED = "created"
    RECEIVED = "received"
    MOTION_AUTHORIZED = "motion_authorized"
    MOTION_STARTED = "motion_started"
    STOP_OBSERVED = "stop_observed"
    STOP_DECIDED = "stop_decided"
    STOP_ACTUATED = "stop_actuated"
    RESULT_OBSERVED = "result_observed"


class RangerR0StopReason(StrEnum):
    HARDWARE_ESTOP = "hardware_estop"
    POLICY_STOP = "policy_stop"
    OBSTACLE_PRESENT = "obstacle_present"
    STOPPING_POINT_REACHED = "stopping_point_reached"


class RangerR0CommandReceiptV1(_StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.ranger-execution.v1"] = (
        RANGER_R0_EXECUTION_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    scenario_id: Literal["agent365-r0-forward-stop-v1"] = MISSION_SCENARIO_ID
    vehicle_id: str = Field(min_length=12, max_length=160)
    delivery_id: str = Field(min_length=1, max_length=256)
    gateway_decision_event_id: str = Field(min_length=1, max_length=512)
    gateway_command_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    received_at: datetime
    received_monotonic_ns: int = Field(ge=0)

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("vehicle_id")
    @classmethod
    def validate_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("received_at")
    @classmethod
    def normalize_received_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0MotionAuthorizationV1(_StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.ranger-execution.v1"] = (
        RANGER_R0_EXECUTION_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    command_id: str = Field(min_length=1, max_length=128)
    mobility_event_id: str = Field(min_length=1, max_length=256)
    mobility_event_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: str = Field(min_length=1, max_length=256)
    policy_version: Literal["r0-forward-stop-policy.v1"] = MISSION_POLICY_VERSION
    selected_motion: MotionVector
    authorization_result: Literal[AuthorizationResult.ALLOWED] = AuthorizationResult.ALLOWED
    authorized_at: datetime
    authorized_monotonic_ns: int = Field(ge=0)
    claim_boundary: Literal["motion_authorization_not_physical_motion"] = (
        "motion_authorization_not_physical_motion"
    )

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("authorized_at")
    @classmethod
    def normalize_authorized_at(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def require_forward_only_motion(self) -> RangerR0MotionAuthorizationV1:
        if self.selected_motion.linear_speed_mps <= 0.0:
            raise ValueError("P0 motion authorization must select forward motion")
        if self.selected_motion.yaw_rate_rad_s != 0.0:
            raise ValueError("P0 motion authorization cannot select a turn")
        return self


class RangerR0MotionStartObservationV1(_StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.ranger-execution.v1"] = (
        RANGER_R0_EXECUTION_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    observation_id: str = Field(min_length=1, max_length=256)
    sensor_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    observed_linear_speed_mps: float = Field(gt=0.0, le=0.25)
    observed_yaw_rate_rad_s: float = Field(ge=-START_YAW_TOLERANCE_RAD_S, le=START_YAW_TOLERANCE_RAD_S)
    source_classification: Literal["observed_fact"] = "observed_fact"
    claim_boundary: Literal["sensor_observation_not_independent_external_proof"] = (
        "sensor_observation_not_independent_external_proof"
    )

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0StopObservationV1(_StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.ranger-execution.v1"] = (
        RANGER_R0_EXECUTION_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    observation_id: str = Field(min_length=1, max_length=256)
    sensor_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    obstacle_present: bool
    obstacle_distance_m: float | None = Field(default=None, ge=0.0, le=100.0)
    stopping_point_reached: bool
    hardware_estop_asserted: bool
    policy_stop_asserted: bool
    source_classification: Literal["observed_fact"] = "observed_fact"
    claim_boundary: Literal["sensor_observation_not_stop_decision"] = (
        "sensor_observation_not_stop_decision"
    )

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0StopDecisionV1(_StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.ranger-execution.v1"] = (
        RANGER_R0_EXECUTION_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    source_observation_id: str = Field(min_length=1, max_length=256)
    reason: RangerR0StopReason
    selected_motion: MotionVector
    decided_at: datetime
    decided_monotonic_ns: int = Field(ge=0)
    classification: Literal["policy_evaluation"] = "policy_evaluation"
    claim_boundary: Literal["stop_decision_not_actuation_or_result"] = (
        "stop_decision_not_actuation_or_result"
    )

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("decided_at")
    @classmethod
    def normalize_decided_at(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def require_stopped_selection(self) -> RangerR0StopDecisionV1:
        if not self.selected_motion.is_stopped:
            raise ValueError("stop decision must select stopped motion")
        return self


class RangerR0StopActuationV1(_StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.ranger-execution.v1"] = (
        RANGER_R0_EXECUTION_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    actuation_id: str = Field(min_length=1, max_length=256)
    source_observation_id: str = Field(min_length=1, max_length=256)
    reason: RangerR0StopReason
    commanded_motion: MotionVector
    commanded_at: datetime
    commanded_monotonic_ns: int = Field(ge=0)
    classification: Literal["actuator_command"] = "actuator_command"
    claim_boundary: Literal["stop_command_not_physical_stop"] = "stop_command_not_physical_stop"

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("commanded_at")
    @classmethod
    def normalize_commanded_at(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def require_stopped_command(self) -> RangerR0StopActuationV1:
        if not self.commanded_motion.is_stopped:
            raise ValueError("stop actuation must command stopped motion")
        return self


class RangerR0ResultingStateObservationV1(_StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.ranger-execution.v1"] = (
        RANGER_R0_EXECUTION_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    observation_id: str = Field(min_length=1, max_length=256)
    sensor_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    observed_linear_speed_mps: float = Field(ge=-0.25, le=0.25)
    stopped_confirmed: bool
    source_classification: Literal["observed_fact"] = "observed_fact"
    claim_boundary: Literal["local_result_observation_not_independent_external_proof"] = (
        "local_result_observation_not_independent_external_proof"
    )

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def require_consistent_stop_classification(self) -> RangerR0ResultingStateObservationV1:
        expected = abs(self.observed_linear_speed_mps) <= STOPPED_SPEED_TOLERANCE_MPS
        if self.stopped_confirmed != expected:
            raise ValueError("stopped_confirmed must match the frozen stop-speed tolerance")
        return self


RangerR0ExecutionPayload = (
    RangerR0CommandReceiptV1
    | RangerR0MotionAuthorizationV1
    | RangerR0MotionStartObservationV1
    | RangerR0StopObservationV1
    | RangerR0StopDecisionV1
    | RangerR0StopActuationV1
    | RangerR0ResultingStateObservationV1
)


@dataclass(frozen=True, slots=True)
class RangerR0ExecutionRecord:
    envelope: MissionCorrelationEnvelopeV1
    payload: RangerR0ExecutionPayload


class RangerR0ExecutionSession:
    """Strict one-command state machine for the frozen four-week R0 demonstration."""

    def __init__(
        self,
        *,
        command: RangerR0GatewayCommandV1,
        expected_mission_id: str,
        vehicle_id: str,
        controller_id: str,
        controller_session_id: str,
        boot_id: str,
        mobility_policy: RangerMobilityPolicy,
        local_clock_quality: ClockQuality = ClockQuality.UNKNOWN,
    ) -> None:
        command = RangerR0GatewayCommandV1.model_validate(command.model_dump())
        _validate_uuid4(expected_mission_id)
        if command.mission_id != expected_mission_id:
            raise RangerR0ExecutionError(
                "mission_id_mismatch",
                "Gateway command mission_id does not match the Ranger mission runtime",
            )
        if not vehicle_id.startswith("ets-ranger:"):
            raise RangerR0ExecutionError(
                "vehicle_id_invalid",
                "vehicle_id must use the ets-ranger: namespace",
            )
        if mobility_policy.policy_version != command.policy_version:
            raise RangerR0ExecutionError(
                "policy_version_mismatch",
                "Ranger mobility policy version does not match the Gateway command",
            )
        if mobility_policy.max_linear_speed_mps > command.command_parameters.max_speed_mps:
            raise RangerR0ExecutionError(
                "mobility_policy_too_broad",
                "Ranger mobility policy exceeds the authorized maximum speed",
            )
        if mobility_policy.allow_reverse:
            raise RangerR0ExecutionError(
                "reverse_not_frozen",
                "P0 Ranger mobility policy must prohibit reverse motion",
            )

        self.command = command
        self.mission_id = command.mission_id
        self.vehicle_id = vehicle_id
        self.phase = RangerR0ExecutionPhase.CREATED
        self._last_envelope: MissionCorrelationEnvelopeV1 | None = None
        self._last_monotonic_ns: int | None = None
        self._event_sequence = 0
        self._stop_observation: RangerR0StopObservationV1 | None = None
        self._stop_decision: RangerR0StopDecisionV1 | None = None
        self._mobility = RangerMobilityController(
            vehicle_id=vehicle_id,
            mission_id=self.mission_id,
            controller_id=controller_id,
            controller_session_id=controller_session_id,
            boot_id=boot_id,
            policy=mobility_policy,
            local_clock_quality=local_clock_quality,
        )

    def receive_command(
        self,
        *,
        received_at: datetime,
        received_monotonic_ns: int,
    ) -> RangerR0ExecutionRecord:
        self._require_phase(RangerR0ExecutionPhase.CREATED)
        self._accept_monotonic(received_monotonic_ns)
        payload = RangerR0CommandReceiptV1(
            mission_id=self.mission_id,
            vehicle_id=self.vehicle_id,
            delivery_id=self.command.delivery_id,
            gateway_decision_event_id=self.command.gateway_decision_event_id,
            gateway_command_sha256=self.command.payload_sha256(),
            authorization_material_sha256=self.command.authorization_material_sha256,
            received_at=received_at,
            received_monotonic_ns=received_monotonic_ns,
        )
        record = self._record("ranger.command.received", payload, received_at)
        self.phase = RangerR0ExecutionPhase.RECEIVED
        return record

    def authorize_motion(
        self,
        *,
        command_sequence: int,
        received_monotonic_ns: int,
        evaluated_monotonic_ns: int,
        evaluated_at: datetime,
        hardware_estop_asserted: bool,
    ) -> tuple[RangerMobilityEvent, RangerR0ExecutionRecord]:
        self._require_phase(RangerR0ExecutionPhase.RECEIVED)
        self._accept_monotonic(evaluated_monotonic_ns)
        self._mobility.arm(
            now_monotonic_ns=received_monotonic_ns,
            hardware_estop_asserted=hardware_estop_asserted,
        )
        drive_command = RangerDriveCommand(
            command_id=f"r0:{self.command.delivery_id}",
            command_sequence=command_sequence,
            mission_id=self.mission_id,
            vehicle_id=self.vehicle_id,
            controller_id=self._mobility.controller_id,
            controller_session_id=self._mobility.controller_session_id,
            issued_at_utc=self.command.issued_at,
            source_clock_quality=ClockQuality.SYNCHRONIZED,
            deadman_asserted=True,
            requested_motion=MotionVector(
                linear_speed_mps=self.command.command_parameters.max_speed_mps,
                yaw_rate_rad_s=0.0,
            ),
        )
        mobility_event = self._mobility.authorize(
            drive_command,
            received_monotonic_ns=received_monotonic_ns,
            evaluated_monotonic_ns=evaluated_monotonic_ns,
            evaluated_at_utc=evaluated_at,
            hardware_estop_asserted=hardware_estop_asserted,
        )
        if mobility_event.policy_evaluation.authorization_result is not AuthorizationResult.ALLOWED:
            reasons = ",".join(reason.value for reason in mobility_event.policy_evaluation.reason_codes)
            raise RangerR0ExecutionError(
                "motion_authorization_denied",
                f"Ranger mobility boundary denied P0 motion: {reasons}",
            )
        payload = RangerR0MotionAuthorizationV1(
            mission_id=self.mission_id,
            command_id=drive_command.command_id,
            mobility_event_id=mobility_event.event_id,
            mobility_event_sha256=_sha256_json(mobility_event.model_dump(mode="json")),
            policy_id=mobility_event.policy_evaluation.policy_id,
            policy_version=self.command.policy_version,
            selected_motion=mobility_event.policy_evaluation.selected_motion,
            authorized_at=evaluated_at,
            authorized_monotonic_ns=evaluated_monotonic_ns,
        )
        record = self._record("ranger.motion.authorized", payload, evaluated_at)
        self.phase = RangerR0ExecutionPhase.MOTION_AUTHORIZED
        return mobility_event, record

    def observe_motion_started(
        self,
        *,
        observation_id: str,
        sensor_id: str,
        observed_at: datetime,
        observed_monotonic_ns: int,
        observed_linear_speed_mps: float,
        observed_yaw_rate_rad_s: float,
    ) -> RangerR0ExecutionRecord:
        self._require_phase(RangerR0ExecutionPhase.MOTION_AUTHORIZED)
        self._accept_monotonic(observed_monotonic_ns)
        if observed_linear_speed_mps > self.command.command_parameters.max_speed_mps:
            raise RangerR0ExecutionError(
                "observed_speed_exceeds_authorization",
                "observed motion start exceeds the authorized maximum speed",
            )
        payload = RangerR0MotionStartObservationV1(
            mission_id=self.mission_id,
            observation_id=observation_id,
            sensor_id=sensor_id,
            observed_at=observed_at,
            observed_monotonic_ns=observed_monotonic_ns,
            observed_linear_speed_mps=observed_linear_speed_mps,
            observed_yaw_rate_rad_s=observed_yaw_rate_rad_s,
        )
        record = self._record("ranger.motion.started.observed", payload, observed_at)
        self.phase = RangerR0ExecutionPhase.MOTION_STARTED
        return record

    def observe_stop_condition(
        self,
        observation: RangerR0StopObservationV1,
    ) -> RangerR0ExecutionRecord:
        self._require_phase(RangerR0ExecutionPhase.MOTION_STARTED)
        observation = RangerR0StopObservationV1.model_validate(observation.model_dump())
        if observation.mission_id != self.mission_id:
            raise RangerR0ExecutionError(
                "mission_id_mismatch",
                "stop observation mission_id does not match the active mission",
            )
        self._accept_monotonic(observation.observed_monotonic_ns)
        self._stop_observation = observation
        record = self._record("ranger.stop-condition.observed", observation, observation.observed_at)
        self.phase = RangerR0ExecutionPhase.STOP_OBSERVED
        return record

    def decide_stop(
        self,
        *,
        decided_at: datetime,
        decided_monotonic_ns: int,
    ) -> RangerR0ExecutionRecord:
        self._require_phase(RangerR0ExecutionPhase.STOP_OBSERVED)
        self._accept_monotonic(decided_monotonic_ns)
        observation = self._stop_observation
        if observation is None:
            raise RangerR0ExecutionError("missing_stop_observation", "stop observation is missing")

        if observation.hardware_estop_asserted:
            reason = RangerR0StopReason.HARDWARE_ESTOP
        elif observation.policy_stop_asserted:
            reason = RangerR0StopReason.POLICY_STOP
        elif observation.obstacle_present:
            reason = RangerR0StopReason.OBSTACLE_PRESENT
        elif observation.stopping_point_reached:
            reason = RangerR0StopReason.STOPPING_POINT_REACHED
        else:
            raise RangerR0ExecutionError(
                "no_stop_condition",
                "frozen P0 stop decision requires obstacle, stopping point, E-stop, or policy stop",
            )

        payload = RangerR0StopDecisionV1(
            mission_id=self.mission_id,
            source_observation_id=observation.observation_id,
            reason=reason,
            selected_motion=MotionVector.stopped(),
            decided_at=decided_at,
            decided_monotonic_ns=decided_monotonic_ns,
        )
        self._stop_decision = payload
        record = self._record("ranger.stop.decision", payload, decided_at)
        self.phase = RangerR0ExecutionPhase.STOP_DECIDED
        return record

    def command_stop(
        self,
        *,
        actuation_id: str,
        commanded_at: datetime,
        commanded_monotonic_ns: int,
    ) -> RangerR0ExecutionRecord:
        self._require_phase(RangerR0ExecutionPhase.STOP_DECIDED)
        self._accept_monotonic(commanded_monotonic_ns)
        decision = self._stop_decision
        if decision is None:
            raise RangerR0ExecutionError("missing_stop_decision", "stop decision is missing")
        self._mobility.disarm(now_monotonic_ns=commanded_monotonic_ns)
        if self._mobility.mode is not SafetyMode.DISARMED or not self._mobility.applied_motion.is_stopped:
            raise RangerR0ExecutionError(
                "local_stop_interlock_failed",
                "local mobility boundary did not enter a stopped disarmed state",
            )
        payload = RangerR0StopActuationV1(
            mission_id=self.mission_id,
            actuation_id=actuation_id,
            source_observation_id=decision.source_observation_id,
            reason=decision.reason,
            commanded_motion=MotionVector.stopped(),
            commanded_at=commanded_at,
            commanded_monotonic_ns=commanded_monotonic_ns,
        )
        record = self._record("ranger.stop.commanded", payload, commanded_at)
        self.phase = RangerR0ExecutionPhase.STOP_ACTUATED
        return record

    def observe_resulting_state(
        self,
        *,
        observation_id: str,
        sensor_id: str,
        observed_at: datetime,
        observed_monotonic_ns: int,
        observed_linear_speed_mps: float,
    ) -> RangerR0ExecutionRecord:
        self._require_phase(RangerR0ExecutionPhase.STOP_ACTUATED)
        self._accept_monotonic(observed_monotonic_ns)
        payload = RangerR0ResultingStateObservationV1(
            mission_id=self.mission_id,
            observation_id=observation_id,
            sensor_id=sensor_id,
            observed_at=observed_at,
            observed_monotonic_ns=observed_monotonic_ns,
            observed_linear_speed_mps=observed_linear_speed_mps,
            stopped_confirmed=(
                abs(observed_linear_speed_mps) <= STOPPED_SPEED_TOLERANCE_MPS
            ),
        )
        record = self._record("ranger.resulting-state.observed", payload, observed_at)
        self.phase = RangerR0ExecutionPhase.RESULT_OBSERVED
        return record

    def _record(
        self,
        event_type: str,
        payload: RangerR0ExecutionPayload,
        observed_at: datetime,
    ) -> RangerR0ExecutionRecord:
        observed_at = _require_utc(observed_at)
        self._event_sequence += 1
        event_id = f"ranger:{self.mission_id}:{self._event_sequence}:{event_type}"
        previous = self._last_envelope
        envelope = MissionCorrelationEnvelopeV1(
            mission_id=self.mission_id,
            event_id=event_id,
            parent_event_id=None if previous is None else previous.event_id,
            event_type=event_type,
            source_domain="ranger.r0",
            observed_at=observed_at,
            payload_sha256=_sha256_json(payload.model_dump(mode="json")),
            authorization_artifact_ref=self.command.authorization_artifact_ref,
            correlation_basis=(
                "controlled_request_context" if previous is None else "ets_parent_event"
            ),
            previous_event_digest=(
                None if previous is None else previous.canonical_digest()
            ),
        )
        self._last_envelope = envelope
        return RangerR0ExecutionRecord(envelope=envelope, payload=payload)

    def _require_phase(self, expected: RangerR0ExecutionPhase) -> None:
        if self.phase is not expected:
            raise RangerR0ExecutionError(
                "invalid_execution_phase",
                f"expected Ranger R0 phase {expected.value}; current phase is {self.phase.value}",
            )

    def _accept_monotonic(self, value: int) -> None:
        if value < 0:
            raise RangerR0ExecutionError("invalid_monotonic_time", "monotonic time cannot be negative")
        if self._last_monotonic_ns is not None and value < self._last_monotonic_ns:
            raise RangerR0ExecutionError(
                "monotonic_clock_regression",
                "Ranger execution monotonic clock regressed",
            )
        self._last_monotonic_ns = value


def _validate_uuid4(value: str) -> None:
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError("mission_id must be a canonical UUIDv4 string") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("mission_id must be a lowercase canonical UUIDv4 string")


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
