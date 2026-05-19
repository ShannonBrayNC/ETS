"""Core ETS protocol models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.core.canonical_json import canonicalize


class EvidenceEvent(BaseModel):
    """Stable event contract for hashable evidence metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    event_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    subject_ref: str | None
    content_hash: str = Field(min_length=1)
    content_hash_alg: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at_utc: datetime
    schema_version: str = "ets.event.v1"
    source_system: str | None = None
    actor_id: str | None = None
    correlation_id: str | None = None
    external_refs: dict[str, Any] | None = None
    redaction_profile: str | None = None

    HASHABLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "event_id",
        "tenant_id",
        "workspace_id",
        "evidence_id",
        "event_type",
        "subject_ref",
        "content_hash",
        "content_hash_alg",
        "metadata",
        "created_at_utc",
        "schema_version",
        "source_system",
        "actor_id",
        "correlation_id",
        "external_refs",
        "redaction_profile",
    )

    @field_validator("created_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("metadata", "external_refs")
    @classmethod
    def require_json_native_mapping(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            canonicalize(value)
        return value

    def hashable_payload(self) -> dict[str, Any]:
        """Return the canonical event payload, excluding future proof/server fields."""

        payload = self.model_dump(mode="json")
        return {field: payload[field] for field in self.HASHABLE_FIELDS}
