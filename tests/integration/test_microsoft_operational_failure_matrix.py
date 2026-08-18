from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
    apply_graph_lifecycle_event,
)
from ets.connectors.enterprise.microsoft_health import (
    MicrosoftOperationalHealthPolicyV1,
    MicrosoftOperationalPostureV1,
    evaluate_microsoft_operational_posture,
)
from ets.connectors.enterprise.microsoft_reconciliation import (
    MicrosoftReconciliationGapV1,
    begin_microsoft_reconciliation,
    open_microsoft_reconciliation_gap,
    resolve_microsoft_reconciliation,
)
from ets.connectors.models import ConnectorHealthV1
from ets.connectors.runtime import ConnectorRuntimeStateV1
from ets.runtime.sync_queue import SyncQueue
from ets.runtime.sync_queue_scope import (
    GATEWAY_SYNC_SCHEMA,
    SourceScopedSyncQueueStatus,
    source_scoped_sync_queue_status,
)

NOW = datetime(2026, 8, 18, 5, 0, tzinfo=UTC)
INSTANCE = "microsoft-sharepoint-prod"
ETS_TENANT = "tenant-authoritative"
WORKSPACE = "workspace-authoritative"
SOURCE = "microsoft-sharepoint-source"
OTHER_SOURCE = "unrelated-source"
GRAPH_TENANT = "11111111-1111-1111-1111-111111111111"
SOURCE_SYSTEM = "microsoft.sharepoint.onedrive_delta"


def _policy() -> MicrosoftOperationalHealthPolicyV1:
    return MicrosoftOperationalHealthPolicyV1(
        profile_id="microsoft-failure-matrix-v1",
        subscription_renewal_warning_seconds=3600,
        maximum_collection_lag_seconds=900,
        maximum_unsynchronized_age_seconds=900,
        maximum_source_queue_depth=100,
    )


def _runtime(*, gap_open: bool = False) -> ConnectorRuntimeStateV1:
    return ConnectorRuntimeStateV1.model_validate(
        {
            "schema_version": "ets.connector.runtime.v1",
            "instance_id": INSTANCE,
            "checkpoint": None,
            "checkpoint_revision": 0,
            "retry_count": 0,
            "next_attempt_at_utc": None,
            "last_success_at_utc": NOW - timedelta(minutes=1),
            "observation_state": "collection_gap" if gap_open else "healthy_observation",
            "gap_open": gap_open,
            "lease_owner": None,
            "lease_expires_at_utc": None,
            "updated_at_utc": NOW,
        }
    )


def _source_health(
    state: str = "healthy",
    code: str = "ok",
    message: str = "Microsoft source is reachable",
) -> ConnectorHealthV1:
    return ConnectorHealthV1.model_validate(
        {
            "schema_version": "ets.connector.health.v1",
            "state": state,
            "code": code,
            "message": message,
        }
    )


def _subscription() -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1(
        schema_version="ets.connector.microsoft.graph_subscription_state.v1",
        subscription_id="subscription-001",
        tenant_id=GRAPH_TENANT,
        cloud="global",
        resource="/sites/site-id/drives/drive-id/root",
        client_state_sha256="0" * 64,
        expiration_date_time=NOW + timedelta(hours=8),
        status="active",
        gap_state="none",
    )


def _lifecycle(
    event: str,
) -> MicrosoftGraphNotificationV1:
    return MicrosoftGraphNotificationV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_notification.v1",
            "source_record_id": f"lifecycle-{event}",
            "kind": "lifecycle",
            "subscription_id": "subscription-001",
            "tenant_id": GRAPH_TENANT,
            "subscription_expiration_date_time": NOW + timedelta(hours=8),
            "change_type": None,
            "resource": None,
            "lifecycle_event": event,
            "resource_data": {},
        }
    )


def _gateway_payload(
    key: str,
    *,
    source_id: str = SOURCE,
    tenant_id: str = ETS_TENANT,
) -> dict[str, object]:
    return {
        "sync_schema": GATEWAY_SYNC_SCHEMA,
        "idempotency_key": key,
        "tenant_id": tenant_id,
        "workspace_id": WORKSPACE,
        "event_id": f"event-{key}",
        "event_hash": f"hash-{key}",
        "log_index": 1,
        "capture": {
            "source_id": source_id,
            "content_hash": f"content-{key}",
            "content_hash_alg": "sha256",
        },
        "raw_payload_included": False,
    }


def _queue_status(queue: SyncQueue) -> SourceScopedSyncQueueStatus:
    return source_scoped_sync_queue_status(
        queue,
        tenant_id=ETS_TENANT,
        workspace_id=WORKSPACE,
        source_id=SOURCE,
        upstream_status="reachable",
        now=NOW + timedelta(minutes=1),
    )


def _evaluate(
    *,
    queue: SourceScopedSyncQueueStatus,
    source_health: ConnectorHealthV1 | None = None,
    runtime: ConnectorRuntimeStateV1 | None = None,
    subscription: MicrosoftGraphSubscriptionStateV1 | None = None,
    reconciliation: MicrosoftReconciliationGapV1 | None = None,
) -> MicrosoftOperationalPostureV1:
    posture = evaluate_microsoft_operational_posture(
        instance_id=INSTANCE,
        ets_tenant_id=ETS_TENANT,
        workspace_id=WORKSPACE,
        source_id=SOURCE,
        microsoft_tenant_id=GRAPH_TENANT,
        source_health=source_health or _source_health(),
        runtime=runtime or _runtime(),
        subscription=subscription or _subscription(),
        queue=queue,
        reconciliation=reconciliation,
        policy=_policy(),
        evaluated_at_utc=NOW,
    )
    assert posture.verification_claimed is False
    assert posture.source_truth_claimed is False
    assert posture.completeness_claimed is False
    return posture


def test_missed_lifecycle_notification_projects_possible_gap(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "missed.db")
    subscription = apply_graph_lifecycle_event(_subscription(), _lifecycle("missed"))
    gap = open_microsoft_reconciliation_gap(
        gap_id="gap-missed",
        instance_id=INSTANCE,
        source_system=SOURCE_SYSTEM,
        reason="missed_notification",
        detected_at_utc=NOW - timedelta(minutes=1),
    )

    posture = _evaluate(
        queue=_queue_status(queue),
        subscription=subscription,
        runtime=_runtime(gap_open=True),
        reconciliation=gap,
    )

    assert subscription.gap_state == "possible"
    assert posture.health.state == "degraded"
    assert posture.health.code == "gap_detected"
    assert posture.reconciliation_status == "possible"


@pytest.mark.parametrize(
    ("lifecycle_event", "expected_state", "expected_code"),
    [
        ("subscriptionRemoved", "failed", "terminal_error"),
        ("reauthorizationRequired", "degraded", "authorization_failed"),
    ],
)
def test_subscription_lifecycle_faults_project_distinct_health(
    tmp_path: Path,
    lifecycle_event: str,
    expected_state: str,
    expected_code: str,
) -> None:
    queue = SyncQueue(tmp_path / f"{lifecycle_event}.db")
    subscription = apply_graph_lifecycle_event(
        _subscription(),
        _lifecycle(lifecycle_event),
    )

    posture = _evaluate(queue=_queue_status(queue), subscription=subscription)

    assert posture.health.state == expected_state
    assert posture.health.code == expected_code


@pytest.mark.parametrize(
    ("state", "code"),
    [
        ("failed", "authentication_failed"),
        ("failed", "authorization_failed"),
        ("degraded", "throttled"),
    ],
)
def test_source_auth_and_throttle_faults_keep_source_health_precedence(
    tmp_path: Path,
    state: str,
    code: str,
) -> None:
    queue = SyncQueue(tmp_path / f"{code}.db")

    posture = _evaluate(
        queue=_queue_status(queue),
        source_health=_source_health(state, code, f"injected {code}"),
    )

    assert posture.health.state == state
    assert posture.health.code == code


def test_delta_state_expiry_unrecoverable_outcome_remains_visible(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "delta-expired.db")
    possible = open_microsoft_reconciliation_gap(
        gap_id="gap-delta-expired",
        instance_id=INSTANCE,
        source_system=SOURCE_SYSTEM,
        reason="delta_state_expired",
        detected_at_utc=NOW - timedelta(minutes=3),
    )
    reconciling = begin_microsoft_reconciliation(
        possible,
        started_at_utc=NOW - timedelta(minutes=2),
    )
    unrecoverable = resolve_microsoft_reconciliation(
        reconciling,
        outcome="unrecoverable",
        resolved_at_utc=NOW - timedelta(minutes=1),
        recovered_records=0,
    )

    posture = _evaluate(
        queue=_queue_status(queue),
        runtime=_runtime(gap_open=True),
        reconciliation=unrecoverable,
    )

    assert posture.health.state == "degraded"
    assert posture.health.code == "gap_detected"
    assert posture.reconciliation_status == "unrecoverable"
    assert posture.reconciliation_outcome == "unrecoverable"


def test_worker_outage_projects_reconciling_gap(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "worker-outage.db")
    possible = open_microsoft_reconciliation_gap(
        gap_id="gap-worker-outage",
        instance_id=INSTANCE,
        source_system=SOURCE_SYSTEM,
        reason="worker_outage",
        detected_at_utc=NOW - timedelta(minutes=2),
    )
    reconciling = begin_microsoft_reconciliation(
        possible,
        started_at_utc=NOW - timedelta(minutes=1),
    )

    posture = _evaluate(
        queue=_queue_status(queue),
        runtime=_runtime(gap_open=True),
        reconciliation=reconciling,
    )

    assert posture.health.code == "gap_detected"
    assert posture.reconciliation_status == "reconciling"


def test_source_scoped_queue_failure_does_not_leak_between_sources_or_tenants(
    tmp_path: Path,
) -> None:
    queue = SyncQueue(tmp_path / "queue-isolation.db")
    other_source = queue.enqueue(_gateway_payload("other-source", source_id=OTHER_SOURCE))
    other_tenant = queue.enqueue(
        _gateway_payload("other-tenant", tenant_id="tenant-other")
    )
    queue.mark_terminal(other_source.idempotency_key, "unrelated source failure")
    queue.mark_terminal(other_tenant.idempotency_key, "unrelated tenant failure")

    healthy = _evaluate(queue=_queue_status(queue))
    assert healthy.health.state == "healthy"
    assert healthy.health.code == "ok"

    target = queue.enqueue(_gateway_payload("target-terminal"))
    queue.mark_terminal(target.idempotency_key, "target source terminal failure")
    failed_queue = _evaluate(queue=_queue_status(queue))

    assert failed_queue.health.state == "degraded"
    assert failed_queue.health.code == "terminal_error"
    assert failed_queue.terminal_failure_count == 1


def test_recovered_gap_returns_to_underlying_healthy_posture(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "recovered.db")
    possible = open_microsoft_reconciliation_gap(
        gap_id="gap-recovered",
        instance_id=INSTANCE,
        source_system=SOURCE_SYSTEM,
        reason="missed_notification",
        detected_at_utc=NOW - timedelta(minutes=3),
    )
    reconciling = begin_microsoft_reconciliation(
        possible,
        started_at_utc=NOW - timedelta(minutes=2),
    )
    recovered = resolve_microsoft_reconciliation(
        reconciling,
        outcome="recovered",
        resolved_at_utc=NOW - timedelta(minutes=1),
        recovered_records=4,
    )
    subscription = apply_graph_lifecycle_event(_subscription(), _lifecycle("missed")).model_copy(
        update={"gap_state": "none"}
    )

    posture = _evaluate(
        queue=_queue_status(queue),
        subscription=subscription,
        runtime=_runtime(gap_open=False),
        reconciliation=recovered,
    )

    assert posture.health.state == "healthy"
    assert posture.health.code == "ok"
    assert posture.reconciliation_outcome == "recovered"
