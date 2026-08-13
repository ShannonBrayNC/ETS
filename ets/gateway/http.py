"""FastAPI transport adapter for bounded ETS Gateway webhook ingress."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Protocol

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressError,
    GatewayIngressReceipt,
    GatewayIngressService,
    GatewayPartialCommitError,
    GatewayWebhookRequest,
)
from ets.gateway.source_registry import SourceAuthorizationError


class SourceAuthenticationError(PermissionError):
    """Raised when the transport cannot establish an authenticated source principal."""


class RequestBodyTooLarge(GatewayIngressError):
    """Raised when streaming request input exceeds the configured byte bound."""


class PrincipalResolver(Protocol):
    """Resolve one authenticated transport principal from an HTTP request."""

    def resolve(self, request: Request) -> str:
        """Return the authenticated source principal or fail closed."""


def create_gateway_app(
    service: GatewayIngressService,
    principal_resolver: PrincipalResolver,
) -> FastAPI:
    """Create the G1C webhook app around injected auth and ingestion services."""

    app = FastAPI(title="ETS Gateway", version="0.1.0-g1c")

    @app.post("/gateway/v1/webhooks")
    async def ingest_webhook(request: Request) -> JSONResponse:
        try:
            principal = principal_resolver.resolve(request)
            body = await _read_bounded_body(request, service.max_body_bytes)
            capture_request = GatewayWebhookRequest(
                body=body,
                idempotency_key=request.headers.get("Idempotency-Key", ""),
                declared_identity=request.headers.get("X-ETS-Declared-Identity"),
                observed_at_utc=_observed_at(request),
                correlation_id=request.headers.get("X-Correlation-ID"),
                media_type=_content_type(request),
            )
            receipt = service.ingest_json(principal, capture_request)
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
        except RequestBodyTooLarge:
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "request body exceeds configured limit"},
            )
        except GatewayConflictError:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "idempotency conflict"},
            )
        except GatewayBackpressureError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Gateway capacity is temporarily exhausted"},
                headers={"Retry-After": "1"},
            )
        except GatewayPartialCommitError as exc:
            content = _receipt_content(exc.receipt)
            content["status"] = "partial_commit"
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=content,
                headers={"Retry-After": "1"},
            )
        except GatewayIngressError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "invalid Gateway webhook request"},
            )

        content = _receipt_content(receipt)
        content["status"] = "duplicate" if receipt.duplicate else "committed_local"
        response_status = status.HTTP_200_OK if receipt.duplicate else status.HTTP_201_CREATED
        return JSONResponse(status_code=response_status, content=content)

    return app


def _content_type(request: Request) -> str:
    value = request.headers.get("Content-Type", "")
    return value.partition(";")[0].strip().lower()


def _observed_at(request: Request) -> datetime | None:
    value = request.headers.get("X-ETS-Observed-At")
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GatewayIngressError("invalid source observation timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GatewayIngressError("source observation timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


async def _read_bounded_body(request: Request, maximum: int) -> bytes:
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise GatewayIngressError("invalid Content-Length") from exc
        if declared_length < 0:
            raise GatewayIngressError("invalid Content-Length")
        if declared_length > maximum:
            raise RequestBodyTooLarge("request body exceeds configured limit")

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > maximum:
            raise RequestBodyTooLarge("request body exceeds configured limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _receipt_content(receipt: GatewayIngressReceipt) -> dict[str, object]:
    return dict(asdict(receipt))
