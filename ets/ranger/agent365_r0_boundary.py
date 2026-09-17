"""Ranger R0 receipt and bounded-motion boundary for the frozen Agent 365 demo.

The Gateway proves that a mission was authorized for dispatch.  This module starts a
new trust boundary on the robot: exact command receipt, execution-once semantics,
local motion authorization, sensor-observed motion, stop-condition evaluation,
stop actuation, and independent observation of the resulting stopped state.

A stop command is evidence of actuation intent only.  It is never treated as proof
that the chassis stopped.
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
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from ets.gateway.agent365_r0_mission import (
    MissionCorrelationEnvelopeV1,
    RangerR0GatewayCommandV1,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerR0BoundaryError(ValueError):
    """Raised when the robot-side P0 boundary must fail closed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class RangerR0Stage(StrEnum):
    RECEIVED = "RECEIVED"
    AUTHORIZED = "AUTHORIZED"
    MOTION_STARTED = "MOTION_STARTED"
    STOP_CONDITION_OBSERVED = "STOP_CONDITION_OBSERVED"
    STOP_DECIDED = "STOP_DECIDED"
    STOP_ACTUATED = "STOP_ACTUATED"
    RESULT_OBSERVED = "RESULT_OBSERVED"


class RangerR0StopReason(StrEnum):
    HARDWARE_ESTOP = "hardware_estop"
    POLICY_ABORT = "policy_abort"
    OBSTACLE_WITHIN_STOP_DISTANCE = "obstacle_within_stop_distance"
    MAX_DISTANCE_REACHED = "max_distance_reached"
    MAX_DURATION_REACHED = "max_duration_reached"


class RangerR0MotionDirectiveV1(StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.motion-directive.v1"] = (
        "ets.demo.agent365-r0.motion-directive.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    delivery_id: str = Field(min_length=1, max_length=256)
    vehicle_id: str = Field(min_length=12, max_length=160)
    controller_id: str = Field(min_length=1, max_length=160)
    issued_at: datetime
    issued_monotonic_ns: int = Field(ge=0)
    linear_speed_mps: float = Field(gt=0.0, le=0.25)
    yaw_rate_rad_s: Literal[0.0] = 0.0
    max_distance_m: float = Field(gt=0.0, le=2.0)
    max_duration_s: int = Field(ge=1, le=20)
    stop_distance_m: float = Field(ge=0.45, le=2.0)
    claim_boundary: Literal["authorized_motion_directive_not_physical_outcome"] = (
        "authorized_motion_directive_not_physical_outcome"
    )

    @field_validator("issued_at")
    @classmethod
    def normalize_issued_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0StopDirectiveV1(StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.stop-directive.v1"] = (
        "ets.demo.agent365-r0.stop-directive.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    vehicle_id: str = Field(min_length=12, max_length=160)
    controller_id: str = Field(min_length=1, max_length=160)
    stop_reason: RangerR0StopReason
    issued_at: datetime
    issued_monotonic_ns: int = Field(ge=0)
    linear_speed_mps: Literal[0.0] = 0.0
    yaw_rate_rad_s: Literal[0.0] = 0.0
    claim_boundary: Literal["stop_actuation_command_not_proof_chassis_stopped"] = (
        "stop_actuation_command_not_proof_chassis_stopped"
    )

    @field_validator("issued_at")
    @classmethod
    def normalize_issued_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0MotionStartObservationV1(StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.motion-start-observation.v1"] = (
        "ets.demo.agent365-r0.motion-start-observation.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    observer_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    speed_mps: float = Field(gt=0.0, le=20.0)
    distance_travelled_m: float = Field(ge=0.0, le=1000.0)
    source_kind: Literal["independent_motion_sensor"] = "independent_motion_sensor"

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0StopObservationV1(StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.stop-observation.v1"] = (
        "ets.demo.agent365-r0.stop-observation.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    observer_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    distance_travelled_m: float = Field(ge=0.0, le=1000.0)
    elapsed_s: float = Field(ge=0.0, le=3600.0)
    obstacle_distance_m: float | None = Field(default=None, ge=0.0, le=1000.0)
    hardware_estop_asserted: bool = False
    policy_abort_asserted: bool = False
    source_kind: Literal["independent_stop_sensor"] = "independent_stop_sensor"

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0ResultObservationV1(StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.result-observation.v1"] = (
        "ets.demo.agent365-r0.result-observation.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    observer_id: str = Field(min_length=1, max_length=256)
    observed_at: datetime
    observed_monotonic_ns: int = Field(ge=0)
    speed_mps: float = Field(ge=0.0, le=20.0)
    distance_travelled_m: float = Field(ge=0.0, le=1000.0)
    stationary_duration_ms: int = Field(ge=0, le=60_000)
    source_kind: Literal["independent_result_sensor"] = "independent_result_sensor"

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class RangerR0BoundaryRecordV1(StrictModel):
    schema_version: Literal["ets.demo.agent365-r0.boundary-record.v1"] = (
        "ets.demo.agent365-r0.boundary-record.v1"
    )
    stage: RangerR0Stage
    envelope: MissionCorrelationEnvelopeV1
    payload: dict[str, JsonValue]

    @model_validator(mode="after")
    def validate_payload_commitment(self) -> RangerR0BoundaryRecordV1:
        if self.envelope.payload_sha256 != _sha256_json(self.payload):
            raise ValueError("envelope payload_sha256 does not match record payload")
        return self


class RangerR0ReceiptResultV1(StrictModel):
    receipt: RangerR0BoundaryRecordV1
    first_delivery: bool
    execution_allowed: bool
    current_stage: RangerR0Stage | None


class RangerR0MotionAuthorizationResultV1(StrictModel):
    record: RangerR0BoundaryRecordV1
    directive: RangerR0MotionDirectiveV1


class RangerR0StopActuationResultV1(StrictModel):
    record: RangerR0BoundaryRecordV1
    directive: RangerR0StopDirectiveV1


class SqliteRangerR0ReceiptLedger:
    """Durable execution-once boundary across Gateway transport retries.

    A new Gateway delivery may be recorded for the same mission only when it is an
    explicit retry of a previously accepted delivery and carries the same semantic
    command and authorization commitment.  A retry is never permission to execute
    the physical mission again.
    """

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
                    semantic_command_sha256 TEXT NOT NULL,
                    authorization_material_sha256 TEXT NOT NULL,
                    first_delivery_id TEXT NOT NULL UNIQUE,
                    first_gateway_payload_sha256 TEXT NOT NULL,
                    first_received_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ranger_r0_deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    retry_of_delivery_id TEXT,
                    semantic_command_sha256 TEXT NOT NULL,
                    gateway_payload_sha256 TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES ranger_r0_missions(mission_id)
                );
                CREATE INDEX IF NOT EXISTS ix_ranger_r0_deliveries_mission
                    ON ranger_r0_deliveries(mission_id);
                """
            )

    def consume_delivery(
        self,
        *,
        command: RangerR0GatewayCommandV1,
        semantic_command_sha256: str,
        received_at: datetime,
    ) -> bool:
        """Return True only for the first accepted delivery for a mission."""

        received_text = _format_utc(received_at)
        gateway_payload_sha256 = command.payload_sha256()
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                "SELECT mission_id FROM ranger_r0_deliveries WHERE delivery_id = ?",
                (command.delivery_id,),
            ).fetchone()
            if duplicate is not None:
                raise RangerR0BoundaryError(
                    "duplicate_delivery_id",
                    "delivery_id has already been received by Ranger R0",
                )

            existing = connection.execute(
                """
                SELECT semantic_command_sha256, authorization_material_sha256
                FROM ranger_r0_missions
                WHERE mission_id = ?
                """,
                (command.mission_id,),
            ).fetchone()

            if existing is None:
                if command.retry_of_delivery_id is not None:
                    raise RangerR0BoundaryError(
                        "orphan_retry",
                        "robot received a retry for a mission with no prior local receipt",
                    )
                connection.execute(
                    """
                    INSERT INTO ranger_r0_missions (
                        mission_id,
                        semantic_command_sha256,
                        authorization_material_sha256,
                        first_delivery_id,
                        first_gateway_payload_sha256,
                        first_received_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        command.mission_id,
                        semantic_command_sha256,
                        command.authorization_material_sha256,
                        command.delivery_id,
                        gateway_payload_sha256,
                        received_text,
                    ),
                )
                first_delivery = True
            else:
                if command.retry_of_delivery_id is None:
                    raise RangerR0BoundaryError(
                        "mission_already_received",
                        "mission already has a robot-side receipt; explicit retry linkage required",
                    )
                if existing[0] != semantic_command_sha256:
                    raise RangerR0BoundaryError(
                        "retry_command_mismatch",
                        "transport retry changed the semantic motion command",
                    )
                if existing[1] != command.authorization_material_sha256:
                    raise RangerR0BoundaryError(
                        "retry_authorization_mismatch",
                        "transport retry changed the authorization commitment",
                    )
                parent = connection.execute(
                    """
                    SELECT mission_id, semantic_command_sha256
                    FROM ranger_r0_deliveries
                    WHERE delivery_id = ?
                    """,
                    (command.retry_of_delivery_id,),
                ).fetchone()
                if parent is None or parent[0] != command.mission_id:
                    raise RangerR0BoundaryError(
                        "invalid_retry_parent",
                        "retry_of_delivery_id is not a prior local delivery for this mission",
                    )
                if parent[1] != semantic_command_sha256:
                    raise RangerR0BoundaryError(
                        "retry_parent_command_mismatch",
                        "retry parent is not the same semantic command",
                    )
                first_delivery = False

            connection.execute(
                """
                INSERT INTO ranger_r0_deliveries (
                    delivery_id,
                    mission_id,
                    retry_of_delivery_id,
                    semantic_command_sha256,
                    gateway_payload_sha256,
                    received_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    command.delivery_id,
                    command.mission_id,
                    command.retry_of_delivery_id,
                    semantic_command_sha256,
                    gateway_payload_sha256,
                    received_text,
                ),
            )
            connection.commit()
            return first_delivery

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection


@dataclass(slots=True)
class _MissionRuntime:
    command: RangerR0GatewayCommandV1
    stage: RangerR0Stage
    latest_record: RangerR0BoundaryRecordV1
    latest_monotonic_ns: int
    motion_directive: RangerR0MotionDirectiveV1 | None = None
    stop_reasons: tuple[RangerR0StopReason, ...] = ()


class RangerR0ReceiptMotionBoundary:
    """Executable robot-side state machine for the frozen R0 demonstration."""

    def __init__(
        self,
        ledger: SqliteRangerR0ReceiptLedger,
        *,
        vehicle_id: str,
        controller_id: str,
        start_speed_threshold_mps: float = 0.02,
        stopped_speed_threshold_mps: float = 0.02,
        required_stationary_duration_ms: int = 250,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:"):
            raise RangerR0BoundaryError(
                "invalid_vehicle_id",
                "vehicle_id must use the ets-ranger: namespace",
            )
        if not controller_id:
            raise RangerR0BoundaryError("invalid_controller_id", "controller_id must not be empty")
        if not 0.0 < start_speed_threshold_mps <= 0.25:
            raise RangerR0BoundaryError(
                "invalid_start_threshold",
                "start_speed_threshold_mps must be in (0, 0.25]",
            )
        if not 0.0 <= stopped_speed_threshold_mps <= start_speed_threshold_mps:
            raise RangerR0BoundaryError(
                "invalid_stop_threshold",
                "stopped_speed_threshold_mps must be between 0 and the start threshold",
            )
        if not 1 <= required_stationary_duration_ms <= 10_000:
            raise RangerR0BoundaryError(
                "invalid_stationary_duration",
                "required_stationary_duration_ms must be in [1, 10000]",
            )
        self._ledger = ledger
        self.vehicle_id = vehicle_id
        self.controller_id = controller_id
        self.start_speed_threshold_mps = start_speed_threshold_mps
        self.stopped_speed_threshold_mps = stopped_speed_threshold_mps
        self.required_stationary_duration_ms = required_stationary_duration_ms
        self._missions: dict[str, _MissionRuntime] = {}

    def receive(
        self,
        command: RangerR0GatewayCommandV1,
        gateway_egress: MissionCorrelationEnvelopeV1,
        *,
        observed_at: datetime,
        observed_monotonic_ns: int,
    ) -> RangerR0ReceiptResultV1:
        observed_at = _require_utc(observed_at)
        _require_nonnegative_monotonic(observed_monotonic_ns)
        self._validate_gateway_egress(command, gateway_egress)

        semantic_digest = _semantic_command_sha256(command)
        first_delivery = self._ledger.consume_delivery(
            command=command,
            semantic_command_sha256=semantic_digest,
            received_at=observed_at,
        )
        payload: dict[str, JsonValue] = {
            "mission_id": command.mission_id,
            "delivery_id": command.delivery_id,
            "retry_of_delivery_id": command.retry_of_delivery_id,
            "gateway_egress_event_id": gateway_egress.event_id,
            "gateway_command_payload_sha256": command.payload_sha256(),
            "semantic_command_sha256": semantic_digest,
            "transport_retry": not first_delivery,
            "claim_boundary": "receipt_of_validated_gateway_command_only",
        }
        receipt = _record(
            stage=RangerR0Stage.RECEIVED,
            mission_id=command.mission_id,
            event_id=f"ranger:{command.delivery_id}:received",
            parent_event_id=gateway_egress.event_id,
            event_type=(
                "ranger.command.received"
                if first_delivery
                else "ranger.command.retry.received"
            ),
            source_domain="ranger.r0",
            observed_at=observed_at,
            payload=payload,
            authorization_artifact_ref=command.authorization_artifact_ref,
            previous_event_digest=gateway_egress.canonical_digest(),
        )

        if first_delivery:
            self._missions[command.mission_id] = _MissionRuntime(
                command=command,
                stage=RangerR0Stage.RECEIVED,
                latest_record=receipt,
                latest_monotonic_ns=observed_monotonic_ns,
            )
            current_stage: RangerR0Stage | None = RangerR0Stage.RECEIVED
        else:
            runtime = self._missions.get(command.mission_id)
            current_stage = runtime.stage if runtime is not None else None

        return RangerR0ReceiptResultV1(
            receipt=receipt,
            first_delivery=first_delivery,
            execution_allowed=first_delivery,
            current_stage=current_stage,
        )

    def authorize_motion(
        self,
        mission_id: str,
        *,
        observed_at: datetime,
        observed_monotonic_ns: int,
        hardware_estop_asserted: bool = False,
    ) -> RangerR0MotionAuthorizationResultV1:
        runtime = self._runtime_at_stage(mission_id, RangerR0Stage.RECEIVED)
        observed_at = _require_utc(observed_at)
        self._advance_clock(runtime, observed_monotonic_ns)

        if hardware_estop_asserted:
            raise RangerR0BoundaryError(
                "hardware_estop_asserted",
                "Ranger R0 motion authorization denied while hardware E-stop is asserted",
            )

        parameters = runtime.command.command_parameters
        directive = RangerR0MotionDirectiveV1(
            mission_id=mission_id,
            delivery_id=runtime.command.delivery_id,
            vehicle_id=self.vehicle_id,
            controller_id=self.controller_id,
            issued_at=observed_at,
            issued_monotonic_ns=observed_monotonic_ns,
            linear_speed_mps=parameters.max_speed_mps,
            max_distance_m=parameters.max_distance_m,
            max_duration_s=parameters.max_duration_s,
            stop_distance_m=parameters.stop_distance_m,
        )
        payload: dict[str, JsonValue] = {
            "decision": "ACCEPT",
            "mission_id": mission_id,
            "delivery_id": runtime.command.delivery_id,
            "policy_version": runtime.command.policy_version,
            "authorization_material_sha256": runtime.command.authorization_material_sha256,
            "selected_motion": {
                "linear_speed_mps": directive.linear_speed_mps,
                "yaw_rate_rad_s": directive.yaw_rate_rad_s,
            },
            "bounds": {
                "max_distance_m": directive.max_distance_m,
                "max_duration_s": directive.max_duration_s,
                "stop_distance_m": directive.stop_distance_m,
            },
            "hardware_estop_asserted": False,
            "claim_boundary": directive.claim_boundary,
        }
        record = self._advance(
            runtime,
            stage=RangerR0Stage.AUTHORIZED,
            event_type="ranger.motion.authorized",
            source_domain="ranger.r0",
            observed_at=observed_at,
            payload=payload,
        )
        runtime.motion_directive = directive
        return RangerR0MotionAuthorizationResultV1(record=record, directive=directive)

    def record_motion_started(
        self,
        observation: RangerR0MotionStartObservationV1,
    ) -> RangerR0BoundaryRecordV1:
        runtime = self._runtime_at_stage(observation.mission_id, RangerR0Stage.AUTHORIZED)
        self._require_independent_observer(observation.observer_id)
        self._advance_clock(runtime, observation.observed_monotonic_ns)
        if observation.speed_mps < self.start_speed_threshold_mps:
            raise RangerR0BoundaryError(
                "motion_not_observed",
                "motion-start observation is below the configured start threshold",
            )
        directive = self._require_motion_directive(runtime)
        if observation.distance_travelled_m > directive.max_distance_m:
            raise RangerR0BoundaryError(
                "motion_start_outside_distance_bound",
                "motion-start observation already exceeds the authorized distance bound",
            )
        payload = observation.model_dump(mode="json")
        payload["claim_boundary"] = "sensor_observed_motion_not_command_inference"
        return self._advance(
            runtime,
            stage=RangerR0Stage.MOTION_STARTED,
            event_type="ranger.motion.started",
            source_domain="ranger.sensor",
            observed_at=observation.observed_at,
            payload=payload,
        )

    def observe_stop_condition(
        self,
        observation: RangerR0StopObservationV1,
    ) -> RangerR0BoundaryRecordV1 | None:
        runtime = self._runtime_at_stage(observation.mission_id, RangerR0Stage.MOTION_STARTED)
        self._require_independent_observer(observation.observer_id)
        self._advance_clock(runtime, observation.observed_monotonic_ns)
        directive = self._require_motion_directive(runtime)
        reasons = _stop_reasons(observation, directive)
        if not reasons:
            return None

        runtime.stop_reasons = reasons
        payload = observation.model_dump(mode="json")
        payload["trigger_reasons"] = [reason.value for reason in reasons]
        payload["claim_boundary"] = "observed_stop_trigger_not_yet_stop_decision_or_outcome"
        return self._advance(
            runtime,
            stage=RangerR0Stage.STOP_CONDITION_OBSERVED,
            event_type="ranger.stop_condition.observed",
            source_domain="ranger.sensor",
            observed_at=observation.observed_at,
            payload=payload,
        )

    def decide_stop(
        self,
        mission_id: str,
        *,
        observed_at: datetime,
        observed_monotonic_ns: int,
    ) -> RangerR0BoundaryRecordV1:
        runtime = self._runtime_at_stage(
            mission_id,
            RangerR0Stage.STOP_CONDITION_OBSERVED,
        )
        observed_at = _require_utc(observed_at)
        self._advance_clock(runtime, observed_monotonic_ns)
        if not runtime.stop_reasons:
            raise RangerR0BoundaryError(
                "missing_stop_reason",
                "stop decision requires a previously observed stop trigger",
            )
        primary_reason = runtime.stop_reasons[0]
        payload: dict[str, JsonValue] = {
            "mission_id": mission_id,
            "decision": "STOP",
            "primary_reason": primary_reason.value,
            "all_reasons": [reason.value for reason in runtime.stop_reasons],
            "policy_version": runtime.command.policy_version,
            "selected_action": "STOP",
            "claim_boundary": "policy_decision_not_stop_actuation_or_physical_outcome",
        }
        return self._advance(
            runtime,
            stage=RangerR0Stage.STOP_DECIDED,
            event_type="ranger.stop.decided",
            source_domain="ranger.r0",
            observed_at=observed_at,
            payload=payload,
        )

    def actuate_stop(
        self,
        mission_id: str,
        *,
        observed_at: datetime,
        observed_monotonic_ns: int,
    ) -> RangerR0StopActuationResultV1:
        runtime = self._runtime_at_stage(mission_id, RangerR0Stage.STOP_DECIDED)
        observed_at = _require_utc(observed_at)
        self._advance_clock(runtime, observed_monotonic_ns)
        primary_reason = runtime.stop_reasons[0]
        directive = RangerR0StopDirectiveV1(
            mission_id=mission_id,
            vehicle_id=self.vehicle_id,
            controller_id=self.controller_id,
            stop_reason=primary_reason,
            issued_at=observed_at,
            issued_monotonic_ns=observed_monotonic_ns,
        )
        payload: dict[str, JsonValue] = {
            "mission_id": mission_id,
            "stop_reason": primary_reason.value,
            "actuator_command": {
                "linear_speed_mps": 0.0,
                "yaw_rate_rad_s": 0.0,
            },
            "claim_boundary": directive.claim_boundary,
        }
        record = self._advance(
            runtime,
            stage=RangerR0Stage.STOP_ACTUATED,
            event_type="ranger.stop.actuated",
            source_domain="ranger.r0",
            observed_at=observed_at,
            payload=payload,
        )
        return RangerR0StopActuationResultV1(record=record, directive=directive)

    def record_result_observed(
        self,
        observation: RangerR0ResultObservationV1,
    ) -> RangerR0BoundaryRecordV1:
        runtime = self._runtime_at_stage(observation.mission_id, RangerR0Stage.STOP_ACTUATED)
        self._require_independent_observer(observation.observer_id)
        self._advance_clock(runtime, observation.observed_monotonic_ns)
        directive = self._require_motion_directive(runtime)

        if observation.speed_mps > self.stopped_speed_threshold_mps:
            raise RangerR0BoundaryError(
                "result_not_stopped",
                "result observation still shows motion above the stopped threshold",
            )
        if observation.stationary_duration_ms < self.required_stationary_duration_ms:
            raise RangerR0BoundaryError(
                "stationary_duration_insufficient",
                "result observation has not remained stationary for the required interval",
            )
        if observation.distance_travelled_m > directive.max_distance_m:
            raise RangerR0BoundaryError(
                "result_distance_exceeded",
                "result observation exceeds the authorized maximum distance",
            )

        payload = observation.model_dump(mode="json")
        payload["outcome"] = "STOP_CONFIRMED"
        payload["stop_reason"] = runtime.stop_reasons[0].value
        payload["stopped_speed_threshold_mps"] = self.stopped_speed_threshold_mps
        payload["required_stationary_duration_ms"] = self.required_stationary_duration_ms
        payload["claim_boundary"] = "independent_result_observation_supports_stopped_state"
        return self._advance(
            runtime,
            stage=RangerR0Stage.RESULT_OBSERVED,
            event_type="ranger.result.observed",
            source_domain="ranger.sensor",
            observed_at=observation.observed_at,
            payload=payload,
        )

    def stage(self, mission_id: str) -> RangerR0Stage:
        runtime = self._missions.get(mission_id)
        if runtime is None:
            raise RangerR0BoundaryError(
                "unknown_runtime_mission",
                "mission has no active in-process Ranger R0 runtime",
            )
        return runtime.stage

    def _validate_gateway_egress(
        self,
        command: RangerR0GatewayCommandV1,
        egress: MissionCorrelationEnvelopeV1,
    ) -> None:
        expected_type = (
            "gateway.command.retry.accepted"
            if command.retry_of_delivery_id is not None
            else "gateway.command.accepted"
        )
        if egress.source_domain != "ets.gateway":
            raise RangerR0BoundaryError(
                "invalid_gateway_source",
                "robot command receipt requires an ets.gateway egress event",
            )
        if egress.event_type != expected_type:
            raise RangerR0BoundaryError(
                "gateway_event_type_mismatch",
                "Gateway egress event type does not match delivery retry semantics",
            )
        if egress.mission_id != command.mission_id:
            raise RangerR0BoundaryError(
                "mission_id_mismatch",
                "Gateway egress and robot command mission_id values differ",
            )
        if egress.parent_event_id != command.gateway_decision_event_id:
            raise RangerR0BoundaryError(
                "gateway_parent_mismatch",
                "robot command does not bind to the Gateway decision parent",
            )
        if egress.payload_sha256 != command.payload_sha256():
            raise RangerR0BoundaryError(
                "gateway_payload_mismatch",
                "Gateway egress payload commitment does not match the robot command",
            )
        if egress.authorization_artifact_ref != command.authorization_artifact_ref:
            raise RangerR0BoundaryError(
                "authorization_artifact_mismatch",
                "Gateway egress and robot command reference different authorization artifacts",
            )

    def _runtime_at_stage(
        self,
        mission_id: str,
        expected: RangerR0Stage,
    ) -> _MissionRuntime:
        runtime = self._missions.get(mission_id)
        if runtime is None:
            raise RangerR0BoundaryError(
                "unknown_runtime_mission",
                "mission has no active in-process Ranger R0 runtime",
            )
        if runtime.stage is not expected:
            raise RangerR0BoundaryError(
                "invalid_stage_transition",
                f"expected {expected.value}, current stage is {runtime.stage.value}",
            )
        return runtime

    def _advance_clock(self, runtime: _MissionRuntime, observed_monotonic_ns: int) -> None:
        _require_nonnegative_monotonic(observed_monotonic_ns)
        if observed_monotonic_ns < runtime.latest_monotonic_ns:
            raise RangerR0BoundaryError(
                "monotonic_clock_regression",
                "robot-side monotonic time moved backwards",
            )
        runtime.latest_monotonic_ns = observed_monotonic_ns

    def _require_independent_observer(self, observer_id: str) -> None:
        if observer_id == self.controller_id:
            raise RangerR0BoundaryError(
                "observer_not_independent",
                "physical-state observation must not be asserted by the motion controller identity",
            )

    @staticmethod
    def _require_motion_directive(runtime: _MissionRuntime) -> RangerR0MotionDirectiveV1:
        if runtime.motion_directive is None:
            raise RangerR0BoundaryError(
                "missing_motion_directive",
                "mission runtime has no authorized motion directive",
            )
        return runtime.motion_directive

    def _advance(
        self,
        runtime: _MissionRuntime,
        *,
        stage: RangerR0Stage,
        event_type: str,
        source_domain: Literal["ranger.r0", "ranger.sensor"],
        observed_at: datetime,
        payload: dict[str, JsonValue],
    ) -> RangerR0BoundaryRecordV1:
        event_id = f"ranger:{runtime.command.delivery_id}:{stage.value.lower()}"
        record = _record(
            stage=stage,
            mission_id=runtime.command.mission_id,
            event_id=event_id,
            parent_event_id=runtime.latest_record.envelope.event_id,
            event_type=event_type,
            source_domain=source_domain,
            observed_at=observed_at,
            payload=payload,
            authorization_artifact_ref=runtime.command.authorization_artifact_ref,
            previous_event_digest=runtime.latest_record.envelope.canonical_digest(),
        )
        runtime.stage = stage
        runtime.latest_record = record
        return record


def _stop_reasons(
    observation: RangerR0StopObservationV1,
    directive: RangerR0MotionDirectiveV1,
) -> tuple[RangerR0StopReason, ...]:
    reasons: list[RangerR0StopReason] = []
    if observation.hardware_estop_asserted:
        reasons.append(RangerR0StopReason.HARDWARE_ESTOP)
    if observation.policy_abort_asserted:
        reasons.append(RangerR0StopReason.POLICY_ABORT)
    if (
        observation.obstacle_distance_m is not None
        and observation.obstacle_distance_m <= directive.stop_distance_m
    ):
        reasons.append(RangerR0StopReason.OBSTACLE_WITHIN_STOP_DISTANCE)
    if observation.distance_travelled_m >= directive.max_distance_m:
        reasons.append(RangerR0StopReason.MAX_DISTANCE_REACHED)
    if observation.elapsed_s >= directive.max_duration_s:
        reasons.append(RangerR0StopReason.MAX_DURATION_REACHED)
    return tuple(reasons)


def _semantic_command_sha256(command: RangerR0GatewayCommandV1) -> str:
    material = {
        "mission_id": command.mission_id,
        "scenario_id": command.scenario_id,
        "requested_action": command.requested_action,
        "policy_version": command.policy_version,
        "command_parameters": command.command_parameters.model_dump(mode="json"),
        "authorization_material_sha256": command.authorization_material_sha256,
        "authorization_artifact_ref": command.authorization_artifact_ref,
    }
    return _sha256_json(material)


def _record(
    *,
    stage: RangerR0Stage,
    mission_id: str,
    event_id: str,
    parent_event_id: str,
    event_type: str,
    source_domain: Literal["ranger.r0", "ranger.sensor"],
    observed_at: datetime,
    payload: dict[str, JsonValue],
    authorization_artifact_ref: str,
    previous_event_digest: str,
) -> RangerR0BoundaryRecordV1:
    envelope = MissionCorrelationEnvelopeV1(
        mission_id=mission_id,
        event_id=event_id,
        parent_event_id=parent_event_id,
        event_type=event_type,
        source_domain=source_domain,
        observed_at=_require_utc(observed_at),
        payload_sha256=_sha256_json(payload),
        authorization_artifact_ref=authorization_artifact_ref,
        correlation_basis="ets_parent_event",
        previous_event_digest=previous_event_digest,
    )
    return RangerR0BoundaryRecordV1(stage=stage, envelope=envelope, payload=payload)


def _require_nonnegative_monotonic(value: int) -> None:
    if value < 0:
        raise RangerR0BoundaryError(
            "invalid_monotonic_time",
            "robot-side monotonic timestamp cannot be negative",
        )


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return _require_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


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


__all__ = [
    "RangerR0BoundaryError",
    "RangerR0BoundaryRecordV1",
    "RangerR0MotionAuthorizationResultV1",
    "RangerR0MotionDirectiveV1",
    "RangerR0MotionStartObservationV1",
    "RangerR0ReceiptMotionBoundary",
    "RangerR0ReceiptResultV1",
    "RangerR0ResultObservationV1",
    "RangerR0Stage",
    "RangerR0StopActuationResultV1",
    "RangerR0StopDirectiveV1",
    "RangerR0StopObservationV1",
    "RangerR0StopReason",
    "SqliteRangerR0ReceiptLedger",
]
