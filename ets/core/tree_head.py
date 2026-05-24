"""Tree head contracts for local ETS development."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SignedTreeHead(BaseModel):
    """Unsigned local tree head with a forward-compatible signing envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    tree_size: int = Field(ge=0)
    root_hash: str = Field(min_length=64, max_length=64)
    created_at_utc: datetime
    log_id: str = Field(min_length=1)
    signature_alg: str | None = None
    signature: str | None = None
    public_key_id: str | None = None

    @field_validator("root_hash")
    @classmethod
    def require_hash_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value

    @field_validator("created_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at_utc must be timezone-aware")
        return value.astimezone(UTC)
