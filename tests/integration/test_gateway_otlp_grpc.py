from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import grpc
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2_grpc
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2_grpc
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import GatewayIngressService
from ets.gateway.otlp_grpc import GatewayOtlpGrpcHost, OtlpGrpcPolicy
from ets.gateway.otlp_http import create_otlp_http_app
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/otlp-grpc"
SOURCE_TIME_NS = 1_786_660_800_123_456_000


class MetadataPrincipalResolver:
    def resolve(self, context: grpc.ServicerContext[Any, Any]) -> str:
        for item in context.invocation_metadata():
            if item.key == "x-test-principal":
                return str(item.value)
        raise PermissionError("missing test principal")


class HttpPrincipalResolver:
    def resolve(self, request: Request) -> str:
        return request.headers.get("X-Test-Principal", PRINCIPAL)


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="otlp-cross-transport",
        source_system="opentelemetry",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        adapter_id="gateway-otlp",
        adapter_version="1.0",
        event_type="telemetry.observed",
        classification="internal",
        redaction_profile="otlp-redaction-v1",
        minimization_profile="otlp-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="synchronized",
    )


def _service(
    tmp_path: Path,
) -> tuple[GatewayIngressService, InMemoryAppendOnlyLog, SyncQueue]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    event_log = InMemoryAppendOnlyLog()
    sync_queue = SyncQueue(tmp_path / "sync.db")
    service = GatewayIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
    )
    return service, event_log, sync_queue


def _logs_request(*, body: str = "log body", second_invalid: bool = False) -> ExportLogsServiceRequest:
    request = ExportLogsServiceRequest()
    resource_logs = request.resource_logs.add()
    resource_attribute = resource_logs.resource.attributes.add()
    resource_attribute.key = "service.name"
    resource_attribute.value.string_value = "orders"
    scope_logs = resource_logs.scope_logs.add()
    scope_logs.scope.name = "orders.instrumentation"
    record = scope_logs.log_records.add()
    record.time_unix_nano = SOURCE_TIME_NS
    record.severity_text = "INFO"
    record.body.string_value = body
    if second_invalid:
        rejected = scope_logs.log_records.add()
        rejected.time_unix_nano = SOURCE_TIME_NS + 1
        attribute = rejected.attributes.add()
        attribute.key = "oversized"
        attribute.value.string_value = "x" * 5000
    return request


def _metrics_request() -> ExportMetricsServiceRequest:
    request = ExportMetricsServiceRequest()
    resource_metrics = request.resource_metrics.add()
    scope_metrics = resource_metrics.scope_metrics.add()
    metric = scope_metrics.metrics.add()
    metric.name = "request.duration"
    point = metric.gauge.data_points.add()
    point.time_unix_nano = SOURCE_TIME_NS
    point.as_double = 12.5
    return request


def _trace_request() -> ExportTraceServiceRequest:
    request = ExportTraceServiceRequest()
    resource_spans = request.resource_spans.add()
    scope_spans = resource_spans.scope_spans.add()
    span = scope_spans.spans.add()
    span.name = "checkout"
    span.start_time_unix_nano = SOURCE_TIME_NS
    span.end_time_unix_nano = SOURCE_TIME_NS + 10_000
    return request


def _metadata(delivery_id: str = "delivery-1") -> tuple[tuple[str, str], ...]:
    return (
        ("x-test-principal", PRINCIPAL),
        ("idempotency-key", delivery_id),
    )


def _start_host(
    tmp_path: Path,
    *,
    policy: OtlpGrpcPolicy | None = None,
) -> tuple[
    GatewayOtlpGrpcHost,
    grpc.Channel,
    InMemoryAppendOnlyLog,
    SyncQueue,
]:
    service, event_log, sync_queue = _service(tmp_path)
    host = GatewayOtlpGrpcHost(
        service,
        MetadataPrincipalResolver(),
        policy=policy,
        host="127.0.0.1",
        port=0,
        allow_insecure_local=True,
    )
    host.start()
    channel = grpc.insecure_channel(f"127.0.0.1:{host.bound_port}")
    grpc.channel_ready_future(channel).result(timeout=5)
    return host, channel, event_log, sync_queue


def test_grpc_requires_explicit_local_compatibility_or_tls(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)

    with pytest.raises(ValueError, match="requires TLS credentials"):
        GatewayOtlpGrpcHost(
            service,
            MetadataPrincipalResolver(),
            host="127.0.0.1",
            port=0,
        )


def test_grpc_logs_metrics_and_traces_commit_through_shared_gateway(tmp_path: Path) -> None:
    host, channel, event_log, sync_queue = _start_host(tmp_path)
    try:
        logs = logs_service_pb2_grpc.LogsServiceStub(channel)
        metrics = metrics_service_pb2_grpc.MetricsServiceStub(channel)
        traces = trace_service_pb2_grpc.TraceServiceStub(channel)

        logs.Export(_logs_request(), metadata=_metadata("logs"), timeout=5)
        metrics.Export(_metrics_request(), metadata=_metadata("metrics"), timeout=5)
        traces.Export(_trace_request(), metadata=_metadata("traces"), timeout=5)

        assert len(event_log.list_entries()) == 3
        assert sync_queue.status().queue_depth == 3
    finally:
        channel.close()
        host.shutdown()


def test_grpc_partial_success_reports_rejected_log_record(tmp_path: Path) -> None:
    host, channel, event_log, _ = _start_host(tmp_path)
    try:
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        response = stub.Export(
            _logs_request(second_invalid=True),
            metadata=_metadata(),
            timeout=5,
        )

        assert response.partial_success.rejected_log_records == 1
        assert "decode_rejected=1" in response.partial_success.error_message
        assert len(event_log.list_entries()) == 1
    finally:
        channel.close()
        host.shutdown()


def test_grpc_gzip_transport_and_receive_limit(tmp_path: Path) -> None:
    request = _logs_request(body="x" * 2000)
    exact_size = len(request.SerializeToString())
    host, channel, event_log, _ = _start_host(
        tmp_path,
        policy=OtlpGrpcPolicy(max_request_bytes=exact_size),
    )
    try:
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        stub.Export(
            request,
            metadata=_metadata("gzip"),
            compression=grpc.Compression.Gzip,
            timeout=5,
        )
        assert len(event_log.list_entries()) == 1
    finally:
        channel.close()
        host.shutdown()

    over_host, over_channel, over_log, _ = _start_host(
        tmp_path / "over",
        policy=OtlpGrpcPolicy(max_request_bytes=exact_size - 1),
    )
    try:
        over_stub = logs_service_pb2_grpc.LogsServiceStub(over_channel)
        with pytest.raises(grpc.RpcError) as exc_info:
            over_stub.Export(
                request,
                metadata=_metadata("over"),
                compression=grpc.Compression.Gzip,
                timeout=5,
            )
        assert exc_info.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED
        assert over_log.list_entries() == []
    finally:
        over_channel.close()
        over_host.shutdown()


def test_grpc_missing_principal_or_retry_identity_fails_before_commit(tmp_path: Path) -> None:
    host, channel, event_log, _ = _start_host(tmp_path)
    try:
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        with pytest.raises(grpc.RpcError) as missing_principal:
            stub.Export(
                _logs_request(),
                metadata=(("idempotency-key", "missing-principal"),),
                timeout=5,
            )
        assert missing_principal.value.code() == grpc.StatusCode.UNAUTHENTICATED

        with pytest.raises(grpc.RpcError) as missing_identity:
            stub.Export(
                _logs_request(),
                metadata=(("x-test-principal", PRINCIPAL),),
                timeout=5,
            )
        assert missing_identity.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        assert event_log.list_entries() == []
    finally:
        channel.close()
        host.shutdown()


def test_grpc_retry_is_idempotent_and_conflict_is_partial_rejection(tmp_path: Path) -> None:
    host, channel, event_log, sync_queue = _start_host(tmp_path)
    try:
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        first = _logs_request(body="first")
        stub.Export(first, metadata=_metadata("retry"), timeout=5)
        stub.Export(first, metadata=_metadata("retry"), timeout=5)
        conflict = stub.Export(
            _logs_request(body="different"),
            metadata=_metadata("retry"),
            timeout=5,
        )

        assert conflict.partial_success.rejected_log_records == 1
        assert "conflict_rejected=1" in conflict.partial_success.error_message
        assert len(event_log.list_entries()) == 1
        assert sync_queue.status().queue_depth == 1
    finally:
        channel.close()
        host.shutdown()


def test_grpc_raw_log_body_absent_from_event_and_sync(tmp_path: Path) -> None:
    marker = "RAW-OTLP-GRPC-MARKER"
    host, channel, event_log, sync_queue = _start_host(tmp_path)
    try:
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        stub.Export(_logs_request(body=marker), metadata=_metadata("marker"), timeout=5)

        event_dump = json.dumps(event_log.list_entries()[0].event.model_dump(mode="json"))
        assert marker not in event_dump
        queued = sync_queue.claim_batch(1)
        assert len(queued) == 1
        assert marker not in json.dumps(queued[0].payload)
    finally:
        channel.close()
        host.shutdown()


def test_http_and_grpc_commit_equivalent_content_hashes(tmp_path: Path) -> None:
    request = _logs_request(body="same-across-transports")

    http_service, http_log, _ = _service(tmp_path / "http")
    http_app = create_otlp_http_app(http_service, HttpPrincipalResolver())
    http_response = TestClient(http_app).post(
        "/v1/logs",
        content=request.SerializeToString(),
        headers={
            "Content-Type": "application/x-protobuf",
            "Idempotency-Key": "equivalent",
            "X-Test-Principal": PRINCIPAL,
        },
    )
    assert http_response.status_code == 200

    grpc_host, channel, grpc_log, _ = _start_host(tmp_path / "grpc")
    try:
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        stub.Export(request, metadata=_metadata("equivalent"), timeout=5)
    finally:
        channel.close()
        grpc_host.shutdown()

    http_event = http_log.list_entries()[0].event
    grpc_event = grpc_log.list_entries()[0].event
    assert http_event.content_hash == grpc_event.content_hash
    assert http_event.tenant_id == grpc_event.tenant_id == "tenant-a"
    assert http_event.workspace_id == grpc_event.workspace_id == "workspace-a"


class SlowIngressService(GatewayIngressService):
    def __init__(self, *args: Any, started: threading.Event, release: threading.Event, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.started = started
        self.release = release

    def ingest_otlp(self, principal: str, request: Any):  # type: ignore[no-untyped-def]
        self.started.set()
        self.release.wait(timeout=5)
        return super().ingest_otlp(principal, request)


def test_grpc_shutdown_drains_admitted_rpc_and_rejects_new(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()
    event_log = InMemoryAppendOnlyLog()
    sync_queue = SyncQueue(tmp_path / "shutdown.db")
    service = SlowIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        started=started,
        release=release,
    )
    host = GatewayOtlpGrpcHost(
        service,
        MetadataPrincipalResolver(),
        policy=OtlpGrpcPolicy(graceful_shutdown_seconds=2.0),
        host="127.0.0.1",
        port=0,
        allow_insecure_local=True,
    )
    host.start()
    channel = grpc.insecure_channel(f"127.0.0.1:{host.bound_port}")
    grpc.channel_ready_future(channel).result(timeout=5)
    stub = logs_service_pb2_grpc.LogsServiceStub(channel)
    result: list[object] = []

    def invoke() -> None:
        result.append(stub.Export(_logs_request(), metadata=_metadata("admitted"), timeout=5))

    rpc_thread = threading.Thread(target=invoke)
    rpc_thread.start()
    assert started.wait(timeout=2)
    shutdown_thread = threading.Thread(target=host.shutdown)
    shutdown_thread.start()

    with pytest.raises(grpc.RpcError):
        stub.Export(_logs_request(), metadata=_metadata("new"), timeout=1)

    release.set()
    rpc_thread.join(timeout=5)
    shutdown_thread.join(timeout=5)
    channel.close()

    assert len(result) == 1
    assert len(event_log.list_entries()) == 1
    assert sync_queue.status().queue_depth == 1
