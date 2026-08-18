"""Policy-bound Microsoft connector operational health for G2E-F."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.connectors.enterprise.microsoft_graph import (
    GraphSubscriptionStatus,
    MicrosoftGraphSubscriptionStateV1,
)
from ets.connectors.enterprise.microsoft_reconciliation import (
    MicrosoftGapOutcome,
    MicrosoftGapStatus,
    MicrosoftReconciliationGapV1,
    project_microsoft_connector_health,
)
from ets.connectors.models import (
    ConnectorHealthState,
    ConnectorHealthV1,
    ConnectorOperationCode,
)
from ets.connectors.runtime import ConnectorRuntimeStateV1
from ets.runtime.sync_queue_scope import SourceScopedSyncQueueStatus

MICROSOFT_OPERATIONAL_HEALTH_POLICY_SCHEMA_VERSION: Literal[
    "ets.connector.microsoft.operational_health_policy.v1"
] = "ets.connector.microsoft.operational_health_policy.v1"
MICROSOFT_OPERATIONAL_POSTURE_SCHEMA_VERSION: Literal[
    "ets.connector.microsoft.operational_posture.v1"
] = "ets.connector.microsoft.operational_posture.v1"


class MicrosoftOperationalHealthError(ValueError):
    """Raised when Microsoft operational-health inputs cannot be scoped safely."""


class StrictMicrosoftHealthModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftOperationalHealthPolicyV1(StrictMicrosoftHealthModel):
    """Governed thresholds for Microsoft operational-health evaluation."""

    schema_version: Literal[
        "ets.connector.microsoft.operational_health_policy.v1"
    ] = MICROSOFT_OPERATIONAL_HEALTH_POLICY_SCHEMA_VERSION
    profile_id: str = Field(min_length=1, max_length=200)
    subscription_renewal_warning_seconds: int = Field(ge=60, le=604_800)
    maximum_collection_lag_seconds: int = Field(ge=1, le=2_592_000)
    maximum_unsynchronized_age_seconds: int = Field(ge=1, le=2_592_000)
    maximum_source_queue_depth: int = Field(ge=1, le=1_000_000)


class MicrosoftOperationalPostureV1(StrictMicrosoftHealthModel):
    """One bounded operational posture, explicitly not evidence verification."""

    schema_version: Literal[
        "ets.connector.microsoft.operational_posture.v1"
    ] = MICROSOFT_OPERATIONAL_POSTURE_SCHEMA_VERSION
    instance_id: str = Field(min_length=1, max_length=128)
    ets_tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=200)
    microsoft_tenant_id: str = Field(min_length=36, max_length=36)
    subscription_id: str = Field(min_length=1, max_length=200)
    evaluated_at_utc: datetime
    policy_profile_id: str = Field(min_length=1, max_length=200)
    health: ConnectorHealthV1
    subscription_status: GraphSubscriptionStatus
    subscription_expiration_date_time: datetime
    seconds_until_subscription_expiration: int
    collection_lag_seconds: float | None = Field(default=None, ge=0)
    queue_depth: int = Field(ge=0)
    oldest_unsynchronized_age_seconds: float | None = Field(default=None, ge=0)
    retryable_failure_count: int = Field(ge=0)
    terminal_failure_count: int = Field(ge=0)
    reconciliation_status: MicrosoftGapStatus | None = None
    reconciliation_outcome: MicrosoftGapOutcome | None = None
    verification_claimed: Literal[False] = False
    source_truth_claimed: Literal[False] = False
    completeness_claimed: Literal[False] = False

    @field_validator("evaluated_at_utc", "subscription_expiration_date_time")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Microsoft operational-health timestamps must be timezone-aware")
        return value.astimezone(UTC)


def evaluate_microsoft_operational_posture(
    *,
    instance_id: str,
    ets_tenant_id: str,
    workspace_id: str,
    source_id: str,
    microsoft_tenant_id: str,
    source_health: ConnectorHealthV1,
    runtime: ConnectorRuntimeStateV1,
    subscription: MicrosoftGraphSubscriptionStateV1,
    queue: SourceScopedSyncQueueStatus,
    reconciliation: MicrosoftReconciliationGapV1 | None,
    policy: MicrosoftOperationalHealthPolicyV1,
    evaluated_at_utc: datetime,
) -> MicrosoftOperationalPostureV1:
    """Evaluate Microsoft operational posture without making verification claims."""

    evaluated = _utc(evaluated_at_utc)
    _validate_scope(
        instance_id=instance_id,
        ets_tenant_id=ets_tenant_id,
        workspace_id=workspace_id,
        source_id=source_id,
        microsoft_tenant_id=microsoft_tenant_id,
        runtime=runtime,
        subscription=subscription,
        queue=queue,
        reconciliation=reconciliation,
    )

    collection_lag = _collection_lag_seconds(runtime, evaluated)
    seconds_until_expiration = int(
        (subscription.expiration_date_time - evaluated).total_seconds()
    )
    projected = project_microsoft_connector_health(
        source_health,
        runtime,
        reconciliation,
    )
    health = _select_primary_health(
        projected=projected,
        subscription=subscription,
        queue=queue,
        collection_lag_seconds=collection_lag,
        seconds_until_expiration=seconds_until_expiration,
        policy=policy,
    )

    return MicrosoftOperationalPostureV1(
        instance_id=instance_id,
        ets_tenant_id=ets_tenant_id,
        workspace_id=workspace_id,
        source_id=source_id,
        microsoft_tenant_id=microsoft_tenant_id.lower(),
        subscription_id=subscription.subscription_id,
        evaluated_at_utc=evaluated,
        policy_profile_id=policy.profile_id,
        health=health,
        subscription_status=subscription.status,
        subscription_expiration_date_time=subscription.expiration_date_time,
        seconds_until_subscription_expiration=seconds_until_expiration,
        collection_lag_seconds=collection_lag,
        queue_depth=queue.queue_depth,
        oldest_unsynchronized_age_seconds=queue.oldest_unsynchronized_age_seconds,
        retryable_failure_count=queue.retryable_failure,
        terminal_failure_count=queue.terminal_failure,
        reconciliation_status=None if reconciliation is None else reconciliation.status,
        reconciliation_outcome=None if reconciliation is None else reconciliation.outcome,
    )


def _select_primary_health(
    *,
    projected: ConnectorHealthV1,
    subscription: MicrosoftGraphSubscriptionStateV1,
    queue: SourceScopedSyncQueueStatus,
    collection_lag_seconds: float | None,
    seconds_until_expiration: int,
    policy: MicrosoftOperationalHealthPolicyV1,
) -> ConnectorHealthV1:
    if projected.state == "failed":
        return projected
    if subscription.status in {"removed", "disabled"}:
        return _health(
            "failed",
            "terminal_error",
            f"Microsoft Graph subscription is {subscription.status}; collection cannot continue",
        )
    if seconds_until_expiration <= 0:
        return _health(
            "degraded",
            "gap_detected",
            "Microsoft Graph subscription is expired; continuity requires reconciliation",
        )
    if subscription.status == "reauthorization_required":
        return _health(
            "degraded",
            "authorization_failed",
            "Microsoft Graph subscription requires reauthorization",
        )
    if subscription.gap_state in {"possible", "reconciling"}:
        return _health(
            "degraded",
            "gap_detected",
            (
                "Microsoft Graph lifecycle state reports a possible collection gap; "
                "this does not prove source records are missing"
            ),
        )
    if projected.code == "gap_detected":
        return projected
    if queue.terminal_failure > 0:
        return _health(
            "degraded",
            "terminal_error",
            "Source-scoped Gateway synchronization has terminal failures",
        )
    if projected.state == "degraded":
        return projected
    if queue.retryable_failure > 0:
        return _health(
            "degraded",
            "retryable_error",
            "Source-scoped Gateway synchronization has retryable failures",
        )
    if queue.queue_depth > policy.maximum_source_queue_depth:
        return _health(
            "degraded",
            "retryable_error",
            "Source-scoped Gateway synchronization backlog exceeds policy",
        )
    queue_age = queue.oldest_unsynchronized_age_seconds
    if queue_age is not None and queue_age > policy.maximum_unsynchronized_age_seconds:
        return _health(
            "degraded",
            "retryable_error",
            "Source-scoped Gateway synchronization age exceeds policy",
        )
    if collection_lag_seconds is None:
        return _health(
            "degraded",
            "unknown_observation",
            "Microsoft collection success time is not yet established",
        )
    if collection_lag_seconds > policy.maximum_collection_lag_seconds:
        return _health(
            "degraded",
            "gap_detected",
            (
                "Microsoft collection lag exceeds policy; lag does not by itself prove "
                "that source records are missing"
            ),
        )
    if seconds_until_expiration <= policy.subscription_renewal_warning_seconds:
        return _health(
            "degraded",
            "retryable_error",
            "Microsoft Graph subscription is inside the governed renewal window",
        )
    return projected


def _collection_lag_seconds(
    runtime: ConnectorRuntimeStateV1,
    evaluated: datetime,
) -> float | None:
    last_success = runtime.last_success_at_utc
    if last_success is None:
        return None
    if last_success > evaluated:
        raise MicrosoftOperationalHealthError(
            "Microsoft connector last-success timestamp is in the future"
        )
    return (evaluated - last_success).total_seconds()


def _validate_scope(
    *,
    instance_id: str,
    ets_tenant_id: str,
    workspace_id: str,
    source_id: str,
    microsoft_tenant_id: str,
    runtime: ConnectorRuntimeStateV1,
    subscription: MicrosoftGraphSubscriptionStateV1,
    queue: SourceScopedSyncQueueStatus,
    reconciliation: MicrosoftReconciliationGapV1 | None,
) -> None:
    if runtime.instance_id != instance_id:
        raise MicrosoftOperationalHealthError("runtime instance does not match health scope")
    if queue.tenant_id != ets_tenant_id or queue.workspace_id != workspace_id:
        raise MicrosoftOperationalHealthError("queue tenant/workspace does not match health scope")
    if queue.source_id != source_id:
        raise MicrosoftOperationalHealthError("queue source does not match health scope")
    if subscription.tenant_id.casefold() != microsoft_tenant_id.casefold():
        raise MicrosoftOperationalHealthError("Graph tenant does not match health scope")
    if reconciliation is not None and reconciliation.instance_id != instance_id:
        raise MicrosoftOperationalHealthError(
            "reconciliation instance does not match health scope"
        )


def _health(
    state: ConnectorHealthState,
    code: ConnectorOperationCode,
    message: str,
) -> ConnectorHealthV1:
    return ConnectorHealthV1(
        schema_version="ets.connector.health.v1",
        state=state,
        code=code,
        message=message,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MicrosoftOperationalHealthError(
            "Microsoft operational-health evaluation time must be timezone-aware"
        )
    return value.astimezone(UTC)
