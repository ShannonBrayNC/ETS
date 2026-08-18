from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ets.connectors.enterprise.microsoft_graph import MicrosoftGraphSubscriptionStateV1
from ets.connectors.enterprise.microsoft_health import (
    MicrosoftOperationalHealthError,
    MicrosoftOperationalHealthPolicyV1,
    MicrosoftOperationalPostureV1,
    evaluate_microsoft_operational_posture,
)
from ets.connectors.enterprise.microsoft_reconciliation import (
    begin_microsoft_reconciliation,
    open_microsoft_reconciliation_gap,
    resolve_microsoft_reconciliation,
)
from ets.connectors.models import ConnectorHealthV1
from ets.connectors.runtime import ConnectorRuntimeStateV1
from ets.runtime.sync_queue_scope import SourceScopedSyncQueueStatus

NOW = datetime(2026, 8, 18, 3, 30, tzinfo=UTC)
INSTANCE = "microsoft-sharepoint-prod"
ETS_TENANT = "tenant-authoritative"
WORKSPACE = "workspace-authoritative"
SOURCE = "microsoft-sharepoint-source"
GRAPH_TENANT = "11111111-1111-1111-1111-111111111111"


def _policy() -> MicrosoftOperationalHealthPolicyV1:
    return MicrosoftOperationalHealthPolicyV1(
        profile_id="microsoft-p0-demo",
        subscription_renewal_warning_seconds=3600,
        maximum_collection_lag_seconds=900,
        maximum_unsynchronized_age_seconds=900,
        maximum_source_queue_depth=100,
    )


def _source_health(
    *,
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


def _runtime(
    *,
    last_success_at_utc: datetime | None = None,
    observation_state: str = "healthy_observation",
    gap_open: bool = False,
) -> ConnectorRuntimeStateV1:
    success = NOW - timedelta(minutes=1) if last_success_at_utc is None else last_success_at_utc
    return ConnectorRuntimeStateV1.model_validate(
        {
            "schema_version": "ets.connector.runtime.v1",
            "instance_id": INSTANCE,
            "checkpoint": None,
            "checkpoint_revision": 0,
            "retry_count": 0,
            "next_attempt_at_utc": None,
            "last_success_at_utc": success,
            "observation_state": observation_state,
            "gap_open": gap_open,
            "lease_owner": None,
            "lease_expires_at_utc": None,
            "updated_at_utc": NOW,
        }
    )


def _subscription(
    *,
    status: str = "active",
    gap_state: str = "none",
    expiration: datetime | None = None,
) -> MicrosoftGraphSubscriptionStateV1:
    expires = NOW + timedelta(hours=8) if expiration is None else expiration
    return MicrosoftGraphSubscriptionStateV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_subscription_state.v1",
            "subscription_id": "subscription-001",
            "tenant_id": GRAPH_TENANT,
            "cloud": "global",
            "resource": "/sites/site-id/drives/drive-id/root",
            "client_state_sha256": "0" * 64,
            "expiration_date_time": expires,
            "status": status,
            "gap_state": gap_state,
        }
    )


def _queue(
    *,
    queue_depth: int = 0,
    retryable_failure: int = 0,
    terminal_failure: int = 0,
    oldest_age: float | None = None,
) -> SourceScopedSyncQueueStatus:
    return SourceScopedSyncQueueStatus(
        tenant_id=ETS_TENANT,
        workspace_id=WORKSPACE,
        source_id=SOURCE,
        queue_depth=queue_depth,
        queue_bytes=queue_depth * 100,
        pending=max(0, queue_depth - retryable_failure - terminal_failure),
        in_flight=0,
        retryable_failure=retryable_failure,
        terminal_failure=terminal_failure,
        synchronized=4,
        shared_max_items=10_000,
        shared_max_bytes=128 * 1024 * 1024,
        oldest_unsynchronized_age_seconds=oldest_age,
        last_successful_sync=NOW.isoformat(),
        latest_active_failure=(
            "2026-08-18T03:29:00Z active failure"
            if retryable_failure or terminal_failure
            else None
        ),
        upstream_status="reachable",
    )


def _evaluate(**overrides: object) -> MicrosoftOperationalPostureV1:
    values: dict[str, object] = {
        "instance_id": INSTANCE,
        "ets_tenant_id": ETS_TENANT,
        "workspace_id": WORKSPACE,
        "source_id": SOURCE,
        "microsoft_tenant_id": GRAPH_TENANT,
        "source_health": _source_health(),
        "runtime": _runtime(),
        "subscription": _subscription(),
        "queue": _queue(),
        "reconciliation": None,
        "policy": _policy(),
        "evaluated_at_utc": NOW,
    }
    values.update(overrides)
    return evaluate_microsoft_operational_posture(**values)  # type: ignore[arg-type]


def test_healthy_posture_is_operational_and_never_a_verification_claim() -> None:
    posture = _evaluate()

    assert posture.health.state == "healthy"
    assert posture.health.code == "ok"
    assert posture.verification_claimed is False
    assert posture.source_truth_claimed is False
    assert posture.completeness_claimed is False
    assert posture.policy_profile_id == "microsoft-p0-demo"


def test_source_failure_has_precedence_over_other_operational_signals() -> None:
    posture = _evaluate(
        source_health=_source_health(
            state="failed",
            code="authorization_failed",
            message="Microsoft source authorization was denied",
        ),
        subscription=_subscription(status="removed"),
        queue=_queue(queue_depth=1, terminal_failure=1),
    )

    assert posture.health.state == "failed"
    assert posture.health.code == "authorization_failed"


@pytest.mark.parametrize("status", ["removed", "disabled"])
def test_terminal_subscription_state_fails_operational_posture(status: str) -> None:
    posture = _evaluate(subscription=_subscription(status=status))

    assert posture.health.state == "failed"
    assert posture.health.code == "terminal_error"
    assert status in posture.health.message


def test_expired_and_reauthorization_subscription_states_are_distinct() -> None:
    expired = _evaluate(subscription=_subscription(expiration=NOW - timedelta(seconds=1)))
    reauth = _evaluate(subscription=_subscription(status="reauthorization_required"))

    assert expired.health.state == "degraded"
    assert expired.health.code == "gap_detected"
    assert reauth.health.state == "degraded"
    assert reauth.health.code == "authorization_failed"


def test_graph_gap_and_partial_reconciliation_remain_visible() -> None:
    graph_gap = _evaluate(subscription=_subscription(gap_state="possible"))

    possible = open_microsoft_reconciliation_gap(
        gap_id="gap-001",
        instance_id=INSTANCE,
        source_system="microsoft.sharepoint.onedrive_delta",
        reason="missed_notification",
        detected_at_utc=NOW - timedelta(minutes=3),
    )
    reconciling = begin_microsoft_reconciliation(
        possible,
        started_at_utc=NOW - timedelta(minutes=2),
    )
    partial = resolve_microsoft_reconciliation(
        reconciling,
        outcome="partial",
        resolved_at_utc=NOW - timedelta(minutes=1),
        recovered_records=2,
    )
    partial_posture = _evaluate(reconciliation=partial)

    assert graph_gap.health.code == "gap_detected"
    assert "does not prove" in graph_gap.health.message
    assert partial_posture.health.code == "gap_detected"
    assert partial_posture.reconciliation_outcome == "partial"


@pytest.mark.parametrize(
    ("queue", "expected_code"),
    [
        (_queue(queue_depth=1, terminal_failure=1), "terminal_error"),
        (_queue(queue_depth=1, retryable_failure=1), "retryable_error"),
        (_queue(queue_depth=101), "retryable_error"),
        (_queue(queue_depth=1, oldest_age=901), "retryable_error"),
    ],
)
def test_source_scoped_queue_conditions_degrade_posture(
    queue: SourceScopedSyncQueueStatus,
    expected_code: str,
) -> None:
    posture = _evaluate(queue=queue)

    assert posture.health.state == "degraded"
    assert posture.health.code == expected_code


def test_collection_lag_and_subscription_renewal_window_are_policy_bound() -> None:
    lagged = _evaluate(runtime=_runtime(last_success_at_utc=NOW - timedelta(seconds=901)))
    renewal = _evaluate(
        subscription=_subscription(expiration=NOW + timedelta(seconds=3599))
    )

    assert lagged.health.code == "gap_detected"
    assert "does not by itself prove" in lagged.health.message
    assert renewal.health.code == "retryable_error"
    assert "renewal window" in renewal.health.message


def test_missing_collection_success_is_unknown_observation() -> None:
    runtime = _runtime().model_copy(update={"last_success_at_utc": None})
    posture = _evaluate(runtime=runtime)

    assert posture.health.state == "degraded"
    assert posture.health.code == "unknown_observation"


def test_scope_mismatch_and_future_runtime_time_fail_closed() -> None:
    wrong_queue = replace(_queue(), source_id="other-source")
    with pytest.raises(MicrosoftOperationalHealthError, match="queue source"):
        _evaluate(queue=wrong_queue)

    with pytest.raises(MicrosoftOperationalHealthError, match="future"):
        _evaluate(runtime=_runtime(last_success_at_utc=NOW + timedelta(seconds=1)))


def test_graph_and_reconciliation_scope_mismatches_fail_closed() -> None:
    with pytest.raises(MicrosoftOperationalHealthError, match="Graph tenant"):
        _evaluate(microsoft_tenant_id="22222222-2222-2222-2222-222222222222")

    wrong_gap = open_microsoft_reconciliation_gap(
        gap_id="gap-other-instance",
        instance_id="other-instance",
        source_system="microsoft.sharepoint.onedrive_delta",
        reason="operator_declared",
        detected_at_utc=NOW - timedelta(minutes=1),
    )
    with pytest.raises(MicrosoftOperationalHealthError, match="reconciliation instance"):
        _evaluate(reconciliation=wrong_gap)
