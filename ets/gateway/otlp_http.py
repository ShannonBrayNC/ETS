"""Bounded OTLP/HTTP binary-Protobuf host for ETS Gateway G1F-C."""

from __future__ import annotations

import asyncio
import gzip
import io
import time
from dataclasses import dataclass

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceResponse
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceResponse
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse

from ets.capture.otlp import OtlpDecodedBatchV1, OtlpSignalClass
from ets.gateway.host import (
    GatewayHostController,
    GatewayHostLimitError,
    GatewayHostPolicy,
    GatewayHostSaturatedError,
    UnsupportedContentEncodingError,
)
from ets.gateway.http import PrincipalResolver, SourceAuthenticationError
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

OTLP_PROTOBUF_MEDIA_TYPE = "application/x-protobuf"


class OtlpHttpRequestError(ValueError):
    """Base error for bounded OTLP/HTTP transport rejection."""


class OtlpHttpBodyTooLarge(OtlpHttpRequestError):
    """Raised when compressed or decoded request bytes exceed configured limits."""


class OtlpHttpBodyTimeout(OtlpHttpRequestError):
    """Raised when the request body cannot be read within the pre-commit deadline."""


@dataclass(frozen=True, slots=True)
class OtlpHttpPolicy:
    """OTLP/HTTP-specific bounds layered on the shared Gateway HTTP controller."""

    max_request_bytes: int = 4 * 1024 * 1024
    max_decompressed_bytes: int = 8 * 1024 * 1024
    processing_budget_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.max_request_bytes < 1 or self.max_decompressed_bytes < 1:
            raise ValueError("OTLP/HTTP byte limits must be positive")
        if self.max_decompressed_bytes < self.max_request_bytes:
            raise ValueError("OTLP decompressed limit must be at least the request byte limit")
        if self.processing_budget_seconds <= 0:
            raise ValueError("OTLP/HTTP processing budget must be positive")


@dataclass(frozen=True, slots=True)
class OtlpHttpBatchResult:
    """Bounded internal accounting for one OTLP/HTTP request."""

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


def create_otlp_http_app(
    service: GatewayIngressService,
    principal_resolver: PrincipalResolver,
    *,
    host_controller: GatewayHostController | None = None,
    policy: OtlpHttpPolicy | None = None,
) -> FastAPI:
    """Create the G1F-C OTLP/HTTP host around injected authentication and shared ingress."""

    app = FastAPI(title="ETS Gateway OTLP", version="0.1.0-g1f-c")
    resolved_policy = policy or OtlpHttpPolicy()
    host = host_controller or GatewayHostController(
        GatewayHostPolicy(allowed_content_encodings=("identity", "gzip"))
    )

    @app.post("/v1/logs")
    async def ingest_logs(request: Request) -> Response:
        return await _handle_request(
            request,
            "logs",
            service,
            principal_resolver,
            host,
            resolved_policy,
        )

    @app.post("/v1/metrics")
    async def ingest_metrics(request: Request) -> Response:
        return await _handle_request(
            request,
            "metrics",
            service,
            principal_resolver,
            host,
            resolved_policy,
        )

    @app.post("/v1/traces")
    async def ingest_traces(request: Request) -> Response:
        return await _handle_request(
            request,
            "traces",
            service,
            principal_resolver,
            host,
            resolved_policy,
        )

    return app


async def _handle_request(
    request: Request,
    signal_class: OtlpSignalClass,
    service: GatewayIngressService,
    principal_resolver: PrincipalResolver,
    host: GatewayHostController,
    policy: OtlpHttpPolicy,
) -> Response:
    try:
        host.validate_headers(request.scope.get("headers", ()))
        host.validate_content_encoding(request.headers.get("Content-Encoding"))
        if _content_type(request) != OTLP_PROTOBUF_MEDIA_TYPE:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"detail": "OTLP/HTTP requires application/x-protobuf"},
            )
        delivery_id = request.headers.get("Idempotency-Key", "")
        if not delivery_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "OTLP/HTTP requires a bounded Idempotency-Key retry identity"},
            )

        async with host.admission():
            principal = principal_resolver.resolve(request)
            try:
                async with asyncio.timeout(host.policy.body_read_timeout_seconds):
                    body = await _read_bounded_body(request, policy.max_request_bytes)
            except TimeoutError as exc:
                raise OtlpHttpBodyTimeout(
                    "OTLP/HTTP body read exceeded pre-commit deadline"
                ) from exc
            decoded_body = _decode_content_encoding(
                body,
                request.headers.get("Content-Encoding"),
                policy.max_decompressed_bytes,
            )
            decoded = decode_otlp_protobuf(signal_class, decoded_body)
            batch = _commit_batch(
                decoded,
                principal=principal,
                delivery_id=delivery_id,
                correlation_id=request.headers.get("X-Correlation-ID"),
                service=service,
                processing_budget_seconds=policy.processing_budget_seconds,
            )
    except SourceAuthenticationError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "source authentication failed"},
        )
    except SourceAuthorizationError:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "source is not authorized"},
        )
    except UnsupportedContentEncodingError:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"detail": "OTLP content encoding is not qualified"},
        )
    except GatewayHostLimitError:
        return JSONResponse(
            status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE,
            content={"detail": "request headers exceed configured host limits"},
        )
    except GatewayHostSaturatedError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Gateway host concurrency is saturated"},
            headers={"Retry-After": "1"},
        )
    except OtlpHttpBodyTimeout:
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content={"detail": "OTLP/HTTP body read exceeded pre-commit deadline"},
        )
    except OtlpHttpBodyTooLarge:
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"detail": "OTLP/HTTP request exceeds configured byte limits"},
        )
    except OtlpProtobufDecodeError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "invalid OTLP protobuf request"},
        )

    return _otlp_success_response(signal_class, batch)


def _commit_batch(
    decoded: OtlpDecodedBatchV1,
    *,
    principal: str,
    delivery_id: str,
    correlation_id: str | None,
    service: GatewayIngressService,
    processing_budget_seconds: float,
) -> OtlpHttpBatchResult:
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

    return OtlpHttpBatchResult(
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


def _otlp_success_response(signal_class: OtlpSignalClass, result: OtlpHttpBatchResult) -> Response:
    response = _new_signal_response(signal_class)
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

    if result.rejected or result.partial_commit:
        partial = response.partial_success
        if signal_class == "logs":
            partial.rejected_log_records = result.rejected
        elif signal_class == "metrics":
            partial.rejected_data_points = result.rejected
        else:
            partial.rejected_spans = result.rejected
        partial.error_message = "; ".join(messages)

    return Response(
        content=response.SerializeToString(),
        status_code=status.HTTP_200_OK,
        media_type=OTLP_PROTOBUF_MEDIA_TYPE,
        headers={
            "X-ETS-Decoded-Records": str(result.decoded_records),
            "X-ETS-Committed-Local": str(result.committed_local),
            "X-ETS-Sync-Queued": str(result.sync_queued),
            "X-ETS-Partial-Commit": str(result.partial_commit),
        },
    )


def _new_signal_response(signal_class: OtlpSignalClass) -> object:
    if signal_class == "logs":
        return ExportLogsServiceResponse()
    if signal_class == "metrics":
        return ExportMetricsServiceResponse()
    return ExportTraceServiceResponse()


def _content_type(request: Request) -> str:
    return request.headers.get("Content-Type", "").partition(";")[0].strip().lower()


async def _read_bounded_body(request: Request, maximum: int) -> bytes:
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise OtlpHttpRequestError("invalid OTLP Content-Length") from exc
        if declared_length < 0:
            raise OtlpHttpRequestError("invalid OTLP Content-Length")
        if declared_length > maximum:
            raise OtlpHttpBodyTooLarge("compressed OTLP request exceeds configured limit")

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > maximum:
            raise OtlpHttpBodyTooLarge("compressed OTLP request exceeds configured limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _decode_content_encoding(payload: bytes, encoding: str | None, maximum: int) -> bytes:
    normalized = "identity" if encoding is None else encoding.strip().lower()
    if normalized == "identity":
        if len(payload) > maximum:
            raise OtlpHttpBodyTooLarge("OTLP request exceeds decompressed limit")
        return payload
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
            decoded = stream.read(maximum + 1)
    except (EOFError, OSError) as exc:
        raise OtlpHttpRequestError("malformed gzip OTLP request") from exc
    if len(decoded) > maximum:
        raise OtlpHttpBodyTooLarge("OTLP request exceeds decompressed limit")
    return decoded
