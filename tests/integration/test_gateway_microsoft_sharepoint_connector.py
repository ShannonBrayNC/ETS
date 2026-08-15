from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
)
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

SOURCE_TIME = datetime(2026, 8, 14, 20, 30, tzinfo=UTC)
RECEIPT_TIME = datetime(2026, 8, 14, 20, 31, tzinfo=UTC)
MANIFESTS = Path("config/connectors/enterprise")
PROFILE_ID = "sharepoint-prod"
CREDENTIAL_REF = "fixture://microsoft/sharepoint"
PRINCIPAL = "spiffe://example.test/workload/microsoft-sharepoint"
CHECKPOINT = "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$skiptoken=next"
RAW_MARKER = "RAW-FILE-CONTENT-MUST-NEVER-COMMIT"


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
        pass


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


def _page(*, changed: bool = False) -> MicrosoftSharePointDeltaPageV1:
    metadata: dict[str, object] = {
        "name": "report-renamed.docx" if changed else "report.docx",
        "size": 1234,
        "parent": {"id": "folder-001", "drive_id": "drive-001"},
    }
    state = "changed" if changed else "initial"
    record = MicrosoftSharePointDeltaRecordV1(
        source_record_id=f"drive:item-001:{state}",
        object_id="item-001",
        scope="drive",
        deleted=False,
        source_modified_at_utc=SOURCE_TIME,
        metadata=metadata,
    )
    return MicrosoftSharePointDeltaPageV1(
        scope="drive",
        records=(record,),
        checkpoint_url=CHECKPOINT,
        cycle_complete=False,
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
    sync_queue = queue or SyncQueue(tmp_path / "sharepoint-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: RECEIPT_TIME,
    )
    return GatewayConnectorCollectionRunner(ingress), event_log, sync_queue


def test_sharepoint_gateway_commits_metadata_before_releasing_cursor(tmp_path: Path) -> None:
    runner, event_log, sync_queue = _runner(tmp_path)

    result = runner.run(
        adapter=_adapter(_page()),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "ok"
    assert result.committed_local == 1
    assert result.sync_queued == 1
    assert result.checkpoint_to_persist is not None
    assert result.checkpoint_to_persist.cursor == CHECKPOINT

    entries = event_log.list_entries()
    assert len(entries) == 1
    event = entries[0].event
    assert event.tenant_id == "tenant-authoritative"
    assert event.workspace_id == "workspace-authoritative"
    assert event.created_at_utc == RECEIPT_TIME
    assert event.metadata["observed_at_utc"] == SOURCE_TIME.isoformat().replace("+00:00", "Z")

    serialized = json.dumps(event.model_dump(mode="json"), sort_keys=True)
    assert "instance-tenant-must-not-authorize" not in serialized
    assert "instance-workspace-must-not-authorize" not in serialized
    assert CREDENTIAL_REF not in serialized
    assert RAW_MARKER not in serialized
    assert "downloadUrl" not in serialized

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert RAW_MARKER not in json.dumps(queued[0].payload, sort_keys=True)


def test_sharepoint_precommit_backpressure_withholds_cursor_and_append(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    runner, event_log, _ = _runner(tmp_path, queue=queue)

    result = runner.run(
        adapter=_adapter(_page()),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "retryable_error"
    assert result.checkpoint_to_persist is None
    assert result.committed_local == 0
    assert result.sync_queued == 0
    assert event_log.list_entries() == []


def test_sharepoint_partial_commit_retry_repairs_sync_before_cursor_release(tmp_path: Path) -> None:
    queue = FailOnceQueue(tmp_path / "partial.db")
    runner, event_log, sync_queue = _runner(tmp_path, queue=queue)
    adapter = _adapter(_page())
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
    assert retry.checkpoint_to_persist.cursor == CHECKPOINT
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_sharepoint_repeated_same_state_is_idempotent_but_changed_state_is_new_observation(
    tmp_path: Path,
) -> None:
    runner, event_log, sync_queue = _runner(tmp_path)
    instance = _instance()

    first = runner.run(
        adapter=_adapter(_page()),
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )
    duplicate = runner.run(
        adapter=_adapter(_page()),
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )
    changed = runner.run(
        adapter=_adapter(_page(changed=True)),
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert first.code == "ok"
    assert duplicate.code == "ok"
    assert changed.code == "ok"
    assert len(event_log.list_entries()) == 2
    assert sync_queue.status().queue_depth == 2
