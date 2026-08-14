from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
    ConnectorCheckpointV1,
    ConnectorCollection,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime_store import ConnectorRuntimeStore
from ets.gateway.connector_management import (
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.connector_runner import GatewayConnectorRunResult
from ets.gateway.microsoft_purview_runtime import (
    MicrosoftPurviewRuntimeError,
    mark_microsoft_purview_collection_gap,
    persist_microsoft_purview_gateway_success,
)

NOW = datetime(2026, 8, 14, 22, 0, tzinfo=UTC)
INSTANCE_ID = "purview-prod"
CREDENTIAL_REF = "fixture://microsoft/purview"
MANIFESTS = Path("config/connectors/enterprise")


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": INSTANCE_ID,
            "connector_id": "microsoft.purview.activity",
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="tenant-a",
                workspace_id="workspace-a",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="purview-audit",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer",
                credential_ref=CREDENTIAL_REF,
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll",
                interval_seconds=60,
                batch_size=500,
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor",
                durable=True,
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.purview.audit.v1",
                normalization_profile="normalize.microsoft.purview.audit.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "management_profile_id": "purview-prod",
                "content_type": "Audit.General",
                "poll_window_seconds": 3600,
                "overlap_seconds": 300,
            },
        }
    )


def _principal() -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id="operator-1",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        can_manage=True,
    )


def _service(tmp_path: Path) -> ConnectorManagementService:
    return ConnectorManagementService(
        registry=ConnectorRegistry.from_manifest_directory(MANIFESTS),
        store=ConnectorRuntimeStore(tmp_path / "connector-runtime.db"),
        now=lambda: NOW,
    )


def _checkpoint(cursor: str) -> ConnectorCheckpointV1:
    return ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=cursor,
        observed_through_utc=NOW,
    )


def _success(*, cursor: str, has_more: bool) -> GatewayConnectorRunResult:
    return GatewayConnectorRunResult(
        code="ok",
        source_records=1,
        committed_local=1,
        sync_queued=1,
        partial_commit=0,
        checkpoint_to_persist=_checkpoint(cursor),
        has_more=has_more,
        message="fixture Gateway success",
    )


def _failure() -> GatewayConnectorRunResult:
    return GatewayConnectorRunResult(
        code="retryable_error",
        source_records=1,
        committed_local=1,
        sync_queued=0,
        partial_commit=1,
        checkpoint_to_persist=None,
        has_more=False,
        message="fixture partial commit",
    )


def _seed_checkpoint(
    service: ConnectorManagementService,
    principal: ConnectorManagementPrincipal,
) -> None:
    service.create_instance(principal, _instance())
    service.update_checkpoint(
        principal,
        INSTANCE_ID,
        _checkpoint("https://manage.office.com/page/old"),
        expected_checkpoint_revision=0,
        observation_state="healthy_observation",
        gap_open=False,
        last_success_at_utc=NOW,
    )


def test_purview_discovery_gap_preserves_existing_watermark(tmp_path: Path) -> None:
    service = _service(tmp_path)
    principal = _principal()
    _seed_checkpoint(service, principal)
    before = service.get_runtime(principal, INSTANCE_ID)

    after = mark_microsoft_purview_collection_gap(service, principal, INSTANCE_ID)

    assert after.gap_open is True
    assert after.observation_state == "collection_gap"
    assert after.checkpoint == before.checkpoint
    assert after.checkpoint_revision == before.checkpoint_revision


def test_purview_failed_gateway_run_cannot_advance_watermark(tmp_path: Path) -> None:
    service = _service(tmp_path)
    principal = _principal()
    _seed_checkpoint(service, principal)
    mark_microsoft_purview_collection_gap(service, principal, INSTANCE_ID)
    before = service.get_runtime(principal, INSTANCE_ID)

    with pytest.raises(MicrosoftPurviewRuntimeError, match="successful Gateway run"):
        persist_microsoft_purview_gateway_success(
            service,
            principal,
            INSTANCE_ID,
            _failure(),
            expected_checkpoint_revision=before.checkpoint_revision,
            completed_at_utc=NOW,
        )

    after = service.get_runtime(principal, INSTANCE_ID)
    assert after.checkpoint == before.checkpoint
    assert after.checkpoint_revision == before.checkpoint_revision
    assert after.gap_open is True
    assert after.observation_state == "collection_gap"


def test_purview_intermediate_page_advances_cursor_but_keeps_gap_open(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    principal = _principal()
    _seed_checkpoint(service, principal)
    mark_microsoft_purview_collection_gap(service, principal, INSTANCE_ID)
    before = service.get_runtime(principal, INSTANCE_ID)

    after = persist_microsoft_purview_gateway_success(
        service,
        principal,
        INSTANCE_ID,
        _success(cursor="https://manage.office.com/page/next", has_more=True),
        expected_checkpoint_revision=before.checkpoint_revision,
        completed_at_utc=NOW,
    )

    assert after.checkpoint is not None
    assert after.checkpoint.cursor == "https://manage.office.com/page/next"
    assert after.checkpoint_revision == before.checkpoint_revision + 1
    assert after.gap_open is True
    assert after.observation_state == "collection_gap"


def test_purview_final_committed_page_persists_watermark_then_reconciles_gap(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    principal = _principal()
    _seed_checkpoint(service, principal)
    mark_microsoft_purview_collection_gap(service, principal, INSTANCE_ID)
    before = service.get_runtime(principal, INSTANCE_ID)

    after = persist_microsoft_purview_gateway_success(
        service,
        principal,
        INSTANCE_ID,
        _success(cursor="https://manage.office.com/page/final", has_more=False),
        expected_checkpoint_revision=before.checkpoint_revision,
        completed_at_utc=NOW,
    )

    assert after.checkpoint is not None
    assert after.checkpoint.cursor == "https://manage.office.com/page/final"
    assert after.checkpoint_revision == before.checkpoint_revision + 1
    assert after.gap_open is False
    assert after.observation_state == "healthy_observation"
    assert after.last_success_at_utc == NOW
