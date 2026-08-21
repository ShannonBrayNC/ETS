"""Strict data contracts for the ETS Black Box incident recorder."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.api import canonicalize


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ClockQuality(StrEnum):
    SYNCHRONIZED = "synchronized"
    ESTIMATED = "estimated"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class TriggerKind(StrEnum):
    MANUAL = "manual"
    FAULT = "fault"
    SECURITY = "security"
    POLICY = "policy"
    POWER_LOSS = "power_loss"
    CRASH = "crash"
    WATCHDOG = "watchdog"


class SealReason(StrEnum):
    POST_WINDOW_COMPLETE = "post_window_complete"
    POWER_LOSS_IMMINENT = "power_loss_imminent"
    OPERATOR = "operator"
    RECOVERY = "recovery"


class BlackBoxBackendCapabilities(StrictModel):
    atomic_frame_state_commit: bool
    crash_consistent: bool
    durable_write: bool
    write_once_sealed_segments: bool
    encryption_at_rest: bool
    power_loss_protection: bool
    hardware_backed_keys: bool
    measured_boot: bool
    tamper_detection: bool
    enforcement_boundary: Literal["test", "software", "hardware"]

    def production_ready(self) -> bool:
        return (
            self.atomic_frame_state_commit
            and self.crash_consistent
            and self.durable_write
            and self.write_once_sealed_segments
            and self.encryption_at_rest
            and self.power_loss_protection
            and self.hardware_backed_keys
            and self.measured_boot
            and self.tamper_detection
            and self.enforcement_boundary == "hardware"
        )


class BlackBoxObservation(StrictModel):
    schema_version: Literal["ets.black-box.observation.v1"] = "ets.black-box.observation.v1"
    device_id: str = Field(min_length=16, max_length=160)
    boot_id: str = Field(min_length=1, max_length=128)
    observation_id: str = Field(min_length=1, max_length=128)
    source_system: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    subject_ref: str | None = Field(default=None, max_length=512)
    correlation_id: str | None = Field(default=None, max_length=128)
    observed_at_utc: datetime
    monotonic_ns: int = Field(ge=0)
    clock_quality: ClockQuality = ClockQuality.UNKNOWN
    clock_error_bound_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    content_hash_sha256: str = Field(min_length=64, max_length=64)
    content_byte_length: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    capture_mode: Literal["digest_only"] = "digest_only"

    @field_validator("device_id")
    @classmethod
    def require_black_box_device_id(cls, value: str) -> str:
        if not value.startswith("ets-black-box:"):
            raise ValueError("device_id must use the ets-black-box: namespace")
        return value

    @field_validator("observed_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("content_hash_sha256")
    @classmethod
    def require_sha256(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("content_hash_sha256 must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("content_hash_sha256 must be a 32-byte SHA-256 value")
        return value.lower()

    @field_validator("attributes")
    @classmethod
    def bound_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 64:
            raise ValueError("attributes must contain at most 64 properties")
        if len(canonicalize(value)) > 16 * 1024:
            raise ValueError("attributes must not exceed 16 KiB canonical JSON")
        return value


class SignedBlackBoxFrame(StrictModel):
    schema_version: Literal["ets.black-box.frame.v1"] = "ets.black-box.frame.v1"
    sequence: int = Field(ge=1)
    boot_counter: int = Field(ge=1)
    observation: BlackBoxObservation
    previous_frame_hash: str = Field(min_length=64, max_length=64)
    frame_hash: str = Field(min_length=64, max_length=64)
    signing_algorithm: Literal["ed25519"] = "ed25519"
    signing_key_id: str = Field(min_length=1, max_length=256)
    signature_hex: str = Field(min_length=128, max_length=128)

    @field_validator("previous_frame_hash", "frame_hash")
    @classmethod
    def require_hash(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("frame hashes must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("frame hashes must be 32 bytes")
        return value.lower()

    @field_validator("signature_hex")
    @classmethod
    def require_signature(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("signature must be hexadecimal") from exc
        if len(raw) != 64:
            raise ValueError("Ed25519 signature must be 64 bytes")
        return value.lower()


class BlackBoxTrigger(StrictModel):
    schema_version: Literal["ets.black-box.trigger.v1"] = "ets.black-box.trigger.v1"
    trigger_id: str = Field(min_length=1, max_length=128)
    kind: TriggerKind
    reason: str = Field(min_length=1, max_length=1024)
    triggered_at_utc: datetime
    trigger_sequence: int = Field(ge=1)
    actor_ref: str | None = Field(default=None, max_length=256)

    @field_validator("triggered_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("triggered_at_utc must be timezone-aware")
        return value.astimezone(UTC)


class ActiveCaptureState(StrictModel):
    trigger: BlackBoxTrigger
    first_sequence: int = Field(ge=1)
    remaining_post_frames: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.first_sequence > self.trigger.trigger_sequence:
            raise ValueError("first_sequence cannot follow trigger_sequence")
        return self


class RecorderState(StrictModel):
    schema_version: Literal["ets.black-box.state.v1"] = "ets.black-box.state.v1"
    device_id: str = Field(min_length=16, max_length=160)
    signing_key_id: str = Field(min_length=1, max_length=256)
    boot_id: str = Field(min_length=1, max_length=128)
    boot_counter: int = Field(ge=1)
    last_sequence: int = Field(default=0, ge=0)
    head_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
    last_monotonic_ns: int | None = Field(default=None, ge=0)
    active_capture: ActiveCaptureState | None = None

    @field_validator("device_id")
    @classmethod
    def require_black_box_device_id(cls, value: str) -> str:
        if not value.startswith("ets-black-box:"):
            raise ValueError("device_id must use the ets-black-box: namespace")
        return value

    @field_validator("head_hash")
    @classmethod
    def require_head_hash(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("head_hash must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("head_hash must be 32 bytes")
        return value.lower()


class BlackBoxSegmentManifest(StrictModel):
    schema_version: Literal["ets.black-box.segment-manifest.v1"] = (
        "ets.black-box.segment-manifest.v1"
    )
    segment_id: str = Field(min_length=71, max_length=71)
    device_id: str = Field(min_length=16, max_length=160)
    trigger: BlackBoxTrigger
    first_sequence: int = Field(ge=1)
    last_sequence: int = Field(ge=1)
    frame_count: int = Field(ge=1)
    first_observed_at_utc: datetime
    last_observed_at_utc: datetime
    sealed_at_utc: datetime
    seal_reason: SealReason
    predecessor_frame_hash: str = Field(min_length=64, max_length=64)
    chain_head_hash: str = Field(min_length=64, max_length=64)
    segment_hash: str = Field(min_length=64, max_length=64)
    signing_algorithm: Literal["ed25519"] = "ed25519"
    signing_key_id: str = Field(min_length=1, max_length=256)
    signature_hex: str = Field(min_length=128, max_length=128)

    @field_validator("first_observed_at_utc", "last_observed_at_utc", "sealed_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("segment timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("predecessor_frame_hash", "chain_head_hash", "segment_hash")
    @classmethod
    def require_hash(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("segment hashes must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("segment hashes must be 32 bytes")
        return value.lower()

    @field_validator("segment_id")
    @classmethod
    def require_segment_id(cls, value: str) -> str:
        if not value.startswith("bbxseg:"):
            raise ValueError("segment_id must use the bbxseg:<sha256> form")
        try:
            raw = bytes.fromhex(value[7:])
        except ValueError as exc:
            raise ValueError("segment_id suffix must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("segment_id suffix must be 32 bytes")
        return value.lower()

    @field_validator("signature_hex")
    @classmethod
    def require_signature(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("signature must be hexadecimal") from exc
        if len(raw) != 64:
            raise ValueError("Ed25519 signature must be 64 bytes")
        return value.lower()

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.last_sequence < self.first_sequence:
            raise ValueError("last_sequence cannot precede first_sequence")
        if self.frame_count != self.last_sequence - self.first_sequence + 1:
            raise ValueError("frame_count must match the sequence range")
        if not (self.first_sequence <= self.trigger.trigger_sequence <= self.last_sequence):
            raise ValueError("trigger_sequence must be inside the sealed segment")
        if self.first_observed_at_utc > self.last_observed_at_utc:
            raise ValueError("first observation time cannot follow last observation time")
        return self


class BlackBoxSegment(StrictModel):
    schema_version: Literal["ets.black-box.segment.v1"] = "ets.black-box.segment.v1"
    manifest: BlackBoxSegmentManifest
    frames: tuple[SignedBlackBoxFrame, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_frames(self) -> Self:
        if len(self.frames) != self.manifest.frame_count:
            raise ValueError("segment frame count does not match manifest")
        if self.frames[0].sequence != self.manifest.first_sequence:
            raise ValueError("segment first frame does not match manifest")
        if self.frames[-1].sequence != self.manifest.last_sequence:
            raise ValueError("segment last frame does not match manifest")
        if any(frame.observation.device_id != self.manifest.device_id for frame in self.frames):
            raise ValueError("all segment frames must belong to manifest device")
        return self


class BlackBoxVerification(StrictModel):
    valid: bool
    reason: str
    frame_count: int = Field(ge=0)
    segment_hash: str | None = None


class BlackBoxRecorderStatus(StrictModel):
    device_id: str
    boot_id: str
    boot_counter: int = Field(ge=1)
    last_sequence: int = Field(ge=0)
    head_hash: str = Field(min_length=64, max_length=64)
    live_frame_count: int = Field(ge=0)
    sealed_segment_count: int = Field(ge=0)
    capture_active: bool
    remaining_post_frames: int | None = Field(default=None, ge=0)
