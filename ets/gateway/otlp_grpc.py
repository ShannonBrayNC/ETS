"""Bounded OTLP/gRPC host for ETS Gateway G1F-D."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, NoReturn, Protocol

import grpc
from google.protobuf.message import Message
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2_grpc
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2_grpc
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)

from ets.capture.otlp import OtlpDecodedBatchV1, OtlpSignalClass
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressError,
    GatewayIngressService,
    GatewayPartialCommitError,
)
from ets.gateway.otlp_capture import GatewayOtlpCaptureRequest
from ets.gateway.otlp_protobuf import OtlpProtobufDecodeError, decode_otlp_protobuf
from ets.gateway.source_registry import SourceAuthorizationError


class OtlpGrpcPrincipalResolver(Protocol):
    """Resolve an authenticated gRPC peer to the Gateway source principal."""

    def resolve(self, context: grpc.ServicerContext[Any, Any]) -> str: ...


@dataclass(frozen=True, slots=True)
class OtlpGrpcPolicy:
    """Bounded OTLP/gRPC host policy."""

    max_request_bytes: int = 4 * 1024 * 1024
    max_response_bytes: int = 64 * 1024
    max_concurrent_rpcs: int = 64
    graceful_shutdown_seconds: float = 30.0
    processing_budget_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.max_request_bytes < 1 or self.max_response_bytes < 1:
            raise ValueError("OTLP/gRPC byte limits must be positive")
        if self.max_concurrent_rpcs < 1:
            raise ValueError("OTLP/gRPC concurrency must be positive")
        if self.graceful_shutdown_seconds <= 0 or self.processing_budget_seconds <= 0:
            raise ValueError("OTLP/gRPC timing limits must be positive")


@dataclass(frozen=True, slots=True)
class OtlpGrpcBatchResult:
    decoded_records: int
    decode_rejected: int
    committed_local: int
    sync_queued: int
    partial_commit: int
    backpressure_rejected: int
    conflict_rejected: int
    ingress_rejected: int
    budget_rejected: int

    @property
    def rejected(self) -> int:
        return (
            self.decode_rejected
            + self.backpressure_rejected
            + self.conflict_rejected
            + self.ingress_rejected
            + self.budget_rejected
        )


class GatewayOtlpGrpcHost:
    """Concrete unary OTLP/gRPC host with explicit secure/local transport profiles."""

    def __init__(
        self,
        service: GatewayIngressService,
        principal_resolver: OtlpGrpcPrincipalResolver,
        *,
        policy: OtlpGrpcPolicy | None = None,
        host: str = "0.0.0.0",
        port: int = 4317,
        server_credentials: grpc.ServerCredentials | None = None,
        allow_insecure_local: bool = False,
    ) -> None:
        if not 0 <= port <= 65535:
            raise ValueError("OTLP/gRPC port must be between 0 and 65535")
        if server_credentials is None and not allow_insecure_local:
            raise ValueError(
                "OTLP/gRPC requires TLS credentials unless local compatibility is explicit"
            )
        self.service = service
        self.principal_resolver = principal_resolver
        self.policy = policy or OtlpGrpcPolicy()
        self.host = host
        self.port = port
        self.server_credentials = server_credentials
        self.allow_insecure_local = allow_insecure_local
        self._executor = ThreadPoolExecutor(
            max_workers=self.policy.max_concurrent_rpcs,
            thread_name_prefix="ets-otlp-grpc",
        )
        self._server = grpc.server(
            self._executor,
            options=(
                ("grpc.max_receive_message_length", self.policy.max_request_bytes),
                ("grpc.max_send_message_length", self.policy.max_response_bytes),
            ),
            maximum_concurrent_rpcs=self.policy.max_concurrent_rpcs,
        )
        logs_service_pb2_grpc.add_LogsServiceServicer_to_server(
            _LogsService(self),
            self._server,
        )
        metrics_service_pb2_grpc.add_MetricsServiceServicer_to_server(
            _MetricsService(self),
            self._server,
        )
        trace_service_pb2_grpc.add_TraceServiceServicer_to_server(
            _TraceService(self),
            self._server,
        )
        address = f"{self.host}:{self.port}"
        if self.server_credentials is None:
            self._bound_port = self._server.add_insecure_port(address)
        else:
            self._bound_port = self._server.add_secure_port(address, self.server_credentials)
        if self._bound_port == 0:
            self._executor.shutdown(wait=False, cancel_futures=True)
            raise RuntimeError("OTLP/gRPC host could not bind configured address")
        self._started = False
        self._stopped = False

    @property
    def bound_port(self) -> int:
        return self._bound_port

    @property
    def transport_profile(self) -> str:
        return "local_insecure" if self.server_credentials is None else "mtls"

    def start(self) -> None:
        if self._started:
            raise RuntimeError("OTLP/gRPC host is already started")
        if self._stopped:
            raise RuntimeError("OTLP/gRPC host cannot restart after shutdown")
        self._server.start()
        self._started = True

    def shutdown(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        event = self._server.stop(self.policy.graceful_shutdown_seconds)
        event.wait(timeout=self.policy.graceful_shutdown_seconds + 1.0)
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _handle(
        self,
        signal_class: OtlpSignalClass,
        request: Message,
        context: grpc.ServicerContext[Any, Any],
    ) -> OtlpGrpcBatchResult:
        principal = self._resolve_principal(context)
        delivery_id = _metadata_value(context, "idempotency-key")
        if delivery_id is None or not 1 <= len(delivery_id) <= 200:
            _abort(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "OTLP/gRPC requires a bounded idempotency-key metadata value",
            )
        correlation_id = _metadata_value(context, "x-correlation-id")
        if correlation_id is not None and len(correlation_id) > 200:
            _abort(context, grpc.StatusCode.INVALID_ARGUMENT, "x-correlation-id is too long")

        payload = request.SerializeToString()
        if len(payload) > self.policy.max_request_bytes:
            _abort(context, grpc.StatusCode.RESOURCE_EXHAUSTED, "OTLP/gRPC request exceeds limit")
        try:
            decoded = decode_otlp_protobuf(signal_class, payload)
        except OtlpProtobufDecodeError:
            _abort(context, grpc.StatusCode.INVALID_ARGUMENT, "invalid OTLP protobuf request")

        remaining = context.time_remaining()
        if remaining is not None and remaining <= 0:
            _abort(context, grpc.StatusCode.DEADLINE_EXCEEDED, "OTLP/gRPC deadline expired")
        budget = self.policy.processing_budget_seconds
        if remaining is not None:
            budget = min(budget, max(remaining, 0.0))
        return _commit_batch(
            decoded,
            principal=principal,
            delivery_id=delivery_id,
            correlation_id=correlation_id,
            service=self.service,
            processing_budget_seconds=budget,
        )

    def _resolve_principal(self, context: grpc.ServicerContext[Any, Any]) -> str:
        try:
            return self.principal_resolver.resolve(context)
        except SourceAuthorizationError:
            _abort(context, grpc.StatusCode.PERMISSION_DENIED, "source is not authorized")
        except PermissionError:
            _abort(context, grpc.StatusCode.UNAUTHENTICATED, "source authentication failed")


def create_otlp_grpc_mtls_credentials(
    *,
    private_key: bytes,
    certificate_chain: bytes,
    client_ca: bytes,
) -> grpc.ServerCredentials:
    """Create the qualified production gRPC TLS profile with required client certificates."""

    if not private_key or not certificate_chain or not client_ca:
        raise ValueError("OTLP/gRPC mTLS credentials must be non-empty")
    return grpc.ssl_server_credentials(
        ((private_key, certificate_chain),),
        root_certificates=client_ca,
        require_client_auth=True,
    )


class _LogsService(logs_service_pb2_grpc.LogsServiceServicer):
    def __init__(self, host: GatewayOtlpGrpcHost) -> None:
        self._host = host

    def Export(
        self,
        request: ExportLogsServiceRequest,
        context: grpc.ServicerContext[Any, Any],
    ) -> ExportLogsServiceResponse:
        result = self._host._handle("logs", request, context)
        response = ExportLogsServiceResponse()
        if result.rejected or result.partial_commit:
            response.partial_success.rejected_log_records = result.rejected
            response.partial_success.error_message = _result_message(result)
        _set_trailing_receipt(context, result)
        return response


class _MetricsService(metrics_service_pb2_grpc.MetricsServiceServicer):
    def __init__(self, host: GatewayOtlpGrpcHost) -> None:
        self._host = host

    def Export(
        self,
        request: ExportMetricsServiceRequest,
        context: grpc.ServicerContext[Any, Any],
    ) -> ExportMetricsServiceResponse:
        result = self._host._handle("metrics", request, context)
        response = ExportMetricsServiceResponse()
        if result.rejected or result.partial_commit:
            response.partial_success.rejected_data_points = result.rejected
            response.partial_success.error_message = _result_message(result)
        _set_trailing_receipt(context, result)
        return response


class _TraceService(trace_service_pb2_grpc.TraceServiceServicer):
    def __init__(self, host: GatewayOtlpGrpcHost) -> None:
        self._host = host

    def Export(
        self,
        request: ExportTraceServiceRequest,
        context: grpc.ServicerContext[Any, Any],
    ) -> ExportTraceServiceResponse:
        result = self._host._handle("traces", request, context)
        response = ExportTraceServiceResponse()
        if result.rejected or result.partial_commit:
            response.partial_success.rejected_spans = result.rejected
            response.partial_success.error_message = _result_message(result)
        _set_trailing_receipt(context, result)
        return response


def _commit_batch(
    decoded: OtlpDecodedBatchV1,
    *,
    principal: str,
    delivery_id: str,
    correlation_id: str | None,
    service: GatewayIngressService,
    processing_budget_seconds: float,
) -> OtlpGrpcBatchResult:
    started = time.monotonic()
    committed_local = 0
    sync_queued = 0
    partial_commit = 0
    backpressure_rejected = 0
    conflict_rejected = 0
    ingress_rejected = 0
    budget_rejected = 0

    for index, observation in enumerate(decoded.accepted):
        if time.monotonic() - started >= processing_budget_seconds:
            budget_rejected = len(decoded.accepted) - index
            break
        try:
            receipt = service.ingest_otlp(
                principal,
                GatewayOtlpCaptureRequest(
                    observation=observation,
                    delivery_id=delivery_id,
                    correlation_id=correlation_id,
                ),
            )
            if receipt.committed_local:
                committed_local += 1
            if receipt.sync_queued:
                sync_queued += 1
        except GatewayPartialCommitError:
            committed_local += 1
            partial_commit += 1
        except GatewayBackpressureError:
            backpressure_rejected += 1
        except GatewayConflictError:
            conflict_rejected += 1
        except GatewayIngressError:
            ingress_rejected += 1

    return OtlpGrpcBatchResult(
        decoded_records=decoded.total_records,
        decode_rejected=len(decoded.rejected),
        committed_local=committed_local,
        sync_queued=sync_queued,
        partial_commit=partial_commit,
        backpressure_rejected=backpressure_rejected,
        conflict_rejected=conflict_rejected,
        ingress_rejected=ingress_rejected,
        budget_rejected=budget_rejected,
    )


def _metadata_value(context: grpc.ServicerContext[Any, Any], key: str) -> str | None:
    for item in context.invocation_metadata():
        if item.key.lower() == key:
            value = item.value
            if isinstance(value, bytes):
                try:
                    return value.decode("utf-8")
                except UnicodeDecodeError:
                    return None
            return str(value)
    return None


def _set_trailing_receipt(
    context: grpc.ServicerContext[Any, Any],
    result: OtlpGrpcBatchResult,
) -> None:
    context.set_trailing_metadata(
        (
            ("x-ets-decoded-records", str(result.decoded_records)),
            ("x-ets-committed-local", str(result.committed_local)),
            ("x-ets-sync-queued", str(result.sync_queued)),
            ("x-ets-partial-commit", str(result.partial_commit)),
        )
    )


def _result_message(result: OtlpGrpcBatchResult) -> str:
    messages: list[str] = []
    if result.decode_rejected:
        messages.append(f"decode_rejected={result.decode_rejected}")
    if result.backpressure_rejected:
        messages.append(f"backpressure_rejected={result.backpressure_rejected}")
    if result.conflict_rejected:
        messages.append(f"conflict_rejected={result.conflict_rejected}")
    if result.ingress_rejected:
        messages.append(f"ingress_rejected={result.ingress_rejected}")
    if result.budget_rejected:
        messages.append(f"budget_rejected={result.budget_rejected}")
    if result.partial_commit:
        messages.append(f"partial_commit={result.partial_commit}")
    return "; ".join(messages)


def _abort(
    context: grpc.ServicerContext[Any, Any],
    code: grpc.StatusCode,
    details: str,
) -> NoReturn:
    context.abort(code, details)
    raise RuntimeError("gRPC context.abort returned unexpectedly")
