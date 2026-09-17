"""Ranger R0 receipt/motion boundary for the frozen Agent 365 P0 demonstration.

This module deliberately separates controller intent, actuator acknowledgement, and observed
physical result. A STOP command or motor-controller acknowledgement never becomes an implicit
claim that the chassis actually stopped; a later sensor observation is required.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.gateway.agent365_r0_mission import (
    MissionCorrelationEnvelopeV1,
    RangerR0GatewayCommandV1,
)

STATIONARY_LINEAR_TOLERANCE_MPS = 0.01
STATIONARY_YAW_TOLERANCE_RAD_S = 0.02


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerR0MotionBoundaryError(ValueError):
    """Raised when the frozen R0 motion boundary must fail closed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class RangerR0MotionState(StrEnum):
    WAITING_FOR_COMMAND = "WAITING_FOR_COMMAND"
    RECEIVED = "RECEIVED"
    AUTHORIZED = "AUTHORIZED"
    MOTION_STARTED = "MOTION_STARTED"
    STOP_CONDITION_OBSERVED = "STOP_CONDITION_OBSERVED"
    STOP_DECIDED = "STOP_DECIDED"
    STOP_ACTUATED = "STOP_ACTUATED"
    RESULT_OBSERVED = "RESULT_OBSERVED"
    REJECTED_AUTHORITY = "REJECTED_AUTHORITY"
    FAILED_ACTUATION = "FAILED_ACTUATION"
    FAILED_OBSERVATION = "FAILED_OBSERVATION"


class RangerR0StopCondition(StrEnum):
    MARKED_STOP_POINT = "MARKED_STOP_POINT"
    OBSTACLE = "OBSTACLE"
    ESTOP = "ESTOP"
    POLICY = "POLICY"


class RangerR0CommandReceiptV1(StrictModel):
    schema_version: Literal["ets.ranger.r0-command-receipt.v1"] = (
        "ets.ranger.r0-command-receipt.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    vehicle_id: str = Field(min_length=12, max_length=160)
    boot_id: str = Field(min_length=1, max_length=128)
    gateway_command_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
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
        return _require_utc(value, "received_at")


class RangerR0LocalAuthorizationV1(StrictModel):
    schema_version: Literal["ets.ranger.r0-local-authorization.v1"] = (
        "ets.ranger.r0-local-authorization.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    decision: Literal["ALLOW", "DENY"]
    hardware_estop_asserted: bool
    local_motion_ready: bool
    reason: str = Field(min_length=1, max_length=512)
    evaluated_at: datetime
    evaluated_monotonic_ns: int = Field(ge=0)

    @field_validator("evaluated_at")
    @classmethod
    def normalize_evaluated_at(cls, value: datetime) -> datetime:
        return _require_utc(value, "evaluated_at")

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        should_allow = self.local_motion_ready and not self.hardware_estop_asserted
        if (self.decision == "ALLOW") != should_allow:
            raise ValueError("local authorization decision conflicts with observed safety facts")
        return self


class RangerR0MotionStartReceiptV1(StrictModel):
    schema_version: Literal["ets.ranger.r0-motion-start-receipt.v1"] = (
        "ets.ranger.r0-motion-start-receipt.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    actuator_id: str = Field(min_length=1, max_length=256)
    actuator_command_id: str = Field(min_length=1, max_length=256)
    commanded_linear_speed_mps: float = Field(gt=0.0, le=0.25)
    commanded_yaw_rate_rad_s: Literal[0.0] = 0.0
    controller_acknowledged: bool
    acknowledged_at: datetime
    acknowledged_monotonic_ns: int = Field(ge=0)
    claim_boundary: Literal["controller_acknowledgement_not_physical_motion_proof"] = (
        "controller_acknowledgement_not_physical_motion_proof"
    )

    @field_validator("acknowledged_at")
    @classmethod
    def normalize_acknowledged_at(cls, value: datetime) -> datetime:
        return _require_utc(value, "acknowledged_at")


class RangerR0StopObservationV1(StrictModel):
    schema_version: Literal["ets.ranger.r0-stop-observation.v1"] = (
        "ets.ranger.r0-stop-observation.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    observation_id: str = Field(min_length=1, max_length=256)
    sensor_id: str = Field(min_length=1, max_length=256)
    condition: RangerR0StopCondition
    marked_stop_detected: bool = False
    obstacle_distance_m: float | None = Field(default=None, ge=0.0, le=100.0)
    hardware_estop_asserted: bool = False
    policy_reason: str | None = Field(default=None, min_length=1, max_length=512)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value, "observed_at")

    @model_validator(mode="after")
    def require_condition_evidence(self) -> Self:
        if self.condition is RangerR0StopCondition.MARKED_STOP_POINT:
            if not self.marked_stop_detected:
                raise ValueError("marked stop condition requires marked_stop_detected=true")
        elif self.condition is RangerR0StopCondition.OBSTACLE:
            if self.obstacle_distance_m is None:
                raise ValueError("obstacle stop condition requires obstacle_distance_m")
        elif self.condition is RangerR0StopCondition.ESTOP:
            if not self.hardware_estop_asserted:
                raise ValueError("E-stop condition requires hardware_estop_asserted=true")
        elif self.condition is RangerR0StopCondition.POLICY and self.policy_reason is None:
            raise ValueError("policy stop condition requires policy_reason")
        return self


class RangerR0StopDecisionV1(StrictModel):
    schema_version: Literal["ets.ranger.r0-stop-decision.v1"] = (
        "ets.ranger.r0-stop-decision.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    decision: Literal["STOP"] = "STOP"
    condition: RangerR0StopCondition
    observation_id: str = Field(min_length=1, max_length=256)
    decided_at: datetime
    decided_monotonic_ns: int = Field(ge=0)

    @field_validator("decided_at")
    @classmethod
    def normalize_decided_at(cls, value: datetime) -> datetime:
        return _require_utc(value, "decided_at")


class RangerR0StopActuationReceiptV1(StrictModel):
    schema_version: Literal["ets.ranger.r0-stop-actuation-receipt.v1"] = (
        "ets.ranger.r0-stop-actuation-receipt.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    actuator_id: str = Field(min_length=1, max_length=256)
    actuator_command_id: str = Field(min_length=1, max_length=256)
    commanded_linear_speed_mps: Literal[0.0] = 0.0
    commanded_yaw_rate_rad_s: Literal[0.0] = 0.0
    controller_acknowledged: bool
    acknowledged_at: datetime
    acknowledged_monotonic_ns: int = Field(ge=0)
    claim_boundary: Literal["stop_command_acknowledgement_not_stopped_state_proof"] = (
        "stop_command_acknowledgement_not_stopped_state_proof"
    )

    @field_validator("acknowledged_at")
    @classmethod
    def normalize_acknowledged_at(cls, value: datetime) -> datetime:
        return _require_utc(value, "acknowledged_at")


class RangerR0ResultObservationV1(StrictModel):
    schema_version: Literal["ets.ranger.r0-result-observation.v1"] = (
        "ets.ranger.r0-result-observation.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    observation_id: str = Field(min_length=1, max_length=256)
    observer_id: str = Field(min_length=1, max_length=256)
    observer_independent_of_actuator: bool
    measured_linear_speed_mps: float = Field(ge=-20.0, le=20.0)
    measured_yaw_rate_rad_s: float = Field(ge=-20.0, le=20.0)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    claim_boundary: Literal["sensor_observation_not_absolute_physical_truth"] = (
        "sensor_observation_not_absolute_physical_truth"
    )

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value, "observed_at")

    @property
    def stationary_within_p0_threshold(self) -> bool:
        return (
            abs(self.measured_linear_speed_mps) <= STATIONARY_LINEAR_TOLERANCE_MPS
            and abs(self.measured_yaw_rate_rad_s) <= STATIONARY_YAW_TOLERANCE_RAD_S
        )


@dataclass(frozen=True, slots=True)
class RangerR0ReceiptResult:
    event: MissionCorrelationEnvelopeV1
    execute: bool
    transport_retry: bool


@dataclass(frozen=True, slots=True)
class RangerR0MotionTranscript:
    mission_id: str
    delivery_id: str
    vehicle_id: str
    state: RangerR0MotionState
    events: tuple[MissionCorrelationEnvelopeV1, ...]
    stop_condition: RangerR0StopCondition | None


class SqliteRangerR0ReceiptLedger:
    """Durable exactly-once execution boundary for Gateway delivery retries."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS ranger_r0_missions (
                    mission_id TEXT PRIMARY KEY,
                    execution_material_sha256 TEXT NOT NULL,
                    first_delivery_id TEXT NOT NULL UNIQUE,
                    first_received_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ranger_r0_deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    retry_of_delivery_id TEXT,
                    execution_material_sha256 TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES ranger_r0_missions(mission_id)
                );
                CREATE INDEX IF NOT EXISTS ix_ranger_r0_deliveries_mission
                    ON ranger_r0_deliveries(mission_id);
                """
            )

    def consume(self, command: RangerR0GatewayCommandV1, *, received_at: datetime) -> bool:
        """Return True only for a deduplicated explicit transport retry."""

        received_at = _require_utc(received_at, "received_at")
        execution_digest = execution_material_sha256(command)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                "SELECT mission_id FROM ranger_r0_deliveries WHERE delivery_id = ?",
                (command.delivery_id,),
            ).fetchone()
            if duplicate is not None:
                raise RangerR0MotionBoundaryError(
                    "duplicate_delivery_id", "delivery_id has already reached Ranger R0"
                )

            existing = connection.execute(
                """
                SELECT execution_material_sha256
                FROM ranger_r0_missions
                WHERE mission_id = ?
                """,
                (command.mission_id,),
            ).fetchone()
            if existing is None:
                if command.retry_of_delivery_id is not None:
                    raise RangerR0MotionBoundaryError(
                        "orphan_retry", "retry reached Ranger before its referenced delivery"
                    )
                connection.execute(
                    """
                    INSERT INTO ranger_r0_missions (
                        mission_id, execution_material_sha256,
                        first_delivery_id, first_received_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        command.mission_id,
                        execution_digest,
                        command.delivery_id,
                        _format_utc(received_at),
                    ),
                )
                transport_retry = False
            else:
                if command.retry_of_delivery_id is None:
                    raise RangerR0MotionBoundaryError(
                        "mission_already_received",
                        "mission already reached Ranger; explicit retry linkage is required",
                    )
                if existing[0] != execution_digest:
                    raise RangerR0MotionBoundaryError(
                        "retry_execution_material_mismatch",
                        "transport retry changed frozen execution material",
                    )
                parent = connection.execute(
                    """
                    SELECT mission_id, execution_material_sha256
                    FROM ranger_r0_deliveries
                    WHERE delivery_id = ?
                    """,
                    (command.retry_of_delivery_id,),
                ).fetchone()
                if parent is None or parent[0] != command.mission_id:
                    raise RangerR0MotionBoundaryError(
                        "invalid_retry_parent",
                        "retry parent does not belong to this Ranger mission",
                    )
                if parent[1] != execution_digest:
                    raise RangerR0MotionBoundaryError(
                        "retry_parent_material_mismatch",
                        "retry parent carries different execution material",
                    )
                transport_retry = True

            connection.execute(
                """
                INSERT INTO ranger_r0_deliveries (
                    delivery_id, mission_id, retry_of_delivery_id,
                    execution_material_sha256, received_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    command.delivery_id,
                    command.mission_id,
                    command.retry_of_delivery_id,
                    execution_digest,
                    _format_utc(received_at),
                ),
            )
            connection.commit()
            return transport_retry

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection


class RangerR0MotionBoundary:
    """Hardware-neutral P0 state machine from Gateway receipt through observed stop."""

    def __init__(
        self,
        *,
        vehicle_id: str,
        boot_id: str,
        receipt_ledger: SqliteRangerR0ReceiptLedger,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerR0MotionBoundaryError(
                "invalid_vehicle_id", "vehicle_id must use the ets-ranger: namespace"
            )
        if not boot_id or len(boot_id) > 128:
            raise RangerR0MotionBoundaryError("invalid_boot_id", "boot_id must be 1-128 chars")
        self.vehicle_id = vehicle_id
        self.boot_id = boot_id
        self._ledger = receipt_ledger
        self._state = RangerR0MotionState.WAITING_FOR_COMMAND
        self._command: RangerR0GatewayCommandV1 | None = None
        self._events: list[MissionCorrelationEnvelopeV1] = []
        self._last_monotonic_ns: int | None = None
        self._sequence = 0
        self._stop_observation: RangerR0StopObservationV1 | None = None
        self._actuator_id: str | None = None

    @property
    def state(self) -> RangerR0MotionState:
        return self._state

    def receive_gateway_command(
        self,
        command: RangerR0GatewayCommandV1,
        gateway_egress_event: MissionCorrelationEnvelopeV1,
        *,
        received_at: datetime,
        received_monotonic_ns: int,
    ) -> RangerR0ReceiptResult:
        command = RangerR0GatewayCommandV1.model_validate(command.model_dump())
        self._validate_gateway_egress(command, gateway_egress_event)
        received_at = _require_utc(received_at, "received_at")
        if received_monotonic_ns < 0:
            raise RangerR0MotionBoundaryError(
                "invalid_monotonic_time", "received_monotonic_ns cannot be negative"
            )

        transport_retry = self._ledger.consume(command, received_at=received_at)
        if transport_retry:
            payload = {
                "mission_id": command.mission_id,
                "delivery_id": command.delivery_id,
                "retry_of_delivery_id": command.retry_of_delivery_id,
                "execution_material_sha256": execution_material_sha256(command),
                "decision": "DEDUPLICATE_NO_REEXECUTION",
            }
            event = _envelope(
                command=command,
                event_id=f"ranger:{command.delivery_id}:retry-deduplicated",
                parent_event_id=gateway_egress_event.event_id,
                event_type="ranger.command.retry.deduplicated",
                source_domain="ranger.r0",
                observed_at=received_at,
                payload=payload,
                previous_event_digest=gateway_egress_event.canonical_digest(),
            )
            return RangerR0ReceiptResult(
                event=event,
                execute=False,
                transport_retry=True,
            )

        if self._state is not RangerR0MotionState.WAITING_FOR_COMMAND:
            raise RangerR0MotionBoundaryError(
                "boundary_busy", "Ranger boundary already owns a mission execution"
            )
        receipt = RangerR0CommandReceiptV1(
            mission_id=command.mission_id,
            delivery_id=command.delivery_id,
            vehicle_id=self.vehicle_id,
            boot_id=self.boot_id,
            gateway_command_sha256=command.payload_sha256(),
            execution_material_sha256=execution_material_sha256(command),
            received_at=received_at,
            received_monotonic_ns=received_monotonic_ns,
        )
        event = _envelope(
            command=command,
            event_id=self._next_event_id(command, "received"),
            parent_event_id=gateway_egress_event.event_id,
            event_type="ranger.command.received",
            source_domain="ranger.r0",
            observed_at=received_at,
            payload=receipt.model_dump(mode="json"),
            previous_event_digest=gateway_egress_event.canonical_digest(),
        )
        self._command = command
        self._state = RangerR0MotionState.RECEIVED
        self._last_monotonic_ns = received_monotonic_ns
        self._events.append(event)
        return RangerR0ReceiptResult(event=event, execute=True, transport_retry=False)

    def authorize_motion(
        self,
        *,
        hardware_estop_asserted: bool,
        local_motion_ready: bool,
        evaluated_at: datetime,
        evaluated_monotonic_ns: int,
    ) -> MissionCorrelationEnvelopeV1:
        command = self._require_state(RangerR0MotionState.RECEIVED)
        self._accept_monotonic(evaluated_monotonic_ns)
        decision = "ALLOW" if local_motion_ready and not hardware_estop_asserted else "DENY"
        if hardware_estop_asserted:
            reason = "hardware_estop_asserted"
        elif not local_motion_ready:
            reason = "local_motion_not_ready"
        else:
            reason = "frozen_command_and_local_safety_checks_passed"
        authorization = RangerR0LocalAuthorizationV1(
            mission_id=command.mission_id,
            delivery_id=command.delivery_id,
            decision=decision,
            hardware_estop_asserted=hardware_estop_asserted,
            local_motion_ready=local_motion_ready,
            reason=reason,
            evaluated_at=evaluated_at,
            evaluated_monotonic_ns=evaluated_monotonic_ns,
        )
        event = self._append_event(
            command,
            label="authorized" if decision == "ALLOW" else "authorization-denied",
            event_type=(
                "ranger.motion.authorized"
                if decision == "ALLOW"
                else "ranger.motion.authorization.denied"
            ),
            source_domain="ranger.r0",
            observed_at=authorization.evaluated_at,
            payload=authorization.model_dump(mode="json"),
        )
        self._state = (
            RangerR0MotionState.AUTHORIZED
            if decision == "ALLOW"
            else RangerR0MotionState.REJECTED_AUTHORITY
        )
        return event

    def record_motion_start(
        self,
        *,
        actuator_id: str,
        actuator_command_id: str,
        commanded_linear_speed_mps: float,
        controller_acknowledged: bool,
        acknowledged_at: datetime,
        acknowledged_monotonic_ns: int,
    ) -> MissionCorrelationEnvelopeV1:
        command = self._require_state(RangerR0MotionState.AUTHORIZED)
        self._accept_monotonic(acknowledged_monotonic_ns)
        if commanded_linear_speed_mps > command.command_parameters.max_speed_mps:
            raise RangerR0MotionBoundaryError(
                "start_speed_exceeds_authorization",
                "motion-start speed exceeds the Gateway-authorized maximum",
            )
        receipt = RangerR0MotionStartReceiptV1(
            mission_id=command.mission_id,
            delivery_id=command.delivery_id,
            actuator_id=actuator_id,
            actuator_command_id=actuator_command_id,
            commanded_linear_speed_mps=commanded_linear_speed_mps,
            controller_acknowledged=controller_acknowledged,
            acknowledged_at=acknowledged_at,
            acknowledged_monotonic_ns=acknowledged_monotonic_ns,
        )
        event = self._append_event(
            command,
            label="motion-start",
            event_type=(
                "ranger.motion.start.acknowledged"
                if controller_acknowledged
                else "ranger.motion.start.failed"
            ),
            source_domain="ranger.r0",
            observed_at=receipt.acknowledged_at,
            payload=receipt.model_dump(mode="json"),
        )
        self._actuator_id = actuator_id
        self._state = (
            RangerR0MotionState.MOTION_STARTED
            if controller_acknowledged
            else RangerR0MotionState.FAILED_ACTUATION
        )
        return event

    def record_stop_observation(
        self,
        observation: RangerR0StopObservationV1,
    ) -> MissionCorrelationEnvelopeV1:
        command = self._require_state(RangerR0MotionState.MOTION_STARTED)
        observation = RangerR0StopObservationV1.model_validate(observation.model_dump())
        self._require_command_binding(
            command, observation.mission_id, observation.delivery_id
        )
        self._accept_monotonic(observation.observed_monotonic_ns)
        if (
            observation.condition is RangerR0StopCondition.OBSTACLE
            and observation.obstacle_distance_m is not None
            and observation.obstacle_distance_m > command.command_parameters.stop_distance_m
        ):
            raise RangerR0MotionBoundaryError(
                "obstacle_outside_stop_threshold",
                "obstacle observation is outside the authorized stop distance",
            )
        event = self._append_event(
            command,
            label="stop-observed",
            event_type="ranger.stop.condition.observed",
            source_domain="ranger.sensor",
            observed_at=observation.observed_at,
            payload=observation.model_dump(mode="json"),
        )
        self._stop_observation = observation
        self._state = RangerR0MotionState.STOP_CONDITION_OBSERVED
        return event

    def record_stop_decision(
        self,
        *,
        decided_at: datetime,
        decided_monotonic_ns: int,
    ) -> MissionCorrelationEnvelopeV1:
        command = self._require_state(RangerR0MotionState.STOP_CONDITION_OBSERVED)
        if self._stop_observation is None:
            raise RangerR0MotionBoundaryError(
                "missing_stop_observation", "stop decision requires retained observation"
            )
        self._accept_monotonic(decided_monotonic_ns)
        decision = RangerR0StopDecisionV1(
            mission_id=command.mission_id,
            delivery_id=command.delivery_id,
            condition=self._stop_observation.condition,
            observation_id=self._stop_observation.observation_id,
            decided_at=decided_at,
            decided_monotonic_ns=decided_monotonic_ns,
        )
        event = self._append_event(
            command,
            label="stop-decided",
            event_type="ranger.stop.decided",
            source_domain="ranger.r0",
            observed_at=decision.decided_at,
            payload=decision.model_dump(mode="json"),
        )
        self._state = RangerR0MotionState.STOP_DECIDED
        return event

    def record_stop_actuation(
        self,
        *,
        actuator_id: str,
        actuator_command_id: str,
        controller_acknowledged: bool,
        acknowledged_at: datetime,
        acknowledged_monotonic_ns: int,
    ) -> MissionCorrelationEnvelopeV1:
        command = self._require_state(RangerR0MotionState.STOP_DECIDED)
        self._accept_monotonic(acknowledged_monotonic_ns)
        if self._actuator_id is not None and actuator_id != self._actuator_id:
            raise RangerR0MotionBoundaryError(
                "actuator_identity_changed",
                "stop actuation must target the actuator used for motion start",
            )
        receipt = RangerR0StopActuationReceiptV1(
            mission_id=command.mission_id,
            delivery_id=command.delivery_id,
            actuator_id=actuator_id,
            actuator_command_id=actuator_command_id,
            controller_acknowledged=controller_acknowledged,
            acknowledged_at=acknowledged_at,
            acknowledged_monotonic_ns=acknowledged_monotonic_ns,
        )
        event = self._append_event(
            command,
            label="stop-actuated",
            event_type=(
                "ranger.stop.actuation.acknowledged"
                if controller_acknowledged
                else "ranger.stop.actuation.failed"
            ),
            source_domain="ranger.r0",
            observed_at=receipt.acknowledged_at,
            payload=receipt.model_dump(mode="json"),
        )
        self._state = (
            RangerR0MotionState.STOP_ACTUATED
            if controller_acknowledged
            else RangerR0MotionState.FAILED_ACTUATION
        )
        return event

    def record_result_observation(
        self,
        observation: RangerR0ResultObservationV1,
    ) -> MissionCorrelationEnvelopeV1:
        command = self._require_state(RangerR0MotionState.STOP_ACTUATED)
        observation = RangerR0ResultObservationV1.model_validate(observation.model_dump())
        self._require_command_binding(
            command, observation.mission_id, observation.delivery_id
        )
        self._accept_monotonic(observation.observed_monotonic_ns)
        if self._actuator_id is not None and observation.observer_id == self._actuator_id:
            raise RangerR0MotionBoundaryError(
                "actuator_cannot_self_attest_result",
                "result observation must not use the actuator identity as observer",
            )
        successful = (
            observation.observer_independent_of_actuator
            and observation.stationary_within_p0_threshold
        )
        event = self._append_event(
            command,
            label="result-observed",
            event_type=(
                "ranger.result.stationary.observed"
                if successful
                else "ranger.result.stop.not_established"
            ),
            source_domain="ranger.sensor",
            observed_at=observation.observed_at,
            payload=observation.model_dump(mode="json"),
        )
        self._state = (
            RangerR0MotionState.RESULT_OBSERVED
            if successful
            else RangerR0MotionState.FAILED_OBSERVATION
        )
        return event

    def transcript(self) -> RangerR0MotionTranscript:
        if self._command is None:
            raise RangerR0MotionBoundaryError(
                "no_mission", "no Ranger mission has been accepted by this boundary"
            )
        return RangerR0MotionTranscript(
            mission_id=self._command.mission_id,
            delivery_id=self._command.delivery_id,
            vehicle_id=self.vehicle_id,
            state=self._state,
            events=tuple(self._events),
            stop_condition=(
                None if self._stop_observation is None else self._stop_observation.condition
            ),
        )

    def _validate_gateway_egress(
        self,
        command: RangerR0GatewayCommandV1,
        egress: MissionCorrelationEnvelopeV1,
    ) -> None:
        if egress.source_domain != "ets.gateway":
            raise RangerR0MotionBoundaryError(
                "invalid_gateway_source", "command must be bound to an ETS Gateway event"
            )
        if egress.event_type not in {
            "gateway.command.accepted",
            "gateway.command.retry.accepted",
        }:
            raise RangerR0MotionBoundaryError(
                "invalid_gateway_event", "Gateway event is not an accepted R0 command"
            )
        if egress.mission_id != command.mission_id:
            raise RangerR0MotionBoundaryError(
                "mission_id_mismatch", "Gateway event and robot command mission_id differ"
            )
        if egress.payload_sha256 != command.payload_sha256():
            raise RangerR0MotionBoundaryError(
                "gateway_payload_mismatch",
                "Gateway egress commitment does not match the received robot command",
            )

    def _require_state(self, expected: RangerR0MotionState) -> RangerR0GatewayCommandV1:
        if self._state is not expected:
            raise RangerR0MotionBoundaryError(
                "invalid_state_transition",
                f"expected Ranger state {expected.value}, found {self._state.value}",
            )
        if self._command is None:
            raise RangerR0MotionBoundaryError("missing_command", "Ranger command is unavailable")
        return self._command

    def _require_command_binding(
        self,
        command: RangerR0GatewayCommandV1,
        mission_id: str,
        delivery_id: str,
    ) -> None:
        if mission_id != command.mission_id:
            raise RangerR0MotionBoundaryError(
                "mission_id_mismatch", "observation does not belong to this mission"
            )
        if delivery_id != command.delivery_id:
            raise RangerR0MotionBoundaryError(
                "delivery_id_mismatch", "observation does not belong to this delivery"
            )

    def _accept_monotonic(self, value: int) -> None:
        if value < 0:
            raise RangerR0MotionBoundaryError(
                "invalid_monotonic_time", "monotonic timestamp cannot be negative"
            )
        if self._last_monotonic_ns is not None and value <= self._last_monotonic_ns:
            raise RangerR0MotionBoundaryError(
                "non_monotonic_event_time",
                "Ranger mission events must advance monotonically",
            )
        self._last_monotonic_ns = value

    def _append_event(
        self,
        command: RangerR0GatewayCommandV1,
        *,
        label: str,
        event_type: str,
        source_domain: Literal["ranger.r0", "ranger.sensor"],
        observed_at: datetime,
        payload: object,
    ) -> MissionCorrelationEnvelopeV1:
        if not self._events:
            raise RangerR0MotionBoundaryError(
                "missing_receipt_event", "Ranger event chain must begin with command receipt"
            )
        previous = self._events[-1]
        event = _envelope(
            command=command,
            event_id=self._next_event_id(command, label),
            parent_event_id=previous.event_id,
            event_type=event_type,
            source_domain=source_domain,
            observed_at=observed_at,
            payload=payload,
            previous_event_digest=previous.canonical_digest(),
        )
        self._events.append(event)
        return event

    def _next_event_id(self, command: RangerR0GatewayCommandV1, label: str) -> str:
        self._sequence += 1
        return f"ranger:{command.mission_id}:{self._sequence:02d}:{label}"


def execution_material_sha256(command: RangerR0GatewayCommandV1) -> str:
    """Hash mission execution material while excluding retry/transport identifiers."""

    payload = {
        "mission_id": command.mission_id,
        "scenario_id": command.scenario_id,
        "requested_action": command.requested_action,
        "policy_version": command.policy_version,
        "command_parameters": command.command_parameters.model_dump(mode="json"),
        "authorization_material_sha256": command.authorization_material_sha256,
        "authorization_artifact_ref": command.authorization_artifact_ref,
    }
    return _payload_sha256(payload)


def _envelope(
    *,
    command: RangerR0GatewayCommandV1,
    event_id: str,
    parent_event_id: str,
    event_type: str,
    source_domain: Literal["ranger.r0", "ranger.sensor"],
    observed_at: datetime,
    payload: object,
    previous_event_digest: str,
) -> MissionCorrelationEnvelopeV1:
    return MissionCorrelationEnvelopeV1(
        mission_id=command.mission_id,
        event_id=event_id,
        parent_event_id=parent_event_id,
        event_type=event_type,
        source_domain=source_domain,
        observed_at=_require_utc(observed_at, "observed_at"),
        payload_sha256=_payload_sha256(payload),
        authorization_artifact_ref=command.authorization_artifact_ref,
        correlation_basis="ets_parent_event",
        previous_event_digest=previous_event_digest,
    )


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validate_uuid4(value: str) -> None:
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError("mission_id must be a canonical UUIDv4 string") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("mission_id must be a lowercase canonical UUIDv4 string")


__all__ = [
    "RangerR0CommandReceiptV1",
    "RangerR0LocalAuthorizationV1",
    "RangerR0MotionBoundary",
    "RangerR0MotionBoundaryError",
    "RangerR0MotionStartReceiptV1",
    "RangerR0MotionState",
    "RangerR0MotionTranscript",
    "RangerR0ReceiptResult",
    "RangerR0ResultObservationV1",
    "RangerR0StopActuationReceiptV1",
    "RangerR0StopCondition",
    "RangerR0StopDecisionV1",
    "RangerR0StopObservationV1",
    "SqliteRangerR0ReceiptLedger",
    "STATIONARY_LINEAR_TOLERANCE_MPS",
    "STATIONARY_YAW_TOLERANCE_RAD_S",
    "execution_material_sha256",
]
