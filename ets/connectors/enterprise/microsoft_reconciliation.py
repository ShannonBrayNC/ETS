"""Truthful Microsoft connector reconciliation and operational health state for G2E-F."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.connectors.models import ConnectorHealthV1
from ets.connectors.runtime import ConnectorAdminAuditEventV1, ConnectorRuntimeStateV1

MICROSOFT_RECONCILIATION_GAP_SCHEMA_VERSION: Literal[
    "ets.connector.microsoft.reconciliation_gap.v1"
] = "ets.connector.microsoft.reconciliation_gap.v1"

MicrosoftGapStatus = Literal[
    "possible",
    "reconciling",
    "recovered",
    "partial",
    "unrecoverable",
    "acknowledged",
]
MicrosoftGapOutcome = Literal["recovered", "partial", "unrecoverable"]
MicrosoftGapReason = Literal[
    "missed_notification",
    "subscription_removed",
    "subscription_expired",
    "delta_state_expired",
    "webhook_outage",
    "worker_outage",
    "queue_outage",
    "operator_declared",
]


class MicrosoftReconciliationStateError(ValueError):
    """Raised when a Microsoft reconciliation transition violates the qualified state machine."""


class MicrosoftReconciliationGapV1(BaseModel):
    """One bounded Microsoft collection-continuity gap and its reconciliation outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.connector.microsoft.reconciliation_gap.v1"]
    gap_id: str = Field(min_length=1, max_length=200)
    instance_id: str = Field(min_length=1, max_length=128)
    source_system: str = Field(min_length=1, max_length=200)
    reason: MicrosoftGapReason
    status: MicrosoftGapStatus
    detected_at_utc: datetime
    updated_at_utc: datetime
    reconciliation_started_at_utc: datetime | None = None
    resolved_at_utc: datetime | None = None
    outcome: MicrosoftGapOutcome | None = None
    recovered_records: int = Field(default=0, ge=0)
    acknowledged_by: str | None = Field(default=None, min_length=1, max_length=200)
    acknowledged_at_utc: datetime | None = None
    note: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator(
        "detected_at_utc",
        "updated_at_utc",
        "reconciliation_started_at_utc",
        "resolved_at_utc",
        "acknowledged_at_utc",
    )
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Microsoft reconciliation timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_state_shape(self) -> MicrosoftReconciliationGapV1:
        if self.updated_at_utc < self.detected_at_utc:
            raise ValueError("Microsoft reconciliation update precedes gap detection")
        started = self.reconciliation_started_at_utc
        resolved = self.resolved_at_utc
        acknowledged = self.acknowledged_at_utc
        if started is not None and started < self.detected_at_utc:
            raise ValueError("Microsoft reconciliation start precedes gap detection")
        if resolved is not None and (started is None or resolved < started):
            raise ValueError("Microsoft reconciliation resolution precedes reconciliation start")
        if acknowledged is not None and (resolved is None or acknowledged < resolved):
            raise ValueError("Microsoft gap acknowledgement precedes reconciliation resolution")

        if self.status == "possible":
            self._require_empty_resolution_state(started, resolved, acknowledged)
        elif self.status == "reconciling":
            if started is None:
                raise ValueError("reconciling Microsoft gap requires a start timestamp")
            if resolved is not None or self.outcome is not None:
                raise ValueError("reconciling Microsoft gap cannot already have an outcome")
            if self.acknowledged_by is not None or acknowledged is not None:
                raise ValueError("reconciling Microsoft gap cannot be acknowledged")
        elif self.status in {"recovered", "partial", "unrecoverable"}:
            if started is None or resolved is None:
                raise ValueError("resolved Microsoft gap requires start and resolution timestamps")
            if self.outcome != self.status:
                raise ValueError("resolved Microsoft gap outcome must match its terminal status")
            if self.acknowledged_by is not None or acknowledged is not None:
                raise ValueError("resolved Microsoft gap must be acknowledged explicitly")
        else:
            if started is None or resolved is None or self.outcome is None:
                raise ValueError("acknowledged Microsoft gap must preserve its resolution outcome")
            if self.acknowledged_by is None or acknowledged is None:
                raise ValueError("acknowledged Microsoft gap requires actor and timestamp")
        return self

    def _require_empty_resolution_state(
        self,
        started: datetime | None,
        resolved: datetime | None,
        acknowledged: datetime | None,
    ) -> None:
        if started is not None or resolved is not None or self.outcome is not None:
            raise ValueError("possible Microsoft gap cannot contain reconciliation outcome state")
        if self.recovered_records != 0:
            raise ValueError("possible Microsoft gap cannot report recovered records")
        if self.acknowledged_by is not None or acknowledged is not None:
            raise ValueError("possible Microsoft gap cannot be acknowledged")


def open_microsoft_reconciliation_gap(
    *,
    gap_id: str,
    instance_id: str,
    source_system: str,
    reason: MicrosoftGapReason,
    detected_at_utc: datetime,
    note: str | None = None,
) -> MicrosoftReconciliationGapV1:
    """Open a possible continuity gap without claiming that source records are missing."""

    detected = _utc(detected_at_utc)
    return MicrosoftReconciliationGapV1(
        schema_version=MICROSOFT_RECONCILIATION_GAP_SCHEMA_VERSION,
        gap_id=gap_id,
        instance_id=instance_id,
        source_system=source_system,
        reason=reason,
        status="possible",
        detected_at_utc=detected,
        updated_at_utc=detected,
        note=note,
    )


def begin_microsoft_reconciliation(
    gap: MicrosoftReconciliationGapV1,
    *,
    started_at_utc: datetime,
) -> MicrosoftReconciliationGapV1:
    """Move a possible gap into active reconciliation exactly once."""

    if gap.status != "possible":
        raise MicrosoftReconciliationStateError(
            "Microsoft reconciliation may begin only from possible state"
        )
    started = _utc(started_at_utc)
    if started < gap.detected_at_utc:
        raise MicrosoftReconciliationStateError(
            "Microsoft reconciliation start precedes gap detection"
        )
    return gap.model_copy(
        update={
            "status": "reconciling",
            "reconciliation_started_at_utc": started,
            "updated_at_utc": started,
        }
    )


def resolve_microsoft_reconciliation(
    gap: MicrosoftReconciliationGapV1,
    *,
    outcome: MicrosoftGapOutcome,
    resolved_at_utc: datetime,
    recovered_records: int = 0,
    note: str | None = None,
) -> MicrosoftReconciliationGapV1:
    """Record the bounded outcome of a reconciliation attempt without completeness claims."""

    if gap.status != "reconciling":
        raise MicrosoftReconciliationStateError(
            "Microsoft reconciliation may resolve only from reconciling state"
        )
    if recovered_records < 0:
        raise MicrosoftReconciliationStateError("recovered_records must not be negative")
    resolved = _utc(resolved_at_utc)
    started = gap.reconciliation_started_at_utc
    if started is None or resolved < started:
        raise MicrosoftReconciliationStateError(
            "Microsoft reconciliation resolution precedes reconciliation start"
        )
    return gap.model_copy(
        update={
            "status": outcome,
            "outcome": outcome,
            "resolved_at_utc": resolved,
            "updated_at_utc": resolved,
            "recovered_records": recovered_records,
            "note": note if note is not None else gap.note,
        }
    )


def acknowledge_microsoft_reconciliation_gap(
    gap: MicrosoftReconciliationGapV1,
    *,
    actor_id: str,
    tenant_id: str,
    workspace_id: str,
    acknowledged_at_utc: datetime,
    message: str | None = None,
) -> tuple[MicrosoftReconciliationGapV1, ConnectorAdminAuditEventV1]:
    """Acknowledge a resolved gap while preserving its terminal recovery outcome."""

    if gap.status not in {"recovered", "partial", "unrecoverable"}:
        raise MicrosoftReconciliationStateError(
            "Microsoft gap acknowledgement requires a resolved reconciliation outcome"
        )
    acknowledged = _utc(acknowledged_at_utc)
    if gap.resolved_at_utc is None or acknowledged < gap.resolved_at_utc:
        raise MicrosoftReconciliationStateError(
            "Microsoft gap acknowledgement precedes reconciliation resolution"
        )
    resolved = gap.model_copy(
        update={
            "status": "acknowledged",
            "acknowledged_by": actor_id,
            "acknowledged_at_utc": acknowledged,
            "updated_at_utc": acknowledged,
        }
    )
    audit = ConnectorAdminAuditEventV1(
        schema_version="ets.connector.admin_audit.v1",
        action="microsoft_reconciliation_gap_acknowledged",
        instance_id=gap.instance_id,
        actor_id=actor_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        result="success",
        message=message or f"Acknowledged Microsoft reconciliation gap {gap.gap_id}",
        created_at_utc=acknowledged,
    )
    return resolved, audit


def project_microsoft_connector_health(
    source_health: ConnectorHealthV1,
    runtime: ConnectorRuntimeStateV1,
    gap: MicrosoftReconciliationGapV1 | None,
) -> ConnectorHealthV1:
    """Project operational Microsoft posture without implying evidence verification or truth."""

    if source_health.state == "failed":
        return source_health

    if gap is not None:
        if gap.status in {"possible", "reconciling"}:
            return _continuity_health(
                f"Microsoft collection continuity is {gap.status}; reconciliation is operational "
                "state and does not assert source completeness"
            )
        outcome = gap.outcome
        if outcome in {"partial", "unrecoverable"}:
            status = "acknowledged" if gap.status == "acknowledged" else outcome
            return _continuity_health(
                f"Microsoft reconciliation is {status} with {outcome} recovery; the known "
                "continuity limitation remains visible"
            )

    if runtime.gap_open or runtime.observation_state == "collection_gap":
        return _continuity_health(
            "Gateway runtime reports an open Microsoft collection gap; source reachability "
            "does not establish observation continuity"
        )
    if source_health.state == "degraded":
        return source_health
    if runtime.retry_count > 0:
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="degraded",
            code="retryable_error",
            message=(
                "Microsoft source is reachable but Gateway runtime has pending connector retries"
            ),
        )
    if runtime.observation_state == "unknown_observation":
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="degraded",
            code="unknown_observation",
            message=(
                "Microsoft source is reachable but collection continuity is not yet established"
            ),
        )
    return source_health


def _continuity_health(message: str) -> ConnectorHealthV1:
    return ConnectorHealthV1(
        schema_version="ets.connector.health.v1",
        state="degraded",
        code="gap_detected",
        message=message,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MicrosoftReconciliationStateError(
            "Microsoft reconciliation timestamps must be timezone-aware"
        )
    return value.astimezone(UTC)
