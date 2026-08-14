"""Product-neutral bounded semantic models for ETS Gateway OTLP intake."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_OTLP_BATCH_RECORDS = 1000
MAX_OTLP_MAPPING_BYTES = 16 * 1024
MAX_OTLP_MAPPING_ITEMS = 128
MAX_OTLP_NESTING_DEPTH = 4
MAX_OTLP_KEY_CHARS = 256
MAX_OTLP_STRING_CHARS = 4096

OtlpSignalClass = Literal["logs", "metrics", "traces"]
OtlpRejectionCode = Literal[
    "unsupported_signal",
    "invalid_record",
    "limit_exceeded",
    "invalid_time",
    "privacy_rejected",
]


class StrictOtlpModel(BaseModel):
    """Strict immutable base for the shared OTLP semantic contract."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _validate_metadata_value(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_OTLP_NESTING_DEPTH:
        raise ValueError("OTLP metadata exceeds the configured nesting depth")

    if value is None or isinstance(value, bool | int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("OTLP metadata floats must be finite")
        return
    if isinstance(value, str):
        if len(value) > MAX_OTLP_STRING_CHARS:
            raise ValueError("OTLP metadata string exceeds the configured length")
        return
    if isinstance(value, list):
        if len(value) > MAX_OTLP_MAPPING_ITEMS:
            raise ValueError("OTLP metadata list exceeds the configured item count")
        for item in value:
            _validate_metadata_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_OTLP_MAPPING_ITEMS:
            raise ValueError("OTLP metadata mapping exceeds the configured item count")
        for key, item in value.items():
            if not isinstance(key, str) or not 1 <= len(key) <= MAX_OTLP_KEY_CHARS:
                raise ValueError("OTLP metadata keys must be bounded non-empty strings")
            _validate_metadata_value(item, depth=depth + 1)
        return
    raise ValueError("OTLP metadata must contain JSON-native bounded values")


def _validate_metadata_mapping(value: dict[str, Any]) -> dict[str, Any]:
    _validate_metadata_value(value)
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("OTLP metadata must be JSON encodable") from exc
    if len(encoded) > MAX_OTLP_MAPPING_BYTES:
        raise ValueError("OTLP metadata mapping exceeds 16 KiB")
    return value


class OtlpObservationV1(StrictOtlpModel):
    """One decoded, bounded OTLP observation before policy and ETS commitment."""

    schema_version: Literal["ets.otlp.observation.v1"]
    signal_class: OtlpSignalClass
    record_ordinal: int = Field(ge=0)
    source_timestamp_utc: datetime | None = None
    decoder_profile: str = Field(min_length=1, max_length=200)
    transformation_profile: str = Field(min_length=1, max_length=200)
    resource_metadata: dict[str, Any] = Field(default_factory=dict, repr=False)
    scope_metadata: dict[str, Any] = Field(default_factory=dict, repr=False)
    record_metadata: dict[str, Any] = Field(default_factory=dict, repr=False)

    @field_validator("source_timestamp_utc")
    @classmethod
    def normalize_source_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("OTLP source timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("resource_metadata", "scope_metadata", "record_metadata")
    @classmethod
    def bound_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_metadata_mapping(value)


class OtlpRejectedRecordV1(StrictOtlpModel):
    """Bounded rejection metadata that never carries the rejected source value."""

    record_ordinal: int = Field(ge=0)
    code: OtlpRejectionCode
    field: str | None = Field(default=None, min_length=1, max_length=200)


class OtlpDecodedBatchV1(StrictOtlpModel):
    """Decoded batch with explicit acceptance and rejection accounting."""

    schema_version: Literal["ets.otlp.decoded_batch.v1"]
    signal_class: OtlpSignalClass
    total_records: int = Field(ge=0, le=MAX_OTLP_BATCH_RECORDS)
    accepted: list[OtlpObservationV1] = Field(
        default_factory=list,
        max_length=MAX_OTLP_BATCH_RECORDS,
        repr=False,
    )
    rejected: list[OtlpRejectedRecordV1] = Field(
        default_factory=list,
        max_length=MAX_OTLP_BATCH_RECORDS,
    )

    @model_validator(mode="after")
    def validate_batch_accounting(self) -> OtlpDecodedBatchV1:
        if self.total_records != len(self.accepted) + len(self.rejected):
            raise ValueError("OTLP batch accounting must include every decoded record")

        ordinals = [item.record_ordinal for item in self.accepted]
        ordinals.extend(item.record_ordinal for item in self.rejected)
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("OTLP batch record ordinals must be unique")

        if any(item.signal_class != self.signal_class for item in self.accepted):
            raise ValueError("OTLP accepted observations must match the batch signal class")
        return self
