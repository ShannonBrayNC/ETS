from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
)
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewContentDescriptorV1,
    MicrosoftPurviewDiscoveryPageV1,
    MicrosoftPurviewManagementProfile,
    PurviewContentType,
    purview_management_profile,
)
from ets.connectors.enterprise.microsoft_purview_audit import (
    MicrosoftPurviewAuditContentV1,
    MicrosoftPurviewAuditRecordV1,
)
from ets.connectors.enterprise.microsoft_purview_connector import (
    MicrosoftPurviewActivityAdapter,
    MicrosoftPurviewConnectorSettings,
)
from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
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
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

NOW = datetime(2026, 8, 14, 21, 30, tzinfo=UTC)
EVENT_TIME = NOW - timedelta(minutes=2)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PUBLISHER_ID = "33333333-3333-3333-3333-333333333333"
RECORD_ID = "44444444-4444-4444-4444-444444444444"
PROFILE_ID = "purview-prod"
CREDENTIAL_REF = "fixture://microsoft/purview"
PRINCIPAL = "spiffe://example.test/workload/purview"
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
        return CredentialLease(b"fixture-purview-token", self.describe(reference))


class FixtureProfileResolver:
    def __init__(self, profile: MicrosoftPurviewManagementProfile) -> None:
        self.profile = profile

    def resolve(self, profile_id: str) -> MicrosoftPurviewManagementProfile:
        if profile_id != PROFILE_ID:
            raise ValueError("unknown Purview profile")
        return self.profile


class FixtureClient:
    def __init__(self, *, operation: str = "FileAccessed") -> None:
        self.operation = operation

    def list_content(
        self,
        content_type: PurviewContentType,
        *,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        next_page_uri: str | None = None,
    ) -> MicrosoftPurviewDiscoveryPageV1:
        assert content_type == "Audit.General"
        assert next_page_uri is None
        assert start_time_utc is not None
        assert end_time_utc == NOW
        return MicrosoftPurviewDiscoveryPageV1(
            content_type="Audit.General",
            descriptors=(_descriptor(),),
            next_page_uri=None,
            discovery_source="poll",
        )

    def retrieve_content(
        self,
        descriptor: MicrosoftPurviewContentDescriptorV1,
        *,
        service_specific_allowlist: frozenset[str] = frozenset(),
        include_client_ip: bool = False,
    ) -> MicrosoftPurviewAuditContentV1:
        assert service_specific_allowlist == frozenset({"SiteUrl"})
        assert include_client_ip is False
        return _content(operation=self.operation)

    def close(self) -> None:
        return None


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated Purview post-append enqueue failure")
        return super().enqueue(payload)


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": "global",
            "credential_ref": {
                "schema_version": "ets.connector.credential_ref.v1",
                "ref": CREDENTIAL_REF,
            },
            "consent_state": "granted",
        }
    )


def _profile() -> MicrosoftPurviewManagementProfile:
    return purview_management_profile(
        PROFILE_ID,
        _tenant(),
        plan="enterprise",
        publisher_identifier=PUBLISHER_ID,
    )


def _descriptor() -> MicrosoftPurviewContentDescriptorV1:
    return MicrosoftPurviewContentDescriptorV1(
        content_type="Audit.General",
        content_id="content-001",
        content_uri=(
            f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/"
            "audit/content-001"
        ),
        content_created_utc=NOW - timedelta(minutes=5),
        content_expiration_utc=NOW + timedelta(days=7),
        discovery_source="poll",
    )


def _content(*, operation: str) -> MicrosoftPurviewAuditContentV1:
    descriptor = _descriptor()
    record = MicrosoftPurviewAuditRecordV1(
        source_record_id=RECORD_ID,
        record_type=1,
        creation_time_utc=EVENT_TIME,
        operation=operation,
        organization_id=TENANT_ID,
        user_type=0,
        user_key="user-key-001",
        workload="SharePoint",
        user_id="alice@example.test",
        result_status="Succeeded",
        object_id="https://contoso.sharepoint.com/sites/a/report.docx",
        client_ip=None,
        scope=0,
        version=1,
        content_type="Audit.General",
        content_id="content-001",
        service_specific={"SiteUrl": "https://contoso.sharepoint.com/sites/a"},
    )
    return MicrosoftPurviewAuditContentV1(
        content_type="Audit.General",
        content_id=descriptor.content_id,
        content_sha256="a" * 64,
        content_created_utc=descriptor.content_created_utc,
        content_expiration_utc=descriptor.content_expiration_utc,
        records=(record,),
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "purview-prod",
            "connector_id": "microsoft.purview.activity",
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="instance-tenant-must-not-authorize",
                workspace_id="instance-workspace-must-not-authorize",
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
                "management_profile_id": PROFILE_ID,
                "content_type": "Audit.General",
                "service_specific_allowlist": ["SiteUrl"],
                "poll_window_seconds": 3600,
                "overlap_seconds": 300,
            },
        }
    )


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="purview-authoritative",
        source_system="microsoft.purview.activity",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id="microsoft.purview.activity",
        adapter_version="1.0",
        event_type="microsoft.purview.audit.observed",
        classification="internal",
        redaction_profile="purview-redaction-v1",
        minimization_profile="purview-common-schema-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="unknown",
    )


def _adapter(*, operation: str = "FileAccessed") -> MicrosoftPurviewActivityAdapter:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: MicrosoftPurviewManagementProfile,
        material: bytes,
        settings: MicrosoftPurviewConnectorSettings,
    ) -> FixtureClient:
        assert profile.profile_id == PROFILE_ID
        assert material == b"fixture-purview-token"
        assert settings.content_type == "Audit.General"
        return FixtureClient(operation=operation)

    return MicrosoftPurviewActivityAdapter(
        registry.get_definition("microsoft.purview.activity"),
        FixtureProfileResolver(_profile()),
        FixtureCredentialResolver(),
        client_factory=factory,
        now=lambda: NOW,
    )


def _runner(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
) -> tuple[GatewayConnectorCollectionRunner, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "purview-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return GatewayConnectorCollectionRunner(ingress), event_log, sync_queue


def test_purview_gateway_commits_before_releasing_checkpoint(tmp_path: Path) -> None:
    runner, event_log, sync_queue = _runner(tmp_path)

    result = runner.run(
        adapter=_adapter(),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "ok"
    assert result.committed_local == 1
    assert result.sync_queued == 1
    assert result.checkpoint_to_persist is not None
    assert result.checkpoint_to_persist.observed_through_utc == NOW

    event = event_log.list_entries()[0].event
    assert event.tenant_id == "tenant-authoritative"
    assert event.workspace_id == "workspace-authoritative"
    assert event.metadata["observed_at_utc"] == EVENT_TIME.isoformat().replace("+00:00", "Z")
    assert event.created_at_utc == NOW
    serialized_event = json.dumps(event.model_dump(mode="json"), sort_keys=True)
    assert "instance-tenant-must-not-authorize" not in serialized_event
    assert "fixture-purview-token" not in serialized_event

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    serialized_queue = json.dumps(queued[0].payload, sort_keys=True)
    assert "fixture-purview-token" not in serialized_queue


def test_purview_precommit_backpressure_withholds_checkpoint_and_append(
    tmp_path: Path,
) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    runner, event_log, _ = _runner(tmp_path, queue=queue)

    result = runner.run(
        adapter=_adapter(),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "retryable_error"
    assert result.checkpoint_to_persist is None
    assert result.committed_local == 0
    assert result.sync_queued == 0
    assert event_log.list_entries() == []


def test_purview_partial_commit_withholds_checkpoint_and_retry_recovers(
    tmp_path: Path,
) -> None:
    queue = FailOnceQueue(tmp_path / "partial.db")
    runner, event_log, sync_queue = _runner(tmp_path, queue=queue)
    adapter = _adapter()
    instance = _instance()

    first = runner.run(
        adapter=adapter,
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )
    retry = runner.run(
        adapter=adapter,
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert first.code == "retryable_error"
    assert first.partial_commit == 1
    assert first.checkpoint_to_persist is None
    assert retry.code == "ok"
    assert retry.checkpoint_to_persist is not None
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_purview_immutable_conflict_withholds_checkpoint(tmp_path: Path) -> None:
    runner, event_log, sync_queue = _runner(tmp_path)
    instance = _instance()

    first = runner.run(
        adapter=_adapter(operation="FileAccessed"),
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )
    conflict = runner.run(
        adapter=_adapter(operation="FileDeleted"),
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert first.code == "ok"
    assert conflict.code == "terminal_error"
    assert conflict.checkpoint_to_persist is None
    assert conflict.committed_local == 0
    assert conflict.sync_queued == 0
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
