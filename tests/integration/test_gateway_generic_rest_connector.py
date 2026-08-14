from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets.connectors.generic.extraction import GenericRestAdapter
from ets.connectors.generic.rest import (
    GenericRestHostPolicy,
    GenericRestRequestProfile,
    GenericRestResponse,
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

NOW = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)
PRINCIPAL = "spiffe://example.test/workload/generic-rest"
RAW_MARKER = "RAW-GENERIC-REST-GATEWAY-MARKER"
SOURCE_CURSOR = "opaque-source-cursor-2"
MANIFESTS = Path("config/connectors/enterprise")


class FixtureClient:
    def __init__(self, response: GenericRestResponse) -> None:
        self._response = response
        self.closed = False

    def get(self) -> GenericRestResponse:
        return self._response

    def close(self) -> None:
        self.closed = True


class FixtureClientFactory:
    def __init__(self, response: GenericRestResponse) -> None:
        self._response = response
        self.profiles: list[GenericRestRequestProfile] = []

    def __call__(
        self,
        profile: GenericRestRequestProfile,
        host_policy: GenericRestHostPolicy,
        credential_material: bytes | None,
    ) -> FixtureClient:
        assert credential_material is None
        host_policy.authorize(profile.endpoint_url)
        self.profiles.append(profile)
        return FixtureClient(self._response)


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated post-append enqueue failure")
        return super().enqueue(payload)


def _response(*, status: str = "succeeded") -> GenericRestResponse:
    payload = {
        "data": {
            "items": [
                {
                    "id": "source-event-001",
                    "observedAt": "2026-08-14T16:59:30Z",
                    "kind": "deployment",
                    "status": status,
                    "raw": RAW_MARKER,
                    "tenant_id": "payload-tenant-must-not-route",
                    "workspace_id": "payload-workspace-must-not-route",
                }
            ],
            "next": SOURCE_CURSOR,
            "hasMore": True,
        },
        "rawEnvelope": RAW_MARKER,
        "tenant_id": "foreign-envelope-tenant",
        "workspace_id": "foreign-envelope-workspace",
    }
    return GenericRestResponse(
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        etag=None,
        last_modified=None,
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "generic-rest-prod",
            "connector_id": "generic.rest",
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="instance-tenant-must-not-authorize",
                workspace_id="instance-workspace-must-not-authorize",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="approved-rest-api",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="none",
                credential_ref=None,
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
                capture_profile="capture.generic-rest.v1",
                normalization_profile="normalize.generic-rest.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "endpoint_url": "https://api.example.test/events",
                "records_path": "/data/items",
                "source_record_id_path": "/id",
                "observed_at_path": "/observedAt",
                "evidence_fields": {
                    "kind": "/kind",
                    "status": "/status",
                },
                "event_type": "generic.rest.fixture.observed",
                "checkpoint_cursor_path": "/data/next",
                "has_more_path": "/data/hasMore",
                "cursor_query_parameter": "after",
                "request_timeout_seconds": 5,
                "max_response_bytes": 65536,
            },
        }
    )


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="generic-rest-authoritative",
        source_system="generic.rest",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id="generic.rest",
        adapter_version="1.0",
        event_type="generic.rest.fixture.observed",
        classification="internal",
        redaction_profile="generic-rest-redaction-v1",
        minimization_profile="generic-rest-selected-fields-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="unknown",
    )


def _adapter(response: GenericRestResponse | None = None) -> GenericRestAdapter:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    factory = FixtureClientFactory(response or _response())
    return GenericRestAdapter(
        registry.get_definition("generic.rest"),
        GenericRestHostPolicy(frozenset({"api.example.test"})),
        client_factory=factory,
    )


def _runner(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
) -> tuple[GatewayConnectorCollectionRunner, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "generic-rest-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return GatewayConnectorCollectionRunner(ingress), event_log, sync_queue


def test_generic_rest_gateway_commits_before_releasing_source_cursor(
    tmp_path: Path,
) -> None:
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
    assert result.checkpoint_to_persist.cursor == SOURCE_CURSOR
    assert result.has_more is True

    entries = event_log.list_entries()
    assert len(entries) == 1
    event = entries[0].event
    assert event.tenant_id == "tenant-authoritative"
    assert event.workspace_id == "workspace-authoritative"
    serialized_event = json.dumps(event.model_dump(mode="json"), sort_keys=True)
    assert RAW_MARKER not in serialized_event
    assert "payload-tenant-must-not-route" not in serialized_event
    assert "instance-tenant-must-not-authorize" not in serialized_event

    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    serialized_queue = json.dumps(queued[0].payload, sort_keys=True)
    assert RAW_MARKER not in serialized_queue
    assert "foreign-envelope-tenant" not in serialized_queue


def test_generic_rest_precommit_backpressure_withholds_cursor_and_append(
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


def test_generic_rest_partial_commit_withholds_cursor_and_retry_recovers(
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
    assert retry.checkpoint_to_persist.cursor == SOURCE_CURSOR
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_generic_rest_conflict_withholds_cursor_and_preserves_original_evidence(
    tmp_path: Path,
) -> None:
    runner, event_log, sync_queue = _runner(tmp_path)
    instance = _instance()

    first = runner.run(
        adapter=_adapter(_response(status="succeeded")),
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )
    conflict = runner.run(
        adapter=_adapter(_response(status="failed")),
        instance=instance,
        principal=PRINCIPAL,
        checkpoint=None,
    )

    assert first.code == "ok"
    assert first.checkpoint_to_persist is not None
    assert conflict.code == "terminal_error"
    assert conflict.committed_local == 0
    assert conflict.sync_queued == 0
    assert conflict.checkpoint_to_persist is None
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
