from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_connector import (
    SHAREPOINT_CONNECTOR_ID,
    MicrosoftSharePointDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRecordV1,
    MicrosoftSharePointDeltaRequestProfile,
)
from ets.connectors.enterprise.microsoft_sharepoint_state import (
    SharePointMetadataStateStore,
    snapshot_sharepoint_metadata_record,
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
from ets.gateway.microsoft_sharepoint_state_release import SharePointMetadataStateReleaseHook
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

SOURCE_TIME = datetime(2026, 8, 14, 20, 30, tzinfo=UTC)
RECEIPT_TIME = datetime(2026, 8, 14, 20, 31, tzinfo=UTC)
MANIFESTS = Path("config/connectors/enterprise")
PROFILE_ID = "sharepoint-prod"
CREDENTIAL_REF = "fixture://microsoft/sharepoint"
PRINCIPAL = "spiffe://example.test/workload/microsoft-sharepoint"
SOURCE_KEY = "tenant-authoritative/workspace-authoritative/sharepoint-authoritative"
CHECKPOINT = "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$skiptoken=next"


class FixtureCredentialResolver:
    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status="available",
            version="1",
            updated_at_utc=RECEIPT_TIME,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        return CredentialLease(b"fixture-sharepoint-token", self.describe(reference))


class FixtureClient:
    def __init__(self, page: MicrosoftSharePointDeltaPageV1) -> None:
        self._page = page

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        return self._page

    def close(self) -> None:
        return None


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated append-before-enqueue failure")
        return super().enqueue(payload)


def _tenant_profile() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "application_id": "22222222-2222-2222-2222-222222222222",
            "cloud": "global",
            "credential_ref": {
                "schema_version": "ets.connector.credential_ref.v1",
                "ref": CREDENTIAL_REF,
            },
            "consent_state": "granted",
        }
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "sharepoint-metadata-prod",
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


def _page(
    *,
    object_id: str = "item-001",
    name: str = "report.docx",
    cycle_complete: bool = False,
) -> MicrosoftSharePointDeltaPageV1:
    return MicrosoftSharePointDeltaPageV1(
        scope="drive",
        records=(
            MicrosoftSharePointDeltaRecordV1(
                source_record_id=f"drive:{object_id}:{name}",
                object_id=object_id,
                scope="drive",
                deleted=False,
                source_modified_at_utc=SOURCE_TIME,
                metadata={
                    "name": name,
                    "size": 1234,
                    "parent": {"id": "folder-001", "drive_id": "drive-001"},
                },
            ),
        ),
        checkpoint_url=CHECKPOINT,
        cycle_complete=cycle_complete,
    )


def _adapter(page: MicrosoftSharePointDeltaPageV1) -> MicrosoftSharePointDeltaAdapter:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: MicrosoftSharePointDeltaRequestProfile,
        material: bytes,
        timeout: float,
        maximum: int,
    ) -> FixtureClient:
        assert profile.scope == "drive"
        assert material == b"fixture-sharepoint-token"
        return FixtureClient(page)

    return MicrosoftSharePointDeltaAdapter(
        registry.get_definition(SHAREPOINT_CONNECTOR_ID),
        FixtureCredentialResolver(),
        {PROFILE_ID: _tenant_profile()},
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


def _runner(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
) -> tuple[GatewayConnectorCollectionRunner, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "sharepoint-state-release-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: RECEIPT_TIME,
    )
    return GatewayConnectorCollectionRunner(ingress), event_log, sync_queue


def _record_mapping(page: MicrosoftSharePointDeltaPageV1) -> dict[str, object]:
    record = page.records[0]
    return {
        "source_record_id": record.source_record_id,
        "object_id": record.object_id,
        "scope": record.scope,
        "deleted": record.deleted,
        "source_modified_at_utc": "2026-08-14T20:30:00Z",
        "metadata": record.metadata,
    }


def test_state_releases_only_after_local_commit_and_durable_sync(tmp_path: Path) -> None:
    page = _page(cycle_complete=True)
    store = SharePointMetadataStateStore(tmp_path / "state.db")
    hook = SharePointMetadataStateReleaseHook(store, source_key=SOURCE_KEY)
    runner, event_log, sync_queue = _runner(tmp_path)

    result = runner.run(
        adapter=_adapter(page),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
        release_hook=hook,
    )

    assert result.code == "ok"
    assert result.checkpoint_to_persist is not None
    assert result.committed_local == 1
    assert result.sync_queued == 1
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
    assert store.get(SOURCE_KEY, "drive", "item-001") is not None
    assert store.baseline_complete(SOURCE_KEY) is True


def test_precommit_backpressure_does_not_advance_sharepoint_state(tmp_path: Path) -> None:
    page = _page(cycle_complete=True)
    store = SharePointMetadataStateStore(tmp_path / "state.db")
    hook = SharePointMetadataStateReleaseHook(store, source_key=SOURCE_KEY)
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    runner, event_log, _ = _runner(tmp_path, queue=queue)

    result = runner.run(
        adapter=_adapter(page),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
        release_hook=hook,
    )

    assert result.code == "retryable_error"
    assert result.checkpoint_to_persist is None
    assert event_log.list_entries() == []
    assert store.get(SOURCE_KEY, "drive", "item-001") is None
    assert store.baseline_complete(SOURCE_KEY) is False


def test_partial_commit_retry_releases_state_only_after_sync_repair(tmp_path: Path) -> None:
    page = _page(cycle_complete=True)
    store = SharePointMetadataStateStore(tmp_path / "state.db")
    hook = SharePointMetadataStateReleaseHook(store, source_key=SOURCE_KEY)
    queue = FailOnceQueue(tmp_path / "partial.db")
    runner, event_log, sync_queue = _runner(tmp_path, queue=queue)
    adapter = _adapter(page)
    instance = _instance()

    first = runner.run(
        adapter=adapter,
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
        release_hook=hook,
    )

    assert first.code == "retryable_error"
    assert first.partial_commit == 1
    assert first.checkpoint_to_persist is None
    assert store.get(SOURCE_KEY, "drive", "item-001") is None
    assert store.baseline_complete(SOURCE_KEY) is False

    retry = runner.run(
        adapter=adapter,
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
        release_hook=hook,
    )

    assert retry.code == "ok"
    assert retry.checkpoint_to_persist is not None
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
    assert store.get(SOURCE_KEY, "drive", "item-001") is not None
    assert store.baseline_complete(SOURCE_KEY) is True


def test_state_release_failure_withholds_checkpoint_after_evidence_is_queued(
    tmp_path: Path,
) -> None:
    store = SharePointMetadataStateStore(tmp_path / "state.db", max_items=1)
    existing_page = _page(object_id="item-existing", cycle_complete=True)
    store.apply(
        SOURCE_KEY,
        [snapshot_sharepoint_metadata_record(_record_mapping(existing_page))],
        mark_baseline_complete=True,
    )
    hook = SharePointMetadataStateReleaseHook(store, source_key=SOURCE_KEY)
    runner, event_log, sync_queue = _runner(tmp_path)

    result = runner.run(
        adapter=_adapter(_page(object_id="item-new", cycle_complete=True)),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
        release_hook=hook,
    )

    assert result.code == "retryable_error"
    assert result.committed_local == 1
    assert result.sync_queued == 1
    assert result.checkpoint_to_persist is None
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
    assert store.get(SOURCE_KEY, "drive", "item-existing") is not None
    assert store.get(SOURCE_KEY, "drive", "item-new") is None
