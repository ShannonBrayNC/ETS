from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ets.connectors.enterprise.kubernetes import KubernetesAuditAdapter
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
from ets.gateway.kubernetes_audit import (
    GatewayKubernetesAuditBatchError,
    GatewayKubernetesAuditIngressService,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

NOW = datetime(2026, 8, 14, 5, 10, tzinfo=UTC)
PRINCIPAL = "spiffe://example.test/workload/kubernetes-audit"


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated post-append enqueue failure")
        return super().enqueue(payload)


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id="kubernetes-audit-prod",
        connector_id="kubernetes.audit",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="source-claim", workspace_id="source-workspace"),
        source=ConnectorSource(name="kubernetes-audit", environment="test"),
        authentication=ConnectorAuthentication(
            method="mtls",
            credential_ref="fixture://kubernetes-audit-tls",
        ),
        collection=ConnectorCollection(mode="push", batch_size=100),
        checkpoint=ConnectorCheckpointPolicy(strategy="none", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.kubernetes.audit.v1",
            normalization_profile="normalize.kubernetes.audit.v1",
        ),
        retry=ConnectorRetryPolicy(),
        gap_detection=ConnectorGapPolicy(),
        settings={"cluster_id": "cluster-prod-a"},
    )


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="kubernetes-audit-authoritative",
        source_system="kubernetes.audit",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id="kubernetes.audit",
        adapter_version="1.0",
        event_type="kubernetes.audit.observed",
        classification="internal",
        redaction_profile="kubernetes-audit-redaction-v1",
        minimization_profile="kubernetes-audit-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="synchronized",
    )


def _raw_event(
    *,
    audit_id: str,
    stage: str = "ResponseComplete",
    marker: str = "raw-source-marker",
) -> dict[str, Any]:
    return {
        "apiVersion": "audit.k8s.io/v1",
        "kind": "Event",
        "level": "RequestResponse",
        "auditID": audit_id,
        "stage": stage,
        "requestURI": "/api/v1/namespaces/default/configmaps/example?token=sensitive",
        "verb": "get",
        "user": {"username": "alice@example.test", "uid": "user-001"},
        "sourceIPs": ["192.0.2.10"],
        "userAgent": "kubectl/fixture",
        "objectRef": {
            "resource": "configmaps",
            "namespace": "default",
            "name": "example",
            "apiVersion": "v1",
        },
        "responseStatus": {"status": "Success", "code": 200},
        "requestReceivedTimestamp": "2026-08-14T05:09:59.000000Z",
        "stageTimestamp": "2026-08-14T05:10:00.000000Z",
        "annotations": {"raw.example/marker": marker},
        "requestObject": {"data": {"secret": marker}},
        "responseObject": {"data": {"secret": marker}},
    }


def _body(*events: dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "apiVersion": "audit.k8s.io/v1",
            "kind": "EventList",
            "items": list(events),
        }
    ).encode("utf-8")


def _service(
    tmp_path: Path,
    *,
    queue: SyncQueue | None = None,
) -> tuple[GatewayKubernetesAuditIngressService, InMemoryAppendOnlyLog, SyncQueue]:
    registry = ConnectorRegistry.from_manifest_directory(Path("config/connectors/enterprise"))
    adapter = KubernetesAuditAdapter(registry.get_definition("kubernetes.audit"))
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "connector-sync.db")
    ingress = GatewayConnectorIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return (
        GatewayKubernetesAuditIngressService(adapter=adapter, ingress=ingress),
        event_log,
        sync_queue,
    )


def test_kubernetes_batch_commits_in_order_under_authoritative_scope(tmp_path: Path) -> None:
    marker = "RAW-KUBERNETES-GATEWAY-MARKER"
    service, event_log, sync_queue = _service(tmp_path)

    result = service.ingest(
        principal=PRINCIPAL,
        instance=_instance(),
        body=_body(
            _raw_event(audit_id="audit-1", marker=marker),
            _raw_event(audit_id="audit-2", marker=marker),
        ),
        received_at_utc=NOW,
    )

    assert result.decoded_events == 2
    assert result.committed_local == 2
    assert result.sync_queued == 2
    assert result.duplicates == 0
    entries = event_log.list_entries()
    assert len(entries) == 2
    assert all(entry.event.tenant_id == "tenant-authoritative" for entry in entries)
    assert all(entry.event.workspace_id == "workspace-authoritative" for entry in entries)
    event_dump = json.dumps([entry.event.model_dump(mode="json") for entry in entries])
    assert marker not in event_dump
    assert "source-claim" not in event_dump
    assert "alice@example.test" not in event_dump
    assert "192.0.2.10" not in event_dump
    assert "token=sensitive" not in event_dump
    queued = sync_queue.claim_batch(10)
    assert len(queued) == 2
    assert marker not in json.dumps([record.payload for record in queued])


def test_kubernetes_batch_retry_is_idempotent(tmp_path: Path) -> None:
    service, event_log, sync_queue = _service(tmp_path)
    body = _body(_raw_event(audit_id="audit-1"), _raw_event(audit_id="audit-2"))

    first = service.ingest(
        principal=PRINCIPAL,
        instance=_instance(),
        body=body,
        received_at_utc=NOW,
    )
    retry = service.ingest(
        principal=PRINCIPAL,
        instance=_instance(),
        body=body,
        received_at_utc=NOW,
    )

    assert first.duplicates == 0
    assert retry.duplicates == 2
    assert len(event_log.list_entries()) == 2
    assert sync_queue.status().queue_depth == 2


def test_kubernetes_precommit_backpressure_stops_batch_without_append(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    service, event_log, _ = _service(tmp_path, queue=queue)

    with pytest.raises(GatewayKubernetesAuditBatchError) as caught:
        service.ingest(
            principal=PRINCIPAL,
            instance=_instance(),
            body=_body(_raw_event(audit_id="audit-1"), _raw_event(audit_id="audit-2")),
            received_at_utc=NOW,
        )

    assert caught.value.failed_index == 0
    assert caught.value.receipts == ()
    assert event_log.list_entries() == []


def test_kubernetes_partial_commit_stops_then_retry_recovers_batch(tmp_path: Path) -> None:
    queue = FailOnceQueue(tmp_path / "race.db")
    service, event_log, sync_queue = _service(tmp_path, queue=queue)
    body = _body(_raw_event(audit_id="audit-1"), _raw_event(audit_id="audit-2"))

    with pytest.raises(GatewayKubernetesAuditBatchError) as caught:
        service.ingest(
            principal=PRINCIPAL,
            instance=_instance(),
            body=body,
            received_at_utc=NOW,
        )

    assert caught.value.failed_index == 0
    assert len(caught.value.receipts) == 1
    assert caught.value.receipts[0].committed_local is True
    assert caught.value.receipts[0].sync_queued is False
    assert len(event_log.list_entries()) == 1

    retry = service.ingest(
        principal=PRINCIPAL,
        instance=_instance(),
        body=body,
        received_at_utc=NOW,
    )

    assert retry.committed_local == 2
    assert retry.sync_queued == 2
    assert len(event_log.list_entries()) == 2
    assert sync_queue.status().queue_depth == 2
