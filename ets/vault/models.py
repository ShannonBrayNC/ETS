"""Domain models for ETS Vault retention and preservation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RetentionMode = Literal["governance", "compliance"]
VaultBackendBoundary = Literal["test", "software", "storage"]
VaultOperation = Literal[
    "preserve",
    "retention_extended",
    "legal_hold_applied",
    "legal_hold_released",
    "purged",
]


class VaultBackendCapabilities(BaseModel):
    """Capabilities that a Vault storage boundary claims to enforce."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    write_once: bool
    retention_enforced: bool
    compliance_lock: bool
    legal_hold: bool
    encryption_at_rest: bool
    durable_write: bool
    audit_logging: bool
    replication: bool
    hardware_backed_keys: bool
    enforcement_boundary: VaultBackendBoundary

    def production_ready(self) -> bool:
        """Return whether the backend satisfies the Vault v1 production floor."""

        return (
            self.write_once
            and self.retention_enforced
            and self.compliance_lock
            and self.legal_hold
            and self.encryption_at_rest
            and self.durable_write
            and self.audit_logging
            and self.replication
            and self.hardware_backed_keys
            and self.enforcement_boundary == "storage"
        )


class VaultRetention(BaseModel):
    """Retention and legal-hold state applied to one preserved object."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mode: RetentionMode
    retain_until_utc: datetime
    legal_holds: tuple[str, ...] = ()

    @field_validator("retain_until_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retain_until_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("legal_holds")
    @classmethod
    def normalize_legal_holds(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted(item.strip() for item in value))
        if any(not item for item in normalized):
            raise ValueError("legal hold identifiers must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("legal hold identifiers must be unique")
        return normalized


class VaultRecord(BaseModel):
    """Immutable logical record describing one preserved Vault object generation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.vault_record.v1"] = "ets.vault_record.v1"
    object_id: str = Field(min_length=70, max_length=70)
    content_hash: str = Field(min_length=64, max_length=64)
    content_hash_alg: Literal["sha256"] = "sha256"
    byte_size: int = Field(ge=0)
    media_type: str = Field(min_length=1, max_length=255)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    source_event_id: str | None = Field(default=None, max_length=128)
    received_at_utc: datetime
    retention: VaultRetention
    generation: int = Field(default=1, ge=1)
    purged_at_utc: datetime | None = None

    @field_validator("object_id")
    @classmethod
    def require_object_id(cls, value: str) -> str:
        if not value.startswith("vault:"):
            raise ValueError("object_id must use the vault:<sha256> form")
        bytes.fromhex(value[6:])
        return value

    @field_validator("content_hash")
    @classmethod
    def require_sha256_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value

    @field_validator("received_at_utc", "purged_at_utc")
    @classmethod
    def require_utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Vault timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_purge_state(self) -> Self:
        if self.purged_at_utc is not None and self.purged_at_utc < self.received_at_utc:
            raise ValueError("purged_at_utc cannot precede received_at_utc")
        return self


class VaultAuthorization(BaseModel):
    """Dual-control authorization for destructive or hold-release actions."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    primary_actor_id: str = Field(min_length=1, max_length=128)
    secondary_actor_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1024)

    @model_validator(mode="after")
    def require_distinct_actors(self) -> Self:
        if self.primary_actor_id == self.secondary_actor_id:
            raise ValueError("dual-control authorization requires two distinct actors")
        return self


class VaultJournalEntry(BaseModel):
    """One hash-chained Vault administrative event."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.vault_journal.v1"] = "ets.vault_journal.v1"
    sequence: int = Field(ge=1)
    operation: VaultOperation
    object_id: str = Field(min_length=70, max_length=70)
    record_generation: int = Field(ge=1)
    actor_id: str = Field(min_length=1, max_length=128)
    secondary_actor_id: str | None = Field(default=None, max_length=128)
    reason: str = Field(min_length=1, max_length=1024)
    occurred_at_utc: datetime
    previous_entry_hash: str = Field(min_length=64, max_length=64)
    entry_hash: str = Field(min_length=64, max_length=64)

    @field_validator("occurred_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("previous_entry_hash", "entry_hash")
    @classmethod
    def require_hash_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value


class VaultReceipt(BaseModel):
    """Receipt returned after a Vault operation that changes object state."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.vault_receipt.v1"] = "ets.vault_receipt.v1"
    record: VaultRecord
    journal_head_hash: str = Field(min_length=64, max_length=64)

    @field_validator("journal_head_hash")
    @classmethod
    def require_hash_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value


class VaultIntegrityResult(BaseModel):
    """Integrity result from re-reading and hashing preserved content."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    valid: bool
    object_id: str
    reason: str
    expected_hash: str
    actual_hash: str | None
    expected_byte_size: int = Field(ge=0)
    actual_byte_size: int | None = Field(default=None, ge=0)


class VaultJournalVerification(BaseModel):
    """Result of validating the Vault administration hash chain."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    valid: bool
    reason: str
    entry_count: int = Field(ge=0)
    head_hash: str = Field(min_length=64, max_length=64)
