"""Protected local HTTP boundary for the ETS Edge Virtual pilot.

The wrapper leaves UDP syslog semantics unchanged, requires the persisted local
API key for operator/webhook HTTP routes, and injects that key only on server-side
service-to-service calls. The Dark Pro browser uses a narrowly allow-listed UI
BFF and never receives or submits the reusable local API key.
"""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ets.edge.device_identity import load_device_identity, load_local_api_key
from ets.edge.webhook_adapter import app as ingress_app

DEFAULT_API_KEY_FILE = "/var/lib/ets/edge-local-api-key"
DEFAULT_DEVICE_IDENTITY_FILE = "/var/lib/ets/edge-device-identity.json"
DEFAULT_EDGE_API_ORIGIN = "http://edge-api:8000"
DEFAULT_UI_TENANT = "tenant_demo"
DEFAULT_UI_WORKSPACE = "workspace_alpha"
DEFAULT_UI_SOURCE_ID = "edge-dark-pro-demo"
INTERNAL_API_PREFIX = "/internal/edge-api"
UI_API_PREFIX = "/edge/ui/v1"
UI_REQUEST_HEADER = "X-ETS-UI-Request"
UI_MAX_BODY_BYTES = 128 * 1024
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

        if path == UI_API_PREFIX or path.startswith(UI_API_PREFIX + "/"):
            return await _handle_ui_request(request)

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


async def _handle_ui_request(request: Request) -> Response:
    if not _ui_enabled():
        return JSONResponse(status_code=404, content={"detail": "not found"})
    if not _valid_ui_request(request):
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "ETS_EDGE_UI_FORBIDDEN", "message": "request rejected"}},
        )

    path = request.url.path
    method = request.method.upper()
    suffix = path.removeprefix(UI_API_PREFIX)

    try:
        if method == "GET" and suffix == "/status":
            return JSONResponse(content=await _ui_status())

        if method == "GET" and suffix == "/events":
            return await _edge_api_json_response("GET", "/api/v1/events", params={"limit": "50", "offset": "0"})

        if method == "POST" and suffix == "/capture":
            body = await _bounded_json_body(request)
            if set(body) != {"payload"} or not isinstance(body["payload"], dict):
                return _ui_validation_error("payload must be a JSON object")
            payload = body["payload"]
            if len(json.dumps(payload, separators=(",", ":")).encode("utf-8")) > 16 * 1024:
                return _ui_validation_error("synthetic payload exceeds the 16 KiB demo limit")
            source_id = os.getenv("ETS_EDGE_UI_SOURCE_ID", DEFAULT_UI_SOURCE_ID).strip()
            if not source_id or len(source_id) > 64:
                return JSONResponse(status_code=503, content={"detail": "Edge UI source is misconfigured"})
            return await _ingress_json_response(
                "POST",
                f"/edge/v1/capture/webhook/{source_id}",
                body=payload,
                include_scope=True,
            )

        if method == "POST" and suffix == "/sync":
            body = await _bounded_json_body(request)
            if set(body) != {"limit"} or not isinstance(body["limit"], int):
                return _ui_validation_error("limit must be an integer")
            limit = body["limit"]
            if limit < 1 or limit > 500:
                return _ui_validation_error("limit must be between 1 and 500")
            return await _ingress_json_response(
                "POST",
                "/edge/v1/sync/run",
                params={"limit": str(limit)},
            )

        proof_prefix = "/proofs/inclusion/"
        if method == "GET" and suffix.startswith(proof_prefix):
            event_id = suffix.removeprefix(proof_prefix)
            if not _valid_identifier(event_id):
                return _ui_validation_error("event id is invalid")
            return await _edge_api_json_response(
                "GET",
                f"/api/v1/proofs/inclusion/{event_id}",
            )

        if method == "POST" and suffix == "/verify/inclusion":
            body = await _bounded_json_body(request)
            return await _edge_api_json_response("POST", "/api/v1/verify/inclusion", body=body)

        bundle_prefix = "/bundles/"
        if method == "GET" and suffix.startswith(bundle_prefix):
            event_id = suffix.removeprefix(bundle_prefix)
            if not _valid_identifier(event_id):
                return _ui_validation_error("event id is invalid")
            return await _edge_api_json_response("GET", f"/api/v1/bundles/{event_id}")
    except (RuntimeError, ValueError):
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "ETS_EDGE_UI_UNAVAILABLE", "message": "Edge UI service is unavailable"}},
        )
    except httpx.HTTPError:
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "ETS_EDGE_UI_UPSTREAM", "message": "Edge service is unavailable"}},
        )

    return JSONResponse(status_code=404, content={"detail": "not found"})


async def _ui_status() -> dict[str, Any]:
    identity = load_device_identity(_device_identity_path())
    health = await _edge_api_json("GET", "/health")
    ready = await _edge_api_json("GET", "/ready")
    tree_head = await _edge_api_json("GET", "/api/v1/log/head")
    sync = await _ingress_json("GET", "/edge/v1/sync/status")
    syslog = await _ingress_json("GET", "/edge/v1/syslog/status")
    return {
        "schema_version": "ets.edge.ui.status.v1",
        "health": health,
        "ready": ready,
        "tree_head": tree_head,
        "sync": sync,
        "syslog": syslog,
        "device_identity": identity,
        "fleet": {
            "enrollment_state": os.getenv("ETS_EDGE_FLEET_ENROLLMENT_STATE", "not_configured"),
            "heartbeat_state": os.getenv("ETS_EDGE_FLEET_HEARTBEAT_STATE", "not_configured"),
        },
    }


async def _edge_api_json_response(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> Response:
    response = await _edge_api_request(method, path, body=body, params=params)
    return _safe_json_response(response)


async def _edge_api_json(method: str, path: str) -> dict[str, Any]:
    response = await _edge_api_request(method, path)
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError("Edge API request failed")
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("Edge API returned an invalid response")
    return data


async def _edge_api_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> httpx.Response:
    if not path.startswith("/"):
        raise RuntimeError("invalid Edge API path")
    api_key = load_local_api_key(_api_key_path())
    headers = {
        "X-ETS-API-Key": api_key,
        "X-ETS-Tenant": _ui_tenant(),
        "X-ETS-Workspace": _ui_workspace(),
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    origin = os.getenv("ETS_EDGE_API_ORIGIN", DEFAULT_EDGE_API_ORIGIN).rstrip("/")
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.request(method, origin + path, headers=headers, params=params, json=body)


async def _ingress_json_response(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    include_scope: bool = False,
) -> Response:
    response = await _ingress_request(
        method,
        path,
        body=body,
        params=params,
        include_scope=include_scope,
    )
    return _safe_json_response(response)


async def _ingress_json(method: str, path: str) -> dict[str, Any]:
    response = await _ingress_request(method, path)
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError("Edge ingress request failed")
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("Edge ingress returned an invalid response")
    return data


async def _ingress_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    include_scope: bool = False,
) -> httpx.Response:
    if not path.startswith("/edge/v1/"):
        raise RuntimeError("invalid Edge ingress path")
    headers: dict[str, str] = {}
    if include_scope:
        headers["X-ETS-Tenant"] = _ui_tenant()
        headers["X-ETS-Workspace"] = _ui_workspace()
    if body is not None:
        headers["Content-Type"] = "application/json"
    transport = httpx.ASGITransport(app=ingress_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://edge-ingress.local") as client:
        return await client.request(method, path, headers=headers, params=params, json=body)


def _safe_json_response(response: httpx.Response) -> Response:
    try:
        data = response.json()
    except ValueError:
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "ETS_EDGE_UI_UPSTREAM", "message": "Edge service returned an invalid response"}},
        )
    if 200 <= response.status_code < 300:
        return JSONResponse(status_code=response.status_code, content=data)
    detail = "Edge operation failed"
    if isinstance(data, dict):
        candidate = data.get("detail")
        if isinstance(candidate, str) and len(candidate) <= 240:
            detail = candidate
        error = data.get("error")
        if isinstance(error, dict):
            candidate = error.get("message")
            if isinstance(candidate, str) and len(candidate) <= 240:
                detail = candidate
    return JSONResponse(
        status_code=response.status_code,
        content={"error": {"code": "ETS_EDGE_UI_OPERATION_FAILED", "message": detail}},
    )


async def _bounded_json_body(request: Request) -> dict[str, Any]:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > UI_MAX_BODY_BYTES:
                raise ValueError("request too large")
        except ValueError as exc:
            raise ValueError("invalid request size") from exc
    raw = await request.body()
    if len(raw) > UI_MAX_BODY_BYTES:
        raise ValueError("request too large")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON request") from exc
    if not isinstance(value, dict):
        raise ValueError("request body must be a JSON object")
    return value


def _valid_ui_request(request: Request) -> bool:
    if request.headers.get(UI_REQUEST_HEADER) != "1":
        return False
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None and fetch_site not in {"same-origin", "none"}:
        return False
    origin = request.headers.get("origin")
    if origin is not None:
        parsed = urlparse(origin)
        host = request.headers.get("host", "")
        if parsed.scheme not in {"http", "https"} or parsed.netloc != host:
            return False
    return True


def _valid_identifier(value: str) -> bool:
    if not value or len(value) > 160:
        return False
    return all(character.isalnum() or character in "-_.:" for character in value)


def _ui_validation_error(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "ETS_EDGE_UI_INVALID_REQUEST", "message": message}},
    )


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


def _ui_enabled() -> bool:
    return os.getenv("ETS_EDGE_UI_BFF_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def _ui_tenant() -> str:
    value = os.getenv("ETS_EDGE_UI_TENANT", DEFAULT_UI_TENANT).strip()
    if not value or len(value) > 128:
        raise RuntimeError("invalid Edge UI tenant")
    return value


def _ui_workspace() -> str:
    value = os.getenv("ETS_EDGE_UI_WORKSPACE", DEFAULT_UI_WORKSPACE).strip()
    if not value or len(value) > 128:
        raise RuntimeError("invalid Edge UI workspace")
    return value


# Wrap the original ingress ASGI app directly. BaseHTTPMiddleware passes
# non-HTTP ASGI scopes through to the child application, preserving the
# FastAPI lifespan that starts/stops the UDP syslog listener.
app = ProtectedEdgeMiddleware(ingress_app)
