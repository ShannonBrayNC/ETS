from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ets.connectors.conformance import ConnectorConformanceHarness
from ets.connectors.enterprise.kubernetes import (
    KubernetesAuditAdapter,
    KubernetesAuditDecodeError,
    parse_kubernetes_audit_event_list,
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
from ets.connectors.sdk import ConnectorConfigurationError

NOW = datetime(2026, 8, 14, 5, 0, tzinfo=UTC)
MANIFESTS = Path("config/connectors/enterprise")


def _instance(*, settings: dict[str, Any] | None = None) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id="kubernetes-audit-test",
        connector_id="kubernetes.audit",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
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
        settings=settings or {"cluster_id": "cluster-prod-a"},
    )


def _raw_event(
    *,
    stage: str = "ResponseComplete",
    marker: str = "RAW-K8S-MARKER",
) -> dict[str, Any]:
    return {
        "apiVersion": "audit.k8s.io/v1",
        "kind": "Event",
        "level": "RequestResponse",
        "auditID": "audit-001",
        "stage": stage,
        "requestURI": "/api/v1/namespaces/default/secrets/example?watch=true&token=secret",
        "verb": "get",
        "user": {
            "username": "alice@example.test",
            "uid": "user-001",
            "groups": ["system:authenticated"],
        },
        "sourceIPs": ["192.0.2.10"],
        "userAgent": "kubectl/fixture",
        "objectRef": {
            "resource": "secrets",
            "namespace": "default",
            "name": "example",
            "apiVersion": "v1",
        },
        "responseStatus": {
            "status": "Success",
            "code": 200,
        },
        "requestReceivedTimestamp": "2026-08-14T04:59:59.000000Z",
        "stageTimestamp": "2026-08-14T05:00:00.000000Z",
        "annotations": {"raw.example/marker": marker},
        "requestObject": {"stringData": {"password": marker}},
        "responseObject": {"data": {"password": marker}},
    }


def _payload(*events: dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "apiVersion": "audit.k8s.io/v1",
            "kind": "EventList",
            "items": list(events),
        }
    ).encode("utf-8")


def _adapter() -> tuple[KubernetesAuditAdapter, ConnectorRegistry]:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)
    adapter = KubernetesAuditAdapter(registry.get_definition("kubernetes.audit"))
    registry.register_adapter(adapter)
    return adapter, registry


def test_kubernetes_audit_adapter_passes_shared_connector_conformance() -> None:
    adapter, registry = _adapter()
    batch = parse_kubernetes_audit_event_list(_payload(_raw_event()))

    report = ConnectorConformanceHarness(registry).validate_sample(
        adapter,
        _instance(),
        batch.records[0],
    )

    assert report.connector_id == "kubernetes.audit"
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_decode_minimizes_raw_request_response_identity_and_network_fields() -> None:
    marker = "RAW-KUBERNETES-AUDIT-MARKER"
    batch = parse_kubernetes_audit_event_list(_payload(_raw_event(marker=marker)))
    record = batch.records[0]
    serialized = json.dumps(record)

    assert record["audit_id"] == "audit-001"
    assert record["stage"] == "ResponseComplete"
    assert record["request_uri_path"] == "/api/v1/namespaces/default/secrets/example"
    assert marker not in serialized
    assert "alice@example.test" not in serialized
    assert "192.0.2.10" not in serialized
    assert "kubectl/fixture" not in serialized
    assert "token=secret" not in serialized


def test_same_audit_request_stages_receive_distinct_bounded_source_record_ids() -> None:
    adapter, _ = _adapter()
    batch = parse_kubernetes_audit_event_list(
        _payload(
            _raw_event(stage="RequestReceived"),
            _raw_event(stage="ResponseComplete"),
        )
    )

    first = adapter.normalize(_instance(), batch.records[0])
    second = adapter.normalize(_instance(), batch.records[1])

    assert first.source_record_id.startswith("audit-stage:")
    assert second.source_record_id.startswith("audit-stage:")
    assert len(first.source_record_id) == len("audit-stage:") + 64
    assert len(second.source_record_id) == len("audit-stage:") + 64
    assert first.source_record_id != second.source_record_id


def test_maximum_audit_id_and_stage_still_produce_bounded_identity() -> None:
    adapter, _ = _adapter()
    raw = _raw_event(stage="S" * 100)
    raw["auditID"] = "A" * 500
    batch = parse_kubernetes_audit_event_list(_payload(raw))

    candidate = adapter.normalize(_instance(), batch.records[0])

    assert candidate.source_record_id.startswith("audit-stage:")
    assert len(candidate.source_record_id) == len("audit-stage:") + 64


def test_stage_timestamp_is_preserved_as_source_observation_time() -> None:
    adapter, _ = _adapter()
    batch = parse_kubernetes_audit_event_list(_payload(_raw_event()))

    candidate = adapter.normalize(_instance(), batch.records[0])

    assert candidate.observed_at_utc == NOW
    assert candidate.metadata["cluster_id"] == "cluster-prod-a"


def test_push_connector_does_not_invent_polling_checkpoint_or_completeness() -> None:
    adapter, _ = _adapter()

    collection = adapter.collect(_instance(), None)
    reconciliation = adapter.reconcile(_instance(), None)

    assert collection.code == "unsupported"
    assert collection.checkpoint is None
    assert reconciliation.code == "unknown_observation"
    assert reconciliation.reconciled is False
    assert reconciliation.gap_detected is False


def test_decode_rejects_wrong_api_version_and_event_kind() -> None:
    wrong_version = _raw_event()
    wrong_version["apiVersion"] = "audit.k8s.io/v1beta1"
    wrong_kind = _raw_event()
    wrong_kind["kind"] = "List"

    with pytest.raises(KubernetesAuditDecodeError, match="audit.k8s.io/v1 Event"):
        parse_kubernetes_audit_event_list(_payload(wrong_version))
    with pytest.raises(KubernetesAuditDecodeError, match="audit.k8s.io/v1 Event"):
        parse_kubernetes_audit_event_list(_payload(wrong_kind))


def test_decode_enforces_body_batch_and_event_bounds() -> None:
    payload = _payload(_raw_event())

    with pytest.raises(KubernetesAuditDecodeError, match="body exceeds"):
        parse_kubernetes_audit_event_list(payload, maximum_body_bytes=len(payload) - 1)
    with pytest.raises(KubernetesAuditDecodeError, match="batch exceeds"):
        parse_kubernetes_audit_event_list(
            _payload(_raw_event(), _raw_event(stage="ResponseStarted")),
            maximum_batch_events=1,
        )
    with pytest.raises(KubernetesAuditDecodeError, match="event exceeds"):
        parse_kubernetes_audit_event_list(payload, maximum_event_bytes=1024)


def test_configuration_rejects_polling_and_unqualified_settings() -> None:
    adapter, _ = _adapter()
    polling = _instance().model_copy(
        update={
            "collection": ConnectorCollection(
                mode="poll",
                interval_seconds=60,
                batch_size=100,
            )
        }
    )
    unsafe = _instance(
        settings={"cluster_id": "cluster-a", "webhook_url": "https://evil.test"}
    )

    with pytest.raises(ConnectorConfigurationError, match="requires push collection"):
        adapter.validate_config(polling)
    with pytest.raises(ConnectorConfigurationError, match="unsupported Kubernetes audit"):
        adapter.validate_config(unsafe)
