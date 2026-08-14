"""Bounded Microsoft Purview Management Activity webhook discovery host for G2E-E."""

from __future__ import annotations

import asyncio
import hmac
import json
from collections.abc import Iterable
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response

from ets.connectors.enterprise.microsoft_purview_activity import (
    PURVIEW_CONTENT_TYPES,
    MicrosoftPurviewActivityError,
    MicrosoftPurviewContentDescriptorV1,
    MicrosoftPurviewDiscoveryPageV1,
    MicrosoftPurviewManagementProfile,
    PurviewContentType,
    parse_purview_discovery_page,
)
from ets.gateway.host import (
    GatewayHostController,
    GatewayHostLimitError,
    GatewayHostSaturatedError,
    UnsupportedContentEncodingError,
)

PURVIEW_WEBHOOK_PATH = "/gateway/v1/microsoft/purview/activity"
PURVIEW_WEBHOOK_DEFAULT_MAXIMUM_BODY_BYTES = 512 * 1024
PURVIEW_WEBHOOK_DEFAULT_MAXIMUM_DESCRIPTORS = 1000
PURVIEW_WEBHOOK_VALIDATION_CODE_MAXIMUM_CHARACTERS = 1000
PURVIEW_WEBHOOK_AUTH_ID_MAXIMUM_CHARACTERS = 500


class MicrosoftPurviewWebhookError(ValueError):
    """Raised when a Purview webhook request violates the qualified profile."""


class MicrosoftPurviewWebhookBodyTooLarge(MicrosoftPurviewWebhookError):
    """Raised when the webhook body exceeds its configured byte bound."""


class MicrosoftPurviewWebhookSinkError(RuntimeError):
    """Raised when an operational discovery sink cannot persist the signal."""


class MicrosoftPurviewDiscoverySink(Protocol):
    """Operational sink for content-discovery state; never ETS evidence persistence."""

    def record(self, page: MicrosoftPurviewDiscoveryPageV1) -> None: ...


@dataclass(frozen=True, slots=True)
class PurviewDiscoverySnapshot:
    descriptors: tuple[MicrosoftPurviewContentDescriptorV1, ...]


class InMemoryMicrosoftPurviewDiscoverySink:
    """Thread-safe discovery sink for tests and explicit local composition."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_content_id: dict[str, MicrosoftPurviewContentDescriptorV1] = {}

    def record(self, page: MicrosoftPurviewDiscoveryPageV1) -> None:
        with self._lock:
            for descriptor in page.descriptors:
                existing = self._by_content_id.get(descriptor.content_id)
                if existing is None:
                    self._by_content_id[descriptor.content_id] = descriptor
                elif existing != descriptor:
                    raise MicrosoftPurviewWebhookSinkError(
                        "Purview discovery contentId conflicts with persisted operational state"
                    )

    def snapshot(self) -> PurviewDiscoverySnapshot:
        with self._lock:
            return PurviewDiscoverySnapshot(tuple(self._by_content_id.values()))


def create_microsoft_purview_webhook_app(
    profile: MicrosoftPurviewManagementProfile,
    discovery_sink: MicrosoftPurviewDiscoverySink,
    *,
    allowed_content_types: Iterable[PurviewContentType],
    webhook_auth_id: str | None = None,
    host_controller: GatewayHostController | None = None,
    maximum_body_bytes: int = PURVIEW_WEBHOOK_DEFAULT_MAXIMUM_BODY_BYTES,
    maximum_descriptors: int = PURVIEW_WEBHOOK_DEFAULT_MAXIMUM_DESCRIPTORS,
) -> FastAPI:
    """Create a webhook host that records discovery state without claiming evidence."""

    allowed = frozenset(allowed_content_types)
    if not allowed or not allowed <= PURVIEW_CONTENT_TYPES:
        raise ValueError("Purview webhook allowed_content_types must be a non-empty approved set")
    if webhook_auth_id is not None and not 1 <= len(webhook_auth_id) <= 500:
        raise ValueError("Purview webhook authId is outside the qualified bound")
    if not 1 <= maximum_body_bytes <= PURVIEW_WEBHOOK_DEFAULT_MAXIMUM_BODY_BYTES:
        raise ValueError("Purview webhook maximum_body_bytes exceeds qualified bound")
    if not 1 <= maximum_descriptors <= PURVIEW_WEBHOOK_DEFAULT_MAXIMUM_DESCRIPTORS:
        raise ValueError("Purview webhook maximum_descriptors exceeds qualified bound")

    app = FastAPI(title="ETS Gateway Microsoft Purview Webhook", version="0.1.0-g2e-e")
    host = host_controller or GatewayHostController()

    @app.post(PURVIEW_WEBHOOK_PATH)
    async def receive_purview_webhook(request: Request) -> Response:
        try:
            host.validate_headers(request.scope.get("headers", ()))
            host.validate_content_encoding(request.headers.get("Content-Encoding"))
            async with host.admission():
                _validate_auth_id(request, webhook_auth_id)
                body = await _read_bounded_body(request, maximum_body_bytes)
                validation = _parse_validation_request(request, body)
                if validation:
                    return Response(status_code=status.HTTP_200_OK)

                _validate_json_content_type(request)
                pages = _parse_discovery_pages(
                    body,
                    profile,
                    allowed,
                    maximum_descriptors=maximum_descriptors,
                )
                for page in pages:
                    await asyncio.to_thread(discovery_sink.record, page)

        except UnsupportedContentEncodingError:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"detail": "Purview webhook content encoding is not qualified"},
            )
        except GatewayHostLimitError:
            return JSONResponse(
                status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE,
                content={"detail": "Purview webhook headers exceed configured host limits"},
            )
        except GatewayHostSaturatedError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Purview webhook host concurrency is saturated"},
                headers={"Retry-After": "1"},
            )
        except MicrosoftPurviewWebhookBodyTooLarge:
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Purview webhook body exceeds configured limit"},
            )
        except MicrosoftPurviewWebhookSinkError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Purview discovery state is temporarily unavailable"},
                headers={"Retry-After": "1"},
            )
        except (MicrosoftPurviewWebhookError, MicrosoftPurviewActivityError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "invalid Microsoft Purview webhook request"},
            )

        return Response(status_code=status.HTTP_200_OK)

    return app


def _validate_auth_id(request: Request, expected: str | None) -> None:
    supplied = request.headers.get("Webhook-AuthID")
    if expected is None:
        if supplied is not None:
            raise MicrosoftPurviewWebhookError(
                "Purview webhook supplied an unexpected authId"
            )
        return
    if supplied is None or not hmac.compare_digest(supplied, expected):
        raise MicrosoftPurviewWebhookError("Purview webhook authId does not match")


def _parse_validation_request(request: Request, body: bytes) -> bool:
    header_code = request.headers.get("Webhook-ValidationCode")
    if header_code is None:
        return False
    if not 1 <= len(header_code) <= PURVIEW_WEBHOOK_VALIDATION_CODE_MAXIMUM_CHARACTERS:
        raise MicrosoftPurviewWebhookError("Purview webhook validation code is invalid")
    _validate_json_content_type(request)
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftPurviewWebhookError(
            "Purview webhook validation body is not valid JSON"
        ) from exc
    if not isinstance(decoded, dict) or set(decoded) != {"validationCode"}:
        raise MicrosoftPurviewWebhookError(
            "Purview webhook validation body must contain only validationCode"
        )
    body_code = decoded.get("validationCode")
    if not isinstance(body_code, str) or not hmac.compare_digest(body_code, header_code):
        raise MicrosoftPurviewWebhookError(
            "Purview webhook validation body/header codes do not match"
        )
    return True


def _parse_discovery_pages(
    body: bytes,
    profile: MicrosoftPurviewManagementProfile,
    allowed: frozenset[str],
    *,
    maximum_descriptors: int,
) -> tuple[MicrosoftPurviewDiscoveryPageV1, ...]:
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftPurviewWebhookError(
            "Purview webhook discovery body is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(decoded, list):
        raise MicrosoftPurviewWebhookError("Purview webhook discovery body must be an array")
    if len(decoded) > maximum_descriptors:
        raise MicrosoftPurviewWebhookError(
            "Purview webhook discovery body exceeds configured descriptor bound"
        )

    grouped: dict[str, list[object]] = {}
    for raw in decoded:
        if not isinstance(raw, dict):
            raise MicrosoftPurviewWebhookError(
                "Purview webhook discovery array contains a non-object value"
            )
        content_type = raw.get("contentType")
        if not isinstance(content_type, str) or content_type not in allowed:
            raise MicrosoftPurviewWebhookError(
                "Purview webhook discovery content type is not approved"
            )
        grouped.setdefault(content_type, []).append(raw)

    pages: list[MicrosoftPurviewDiscoveryPageV1] = []
    for content_type, records in grouped.items():
        pages.append(
            parse_purview_discovery_page(
                records,
                profile,
                content_type,  # type: ignore[arg-type]
                discovery_source="webhook",
                maximum_records=maximum_descriptors,
            )
        )
    return tuple(pages)


def _validate_json_content_type(request: Request) -> None:
    media_type = request.headers.get("Content-Type", "").partition(";")[0].strip().lower()
    if media_type != "application/json":
        raise MicrosoftPurviewWebhookError(
            "Purview webhook requires application/json"
        )


async def _read_bounded_body(request: Request, maximum: int) -> bytes:
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise MicrosoftPurviewWebhookError(
                "Purview webhook Content-Length is invalid"
            ) from exc
        if declared_length < 0:
            raise MicrosoftPurviewWebhookError(
                "Purview webhook Content-Length is invalid"
            )
        if declared_length > maximum:
            raise MicrosoftPurviewWebhookBodyTooLarge(
                "Purview webhook body exceeds configured limit"
            )

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > maximum:
            raise MicrosoftPurviewWebhookBodyTooLarge(
                "Purview webhook body exceeds configured limit"
            )
        chunks.append(chunk)
    return b"".join(chunks)
