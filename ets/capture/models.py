"""Product-neutral ETS capture envelope models."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_CAPTURE_MAPPING_BYTES = 16 * 1024


class StrictCaptureModel(BaseModel):
    """Strict immutable base for the shared capture contract."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CaptureSource(StrictCaptureModel):
    system: str = Field(min_length=1, max_length=200)
    identifier: str = Field(min_length=1, max_length=500)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    sequence: int | str | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=500)
    transport_identity: str | None = Field(default=None, min_length=1, max_length=500)
    declared_identity: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("sequence")
    @classmethod
    def reject_invalid_sequence(cls, value: int | str | None) -> int | str | None:
        if isinstance(value, str) and not 1 <= len(value) <= 500:
            raise ValueError("sequence strings must be 1-500 characters")
        return value


class ContentDigest(StrictCaptureModel):
    algorithm: Literal["sha256"]
    value: str = Field(pattern=r"^[0-9a-f]{64}$")
    representation: str = Field(min_length=1, max_length=200)
    profile: Literal["ets.content.sha256.v1"]


class EvidenceReference(StrictCaptureModel):
    uri: str | None = Field(default=None, min_length=1, max_length=4096)
    retention_mode: Literal[
        "source_retained",
        "external_store",
        "not_retained",
        "managed_store",
    ]
    store_profile: str | None = Field(default=None, min_length=1, max_length=200)


class CaptureTransformation(StrictCaptureModel):
    profile: str = Field(min_length=1, max_length=200)
    input_format: str | None = Field(default=None, min_length=1, max_length=200)
    output_event_type: str = Field(min_length=1, max_length=128)
    lossless: bool
    notes: str | None = Field(default=None, min_length=1, max_length=2000)


class CapturePrivacy(StrictCaptureModel):
    classification: str | None = Field(default=None, min_length=1, max_length=100)
    redaction_profile: str | None = Field(default=None, min_length=1, max_length=100)
    minimization_profile: str | None = Field(default=None, min_length=1, max_length=100)
    contains_raw_evidence: Literal[False]


class CaptureEnvelopeV1(StrictCaptureModel):
    """Metadata envelope for an explicitly declared captured representation."""

    schema_version: Literal["ets.capture.v1"]
    capture_id: str = Field(min_length=1, max_length=200)
    collector_id: str = Field(min_length=1, max_length=200)
    adapter_id: str = Field(min_length=1, max_length=200)
    adapter_version: str | None = Field(default=None, min_length=1, max_length=100)
    source: CaptureSource
    observed_at_utc: datetime | None = None
    received_at_utc: datetime
    clock_quality: Literal["synchronized", "estimated", "degraded", "unknown"]
    media_type: str | None = Field(default=None, min_length=1, max_length=200)
    content_length: int | None = Field(default=None, ge=0)
    content_digest: ContentDigest
    evidence_reference: EvidenceReference
    transformation: CaptureTransformation
    correlation_id: str | None = Field(default=None, min_length=1, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)
    privacy: CapturePrivacy
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observed_at_utc", "received_at_utc")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("capture timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("metadata", "extensions")
    @classmethod
    def bound_mapping(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("capture mappings must contain JSON-native values") from exc
        if len(encoded) > MAX_CAPTURE_MAPPING_BYTES:
            raise ValueError("capture mappings must not exceed 16 KiB")
        return value
