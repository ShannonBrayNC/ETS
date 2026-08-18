from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.microsoft_reconciliation import (
    MICROSOFT_RECONCILIATION_GAP_SCHEMA_VERSION,
    MicrosoftReconciliationGapV1,
    MicrosoftReconciliationStateError,
    acknowledge_microsoft_reconciliation_gap,
    begin_microsoft_reconciliation,
    open_microsoft_reconciliation_gap,
    project_microsoft_connector_health,
    resolve_microsoft_reconciliation,
)
from ets.connectors.models import ConnectorHealthV1
from ets.connectors.runtime import ConnectorRuntimeStateV1

NOW = datetime(2026, 8, 18, 3, 0, tzinfo=UTC)
INSTANCE_ID = "microsoft-sharepoint-prod"
GAP_ID = "gap-sharepoint-20260818-001"


def _healthy_source() -> ConnectorHealthV1:
    return ConnectorHealthV1(
        schema_version="ets.connector.health.v1",
        state="healthy",
        code="ok",
        message="Microsoft source is reachable",
    )


def _failed_source() -> ConnectorHealthV1:
    return ConnectorHealthV1(
        schema_version="ets.connector.health.v1",
        state="failed",
        code="authorization_failed",
        message="Microsoft source authorization was denied",
    )


def _runtime(
    *,
    observation_state: str = "healthy_observation",
    gap_open: bool = False,
    retry_count: int = 0,
) -> ConnectorRuntimeStateV1:
    return ConnectorRuntimeStateV1.model_validate(
        {
            "schema_version": "ets.connector.runtime.v1",
            "instance_id": INSTANCE_ID,
            "checkpoint": None,
            "checkpoint_revision": 0,
            "retry_count": retry_count,
            "next_attempt_at_utc": None,
            "last_success_at_utc": NOW,
            "observation_state": observation_state,
            "gap_open": gap_open,
            "lease_owner": None,
            "lease_expires_at_utc": None,
            "updated_at_utc": NOW,
        }
    )


def _possible() -> MicrosoftReconciliationGapV1:
    return open_microsoft_reconciliation_gap(
        gap_id=GAP_ID,
        instance_id=INSTANCE_ID,
        source_system="microsoft.sharepoint.onedrive_delta",
        reason="missed_notification",
        detected_at_utc=NOW,
        note="Graph reported a missed notification signal",
    )


def _resolved(outcome: str) -> MicrosoftReconciliationGapV1:
    gap = begin_microsoft_reconciliation(
        _possible(),
        started_at_utc=NOW + timedelta(minutes=1),
    )
    if outcome == "recovered":
        return resolve_microsoft_reconciliation(
            gap,
            outcome="recovered",
            resolved_at_utc=NOW + timedelta(minutes=2),
            recovered_records=4,
        )
    if outcome == "partial":
        return resolve_microsoft_reconciliation(
            gap,
            outcome="partial",
            resolved_at_utc=NOW + timedelta(minutes=2),
            recovered_records=2,
        )
    return resolve_microsoft_reconciliation(
        gap,
        outcome="unrecoverable",
        resolved_at_utc=NOW + timedelta(minutes=2),
        recovered_records=0,
    )


def test_gap_lifecycle_preserves_recovered_outcome_through_operator_acknowledgement() -> None:
    possible = _possible()
    assert possible.schema_version == MICROSOFT_RECONCILIATION_GAP_SCHEMA_VERSION
    assert possible.status == "possible"
    assert possible.outcome is None

    reconciling = begin_microsoft_reconciliation(
        possible,
        started_at_utc=NOW + timedelta(minutes=1),
    )
    assert reconciling.status == "reconciling"

    recovered = resolve_microsoft_reconciliation(
        reconciling,
        outcome="recovered",
        resolved_at_utc=NOW + timedelta(minutes=2),
        recovered_records=4,
    )
    assert recovered.status == "recovered"
    assert recovered.outcome == "recovered"
    assert recovered.recovered_records == 4

    acknowledged, audit = acknowledge_microsoft_reconciliation_gap(
        recovered,
        actor_id="operator-001",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        acknowledged_at_utc=NOW + timedelta(minutes=3),
    )

    assert acknowledged.status == "acknowledged"
    assert acknowledged.outcome == "recovered"
    assert acknowledged.recovered_records == 4
    assert acknowledged.acknowledged_by == "operator-001"
    assert audit.action == "microsoft_reconciliation_gap_acknowledged"
    assert audit.instance_id == INSTANCE_ID
    assert audit.actor_id == "operator-001"


@pytest.mark.parametrize("outcome", ["partial", "unrecoverable"])
def test_known_continuity_limitation_remains_degraded_after_acknowledgement(
    outcome: str,
) -> None:
    resolved = _resolved(outcome)
    acknowledged, _ = acknowledge_microsoft_reconciliation_gap(
        resolved,
        actor_id="operator-001",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        acknowledged_at_utc=NOW + timedelta(minutes=3),
    )

    health = project_microsoft_connector_health(
        _healthy_source(),
        _runtime(),
        acknowledged,
    )

    assert health.state == "degraded"
    assert health.code == "gap_detected"
    assert outcome in health.message
    assert "limitation remains visible" in health.message


def test_recovered_gap_allows_healthy_operational_posture_when_runtime_gap_is_closed() -> None:
    health = project_microsoft_connector_health(
        _healthy_source(),
        _runtime(),
        _resolved("recovered"),
    )

    assert health.state == "healthy"
    assert health.code == "ok"


def test_possible_and_reconciling_states_are_explicit_collection_continuity_health() -> None:
    possible = _possible()
    reconciling = begin_microsoft_reconciliation(
        possible,
        started_at_utc=NOW + timedelta(minutes=1),
    )

    for gap in (possible, reconciling):
        health = project_microsoft_connector_health(_healthy_source(), _runtime(), gap)
        assert health.state == "degraded"
        assert health.code == "gap_detected"
        assert gap.status in health.message
        assert "does not assert source completeness" in health.message


def test_source_failure_remains_stronger_than_collection_gap_projection() -> None:
    health = project_microsoft_connector_health(
        _failed_source(),
        _runtime(gap_open=True, observation_state="collection_gap"),
        _possible(),
    )

    assert health.state == "failed"
    assert health.code == "authorization_failed"


def test_runtime_gap_and_pending_retry_degrade_reachable_source_without_truth_claim() -> None:
    gap_health = project_microsoft_connector_health(
        _healthy_source(),
        _runtime(gap_open=True, observation_state="collection_gap"),
        None,
    )
    retry_health = project_microsoft_connector_health(
        _healthy_source(),
        _runtime(retry_count=2),
        None,
    )

    assert gap_health.code == "gap_detected"
    assert "does not establish observation continuity" in gap_health.message
    assert retry_health.state == "degraded"
    assert retry_health.code == "retryable_error"


def test_unknown_runtime_observation_is_not_reported_as_healthy() -> None:
    health = project_microsoft_connector_health(
        _healthy_source(),
        _runtime(observation_state="unknown_observation"),
        None,
    )

    assert health.state == "degraded"
    assert health.code == "unknown_observation"


def test_invalid_transition_order_fails_closed() -> None:
    with pytest.raises(MicrosoftReconciliationStateError, match="resolve only"):
        resolve_microsoft_reconciliation(
            _possible(),
            outcome="recovered",
            resolved_at_utc=NOW + timedelta(minutes=1),
        )

    with pytest.raises(MicrosoftReconciliationStateError, match="resolved reconciliation"):
        acknowledge_microsoft_reconciliation_gap(
            _possible(),
            actor_id="operator-001",
            tenant_id="tenant-authoritative",
            workspace_id="workspace-authoritative",
            acknowledged_at_utc=NOW + timedelta(minutes=1),
        )


def test_strict_gap_model_rejects_acknowledged_state_without_preserved_outcome() -> None:
    with pytest.raises(ValidationError, match="preserve its resolution outcome"):
        MicrosoftReconciliationGapV1(
            schema_version=MICROSOFT_RECONCILIATION_GAP_SCHEMA_VERSION,
            gap_id=GAP_ID,
            instance_id=INSTANCE_ID,
            source_system="microsoft.sharepoint.onedrive_delta",
            reason="delta_state_expired",
            status="acknowledged",
            detected_at_utc=NOW,
            updated_at_utc=NOW + timedelta(minutes=3),
            reconciliation_started_at_utc=NOW + timedelta(minutes=1),
            resolved_at_utc=NOW + timedelta(minutes=2),
            outcome=None,
            acknowledged_by="operator-001",
            acknowledged_at_utc=NOW + timedelta(minutes=3),
        )
