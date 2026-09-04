"""Fail-closed Ranger R0.1 motion authorization reference.

This module is deliberately hardware-neutral.  A simulator and a future motor-controller
adapter must submit commands to the same boundary.  The returned records describe command
authorization, not proof that an actuator or vehicle produced the requested physical result.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class SafetyMode(StrEnum):
    DISARMED = "disarmed"
    ARMED = "armed"
    ESTOP_LATCHED = "estop_latched"
    COMMAND_TIMEOUT = "command_timeout"


class CommandSource(StrEnum):
    TELEOPERATOR = "teleoperator"


class ClockQuality(StrEnum):
    SYNCHRONIZED = "synchronized"
    ESTIMATED = "estimated"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class AuthorizationResult(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class MobilityEventKind(StrEnum):
    COMMAND_AUTHORIZATION = "command_authorization"
    SAFETY_STOP = "safety_stop"


class MotionReason(StrEnum):
    HARDWARE_ESTOP_ASSERTED = "hardware_estop_asserted"
    ESTOP_LATCHED = "estop_latched"
    NOT_ARMED = "not_armed"
    COMMAND_TIMEOUT_LATCHED = "command_timeout_latched"
    DEADMAN_RELEASED = "deadman_released"
    IDENTITY_MISMATCH = "identity_mismatch"
    NON_MONOTONIC_COMMAND = "non_monotonic_command"
    INVALID_MONOTONIC_ORDER = "invalid_monotonic_order"
    STALE_COMMAND = "stale_command"
    LINEAR_SPEED_LIMIT = "linear_speed_limit"
    YAW_RATE_LIMIT = "yaw_rate_limit"
    REVERSE_PROHIBITED = "reverse_prohibited"
    WATCHDOG_TIMEOUT = "watchdog_timeout"


class MotionVector(StrictModel):
    """Topology-neutral motion intent for skid-steer or Ackermann adapters."""

    linear_speed_mps: float = Field(ge=-20.0, le=20.0)
    yaw_rate_rad_s: float = Field(ge=-20.0, le=20.0)

    @classmethod
    def stopped(cls) -> MotionVector:
        return cls(linear_speed_mps=0.0, yaw_rate_rad_s=0.0)

    @property
    def is_stopped(self) -> bool:
        return self.linear_speed_mps == 0.0 and self.yaw_rate_rad_s == 0.0


class RangerDriveCommand(StrictModel):
    schema_version: Literal["ets.ranger.drive-command.v1"] = "ets.ranger.drive-command.v1"
    command_id: str = Field(min_length=1, max_length=128)
    command_sequence: int = Field(ge=1, le=2**63 - 1)
    mission_id: str = Field(min_length=1, max_length=128)
    vehicle_id: str = Field(min_length=12, max_length=160)
    controller_id: str = Field(min_length=1, max_length=160)
    controller_session_id: str = Field(min_length=1, max_length=128)
    source: Literal[CommandSource.TELEOPERATOR] = CommandSource.TELEOPERATOR
    issued_at_utc: datetime
    source_clock_quality: ClockQuality = ClockQuality.UNKNOWN
    deadman_asserted: bool
    requested_motion: MotionVector

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("issued_at_utc")
    @classmethod
    def normalize_issued_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("issued_at_utc must be timezone-aware")
        return value.astimezone(UTC)


class RangerMobilityPolicy(StrictModel):
    schema_version: Literal["ets.ranger.mobility-policy.v1"] = "ets.ranger.mobility-policy.v1"
    policy_id: str = Field(min_length=1, max_length=256)
    policy_version: str = Field(min_length=1, max_length=64)
    max_linear_speed_mps: float = Field(gt=0.0, le=6.7056)
    max_yaw_rate_rad_s: float = Field(gt=0.0, le=6.2832)
    max_command_queue_age_ms: int = Field(ge=1, le=5_000)
    watchdog_timeout_ms: int = Field(ge=1, le=5_000)
    allow_reverse: bool = True

    @model_validator(mode="after")
    def require_watchdog_to_cover_queue_age(self) -> Self:
        if self.watchdog_timeout_ms < self.max_command_queue_age_ms:
            raise ValueError("watchdog_timeout_ms must cover max_command_queue_age_ms")
        return self


class ObservedSafetyFacts(StrictModel):
    classification: Literal["observed_fact"] = "observed_fact"
    mode_before: SafetyMode
    hardware_estop_asserted: bool
    software_estop_latched_before: bool
    deadman_asserted: bool | None
    vehicle_identity_match: bool | None
    mission_identity_match: bool | None
    controller_identity_match: bool | None
    controller_session_identity_match: bool | None
    command_sequence_is_fresh: bool | None
    applied_motion_before: MotionVector


class DerivedSafetyValues(StrictModel):
    classification: Literal["derived_value"] = "derived_value"
    command_queue_age_ms: int | None = Field(default=None, ge=0)
    watchdog_elapsed_ms: int | None = Field(default=None, ge=0)
    requested_linear_speed_abs_mps: float | None = Field(default=None, ge=0.0)
    requested_yaw_rate_abs_rad_s: float | None = Field(default=None, ge=0.0)


class MobilityPolicyEvaluation(StrictModel):
    classification: Literal["policy_evaluation"] = "policy_evaluation"
    evaluator: Literal["ets.ranger.mobility-safety.v1"] = "ets.ranger.mobility-safety.v1"
    policy_id: str = Field(min_length=1, max_length=256)
    policy_version: str = Field(min_length=1, max_length=64)
    policy_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_result: AuthorizationResult
    reason_codes: tuple[MotionReason, ...]
    selected_motion: MotionVector

    @model_validator(mode="after")
    def require_fail_closed_result(self) -> Self:
        if self.authorization_result is AuthorizationResult.ALLOWED and self.reason_codes:
            raise ValueError("allowed evaluations cannot contain denial reasons")
        if self.authorization_result is AuthorizationResult.DENIED:
            if not self.reason_codes:
                raise ValueError("denied evaluations require at least one reason")
            if not self.selected_motion.is_stopped:
                raise ValueError("denied evaluations must select stopped motion")
        return self


class ActuatorCommand(StrictModel):
    classification: Literal["actuator_command"] = "actuator_command"
    command_profile: Literal["ets.ranger.motion-vector.v1"] = "ets.ranger.motion-vector.v1"
    motion: MotionVector


class RangerMobilityEvent(StrictModel):
    """Unsigned R0.1 source record emitted at the motion safety boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/mobility-event/v1"
        },
    )

    schema_version: Literal["ets.ranger.mobility-event.v1"] = "ets.ranger.mobility-event.v1"
    event_id: str = Field(min_length=1, max_length=256)
    event_sequence: int = Field(ge=1, le=2**63 - 1)
    event_kind: MobilityEventKind
    vehicle_id: str = Field(min_length=12, max_length=160)
    mission_id: str = Field(min_length=1, max_length=128)
    controller_id: str = Field(min_length=1, max_length=160)
    controller_session_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    evaluated_at_utc: datetime
    evaluated_monotonic_ns: int = Field(ge=0)
    local_clock_quality: ClockQuality = ClockQuality.UNKNOWN
    operator_command: RangerDriveCommand | None
    observed_facts: ObservedSafetyFacts
    derived_values: DerivedSafetyValues
    policy_evaluation: MobilityPolicyEvaluation
    actuator_command: ActuatorCommand
    mode_after: SafetyMode
    observed_result: None = None
    claim_boundary: Literal["authorization_only_no_actuator_or_physical_outcome"] = (
        "authorization_only_no_actuator_or_physical_outcome"
    )

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("evaluated_at_utc")
    @classmethod
    def normalize_evaluated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_event_kind_payload(self) -> Self:
        if self.event_kind is MobilityEventKind.COMMAND_AUTHORIZATION:
            if self.operator_command is None:
                raise ValueError("command_authorization requires an operator command")
        elif self.operator_command is not None:
            raise ValueError("safety_stop cannot contain an operator command")
        if self.actuator_command.motion != self.policy_evaluation.selected_motion:
            raise ValueError("actuator command must match the selected policy action")
        if self.event_kind is MobilityEventKind.SAFETY_STOP:
            if self.policy_evaluation.authorization_result is not AuthorizationResult.DENIED:
                raise ValueError("safety_stop must carry a denied authorization result")
            if not self.actuator_command.motion.is_stopped:
                raise ValueError("safety_stop must command stopped motion")
        if self.policy_evaluation.authorization_result is AuthorizationResult.ALLOWED:
            if self.mode_after is not SafetyMode.ARMED:
                raise ValueError("allowed motion requires armed mode")
            if self.operator_command is None:
                raise ValueError("allowed motion requires an operator command")
            if not all(
                (
                    self.observed_facts.vehicle_identity_match,
                    self.observed_facts.mission_identity_match,
                    self.observed_facts.controller_identity_match,
                    self.observed_facts.controller_session_identity_match,
                    self.observed_facts.command_sequence_is_fresh,
                    self.observed_facts.deadman_asserted,
                )
            ):
                raise ValueError("allowed motion requires positive standing observations")
            if self.observed_facts.hardware_estop_asserted:
                raise ValueError("allowed motion cannot coexist with asserted E-stop")
        return self


class RangerSafetyInputError(ValueError):
    """Raised for an invalid local safety-clock or lifecycle transition."""


class RangerMobilityController:
    """Deterministic reference interlock shared by simulation and future adapters."""

    def __init__(
        self,
        *,
        vehicle_id: str,
        mission_id: str,
        controller_id: str,
        controller_session_id: str,
        boot_id: str,
        policy: RangerMobilityPolicy,
        local_clock_quality: ClockQuality = ClockQuality.UNKNOWN,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerSafetyInputError("vehicle_id must use the ets-ranger: namespace")
        for name, value, maximum in (
            ("mission_id", mission_id, 128),
            ("controller_id", controller_id, 160),
            ("controller_session_id", controller_session_id, 128),
            ("boot_id", boot_id, 128),
        ):
            if not value or len(value) > maximum:
                raise RangerSafetyInputError(f"{name} must contain 1-{maximum} characters")

        self.vehicle_id = vehicle_id
        self.mission_id = mission_id
        self.controller_id = controller_id
        self.controller_session_id = controller_session_id
        self.boot_id = boot_id
        self.policy = RangerMobilityPolicy.model_validate(policy.model_dump())
        self.local_clock_quality = local_clock_quality
        self._mode = SafetyMode.DISARMED
        self._applied_motion = MotionVector.stopped()
        self._event_sequence = 0
        self._last_command_sequence: int | None = None
        self._last_control_monotonic_ns: int | None = None
        self._last_evaluation_monotonic_ns: int | None = None
        self._policy_digest = canonical_sha256(self.policy.model_dump(mode="json"))

    @property
    def policy_digest_sha256(self) -> str:
        return self._policy_digest

    @property
    def mode(self) -> SafetyMode:
        return self._mode

    @property
    def applied_motion(self) -> MotionVector:
        return self._applied_motion

    def arm(self, *, now_monotonic_ns: int, hardware_estop_asserted: bool) -> SafetyMode:
        self._accept_lifecycle_time(now_monotonic_ns)
        self._applied_motion = MotionVector.stopped()
        if hardware_estop_asserted:
            self._mode = SafetyMode.ESTOP_LATCHED
            self._last_control_monotonic_ns = None
            return self._mode
        if self._mode is SafetyMode.ESTOP_LATCHED:
            return self._mode
        self._mode = SafetyMode.ARMED
        self._last_control_monotonic_ns = now_monotonic_ns
        return self._mode

    def disarm(self, *, now_monotonic_ns: int) -> SafetyMode:
        self._accept_lifecycle_time(now_monotonic_ns)
        self._mode = SafetyMode.DISARMED
        self._applied_motion = MotionVector.stopped()
        self._last_control_monotonic_ns = None
        return self._mode

    def reset_estop(
        self,
        *,
        now_monotonic_ns: int,
        hardware_estop_asserted: bool,
    ) -> SafetyMode:
        self._accept_lifecycle_time(now_monotonic_ns)
        self._applied_motion = MotionVector.stopped()
        if hardware_estop_asserted:
            self._mode = SafetyMode.ESTOP_LATCHED
            raise RangerSafetyInputError("hardware E-stop must be released before reset")
        if self._mode is not SafetyMode.ESTOP_LATCHED:
            raise RangerSafetyInputError("E-stop reset requires the latched state")
        self._mode = SafetyMode.DISARMED
        self._last_control_monotonic_ns = None
        return self._mode

    def authorize(
        self,
        command: RangerDriveCommand,
        *,
        received_monotonic_ns: int,
        evaluated_monotonic_ns: int,
        evaluated_at_utc: datetime,
        hardware_estop_asserted: bool,
    ) -> RangerMobilityEvent:
        command = RangerDriveCommand.model_validate(command.model_dump())
        evaluated_at_utc = self._normalize_utc(evaluated_at_utc)
        mode_before = self._mode
        applied_before = self._applied_motion
        reasons: list[MotionReason] = []

        if hardware_estop_asserted:
            self._mode = SafetyMode.ESTOP_LATCHED
            reasons.append(MotionReason.HARDWARE_ESTOP_ASSERTED)
        elif self._mode is SafetyMode.ESTOP_LATCHED:
            reasons.append(MotionReason.ESTOP_LATCHED)
        elif self._mode is SafetyMode.COMMAND_TIMEOUT:
            reasons.append(MotionReason.COMMAND_TIMEOUT_LATCHED)
        elif self._mode is not SafetyMode.ARMED:
            reasons.append(MotionReason.NOT_ARMED)

        vehicle_match = command.vehicle_id == self.vehicle_id
        mission_match = command.mission_id == self.mission_id
        controller_match = command.controller_id == self.controller_id
        session_match = command.controller_session_id == self.controller_session_id
        if not all((vehicle_match, mission_match, controller_match, session_match)):
            reasons.append(MotionReason.IDENTITY_MISMATCH)

        sequence_fresh = (
            self._last_command_sequence is None
            or command.command_sequence > self._last_command_sequence
        )
        if not sequence_fresh:
            reasons.append(MotionReason.NON_MONOTONIC_COMMAND)

        valid_monotonic_order = (
            received_monotonic_ns >= 0
            and evaluated_monotonic_ns >= received_monotonic_ns
            and (
                self._last_evaluation_monotonic_ns is None
                or evaluated_monotonic_ns >= self._last_evaluation_monotonic_ns
            )
        )
        command_age_ms: int | None = None
        if not valid_monotonic_order:
            reasons.append(MotionReason.INVALID_MONOTONIC_ORDER)
            self._mode = SafetyMode.COMMAND_TIMEOUT
        else:
            command_age_ns = evaluated_monotonic_ns - received_monotonic_ns
            command_age_ms = command_age_ns // 1_000_000
            if command_age_ns > self.policy.max_command_queue_age_ms * 1_000_000:
                reasons.append(MotionReason.STALE_COMMAND)

        if not command.deadman_asserted:
            reasons.append(MotionReason.DEADMAN_RELEASED)
        if abs(command.requested_motion.linear_speed_mps) > self.policy.max_linear_speed_mps:
            reasons.append(MotionReason.LINEAR_SPEED_LIMIT)
        if abs(command.requested_motion.yaw_rate_rad_s) > self.policy.max_yaw_rate_rad_s:
            reasons.append(MotionReason.YAW_RATE_LIMIT)
        if not self.policy.allow_reverse and command.requested_motion.linear_speed_mps < 0.0:
            reasons.append(MotionReason.REVERSE_PROHIBITED)

        identity_matches = all((vehicle_match, mission_match, controller_match, session_match))
        if identity_matches and sequence_fresh:
            self._last_command_sequence = command.command_sequence
        if valid_monotonic_order:
            self._last_evaluation_monotonic_ns = evaluated_monotonic_ns

        if reasons:
            authorization = AuthorizationResult.DENIED
            selected = MotionVector.stopped()
        else:
            authorization = AuthorizationResult.ALLOWED
            selected = command.requested_motion
            self._last_control_monotonic_ns = evaluated_monotonic_ns
        self._applied_motion = selected

        return self._event(
            event_kind=MobilityEventKind.COMMAND_AUTHORIZATION,
            evaluated_at_utc=evaluated_at_utc,
            evaluated_monotonic_ns=evaluated_monotonic_ns,
            operator_command=command,
            observed_facts=ObservedSafetyFacts(
                mode_before=mode_before,
                hardware_estop_asserted=hardware_estop_asserted,
                software_estop_latched_before=mode_before is SafetyMode.ESTOP_LATCHED,
                deadman_asserted=command.deadman_asserted,
                vehicle_identity_match=vehicle_match,
                mission_identity_match=mission_match,
                controller_identity_match=controller_match,
                controller_session_identity_match=session_match,
                command_sequence_is_fresh=sequence_fresh,
                applied_motion_before=applied_before,
            ),
            derived_values=DerivedSafetyValues(
                command_queue_age_ms=command_age_ms,
                requested_linear_speed_abs_mps=abs(command.requested_motion.linear_speed_mps),
                requested_yaw_rate_abs_rad_s=abs(command.requested_motion.yaw_rate_rad_s),
            ),
            authorization=authorization,
            reasons=tuple(dict.fromkeys(reasons)),
            selected=selected,
        )

    def enforce_watchdog(
        self,
        *,
        now_monotonic_ns: int,
        observed_at_utc: datetime,
        hardware_estop_asserted: bool,
    ) -> RangerMobilityEvent | None:
        observed_at_utc = self._normalize_utc(observed_at_utc)
        if now_monotonic_ns < 0:
            raise RangerSafetyInputError("now_monotonic_ns cannot be negative")

        mode_before = self._mode
        applied_before = self._applied_motion
        reason: MotionReason | None = None
        elapsed_ms: int | None = None

        if hardware_estop_asserted and self._mode is not SafetyMode.ESTOP_LATCHED:
            self._mode = SafetyMode.ESTOP_LATCHED
            reason = MotionReason.HARDWARE_ESTOP_ASSERTED
        elif self._mode is SafetyMode.ARMED:
            if self._last_control_monotonic_ns is None:
                self._mode = SafetyMode.COMMAND_TIMEOUT
                reason = MotionReason.WATCHDOG_TIMEOUT
            elif now_monotonic_ns < self._last_control_monotonic_ns:
                self._mode = SafetyMode.COMMAND_TIMEOUT
                reason = MotionReason.INVALID_MONOTONIC_ORDER
            else:
                elapsed_ms = (now_monotonic_ns - self._last_control_monotonic_ns) // 1_000_000
                if elapsed_ms >= self.policy.watchdog_timeout_ms:
                    self._mode = SafetyMode.COMMAND_TIMEOUT
                    reason = MotionReason.WATCHDOG_TIMEOUT

        if reason is None:
            if (
                self._last_evaluation_monotonic_ns is not None
                and now_monotonic_ns < self._last_evaluation_monotonic_ns
            ):
                self._mode = SafetyMode.COMMAND_TIMEOUT
                self._applied_motion = MotionVector.stopped()
                raise RangerSafetyInputError("local monotonic clock regressed")
            self._last_evaluation_monotonic_ns = now_monotonic_ns
            return None

        self._applied_motion = MotionVector.stopped()
        self._last_control_monotonic_ns = None
        self._last_evaluation_monotonic_ns = max(
            now_monotonic_ns,
            self._last_evaluation_monotonic_ns or 0,
        )
        return self._event(
            event_kind=MobilityEventKind.SAFETY_STOP,
            evaluated_at_utc=observed_at_utc,
            evaluated_monotonic_ns=now_monotonic_ns,
            operator_command=None,
            observed_facts=ObservedSafetyFacts(
                mode_before=mode_before,
                hardware_estop_asserted=hardware_estop_asserted,
                software_estop_latched_before=mode_before is SafetyMode.ESTOP_LATCHED,
                deadman_asserted=None,
                vehicle_identity_match=None,
                mission_identity_match=None,
                controller_identity_match=None,
                controller_session_identity_match=None,
                command_sequence_is_fresh=None,
                applied_motion_before=applied_before,
            ),
            derived_values=DerivedSafetyValues(watchdog_elapsed_ms=elapsed_ms),
            authorization=AuthorizationResult.DENIED,
            reasons=(reason,),
            selected=MotionVector.stopped(),
        )

    def _event(
        self,
        *,
        event_kind: MobilityEventKind,
        evaluated_at_utc: datetime,
        evaluated_monotonic_ns: int,
        operator_command: RangerDriveCommand | None,
        observed_facts: ObservedSafetyFacts,
        derived_values: DerivedSafetyValues,
        authorization: AuthorizationResult,
        reasons: tuple[MotionReason, ...],
        selected: MotionVector,
    ) -> RangerMobilityEvent:
        self._event_sequence += 1
        evaluation = MobilityPolicyEvaluation(
            policy_id=self.policy.policy_id,
            policy_version=self.policy.policy_version,
            policy_digest_sha256=self.policy_digest_sha256,
            authorization_result=authorization,
            reason_codes=reasons,
            selected_motion=selected,
        )
        event_id = "rme:" + canonical_sha256(
            {
                "vehicle_id": self.vehicle_id,
                "mission_id": self.mission_id,
                "boot_id": self.boot_id,
                "event_sequence": self._event_sequence,
            }
        )
        return RangerMobilityEvent(
            event_id=event_id,
            event_sequence=self._event_sequence,
            event_kind=event_kind,
            vehicle_id=self.vehicle_id,
            mission_id=self.mission_id,
            controller_id=self.controller_id,
            controller_session_id=self.controller_session_id,
            boot_id=self.boot_id,
            evaluated_at_utc=evaluated_at_utc,
            evaluated_monotonic_ns=evaluated_monotonic_ns,
            local_clock_quality=self.local_clock_quality,
            operator_command=operator_command,
            observed_facts=observed_facts,
            derived_values=derived_values,
            policy_evaluation=evaluation,
            actuator_command=ActuatorCommand(motion=selected),
            mode_after=self._mode,
        )

    def _accept_lifecycle_time(self, now_monotonic_ns: int) -> None:
        if now_monotonic_ns < 0:
            raise RangerSafetyInputError("now_monotonic_ns cannot be negative")
        if (
            self._last_evaluation_monotonic_ns is not None
            and now_monotonic_ns < self._last_evaluation_monotonic_ns
        ):
            self._mode = SafetyMode.COMMAND_TIMEOUT
            self._applied_motion = MotionVector.stopped()
            raise RangerSafetyInputError("local monotonic clock regressed")
        self._last_evaluation_monotonic_ns = now_monotonic_ns

    @staticmethod
    def _normalize_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise RangerSafetyInputError("wall-clock evidence time must be timezone-aware")
        return value.astimezone(UTC)
