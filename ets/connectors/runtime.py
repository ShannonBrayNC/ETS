"""Versioned connector runtime and management models for Gateway G2C."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.connectors.models import ConnectorCheckpointV1, ConnectorInstanceV1

CONNECTOR_RUNTIME_SCHEMA_VERSION = "ets.connector.runtime.v1"
CONNECTOR_INSTANCE_RECORD_SCHEMA_VERSION = "ets.connector.instance_record.v1"
CONNECTOR_OPERATION_RECEIPT_SCHEMA_VERSION = "ets.connector.operation_receipt.v1"
CONNECTOR_ADMIN_AUDIT_SCHEMA_VERSION = "ets.connector.admin_audit.v1"

ConnectorObservationState = Literal[
    "healthy_observation",
    "degraded_observation",
    "collection_gap",
    "unknown_observation",
]
ConnectorOperationStage = Literal[
    "configured",
    "source_received",
    "normalized",
    "committed_local",
    "sync_queued",
    "sync_acknowledged",
    "rejected",
]


class StrictRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ConnectorInstanceRecordV1(StrictRuntimeModel):
    schema_version: Literal["ets.connector.instance_record.v1"]
    instance: ConnectorInstanceV1
    revision: int = Field(ge=1)
    created_at_utc: datetime
    updated_at_utc: datetime

    @field_validator("created_at_utc", "updated_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)


class ConnectorRuntimeStateV1(StrictRuntimeModel):
    schema_version: Literal["ets.connector.runtime.v1"]
    instance_id: str = Field(min_length=1, max_length=128)
    checkpoint: ConnectorCheckpointV1 | None = None
    checkpoint_revision: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0, le=1_000_000)
    next_attempt_at_utc: datetime | None = None
    last_success_at_utc: datetime | None = None
    observation_state: ConnectorObservationState = "unknown_observation"
    gap_open: bool = False
    lease_owner: str | None = Field(default=None, min_length=1, max_length=200)
    lease_expires_at_utc: datetime | None = None
    updated_at_utc: datetime

    @field_validator(
        "next_attempt_at_utc",
        "last_success_at_utc",
        "lease_expires_at_utc",
        "updated_at_utc",
    )
    @classmethod
    def normalize_optional_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @model_validator(mode="after")
    def validate_lease_pair(self) -> ConnectorRuntimeStateV1:
        if (self.lease_owner is None) != (self.lease_expires_at_utc is None):
            raise ValueError("lease owner and expiry must be set or cleared together")
        if self.observation_state == "collection_gap" and not self.gap_open:
            raise ValueError("collection_gap requires gap_open")
        return self


class ConnectorOperationReceiptV1(StrictRuntimeModel):
    schema_version: Literal["ets.connector.operation_receipt.v1"]
    instance_id: str = Field(min_length=1, max_length=128)
    stage: ConnectorOperationStage
    source_received: bool = False
    committed_local: bool = False
    sync_queued: bool = False
    sync_acknowledged: bool = False
    message: str | None = Field(default=None, min_length=1, max_length=1000)
    created_at_utc: datetime

    @field_validator("created_at_utc")
    @classmethod
    def normalize_created(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def validate_stage_truth(self) -> ConnectorOperationReceiptV1:
        if self.sync_acknowledged and not self.sync_queued:
            raise ValueError("sync acknowledgement requires sync_queued")
        if self.sync_queued and not self.committed_local:
            raise ValueError("sync_queued requires committed_local")
        if self.committed_local and not self.source_received:
            raise ValueError("local commitment requires source_received")
        return self


class ConnectorAdminAuditEventV1(StrictRuntimeModel):
    schema_version: Literal["ets.connector.admin_audit.v1"]
    action: str = Field(min_length=1, max_length=100)
    instance_id: str = Field(min_length=1, max_length=128)
    actor_id: str = Field(min_length=1, max_length=200)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    result: Literal["success", "failure"]
    revision: int | None = Field(default=None, ge=1)
    message: str | None = Field(default=None, min_length=1, max_length=500)
    created_at_utc: datetime

    @field_validator("created_at_utc")
    @classmethod
    def normalize_audit_time(cls, value: datetime) -> datetime:
        return _utc(value)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("connector runtime timestamps must be timezone-aware")
    return value.astimezone(UTC)
