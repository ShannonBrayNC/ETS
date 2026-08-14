"""Provider-neutral connector credential models."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import SplitResult, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

CREDENTIAL_REFERENCE_SCHEMA_VERSION = "ets.connector.credential_ref.v1"
CREDENTIAL_METADATA_SCHEMA_VERSION = "ets.connector.credential_metadata.v1"
CREDENTIAL_AUDIT_SCHEMA_VERSION = "ets.connector.credential_audit.v1"
CREDENTIAL_HEALTH_SCHEMA_VERSION = "ets.connector.credential_health.v1"

CREDENTIAL_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]{1,31}$")

CredentialStatus = Literal[
    "available",
    "missing",
    "expired",
    "revoked",
    "incompatible",
    "unavailable",
]
CredentialAuditEventType = Literal[
    "credential.created",
    "credential.rotated",
    "credential.revoked",
    "credential.resolve_failed",
]
CredentialAuditOutcome = Literal["success", "failure"]


class StrictCredentialModel(BaseModel):
    """Strict immutable base for management-safe credential metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CredentialReferenceV1(StrictCredentialModel):
    """Opaque credential locator; reusable credential material is never embedded."""

    schema_version: Literal["ets.connector.credential_ref.v1"]
    ref: str = Field(min_length=3, max_length=500)

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, value: str) -> str:
        parse_credential_reference(value)
        return value

    @property
    def provider_scheme(self) -> str:
        return parse_credential_reference(self.ref).scheme


class CredentialMetadataV1(StrictCredentialModel):
    """Management-safe credential state with no reusable material."""

    schema_version: Literal["ets.connector.credential_metadata.v1"]
    reference: CredentialReferenceV1
    provider: str = Field(min_length=1, max_length=64)
    status: CredentialStatus
    version: str | None = Field(default=None, min_length=1, max_length=100)
    expires_at_utc: datetime | None = None
    updated_at_utc: datetime

    @field_validator("expires_at_utc", "updated_at_utc")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("credential timestamps must be timezone-aware")
        return value.astimezone(UTC)


class CredentialHealthV1(StrictCredentialModel):
    """Connector credential availability state, separate from evidence verification."""

    schema_version: Literal["ets.connector.credential_health.v1"]
    status: CredentialStatus
    message: str = Field(min_length=1, max_length=500)


class CredentialAuditEventV1(StrictCredentialModel):
    """Redacted credential lifecycle audit event."""

    schema_version: Literal["ets.connector.credential_audit.v1"]
    event_type: CredentialAuditEventType
    provider: str = Field(min_length=1, max_length=64)
    reference_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    version: str | None = Field(default=None, min_length=1, max_length=100)
    outcome: CredentialAuditOutcome
    status: CredentialStatus
    occurred_at_utc: datetime

    @field_validator("occurred_at_utc")
    @classmethod
    def normalize_event_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("credential audit timestamps must be timezone-aware")
        return value.astimezone(UTC)


def parse_credential_reference(value: str) -> SplitResult:
    """Parse a provider reference while rejecting inline data-bearing URL components."""

    parsed = urlsplit(value)
    if CREDENTIAL_SCHEME_PATTERN.fullmatch(parsed.scheme) is None:
        raise ValueError("credential reference requires a valid provider scheme")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("credential reference must not contain user information")
    if parsed.query or parsed.fragment:
        raise ValueError("credential reference must not contain query or fragment data")
    if not parsed.netloc and not parsed.path.strip("/"):
        raise ValueError("credential reference requires a provider-local identifier")
    return parsed


def credential_reference_fingerprint(reference: CredentialReferenceV1) -> str:
    """Return a stable audit correlation fingerprint without repeating the locator."""

    return hashlib.sha256(reference.ref.encode("utf-8")).hexdigest()
