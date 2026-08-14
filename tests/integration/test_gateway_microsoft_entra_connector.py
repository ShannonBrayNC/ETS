from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets.connectors.credentials.broker import CredentialBroker
from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_entra_connector import (
    ENTRA_CONNECTOR_ID,
    MicrosoftEntraDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_entra_delta import (
    MicrosoftEntraDeltaPageV1,
    entra_delta_request_profile,
    parse_entra_delta_page,
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

NOW = datetime(2026, 8, 14, 15, 30, tzinfo=UTC)
PRINCIPAL = "spiffe://example.test/workload/microsoft-entra"
PROFILE_ID = "entra-prod"
CREDENTIAL_REF = "fixture://microsoft/entra-directory"
RAW_MARKER = "RAW-ENTRA-GATEWAY-MARKER"


class FixtureCredentialProvider:
    scheme = "fixture"

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
        return CredentialLease(b"fixture-entra-token", self.describe(reference))


class OnePageEntraClient:
    def __init__(self, page: MicrosoftEntraDeltaPageV1) -> None:
        self.page = page
        self.closed = False

    def fetch(self, request_url: str | None = None) -> MicrosoftEntraDeltaPageV1:
        return self.page

    def close(self) -> None:
        self.closed = True


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated post-append enqueue failure")
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
            "instance_id": "entra-directory-prod",
            "connector_id": ENTRA_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="source-claim",
                workspace_id="source-workspace",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="entra-directory",
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
                capture_profile="capture.microsoft.entra.delta.v1",
                normalization_profile="normalize.microsoft.entra.delta.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "collection": "users",
            },
        }
    )


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="entra-directory-authoritative",
        source_system=ENTRA_CONNECTOR_ID,
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id=ENTRA_CONNECTOR_ID,
        adapter_version="1.0",
        event_type="microsoft.entra.directory_change.observed",
        classification="internal",
        redaction_profile="microsoft-entra-redaction-v1",
        minimization_profile="microsoft-entra-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="unknown",
    )


def _page(marker: str = RAW_MARKER) -> MicrosoftEntraDeltaPageV1:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    next_link = profile.initial_url + "?$skiptoken=opaque-next-state"
    payload = json.dumps(
        {
            "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
            "@odata.nextLink": next_link,
            "value": [
                {
                    "id": "user-001",
                    "accountEnabled": True,
                    "userType": "Member",
                    "displayName": marker,
                    "userPrincipalName": "alice@example.test",
                    "mail": "alice@example.test",
                    "raw_marker": marker,
                }
            ],
        }
    ).encode("utf-8")
    return parse_entra_delta_page(
        payload,
        profile=profile,
        request_url=profile.initial_url,
    )


def _adapter(page: MicrosoftEntraDeltaPageV1) -> MicrosoftEntraDeltaAdapter:
    registry = ConnectorRegistry.from_manifest_directory(Path("config/connectors/enterprise"))
    broker = CredentialBroker()
    broker.register(FixtureCredentialProvider())
    client = OnePageEntraClient(page)

    def factory(_profile, material: bytes, timeout: float, maximum: int):
        assert material == b"fixture-entra-token"
        assert timeout == 30.0
        assert maximum == 2 * 1024 * 1024
        return client

    return MicrosoftEntraDeltaAdapter(
        registry.get_definition(ENTRA_CONNECTOR_ID),
        broker,
        {PROFILE_ID: _tenant_profile()},
        client_factory=factory,
    )


def _runner(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
) -> tuple[GatewayConnectorCollectionRunner, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "connector-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return GatewayConnectorCollectionRunner(ingress), event_log, sync_queue


def test_entra_page_commits_before_source_cursor_is_released(tmp_path: Path) -> None:
    runner, event_log, sync_queue = _runner(tmp_path)
    page = _page()

    result = runner.run(
        adapter=_adapter(page),
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert result.code == "ok"
    assert result.committed_local == 1
    assert result.sync_queued == 1
    assert result.checkpoint_to_persist is not None
    assert result.checkpoint_to_persist.cursor == page.checkpoint_url
    entries = event_log.list_entries()
    assert len(entries) == 1
    assert entries[0].event.tenant_id == "tenant-authoritative"
    assert entries[0].event.workspace_id == "workspace-authoritative"
    event_dump = json.dumps(entries[0].event.model_dump(mode="json"))
    assert RAW_MARKER not in event_dump
    assert "alice@example.test" not in event_dump
    assert "source-claim" not in event_dump
    assert CREDENTIAL_REF not in event_dump
    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert RAW_MARKER not in json.dumps(queued[0].payload)


def test_entra_backpressure_withholds_cursor_and_local_append(tmp_path: Path) -> None:
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
    assert event_log.list_entries() == []


def test_entra_partial_commit_withholds_cursor_then_idempotent_retry_recovers(
    tmp_path: Path,
) -> None:
    queue = FailOnceQueue(tmp_path / "race.db")
    runner, event_log, sync_queue = _runner(tmp_path, queue=queue)
    adapter = _adapter(_page())

    first = runner.run(
        adapter=adapter,
        instance=_instance(),
        principal=PRINCIPAL,
        checkpoint=None,
    )
    retry = runner.run(
        adapter=adapter,
        instance=_instance(),
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
