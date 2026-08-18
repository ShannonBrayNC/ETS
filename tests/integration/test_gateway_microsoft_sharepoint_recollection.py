from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
)
from ets.connectors.enterprise.microsoft_sharepoint_connector import (
    SHAREPOINT_CONNECTOR_ID,
    MicrosoftSharePointDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRecordV1,
    MicrosoftSharePointDeltaRequestProfile,
    sharepoint_drive_delta_request_profile,
)
from ets.connectors.enterprise.microsoft_sharepoint_notifications import (
    MicrosoftSharePointNotificationError,
)
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
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.connector_runner import GatewayConnectorCollectionRunner
from ets.gateway.microsoft_sharepoint_recollection import (
    GatewayMicrosoftSharePointRecollectionService,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

NOW = datetime(2026, 8, 18, 2, 30, tzinfo=UTC)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "33333333-3333-3333-3333-333333333333"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PROFILE_ID = "sharepoint-prod"
CREDENTIAL_REF = "fixture://microsoft/sharepoint"
SUBSCRIPTION_ID = "subscription-001"
NOTIFICATION_ID = "notification-sharepoint-001"
PRINCIPAL = "spiffe://example.test/workload/microsoft-sharepoint"
CHECKPOINT = "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$skiptoken=prior"
NEXT_CHECKPOINT = (
    "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$deltatoken=complete"
)
MANIFESTS = Path("config/connectors/enterprise")


class FixtureCredentialResolver:
    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status="available",
            version="1",
            updated_at_utc=NOW,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        return CredentialLease(b"fixture-sharepoint-token", self.describe(reference))


class FixturePageClient:
    def __init__(self, page: MicrosoftSharePointDeltaPageV1) -> None:
        self.page = page
        self.request_urls: list[str | None] = []

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        self.request_urls.append(request_url)
        return self.page

    def close(self) -> None:
        return None


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=TENANT_ID,
        application_id=APPLICATION_ID,
        cloud="global",
        credential_ref=CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=CREDENTIAL_REF,
        ),
        consent_state="granted",
    )


def _profile() -> MicrosoftSharePointDeltaRequestProfile:
    return sharepoint_drive_delta_request_profile(PROFILE_ID, _tenant(), "drive-001")


def _subscription() -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_subscription_state.v1",
            "subscription_id": SUBSCRIPTION_ID,
            "tenant_id": TENANT_ID,
            "cloud": "global",
            "resource": "/drives/drive-001/root",
            "client_state_sha256": "a" * 64,
            "expiration_date_time": NOW + timedelta(hours=1),
            "status": "active",
            "gap_state": "none",
        }
    )


def _notification(*, tenant_id: str = TENANT_ID) -> MicrosoftGraphNotificationV1:
    return MicrosoftGraphNotificationV1(
        schema_version="ets.connector.microsoft.graph_notification.v1",
        source_record_id=NOTIFICATION_ID,
        kind="resource",
        subscription_id=SUBSCRIPTION_ID,
        tenant_id=tenant_id,
        subscription_expiration_date_time=NOW + timedelta(hours=1),
        change_type="updated",
        resource="drives/drive-001/items/item-001",
        resource_data={"id": "item-001"},
    )


def _checkpoint() -> ConnectorCheckpointV1:
    return ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=CHECKPOINT,
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "sharepoint-notification-commit",
            "connector_id": SHAREPOINT_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="instance-tenant-must-not-authorize",
                workspace_id="instance-workspace-must-not-authorize",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="sharepoint-approved-scope",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer",
                credential_ref=CREDENTIAL_REF,
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll",
                interval_seconds=60,
                batch_size=100,
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor",
                durable=True,
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.sharepoint.metadata.v1",
                normalization_profile="normalize.microsoft.sharepoint.metadata.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "scope": "drive",
                "drive_id": "drive-001",
            },
        }
    )


def _page() -> MicrosoftSharePointDeltaPageV1:
    return MicrosoftSharePointDeltaPageV1(
        scope="drive",
        records=(
            MicrosoftSharePointDeltaRecordV1(
                source_record_id="drive:item-001:" + "b" * 32,
                object_id="item-001",
                scope="drive",
                deleted=False,
                source_modified_at_utc=NOW,
                metadata={
                    "name": "report.docx",
                    "etag": "etag-version-002",
                    "ctag": "ctag-version-002",
                    "size": 1234,
                    "parent": {"id": "folder-001", "drive_id": "drive-001"},
                    "file": {
                        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "hashes": {"quick_xor_hash": "source-fingerprint-002"},
                    },
                },
            ),
        ),
        checkpoint_url=NEXT_CHECKPOINT,
        cycle_complete=True,
    )


def _adapter(client: FixturePageClient) -> MicrosoftSharePointDeltaAdapter:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: MicrosoftSharePointDeltaRequestProfile,
        material: bytes,
        timeout: float,
        maximum: int,
    ) -> FixturePageClient:
        assert profile.resource_path == "/v1.0/drives/drive-001/root/delta"
        assert material == b"fixture-sharepoint-token"
        return client

    return MicrosoftSharePointDeltaAdapter(
        registry.get_definition(SHAREPOINT_CONNECTOR_ID),
        FixtureCredentialResolver(),
        {PROFILE_ID: _tenant()},
        client_factory=factory,
    )


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="sharepoint-authoritative",
        source_system=SHAREPOINT_CONNECTOR_ID,
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id=SHAREPOINT_CONNECTOR_ID,
        adapter_version="1.0",
        event_type="microsoft.sharepoint.metadata.observed",
        classification="internal",
        redaction_profile="sharepoint-metadata-redaction-v1",
        minimization_profile="sharepoint-metadata-only-v1",
        clock_quality="unknown",
    )


def _service(
    tmp_path: Path,
    client: FixturePageClient,
) -> tuple[GatewayMicrosoftSharePointRecollectionService, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = SyncQueue(tmp_path / "sharepoint-notification-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    runner = GatewayConnectorCollectionRunner(ingress)
    service = GatewayMicrosoftSharePointRecollectionService(
        runner,
        adapter=_adapter(client),
        instance=_instance(),
        principal=PRINCIPAL,
        subscription=_subscription(),
        profile=_profile(),
    )
    return service, event_log, sync_queue


def test_notification_recollection_commits_delta_evidence_with_trigger_correlation(
    tmp_path: Path,
) -> None:
    client = FixturePageClient(_page())
    service, event_log, sync_queue = _service(tmp_path, client)

    result = service.commit(_notification(), _checkpoint())

    assert result.directive.reason == "resource_notification"
    assert result.directive.resume_checkpoint == _checkpoint()
    assert client.request_urls == [CHECKPOINT]
    assert result.run.code == "ok"
    assert result.run.checkpoint_to_persist is not None
    assert result.run.checkpoint_to_persist.cursor == NEXT_CHECKPOINT
    assert sync_queue.status().queue_depth == 1

    entries = event_log.list_entries()
    assert len(entries) == 1
    event = entries[0].event
    assert event.correlation_id == NOTIFICATION_ID
    assert event.tenant_id == "tenant-authoritative"
    assert event.workspace_id == "workspace-authoritative"

    committed = event.metadata["capture_metadata"]["committed_connector_metadata"]
    assert committed["metadata"]["etag"] == "etag-version-002"
    assert committed["metadata"]["ctag"] == "ctag-version-002"
    assert committed["metadata"]["file"]["hashes"]["quick_xor_hash"] == (
        "source-fingerprint-002"
    )

    serialized = json.dumps(event.model_dump(mode="json"), sort_keys=True)
    assert SUBSCRIPTION_ID not in serialized
    assert TENANT_ID not in serialized
    assert "drives/drive-001/items/item-001" not in serialized


def test_duplicate_notification_recollection_reuses_one_immutable_event(tmp_path: Path) -> None:
    client = FixturePageClient(_page())
    service, event_log, sync_queue = _service(tmp_path, client)

    first = service.commit(_notification(), _checkpoint())
    retry = service.commit(_notification(), _checkpoint())

    assert first.run.code == "ok"
    assert retry.run.code == "ok"
    assert client.request_urls == [CHECKPOINT, CHECKPOINT]
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_unapproved_notification_tenant_fails_before_delta_recollection_or_commit(
    tmp_path: Path,
) -> None:
    client = FixturePageClient(_page())
    service, event_log, sync_queue = _service(tmp_path, client)

    with pytest.raises(MicrosoftSharePointNotificationError):
        service.commit(_notification(tenant_id=OTHER_TENANT_ID), _checkpoint())

    assert client.request_urls == []
    assert event_log.list_entries() == []
    assert sync_queue.status().queue_depth == 0
