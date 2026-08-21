"""Strict AI Witness evidence contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_P256_ORDER = int(
    "FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551",
    16,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WitnessEventKind(StrEnum):
    SESSION_START = "session_start"
    MODEL_REQUEST = "model_request"
    RETRIEVAL = "retrieval"
    TOOL_CALL = "tool_call"
    MODEL_RESPONSE = "model_response"
    HUMAN_DECISION = "human_decision"
    ACTION_RESULT = "action_result"
    SESSION_END = "session_end"


class ClockQuality(StrEnum):
    SYNCHRONIZED = "synchronized"
    ESTIMATED = "estimated"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ToolDisposition(StrEnum):
    PROPOSED = "proposed"
    ALLOWED = "allowed"
    DENIED = "denied"
    EXECUTED = "executed"
    FAILED = "failed"


class HumanDecisionValue(StrEnum):
    APPROVED = "approved"
    DENIED = "denied"
    MODIFIED = "modified"


class SigningAlgorithm(StrEnum):
    ED25519 = "ed25519"
    ECDSA_P256_SHA256 = "ecdsa-p256-sha256"


class DigestRef(StrictModel):
    algorithm: Literal["sha256"] = "sha256"
    digest: str = Field(min_length=64, max_length=64)
    byte_length: int | None = Field(default=None, ge=0)
    media_type: str | None = Field(default=None, max_length=128)
    source_ref: str | None = Field(default=None, max_length=256)

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("digest must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("digest must be a 32-byte SHA-256 value")
        return value.lower()


class ModelIdentity(StrictModel):
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=256)
    revision: str | None = Field(default=None, max_length=256)
    deployment_ref: str | None = Field(default=None, max_length=256)


class GenerationParameters(StrictModel):
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    seed: int | None = None
    max_output_tokens: int | None = Field(default=None, ge=1, le=1_000_000)


class ToolObservation(StrictModel):
    tool_name: str = Field(min_length=1, max_length=256)
    tool_version: str | None = Field(default=None, max_length=128)
    call_id_digest: DigestRef
    arguments_digest: DigestRef
    result_digest: DigestRef | None = None
    requested_scopes: tuple[str, ...] = Field(default=(), max_length=64)
    authorization_policy_ref: str | None = Field(default=None, max_length=512)
    disposition: ToolDisposition

    @field_validator("requested_scopes")
    @classmethod
    def validate_scopes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or len(item) > 256 for item in value):
            raise ValueError("tool scopes must contain 1-256 characters")
        if len(set(value)) != len(value):
            raise ValueError("tool scopes must be unique")
        return value


class HumanOversight(StrictModel):
    reviewer_ref: str = Field(min_length=1, max_length=512)
    decision: HumanDecisionValue
    reason_digest: DigestRef | None = None
    policy_ref: str | None = Field(default=None, max_length=512)


class AIWitnessEvent(StrictModel):
    schema_version: Literal["ets.ai-witness.event.v1"] = "ets.ai-witness.event.v1"
    witness_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=64)
    event_id: str = Field(min_length=1, max_length=64)
    sequence: int = Field(ge=0)
    kind: WitnessEventKind
    workload_ref: str = Field(min_length=1, max_length=512)
    occurred_at: datetime
    observed_at: datetime
    clock_quality: ClockQuality = ClockQuality.UNKNOWN
    trace_id: str | None = Field(default=None, min_length=32, max_length=32)
    span_id: str | None = Field(default=None, min_length=16, max_length=16)
    model: ModelIdentity | None = None
    parameters: GenerationParameters | None = None
    system_instruction_digest: DigestRef | None = None
    input_digests: tuple[DigestRef, ...] = Field(default=(), max_length=16)
    retrieval_digests: tuple[DigestRef, ...] = Field(default=(), max_length=32)
    output_digests: tuple[DigestRef, ...] = Field(default=(), max_length=16)
    tool: ToolObservation | None = None
    human_oversight: HumanOversight | None = None
    policy_refs: tuple[str, ...] = Field(default=(), max_length=64)
    content_capture: Literal["digest_only"] = "digest_only"

    @field_validator("occurred_at", "observed_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("AI Witness timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("trace_id", "span_id")
    @classmethod
    def validate_hex_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("trace/span identifiers must be hexadecimal") from exc
        return value.lower()

    @field_validator("policy_refs")
    @classmethod
    def validate_policy_refs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or len(item) > 512 for item in value):
            raise ValueError("policy refs must contain 1-512 characters")
        if len(set(value)) != len(value):
            raise ValueError("policy refs must be unique")
        return value

    @model_validator(mode="after")
    def validate_kind_specific_context(self) -> AIWitnessEvent:
        if self.kind in {WitnessEventKind.MODEL_REQUEST, WitnessEventKind.MODEL_RESPONSE}:
            if self.model is None:
                raise ValueError("model_request/model_response require model identity")
        if self.kind is WitnessEventKind.MODEL_REQUEST and not self.input_digests:
            raise ValueError("model_request requires at least one input digest")
        if self.kind is WitnessEventKind.MODEL_RESPONSE and not self.output_digests:
            raise ValueError("model_response requires at least one output digest")
        if self.kind is WitnessEventKind.RETRIEVAL and not self.retrieval_digests:
            raise ValueError("retrieval requires at least one retrieval digest")
        if self.kind is WitnessEventKind.TOOL_CALL and self.tool is None:
            raise ValueError("tool_call requires tool observation")
        if self.kind is WitnessEventKind.HUMAN_DECISION and self.human_oversight is None:
            raise ValueError("human_decision requires human oversight")
        return self


class SignedWitnessRecord(StrictModel):
    schema_version: Literal[
        "ets.ai-witness.record.v1",
        "ets.ai-witness.record.v2",
    ] = "ets.ai-witness.record.v1"
    event: AIWitnessEvent
    previous_record_digest: str | None = Field(default=None, min_length=64, max_length=64)
    record_digest: str = Field(min_length=64, max_length=64)
    signing_algorithm: SigningAlgorithm = SigningAlgorithm.ED25519
    signing_key_id: str = Field(min_length=1, max_length=256)
    signature_hex: str = Field(min_length=16, max_length=160)

    @field_validator("previous_record_digest", "record_digest")
    @classmethod
    def validate_record_digest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("record digest must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("record digest must be 32 bytes")
        return value.lower()

    @field_validator("signature_hex")
    @classmethod
    def validate_signature_hex(cls, value: str) -> str:
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("signature must be hexadecimal") from exc
        return value.lower()

    @model_validator(mode="after")
    def validate_signature_contract(self) -> SignedWitnessRecord:
        raw = bytes.fromhex(self.signature_hex)
        if self.schema_version == "ets.ai-witness.record.v1":
            if self.signing_algorithm is not SigningAlgorithm.ED25519:
                raise ValueError("v1 Witness records require Ed25519")
            if len(raw) != 64:
                raise ValueError("Ed25519 signature must be 64 bytes")
            return self

        if self.signing_algorithm is SigningAlgorithm.ED25519:
            if len(raw) != 64:
                raise ValueError("Ed25519 signature must be 64 bytes")
            return self

        try:
            r, s = decode_dss_signature(raw)
        except ValueError as exc:
            raise ValueError("ECDSA P-256 signature must use DER encoding") from exc
        if not 1 <= r < _P256_ORDER or not 1 <= s < _P256_ORDER:
            raise ValueError("ECDSA P-256 signature scalar is out of range")
        if s > _P256_ORDER // 2:
            raise ValueError("ECDSA P-256 signature must use canonical low-S form")
        return self
