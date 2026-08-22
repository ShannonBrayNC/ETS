"""Authenticated BFF routes for the ETS Fleet Dark Pro read portal."""

from __future__ import annotations

from collections.abc import Callable
from typing import NoReturn

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response

from ets.fleet.portal import FleetPortalNotFound, FleetPortalService, FleetPrincipal
from ets.fleet.portal_assets import (
    FLEET_DARK_PRO_CSS,
    FLEET_DARK_PRO_HTML,
    FLEET_DARK_PRO_JS,
)

PrincipalResolver = Callable[[Request], FleetPrincipal | None]

_SECURITY_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
        "object-src 'none'; form-action 'self'; script-src 'self'; "
        "style-src 'self'; connect-src 'self'; img-src 'self' data:"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "serial=(), bluetooth=()"
    ),
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def build_fleet_portal_router(
    *,
    service: FleetPortalService,
    principal_resolver: PrincipalResolver,
) -> APIRouter:
    """Build read-only Fleet portal routes behind a trusted Entra session resolver."""

    router = APIRouter(tags=["fleet-portal"])

    @router.get("/fleet", include_in_schema=False)
    @router.get("/fleet/", include_in_schema=False)
    def portal_shell(request: Request) -> HTMLResponse:
        _require_principal(request, principal_resolver)
        return HTMLResponse(FLEET_DARK_PRO_HTML, headers=_SECURITY_HEADERS)

    @router.get("/fleet/assets/app.css", include_in_schema=False)
    def portal_css(request: Request) -> Response:
        _require_principal(request, principal_resolver)
        return Response(
            FLEET_DARK_PRO_CSS,
            media_type="text/css",
            headers=_SECURITY_HEADERS,
        )

    @router.get("/fleet/assets/app.js", include_in_schema=False)
    def portal_js(request: Request) -> Response:
        _require_principal(request, principal_resolver)
        return Response(
            FLEET_DARK_PRO_JS,
            media_type="application/javascript",
            headers=_SECURITY_HEADERS,
        )

    @router.get("/fleet/bff/v1/session")
    def session(request: Request) -> JSONResponse:
        principal = _require_principal(request, principal_resolver)
        return _json(
            {
                "subject": principal.subject,
                "roles": [item.value for item in principal.roles],
                "capabilities": [item.value for item in principal.capabilities],
                "authorized_scope_count": len(principal.scope_bindings),
            }
        )

    @router.get("/fleet/bff/v1/overview")
    def overview(request: Request) -> JSONResponse:
        principal = _require_principal(request, principal_resolver)
        return _json(service.overview(principal).model_dump(mode="json"))

    @router.get("/fleet/bff/v1/devices")
    def devices(
        request: Request,
        offset: int = Query(default=0, ge=0, le=100_000),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> JSONResponse:
        principal = _require_principal(request, principal_resolver)
        try:
            page = service.list_devices(principal, offset=offset, limit=limit)
        except ValueError:
            _raise_sanitized(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "ETS_FLEET_QUERY_INVALID",
            )
        return _json(page.model_dump(mode="json"))

    @router.get("/fleet/bff/v1/devices/{device_id}")
    def device_detail(request: Request, device_id: str) -> JSONResponse:
        principal = _require_principal(request, principal_resolver)
        if not device_id or len(device_id) > 160:
            _raise_sanitized(
                status.HTTP_404_NOT_FOUND,
                "ETS_FLEET_DEVICE_NOT_FOUND",
            )
        try:
            detail = service.get_device(principal, device_id)
        except FleetPortalNotFound:
            _raise_sanitized(
                status.HTTP_404_NOT_FOUND,
                "ETS_FLEET_DEVICE_NOT_FOUND",
            )
        return _json(detail.model_dump(mode="json"))

    return router


def _require_principal(
    request: Request,
    resolver: PrincipalResolver,
) -> FleetPrincipal:
    try:
        principal = resolver(request)
    except (TypeError, ValueError):
        principal = None
    if principal is None:
        _raise_sanitized(
            status.HTTP_401_UNAUTHORIZED,
            "ETS_FLEET_AUTHENTICATION_REQUIRED",
        )
    return principal


def _raise_sanitized(status_code: int, code: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code},
        headers=dict(_SECURITY_HEADERS),
    )


def _json(content: object) -> JSONResponse:
    return JSONResponse(content=content, headers=_SECURITY_HEADERS)
