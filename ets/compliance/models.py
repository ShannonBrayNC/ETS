"""Strict ETS Compliance control/evidence contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

type Scalar = str | int | float | bool | None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AssessmentOutcome(StrEnum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    UNKNOWN = "unknown"
    NOT_OBSERVED = "not_observed"


class EvidenceDisposition(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    INDETERMINATE = "indeterminate"


class VerificationState(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


class ObservationMethod(StrEnum):
    EXAMINE = "examine"
    INTERVIEW = "interview"
    TEST = "test"


class FrameworkReference(StrictModel):
    framework_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=128)
    authority: str = Field(min_length=1, max_length=256)
    profile_id: str | None = Field(default=None, max_length=128)
    source_uri: str | None = Field(default=None, max_length=1024)


class EvidenceRequirement(StrictModel):
    requirement_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=2048)
    evidence_types: tuple[str, ...] = Field(min_length=1, max_length=32)
    source_systems: tuple[str, ...] = Field(default=(), max_length=32)
    methods: tuple[ObservationMethod, ...] = Field(default=(), max_length=3)
    minimum_observations: int = Field(default=1, ge=1, le=1024)
    max_age_seconds: int | None = Field(default=None, ge=1, le=315_576_000)

    @field_validator("evidence_types", "source_systems")
    @classmethod
    def normalize_strings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item or len(item) > 256 for item in normalized):
            raise ValueError("evidence/source values must contain 1-256 characters")
        if len(set(normalized)) != len(normalized):
            raise ValueError("evidence/source values must be unique")
        return normalized

    @field_validator("methods")
    @classmethod
    def unique_methods(
        cls, value: tuple[ObservationMethod, ...]
    ) -> tuple[ObservationMethod, ...]:
        if len(set(value)) != len(value):
            raise ValueError("observation methods must be unique")
        return value


class ControlDefinition(StrictModel):
    control_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    objective_id: str | None = Field(default=None, max_length=256)
    requirements: tuple[EvidenceRequirement, ...] = Field(min_length=1, max_length=64)
    source_refs: tuple[str, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def unique_requirement_ids(self) -> ControlDefinition:
        identifiers = [item.requirement_id for item in self.requirements]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("control requirement identifiers must be unique")
        return self


class ControlPack(StrictModel):
    schema_version: Literal["ets.compliance.pack.v1"] = "ets.compliance.pack.v1"
    pack_id: str = Field(min_length=1, max_length=128)
    pack_version: str = Field(min_length=1, max_length=128)
    framework: FrameworkReference
    controls: tuple[ControlDefinition, ...] = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def unique_control_ids(self) -> ControlPack:
        identifiers = [item.control_id for item in self.controls]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("control identifiers must be unique")
        return self


_SENSITIVE_ATTRIBUTE_PARTS = (
    "api_key",
    "password",
    "prompt",
    "raw_content",
    "raw_payload",
    "secret",
    "token",
)


class EvidenceObservation(StrictModel):
    schema_version: Literal["ets.compliance.observation.v1"] = (
        "ets.compliance.observation.v1"
    )
    observation_id: str = Field(min_length=1, max_length=128)
    requirement_id: str = Field(min_length=1, max_length=128)
    evidence_id: str = Field(min_length=1, max_length=128)
    event_id: str = Field(min_length=1, max_length=128)
    event_hash: str = Field(min_length=64, max_length=64)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    subject_ref: str = Field(min_length=1, max_length=512)
    evidence_type: str = Field(min_length=1, max_length=256)
    event_type: str = Field(min_length=1, max_length=256)
    source_system: str = Field(min_length=1, max_length=256)
    observed_at_utc: datetime
    method: ObservationMethod
    origin_ref: str = Field(min_length=1, max_length=512)
    disposition: EvidenceDisposition
    verification_state: VerificationState
    attributes: dict[str, Scalar] = Field(default_factory=dict, max_length=32)

    @field_validator("event_hash")
    @classmethod
    def require_sha256_hex(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("event_hash must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("event_hash must be a 32-byte SHA-256 value")
        return value.lower()

    @field_validator("observed_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("attributes")
    @classmethod
    def reject_sensitive_attributes(cls, value: dict[str, Scalar]) -> dict[str, Scalar]:
        for key in value:
            normalized = key.lower()
            if any(part in normalized for part in _SENSITIVE_ATTRIBUTE_PARTS):
                raise ValueError(
                    "Compliance observations may reference evidence but may not embed "
                    "raw/sensitive content"
                )
        return value


class AssessmentContext(StrictModel):
    schema_version: Literal["ets.compliance.context.v1"] = "ets.compliance.context.v1"
    assessment_id: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    subject_ref: str = Field(min_length=1, max_length=512)
    evaluated_at_utc: datetime
    observations: tuple[EvidenceObservation, ...] = Field(default=(), max_length=10000)

    @field_validator("evaluated_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def unique_observation_ids(self) -> AssessmentContext:
        identifiers = [item.observation_id for item in self.observations]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("observation identifiers must be unique")
        return self


class CompliancePolicy(StrictModel):
    schema_version: Literal["ets.compliance.policy.v1"] = "ets.compliance.policy.v1"
    policy_version: str = Field(default="1", min_length=1, max_length=128)
    max_future_skew_seconds: int = Field(default=300, ge=0, le=86400)


class RequirementEvaluation(StrictModel):
    requirement_id: str
    outcome: AssessmentOutcome
    reason_codes: tuple[str, ...]
    matched_observation_ids: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    stale_evidence_ids: tuple[str, ...]
    unverified_evidence_ids: tuple[str, ...]
    valid_until_utc: datetime | None = None


class ControlEvaluation(StrictModel):
    control_id: str
    outcome: AssessmentOutcome
    reason_codes: tuple[str, ...]
    requirement_results: tuple[RequirementEvaluation, ...]
    valid_until_utc: datetime | None = None


class AssessmentSummary(StrictModel):
    total_controls: int = Field(ge=0)
    satisfied: int = Field(ge=0)
    not_satisfied: int = Field(ge=0)
    unknown: int = Field(ge=0)
    not_observed: int = Field(ge=0)


class AssessmentReport(StrictModel):
    schema_version: Literal["ets.compliance.report.v1"] = "ets.compliance.report.v1"
    assessment_id: str
    tenant_id: str
    workspace_id: str
    subject_ref: str
    framework: FrameworkReference
    pack_id: str
    pack_version: str
    policy_version: str
    evaluated_at_utc: datetime
    control_results: tuple[ControlEvaluation, ...]
    summary: AssessmentSummary
    input_digest: str = Field(min_length=64, max_length=64)
    result_digest: str = Field(min_length=64, max_length=64)

    @field_validator("evaluated_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("input_digest", "result_digest")
    @classmethod
    def require_digest_hex(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("assessment digests must be hexadecimal") from exc
        if len(raw) != 32:
            raise ValueError("assessment digests must be 32-byte SHA-256 values")
        return value.lower()
