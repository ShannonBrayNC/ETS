from __future__ import annotations

import gzip
import json
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import GatewayIngressService
from ets.gateway.otlp_http import OtlpHttpPolicy, create_otlp_http_app
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/otlp-http"
SOURCE_TIME_NS = 1_786_660_800_123_456_000


class StaticResolver:
    def resolve(self, request: Request) -> str:
        return request.headers.get("X-Test-Principal", PRINCIPAL)


def _registration(*, enabled: bool = True) -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="otlp-http-a",
        source_system="opentelemetry",
        tenant_id="tenant-authoritative",
        workspace_id="workspace-authoritative",
        adapter_id="gateway-otlp-http",
        adapter_version="1.0",
        event_type="telemetry.observed",
        classification="internal",
        redaction_profile="otlp-http-redaction-v1",
        minimization_profile="otlp-http-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="synchronized",
        enabled=enabled,
    )


def _request(*, body: str = "log body", oversized_attribute: bool = False) -> bytes:
    request = ExportLogsServiceRequest()
    resource_logs = request.resource_logs.add()
    resource_attribute = resource_logs.resource.attributes.add()
    resource_attribute.key = "service.name"
    resource_attribute.value.string_value = "orders"
    scope_logs = resource_logs.scope_logs.add()
    scope_logs.scope.name = "orders.instrumentation"
    record = scope_logs.log_records.add()
    record.time_unix_nano = SOURCE_TIME_NS
    record.body.string_value = body
    record.severity_text = "INFO"
    if oversized_attribute:
        attribute = record.attributes.add()
        attribute.key = "oversized"
        attribute.value.string_value = "x" * 5000
    return request.SerializeToString()


def _two_record_request() -> bytes:
    request = ExportLogsServiceRequest()
    resource_logs = request.resource_logs.add()
    scope_logs = resource_logs.scope_logs.add()
    first = scope_logs.log_records.add()
    first.time_unix_nano = SOURCE_TIME_NS
    first.body.string_value = "accepted"
    second = scope_logs.log_records.add()
    second.time_unix_nano = SOURCE_TIME_NS + 1
    attribute = second.attributes.add()
    attribute.key = "oversized"
    attribute.value.string_value = "x" * 5000
    return request.SerializeToString()


def _client(
    tmp_path: Path,
    *,
    enabled: bool = True,
    queue: SyncQueue | None = None,
    policy: OtlpHttpPolicy | None = None,
) -> tuple[TestClient, InMemoryAppendOnlyLog, SyncQueue]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "otlp-http-sync.db")
    service = GatewayIngressService(
        registry=StaticSourceRegistry([_registration(enabled=enabled)]),
        event_log=event_log,
        sync_queue=sync_queue,
    )
    app = create_otlp_http_app(service, StaticResolver(), policy=policy)
    return TestClient(app), event_log, sync_queue


def _headers(delivery_id: str = "delivery-1") -> dict[str, str]:
    return {
        "Content-Type": "application/x-protobuf",
        "Idempotency-Key": delivery_id,
    }


def test_otlp_http_log_request_commits_and_returns_binary_success(tmp_path: Path) -> None:
    client, event_log, sync_queue = _client(tmp_path)

    response = client.post("/v1/logs", content=_request(), headers=_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-protobuf")
    parsed = ExportLogsServiceResponse.FromString(response.content)
    assert not parsed.HasField("partial_success")
    assert response.headers["X-ETS-Committed-Local"] == "1"
    assert response.headers["X-ETS-Sync-Queued"] == "1"
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_otlp_http_supports_bounded_gzip(tmp_path: Path) -> None:
    payload = _request()
    compressed = gzip.compress(payload)
    client, event_log, _ = _client(tmp_path)
    headers = _headers()
    headers["Content-Encoding"] = "gzip"

    response = client.post("/v1/logs", content=compressed, headers=headers)

    assert response.status_code == 200
    assert len(event_log.list_entries()) == 1


def test_otlp_http_exact_and_over_bound_request_bytes(tmp_path: Path) -> None:
    payload = _request()
    exact_policy = OtlpHttpPolicy(
        max_request_bytes=len(payload),
        max_decompressed_bytes=len(payload),
    )
    exact_client, exact_log, _ = _client(tmp_path / "exact", policy=exact_policy)
    exact = exact_client.post("/v1/logs", content=payload, headers=_headers("exact"))
    assert exact.status_code == 200
    assert len(exact_log.list_entries()) == 1

    over_policy = OtlpHttpPolicy(
        max_request_bytes=len(payload) - 1,
        max_decompressed_bytes=len(payload),
    )
    over_client, over_log, _ = _client(tmp_path / "over", policy=over_policy)
    over = over_client.post("/v1/logs", content=payload, headers=_headers("over"))
    assert over.status_code == 413
    assert over_log.list_entries() == []


def test_otlp_http_gzip_decompressed_limit_fails_closed(tmp_path: Path) -> None:
    payload = _request(body="x" * 4000)
    compressed = gzip.compress(payload)
    maximum = max(len(compressed), 128)
    policy = OtlpHttpPolicy(
        max_request_bytes=maximum,
        max_decompressed_bytes=maximum,
    )
    client, event_log, _ = _client(tmp_path, policy=policy)
    headers = _headers()
    headers["Content-Encoding"] = "gzip"

    response = client.post("/v1/logs", content=compressed, headers=headers)

    assert response.status_code == 413
    assert event_log.list_entries() == []


def test_otlp_http_requires_binary_protobuf_and_retry_identity(tmp_path: Path) -> None:
    client, event_log, _ = _client(tmp_path)

    wrong_type = client.post(
        "/v1/logs",
        content=_request(),
        headers={"Content-Type": "application/json", "Idempotency-Key": "wrong"},
    )
    no_identity = client.post(
        "/v1/logs",
        content=_request(),
        headers={"Content-Type": "application/x-protobuf"},
    )

    assert wrong_type.status_code == 415
    assert no_identity.status_code == 400
    assert event_log.list_entries() == []


def test_otlp_http_disabled_source_fails_before_commit(tmp_path: Path) -> None:
    client, event_log, _ = _client(tmp_path, enabled=False)

    response = client.post("/v1/logs", content=_request(), headers=_headers())

    assert response.status_code == 403
    assert event_log.list_entries() == []


def test_otlp_http_partial_success_reports_rejected_log_record(tmp_path: Path) -> None:
    client, event_log, _ = _client(tmp_path)

    response = client.post("/v1/logs", content=_two_record_request(), headers=_headers())

    assert response.status_code == 200
    parsed = ExportLogsServiceResponse.FromString(response.content)
    assert parsed.partial_success.rejected_log_records == 1
    assert "decode_rejected=1" in parsed.partial_success.error_message
    assert response.headers["X-ETS-Decoded-Records"] == "2"
    assert response.headers["X-ETS-Committed-Local"] == "1"
    assert len(event_log.list_entries()) == 1


def test_otlp_http_identical_retry_is_idempotent_and_conflict_is_rejected(tmp_path: Path) -> None:
    client, event_log, sync_queue = _client(tmp_path)
    payload = _request(body="first")

    first = client.post("/v1/logs", content=payload, headers=_headers("retry"))
    retry = client.post("/v1/logs", content=payload, headers=_headers("retry"))
    conflict = client.post(
        "/v1/logs",
        content=_request(body="different"),
        headers=_headers("retry"),
    )

    assert first.status_code == retry.status_code == conflict.status_code == 200
    conflict_body = ExportLogsServiceResponse.FromString(conflict.content)
    assert conflict_body.partial_success.rejected_log_records == 1
    assert "conflict_rejected=1" in conflict_body.partial_success.error_message
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1


def test_otlp_http_precommit_backpressure_reports_rejection_without_append(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "tiny.db", max_bytes=4095)
    client, event_log, _ = _client(tmp_path, queue=queue)

    response = client.post("/v1/logs", content=_request(), headers=_headers())

    assert response.status_code == 200
    parsed = ExportLogsServiceResponse.FromString(response.content)
    assert parsed.partial_success.rejected_log_records == 1
    assert "backpressure_rejected=1" in parsed.partial_success.error_message
    assert response.headers["X-ETS-Committed-Local"] == "0"
    assert event_log.list_entries() == []


def test_otlp_http_raw_log_body_absent_from_event_and_sync(tmp_path: Path) -> None:
    marker = "RAW-OTLP-HTTP-MARKER"
    client, event_log, sync_queue = _client(tmp_path)

    response = client.post(
        "/v1/logs",
        content=_request(body=marker),
        headers=_headers("marker"),
    )

    assert response.status_code == 200
    event_dump = json.dumps(event_log.list_entries()[0].event.model_dump(mode="json"))
    assert marker not in event_dump
    queued = sync_queue.claim_batch(1)
    assert len(queued) == 1
    assert marker not in json.dumps(queued[0].payload)
