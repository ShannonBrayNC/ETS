"""Fail-closed Gateway boundary for the frozen Agent 365 + Ranger R0 P0 demo."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from ets.demos.agent365_r0_mission import (
    MISSION_REQUESTED_ACTION,
    MISSION_SCENARIO_ID,
    MissionAuthorizationState,
    MissionStatus,
    SharePointMissionArtifactV1,
)

MISSION_EVENT_SCHEMA_VERSION: Final = "ets.demo.agent365-r0.mission-event.v1"
MISSION_POLICY_VERSION: Final = "r0-forward-stop-policy.v1"
GATEWAY_SOURCE_DOMAIN: Final = "ets.gateway"

_TERMINAL_STATUSES: Final = frozenset(
    {
        MissionStatus.COMPLETED_STOP_POINT,
        MissionStatus.COMPLETED_OBSTACLE_STOP,
        MissionStatus.ABORTED_ESTOP,
        MissionStatus.ABORTED_POLICY,
        MissionStatus.FAILED,
    }
)

CorrelationBasis = Literal[
    "native_mission_id",
    "controlled_request_context",
    "authorization_artifact",
    "native_parent_identifier",
    "ets_parent_event",
    "not_applicable",
]

SourceDomain = Literal[
    "microsoft.sharepoint",
    "microsoft.graph",
    "microsoft.agent365",
    "ets.microsoft-collector",
    "ets.gateway",
    "ranger.r0",
    "ranger.sensor",
    "ets.evidence-object",
    "ets.verifier",
]


class GatewayMissionEnforcementError(ValueError):
    """Raised when a P0 mission-scoped motion request must fail closed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MissionCorrelationEnvelopeV1(BaseModel):
    """Executable form of the frozen cross-domain P0 mission correlation envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.mission-event.v1"] = (
        MISSION_EVENT_SCHEMA_VERSION
    )
    mission_id: str = Field(min_length=36, max_length=36)
    scenario_id: Literal["agent365-r0-forward-stop-v1"] = MISSION_SCENARIO_ID
    event_id: str = Field(min_length=1, max_length=512)
    parent_event_id: str | None = Field(default=None, min_length=1, max_length=512)
    event_type: str = Field(min_length=1, max_length=256)
    source_domain: SourceDomain
    observed_at: datetime
    source_time: datetime | None = None
    source_event_id: str | None = Field(default=None, min_length=1, max_length=2048)
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_ref: str | None = Field(default=None, min_length=1, max_length=4096)
    authorization_artifact_ref: str | None = Field(default=None, min_length=1, max_length=4096)
    collector_identity: str | None = Field(default=None, min_length=1, max_length=512)
    collector_version: str | None = Field(default=None, min_length=1, max_length=256)
    correlation_basis: CorrelationBasis | None = None
    previous_event_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("observed_at", "source_time")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("mission event timestamps must be timezone-aware")
        return value.astimezone(UTC)

    def canonical_digest(self) -> str:
        """Return a stable digest for chaining ETS-controlled mission events."""

        encoded = _canonical_json(self.model_dump(mode="json")).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()


class FrozenR0CommandParameters(BaseModel):
    """Maximum P0 motion profile; values may be safer, never broader."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    max_speed_mps: float = Field(gt=0.0, le=0.25)
    max_distance_m: float = Field(gt=0.0, le=2.0)
    max_duration_s: int = Field(ge=1, le=20)
    stop_distance_m: float = Field(ge=0.45, le=2.0)

    @model_validator(mode="after")
    def validate_stop_geometry(self) -> FrozenR0CommandParameters:
        if self.stop_distance_m > self.max_distance_m:
            raise ValueError("stop_distance_m cannot exceed max_distance_m")
        return self


class GatewayR0MotionRequestV1(BaseModel):
    """Mission-scoped request accepted at the P0 Gateway motion boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mission_id: str = Field(min_length=36, max_length=36)
    scenario_id: Literal["agent365-r0-forward-stop-v1"] = MISSION_SCENARIO_ID
    requested_action: Literal["MOVE_FORWARD_UNTIL_STOP_CONDITION"] = MISSION_REQUESTED_ACTION
    policy_version: Literal["r0-forward-stop-policy.v1"] = MISSION_POLICY_VERSION
    command_parameters: FrozenR0CommandParameters
    authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_artifact_ref: str = Field(min_length=1, max_length=4096)
    delivery_id: str = Field(min_length=1, max_length=256)
    retry_of_delivery_id: str | None = Field(default=None, min_length=1, max_length=256)

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    def command_material(self) -> dict[str, JsonValue]:
        return {
            "mission_id": self.mission_id,
            "scenario_id": self.scenario_id,
            "requested_action": self.requested_action,
            "policy_version": self.policy_version,
            "command_parameters": self.command_parameters.model_dump(mode="json"),
            "authorization_material_sha256": self.authorization_material_sha256,
            "authorization_artifact_ref": self.authorization_artifact_ref,
        }

    def command_payload_sha256(self) -> str:
        return hashlib.sha256(_canonical_json(self.command_material()).encode("utf-8")).hexdigest()


class RangerR0GatewayCommandV1(BaseModel):
    """Bounded robot command emitted by the Gateway after authorization enforcement."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mission_id: str = Field(min_length=36, max_length=36)
    scenario_id: Literal["agent365-r0-forward-stop-v1"] = MISSION_SCENARIO_ID
    requested_action: Literal["MOVE_FORWARD_UNTIL_STOP_CONDITION"] = MISSION_REQUESTED_ACTION
    policy_version: Literal["r0-forward-stop-policy.v1"] = MISSION_POLICY_VERSION
    command_parameters: FrozenR0CommandParameters
    authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_artifact_ref: str = Field(min_length=1, max_length=4096)
    gateway_decision_event_id: str = Field(min_length=1, max_length=512)
    delivery_id: str = Field(min_length=1, max_length=256)
    retry_of_delivery_id: str | None = Field(default=None, min_length=1, max_length=256)
    issued_at: datetime

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        _validate_uuid4(value)
        return value

    @field_validator("issued_at")
    @classmethod
    def normalize_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        return value.astimezone(UTC)

    def payload_sha256(self) -> str:
        encoded = _canonical_json(self.model_dump(mode="json")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GatewayR0DispatchBundle:
    """All ETS-controlled records created by one accepted dispatch or transport retry."""

    ingress_event: MissionCorrelationEnvelopeV1
    decision_event: MissionCorrelationEnvelopeV1
    egress_event: MissionCorrelationEnvelopeV1
    robot_command: RangerR0GatewayCommandV1
    transport_retry: bool


class SqliteMissionDispatchLedger:
    """Durable replay boundary for P0 mission authorization consumption and retries."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS gateway_r0_missions (
                    mission_id TEXT PRIMARY KEY,
                    authorization_material_sha256 TEXT NOT NULL,
                    command_payload_sha256 TEXT NOT NULL,
                    first_delivery_id TEXT NOT NULL UNIQUE,
                    first_dispatched_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gateway_r0_deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    retry_of_delivery_id TEXT,
                    command_payload_sha256 TEXT NOT NULL,
                    dispatched_at TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES gateway_r0_missions(mission_id)
                );
                CREATE INDEX IF NOT EXISTS ix_gateway_r0_deliveries_mission
                    ON gateway_r0_deliveries(mission_id);
                """
            )

    def consume(
        self,
        *,
        mission_id: str,
        authorization_material_sha256: str,
        command_payload_sha256: str,
        delivery_id: str,
        retry_of_delivery_id: str | None,
        dispatched_at: datetime,
    ) -> bool:
        """Consume once or register an explicit same-command transport retry."""

        timestamp = _format_utc(dispatched_at)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                "SELECT mission_id FROM gateway_r0_deliveries WHERE delivery_id = ?",
                (delivery_id,),
            ).fetchone()
            if duplicate is not None:
                raise GatewayMissionEnforcementError(
                    "duplicate_delivery_id",
                    "delivery_id has already been consumed",
                )

            existing = connection.execute(
                """
                SELECT authorization_material_sha256, command_payload_sha256
                FROM gateway_r0_missions
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()

            if existing is None:
                if retry_of_delivery_id is not None:
                    raise GatewayMissionEnforcementError(
                        "orphan_retry",
                        "retry references a mission that has not been dispatched",
                    )
                connection.execute(
                    """
                    INSERT INTO gateway_r0_missions (
                        mission_id,
                        authorization_material_sha256,
                        command_payload_sha256,
                        first_delivery_id,
                        first_dispatched_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        mission_id,
                        authorization_material_sha256,
                        command_payload_sha256,
                        delivery_id,
                        timestamp,
                    ),
                )
                transport_retry = False
            else:
                if retry_of_delivery_id is None:
                    raise GatewayMissionEnforcementError(
                        "authorization_already_consumed",
                        (
                            "mission authorization was already consumed; "
                            "explicit retry linkage required"
                        ),
                    )
                if existing[0] != authorization_material_sha256:
                    raise GatewayMissionEnforcementError(
                        "authorization_digest_mismatch",
                        "retry changed the consumed authorization commitment",
                    )
                if existing[1] != command_payload_sha256:
                    raise GatewayMissionEnforcementError(
                        "retry_command_mismatch",
                        "retry changed the consumed command payload",
                    )
                parent = connection.execute(
                    """
                    SELECT mission_id, command_payload_sha256
                    FROM gateway_r0_deliveries
                    WHERE delivery_id = ?
                    """,
                    (retry_of_delivery_id,),
                ).fetchone()
                if parent is None or parent[0] != mission_id:
                    raise GatewayMissionEnforcementError(
                        "invalid_retry_parent",
                        "retry_of_delivery_id does not belong to this mission",
                    )
                if parent[1] != command_payload_sha256:
                    raise GatewayMissionEnforcementError(
                        "retry_parent_command_mismatch",
                        "retry parent does not carry the same command payload",
                    )
                transport_retry = True

            connection.execute(
                """
                INSERT INTO gateway_r0_deliveries (
                    delivery_id,
                    mission_id,
                    retry_of_delivery_id,
                    command_payload_sha256,
                    dispatched_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    delivery_id,
                    mission_id,
                    retry_of_delivery_id,
                    command_payload_sha256,
                    timestamp,
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


class GatewayR0MissionGuard:
    """Validate Microsoft authorization and emit one bounded Ranger R0 command."""

    def __init__(self, ledger: SqliteMissionDispatchLedger) -> None:
        self._ledger = ledger

    def dispatch(
        self,
        request: GatewayR0MotionRequestV1,
        authorized_mission: SharePointMissionArtifactV1,
        *,
        observed_at: datetime,
    ) -> GatewayR0DispatchBundle:
        observed_at = _require_utc(observed_at)
        self._validate_authorized_mission(request, authorized_mission)

        command_payload_sha256 = request.command_payload_sha256()
        transport_retry = self._ledger.consume(
            mission_id=request.mission_id,
            authorization_material_sha256=request.authorization_material_sha256,
            command_payload_sha256=command_payload_sha256,
            delivery_id=request.delivery_id,
            retry_of_delivery_id=request.retry_of_delivery_id,
            dispatched_at=observed_at,
        )

        ingress_id = f"gateway:{request.delivery_id}:ingress"
        decision_id = f"gateway:{request.delivery_id}:decision"
        egress_id = f"gateway:{request.delivery_id}:egress"
        ingress_event_type = (
            "gateway.command.retry.received"
            if transport_retry
            else "gateway.command.received"
        )
        egress_event_type = (
            "gateway.command.retry.accepted"
            if transport_retry
            else "gateway.command.accepted"
        )

        ingress = MissionCorrelationEnvelopeV1(
            mission_id=request.mission_id,
            event_id=ingress_id,
            event_type=ingress_event_type,
            source_domain=GATEWAY_SOURCE_DOMAIN,
            observed_at=observed_at,
            payload_sha256=command_payload_sha256,
            authorization_artifact_ref=request.authorization_artifact_ref,
            correlation_basis="controlled_request_context",
        )

        decision_payload = {
            "decision": "ACCEPT",
            "mission_id": request.mission_id,
            "policy_version": request.policy_version,
            "authorization_material_sha256": request.authorization_material_sha256,
            "command_payload_sha256": command_payload_sha256,
            "transport_retry": transport_retry,
        }
        decision = MissionCorrelationEnvelopeV1(
            mission_id=request.mission_id,
            event_id=decision_id,
            parent_event_id=ingress.event_id,
            event_type="gateway.authorization.accepted",
            source_domain=GATEWAY_SOURCE_DOMAIN,
            observed_at=observed_at,
            payload_sha256=_sha256_json(decision_payload),
            authorization_artifact_ref=request.authorization_artifact_ref,
            correlation_basis="authorization_artifact",
            previous_event_digest=ingress.canonical_digest(),
        )

        command = RangerR0GatewayCommandV1(
            mission_id=request.mission_id,
            policy_version=request.policy_version,
            command_parameters=request.command_parameters,
            authorization_material_sha256=request.authorization_material_sha256,
            authorization_artifact_ref=request.authorization_artifact_ref,
            gateway_decision_event_id=decision.event_id,
            delivery_id=request.delivery_id,
            retry_of_delivery_id=request.retry_of_delivery_id,
            issued_at=observed_at,
        )
        egress = MissionCorrelationEnvelopeV1(
            mission_id=request.mission_id,
            event_id=egress_id,
            parent_event_id=decision.event_id,
            event_type=egress_event_type,
            source_domain=GATEWAY_SOURCE_DOMAIN,
            observed_at=observed_at,
            payload_sha256=command.payload_sha256(),
            authorization_artifact_ref=request.authorization_artifact_ref,
            correlation_basis="ets_parent_event",
            previous_event_digest=decision.canonical_digest(),
        )
        return GatewayR0DispatchBundle(
            ingress_event=ingress,
            decision_event=decision,
            egress_event=egress,
            robot_command=command,
            transport_retry=transport_retry,
        )

    def _validate_authorized_mission(
        self,
        request: GatewayR0MotionRequestV1,
        mission: SharePointMissionArtifactV1,
    ) -> None:
        if mission.mission_id != request.mission_id:
            raise GatewayMissionEnforcementError(
                "mission_id_mismatch",
                "Gateway request mission_id does not match the SharePoint authorization artifact",
            )
        if mission.scenario_id != request.scenario_id:
            raise GatewayMissionEnforcementError(
                "scenario_mismatch",
                "Gateway request scenario does not match the authorization artifact",
            )
        if mission.requested_action != request.requested_action:
            raise GatewayMissionEnforcementError(
                "requested_action_mismatch",
                "Gateway request action does not match the authorization artifact",
            )
        if mission.authorization_state != MissionAuthorizationState.AUTHORIZED:
            raise GatewayMissionEnforcementError(
                "mission_not_authorized",
                "SharePoint mission authorization state is not AUTHORIZED",
            )
        if mission.status in _TERMINAL_STATUSES:
            raise GatewayMissionEnforcementError(
                "mission_terminal",
                "terminal missions cannot be dispatched",
            )
        if mission.status not in {MissionStatus.AUTHORIZED, MissionStatus.DISPATCHED}:
            raise GatewayMissionEnforcementError(
                "mission_status_not_dispatchable",
                "mission status is outside the P0 dispatch/retry boundary",
            )
        if mission.policy_version != request.policy_version:
            raise GatewayMissionEnforcementError(
                "policy_version_mismatch",
                "Gateway request policy version does not match the authorization artifact",
            )

        expected_digest = mission.authorization_material_sha256()
        if request.authorization_material_sha256 != expected_digest:
            raise GatewayMissionEnforcementError(
                "authorization_digest_mismatch",
                "Gateway request does not carry the authorized command commitment",
            )

        try:
            authorized_parameters = FrozenR0CommandParameters.model_validate(
                mission.command_parameters
            )
        except ValueError as exc:
            raise GatewayMissionEnforcementError(
                "authorized_parameters_outside_safety_profile",
                "authorized SharePoint command parameters exceed the frozen P0 safety profile",
            ) from exc

        if authorized_parameters != request.command_parameters:
            raise GatewayMissionEnforcementError(
                "command_parameters_mismatch",
                "Gateway request command parameters differ from the authorized mission",
            )


def build_correlation_envelope(
    *,
    mission_id: str,
    event_id: str,
    event_type: str,
    source_domain: SourceDomain,
    observed_at: datetime,
    payload: bytes,
    parent_event_id: str | None = None,
    authorization_artifact_ref: str | None = None,
    correlation_basis: CorrelationBasis | None = None,
    previous_event_digest: str | None = None,
) -> MissionCorrelationEnvelopeV1:
    """Attach ETS mission correlation without changing preserved source bytes."""

    return MissionCorrelationEnvelopeV1(
        mission_id=mission_id,
        event_id=event_id,
        parent_event_id=parent_event_id,
        event_type=event_type,
        source_domain=source_domain,
        observed_at=_require_utc(observed_at),
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        authorization_artifact_ref=authorization_artifact_ref,
        correlation_basis=correlation_basis,
        previous_event_digest=previous_event_digest,
    )


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


def _format_utc(value: datetime) -> str:
    return _require_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, object] | object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_json(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
