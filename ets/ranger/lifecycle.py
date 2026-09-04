"""First-class Ranger R0.1 evidence for motion-authority lifecycle transitions.

Lifecycle records are distinct from mobility authorization records. They establish how
software motion authority changed (arm, disarm, E-stop latch/reset, watchdog timeout, and
explicit timeout recovery) without claiming a physical actuator response or outcome.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.ranger.mobility import (
    ClockQuality,
    MotionReason,
    RangerDriveCommand,
    RangerMobilityController,
    RangerMobilityEvent,
    RangerSafetyInputError,
    SafetyMode,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerLifecycleKind(StrEnum):
    ARM = "arm"
    DISARM = "disarm"
    ESTOP_LATCH = "estop_latch"
    ESTOP_RESET = "estop_reset"
    WATCHDOG_TIMEOUT = "watchdog_timeout"
    TIMEOUT_RECOVERY_REARM = "timeout_recovery_rearm"


class RangerLifecycleResult(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"


class RangerLifecycleEvent(StrictModel):
    """Unsigned R0.1 source record describing a motion-authority transition."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/lifecycle-event/v1"
        },
    )

    schema_version: Literal["ets.ranger.lifecycle-event.v1"] = "ets.ranger.lifecycle-event.v1"
    event_id: str = Field(min_length=1, max_length=256)
    lifecycle_sequence: int = Field(ge=1, le=2**63 - 1)
    lifecycle_kind: RangerLifecycleKind
    transition_result: RangerLifecycleResult
    vehicle_id: str = Field(min_length=12, max_length=160)
    mission_id: str = Field(min_length=1, max_length=128)
    controller_id: str = Field(min_length=1, max_length=160)
    controller_session_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    occurred_at_utc: datetime
    occurred_monotonic_ns: int = Field(ge=0)
    local_clock_quality: ClockQuality = ClockQuality.UNKNOWN
    mode_before: SafetyMode
    mode_after: SafetyMode
    hardware_estop_asserted: bool | None = None
    source_mobility_event_id: str | None = Field(default=None, min_length=1, max_length=256)
    source_mobility_event_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    reason_code: MotionReason | None = None
    operator_rearm_required: bool
    physical_estop_state_proven: Literal[False] = False
    physical_motion_state_proven: Literal[False] = False
    claim_boundary: Literal["software_authority_transition_only_no_physical_outcome"] = (
        "software_authority_transition_only_no_physical_outcome"
    )

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("occurred_at_utc")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_transition_semantics(self) -> Self:
        if (self.source_mobility_event_id is None) != (
            self.source_mobility_event_digest_sha256 is None
        ):
            raise ValueError("mobility-event id and digest must be supplied together")
        if self.lifecycle_kind in {
            RangerLifecycleKind.ESTOP_LATCH,
            RangerLifecycleKind.WATCHDOG_TIMEOUT,
        } and self.source_mobility_event_id is None:
            raise ValueError("safety-triggered lifecycle events must link to a mobility event")
        if self.lifecycle_kind is RangerLifecycleKind.ESTOP_LATCH:
            if self.mode_after is not SafetyMode.ESTOP_LATCHED:
                raise ValueError("E-stop latch evidence must end in estop_latched")
        if self.lifecycle_kind is RangerLifecycleKind.ESTOP_RESET:
            if self.mode_before is not SafetyMode.ESTOP_LATCHED or self.mode_after is not SafetyMode.DISARMED:
                raise ValueError("E-stop reset must transition estop_latched to disarmed")
        if self.lifecycle_kind is RangerLifecycleKind.WATCHDOG_TIMEOUT:
            if self.mode_after is not SafetyMode.COMMAND_TIMEOUT:
                raise ValueError("watchdog timeout evidence must end in command_timeout")
        if self.lifecycle_kind is RangerLifecycleKind.TIMEOUT_RECOVERY_REARM:
            if self.mode_before is not SafetyMode.COMMAND_TIMEOUT or self.mode_after is not SafetyMode.ARMED:
                raise ValueError("timeout recovery must explicitly re-arm from command_timeout")
        if self.lifecycle_kind is RangerLifecycleKind.ARM and self.mode_after is SafetyMode.ARMED:
            if self.mode_before is SafetyMode.COMMAND_TIMEOUT:
                raise ValueError("timeout recovery must use timeout_recovery_rearm")
        return self


class RangerLifecycleController:
    """Evidence-aware façade over the deterministic Ranger mobility controller."""

    def __init__(self, controller: RangerMobilityController) -> None:
        self.controller = controller
        self._lifecycle_sequence = 0

    def arm(
        self,
        *,
        now_monotonic_ns: int,
        occurred_at_utc: datetime,
        hardware_estop_asserted: bool,
    ) -> RangerLifecycleEvent:
        mode_before = self.controller.mode
        mode_after = self.controller.arm(
            now_monotonic_ns=now_monotonic_ns,
            hardware_estop_asserted=hardware_estop_asserted,
        )
        if mode_before is SafetyMode.COMMAND_TIMEOUT and mode_after is SafetyMode.ARMED:
            kind = RangerLifecycleKind.TIMEOUT_RECOVERY_REARM
        elif mode_after is SafetyMode.ESTOP_LATCHED:
            # Arming while the hardware E-stop input is asserted latches the stop instead.
            kind = RangerLifecycleKind.ARM
        else:
            kind = RangerLifecycleKind.ARM
        return self._event(
            kind=kind,
            result=RangerLifecycleResult.APPLIED,
            mode_before=mode_before,
            mode_after=mode_after,
            occurred_at_utc=occurred_at_utc,
            occurred_monotonic_ns=now_monotonic_ns,
            hardware_estop_asserted=hardware_estop_asserted,
            reason_code=(
                MotionReason.HARDWARE_ESTOP_ASSERTED
                if mode_after is SafetyMode.ESTOP_LATCHED
                else None
            ),
        )

    def disarm(
        self,
        *,
        now_monotonic_ns: int,
        occurred_at_utc: datetime,
    ) -> RangerLifecycleEvent:
        mode_before = self.controller.mode
        mode_after = self.controller.disarm(now_monotonic_ns=now_monotonic_ns)
        return self._event(
            kind=RangerLifecycleKind.DISARM,
            result=RangerLifecycleResult.APPLIED,
            mode_before=mode_before,
            mode_after=mode_after,
            occurred_at_utc=occurred_at_utc,
            occurred_monotonic_ns=now_monotonic_ns,
        )

    def reset_estop(
        self,
        *,
        now_monotonic_ns: int,
        occurred_at_utc: datetime,
        hardware_estop_asserted: bool,
    ) -> RangerLifecycleEvent:
        mode_before = self.controller.mode
        mode_after = self.controller.reset_estop(
            now_monotonic_ns=now_monotonic_ns,
            hardware_estop_asserted=hardware_estop_asserted,
        )
        return self._event(
            kind=RangerLifecycleKind.ESTOP_RESET,
            result=RangerLifecycleResult.APPLIED,
            mode_before=mode_before,
            mode_after=mode_after,
            occurred_at_utc=occurred_at_utc,
            occurred_monotonic_ns=now_monotonic_ns,
            hardware_estop_asserted=hardware_estop_asserted,
        )

    def authorize(
        self,
        command: RangerDriveCommand,
        *,
        received_monotonic_ns: int,
        evaluated_monotonic_ns: int,
        evaluated_at_utc: datetime,
        hardware_estop_asserted: bool,
    ) -> tuple[RangerMobilityEvent, RangerLifecycleEvent | None]:
        mode_before = self.controller.mode
        mobility_event = self.controller.authorize(
            command,
            received_monotonic_ns=received_monotonic_ns,
            evaluated_monotonic_ns=evaluated_monotonic_ns,
            evaluated_at_utc=evaluated_at_utc,
            hardware_estop_asserted=hardware_estop_asserted,
        )
        lifecycle_event = self._transition_from_mobility_event(mode_before, mobility_event)
        return mobility_event, lifecycle_event

    def enforce_watchdog(
        self,
        *,
        now_monotonic_ns: int,
        observed_at_utc: datetime,
        hardware_estop_asserted: bool,
    ) -> tuple[RangerMobilityEvent | None, RangerLifecycleEvent | None]:
        mode_before = self.controller.mode
        mobility_event = self.controller.enforce_watchdog(
            now_monotonic_ns=now_monotonic_ns,
            observed_at_utc=observed_at_utc,
            hardware_estop_asserted=hardware_estop_asserted,
        )
        if mobility_event is None:
            return None, None
        return mobility_event, self._transition_from_mobility_event(mode_before, mobility_event)

    def _transition_from_mobility_event(
        self,
        mode_before: SafetyMode,
        mobility_event: RangerMobilityEvent,
    ) -> RangerLifecycleEvent | None:
        if mode_before is mobility_event.mode_after:
            return None
        reasons = mobility_event.policy_evaluation.reason_codes
        event_digest = canonical_sha256(mobility_event.model_dump(mode="json"))
        if mobility_event.mode_after is SafetyMode.ESTOP_LATCHED:
            kind = RangerLifecycleKind.ESTOP_LATCH
            reason = (
                MotionReason.HARDWARE_ESTOP_ASSERTED
                if MotionReason.HARDWARE_ESTOP_ASSERTED in reasons
                else MotionReason.ESTOP_LATCHED
            )
        elif mobility_event.mode_after is SafetyMode.COMMAND_TIMEOUT:
            kind = RangerLifecycleKind.WATCHDOG_TIMEOUT
            reason = reasons[0] if reasons else MotionReason.WATCHDOG_TIMEOUT
        else:
            return None
        return self._event(
            kind=kind,
            result=RangerLifecycleResult.APPLIED,
            mode_before=mode_before,
            mode_after=mobility_event.mode_after,
            occurred_at_utc=mobility_event.evaluated_at_utc,
            occurred_monotonic_ns=mobility_event.evaluated_monotonic_ns,
            hardware_estop_asserted=mobility_event.observed_facts.hardware_estop_asserted,
            source_mobility_event_id=mobility_event.event_id,
            source_mobility_event_digest_sha256=event_digest,
            reason_code=reason,
        )

    def _event(
        self,
        *,
        kind: RangerLifecycleKind,
        result: RangerLifecycleResult,
        mode_before: SafetyMode,
        mode_after: SafetyMode,
        occurred_at_utc: datetime,
        occurred_monotonic_ns: int,
        hardware_estop_asserted: bool | None = None,
        source_mobility_event_id: str | None = None,
        source_mobility_event_digest_sha256: str | None = None,
        reason_code: MotionReason | None = None,
    ) -> RangerLifecycleEvent:
        occurred_at_utc = self._normalize_utc(occurred_at_utc)
        if occurred_monotonic_ns < 0:
            raise RangerSafetyInputError("occurred_monotonic_ns cannot be negative")
        self._lifecycle_sequence += 1
        event_id = "rle:" + canonical_sha256(
            {
                "vehicle_id": self.controller.vehicle_id,
                "mission_id": self.controller.mission_id,
                "boot_id": self.controller.boot_id,
                "lifecycle_sequence": self._lifecycle_sequence,
                "kind": kind.value,
                "occurred_monotonic_ns": occurred_monotonic_ns,
            }
        )
        return RangerLifecycleEvent(
            event_id=event_id,
            lifecycle_sequence=self._lifecycle_sequence,
            lifecycle_kind=kind,
            transition_result=result,
            vehicle_id=self.controller.vehicle_id,
            mission_id=self.controller.mission_id,
            controller_id=self.controller.controller_id,
            controller_session_id=self.controller.controller_session_id,
            boot_id=self.controller.boot_id,
            occurred_at_utc=occurred_at_utc,
            occurred_monotonic_ns=occurred_monotonic_ns,
            local_clock_quality=self.controller.local_clock_quality,
            mode_before=mode_before,
            mode_after=mode_after,
            hardware_estop_asserted=hardware_estop_asserted,
            source_mobility_event_id=source_mobility_event_id,
            source_mobility_event_digest_sha256=source_mobility_event_digest_sha256,
            reason_code=reason_code,
            operator_rearm_required=mode_after in {
                SafetyMode.DISARMED,
                SafetyMode.ESTOP_LATCHED,
                SafetyMode.COMMAND_TIMEOUT,
            },
        )

    @staticmethod
    def _normalize_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise RangerSafetyInputError("wall-clock evidence time must be timezone-aware")
        return value.astimezone(UTC)
