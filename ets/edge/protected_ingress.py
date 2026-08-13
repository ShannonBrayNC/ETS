"""Protected local HTTP boundary for the ETS Edge Virtual pilot.

The wrapper leaves UDP syslog semantics unchanged, requires the persisted local
API key for operator/webhook HTTP routes, and injects that key only on loopback
service-to-service calls from the ingress process to the protected ETS API.
"""

from __future__ import annotations

import hmac
import os
from pathlib import Path

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ets.edge.device_identity import load_device_identity, load_local_api_key
from ets.edge.webhook_adapter import app

DEFAULT_API_KEY_FILE = "/var/lib/ets/edge-local-api-key"
DEFAULT_DEVICE_IDENTITY_FILE = "/var/lib/ets/edge-device-identity.json"
DEFAULT_EDGE_API_ORIGIN = "http://edge-api:8000"
INTERNAL_API_PREFIX = "/internal/edge-api"
PROTECTED_PREFIXES = (
    "/edge/v1/capture/",
    "/edge/v1/sync/",
    "/edge/v1/syslog/",
)


class ProtectedEdgeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path.startswith(INTERNAL_API_PREFIX + "/"):
            if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
                return JSONResponse(status_code=404, content={"detail": "not found"})
            return await _proxy_to_edge_api(request)

        if path == "/edge/v1/device/identity":
            if request.method != "GET":
                return JSONResponse(status_code=405, content={"detail": "method not allowed"})
            try:
                identity = load_device_identity(_device_identity_path())
            except (RuntimeError, ValueError) as exc:
                return JSONResponse(
                    status_code=503,
                    content={"detail": f"device identity unavailable: {type(exc).__name__}"},
                )
            return JSONResponse(content=dict(identity))

        if any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES):
            try:
                expected = load_local_api_key(_api_key_path())
            except RuntimeError:
                return _auth_error("local API key is unavailable")
            provided = request.headers.get("X-ETS-API-Key")
            if provided is None or not hmac.compare_digest(provided, expected):
                return _auth_error("invalid local API key")

        return await call_next(request)


async def _proxy_to_edge_api(request: Request) -> Response:
    api_key = load_local_api_key(_api_key_path())
    suffix = request.url.path.removeprefix(INTERNAL_API_PREFIX)
    if not suffix.startswith("/"):
        return JSONResponse(status_code=404, content={"detail": "not found"})

    headers: dict[str, str] = {"X-ETS-API-Key": api_key}
    for header_name in (
        "Content-Type",
        "X-ETS-Tenant",
        "X-ETS-Workspace",
        "X-Correlation-ID",
    ):
        value = request.headers.get(header_name)
        if value is not None:
            headers[header_name] = value

    origin = os.getenv("ETS_EDGE_API_ORIGIN", DEFAULT_EDGE_API_ORIGIN).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                request.method,
                origin + suffix,
                headers=headers,
                params=request.query_params,
                content=await request.body(),
            )
    except httpx.HTTPError:
        return JSONResponse(status_code=502, content={"detail": "ETS Edge API is unavailable"})

    response_headers: dict[str, str] = {}
    content_type = response.headers.get("content-type")
    if content_type is not None:
        response_headers["content-type"] = content_type
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )


def _auth_error(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "ETS_EDGE_AUTH_REQUIRED",
                "message": message,
            }
        },
    )


def _api_key_path() -> Path:
    return Path(os.getenv("ETS_EDGE_API_KEY_FILE", DEFAULT_API_KEY_FILE))


def _device_identity_path() -> Path:
    return Path(os.getenv("ETS_EDGE_DEVICE_IDENTITY_FILE", DEFAULT_DEVICE_IDENTITY_FILE))


app.add_middleware(ProtectedEdgeMiddleware)
