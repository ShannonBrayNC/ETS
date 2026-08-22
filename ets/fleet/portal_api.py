"""Authenticated BFF routes for the ETS Fleet Dark Pro portal."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import NoReturn

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, ValidationError

from ets.fleet.models import EnrollmentValidationError
from ets.fleet.portal import FleetPortalNotFound, FleetPortalService, FleetPrincipal
from ets.fleet.portal_admin import (
    FleetAdminAction,
    FleetAdminConfirmationError,
    FleetAdminForbidden,
    FleetAdminIdempotencyConflict,
    FleetAdminNotFound,
    FleetAdminStepUpRequired,
    FleetPortalAdminService,
    FleetSecuritySession,
)
from ets.fleet.portal_admin_durable import (
    FleetAdminDurabilityError,
    FleetAdminMutationPending,
)
from ets.fleet.portal_assets import (
    FLEET_DARK_PRO_CSS,
    FLEET_DARK_PRO_HTML,
    FLEET_DARK_PRO_JS,
)
from ets.fleet.store import EnrollmentStoreConflict

PrincipalResolver = Callable[[Request], FleetPrincipal | None]
SecuritySessionResolver = Callable[[Request], FleetSecuritySession | None]
MutationRateLimiter = Callable[[FleetPrincipal, FleetAdminAction], bool]
_MAX_MUTATION_BODY_BYTES = 4096

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


class FleetMutationBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    confirmation: str | None = None
    replacement_enrollment_id: str | None = None
    overlap_expires_at_utc: datetime | None = None


class FleetPortalReadiness(BaseModel):
    """Safe production readiness dimensions; never a device/trust/proof claim."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    auth_config_ready: bool
    store_ready: bool

    @property
    def ready(self) -> bool:
        return self.auth_config_ready and self.store_ready


ReadinessProbe = Callable[[], FleetPortalReadiness]


def build_fleet_portal_router(
    *,
    service: FleetPortalService,
    principal_resolver: PrincipalResolver,
    admin_service: FleetPortalAdminService | None = None,
    security_session_resolver: SecuritySessionResolver | None = None,
    mutation_rate_limiter: MutationRateLimiter | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> APIRouter:
    """Build Fleet portal routes behind trusted Entra/session boundaries."""

    if (admin_service is None) != (security_session_resolver is None):
        raise ValueError(
            "Fleet C2 requires both admin_service and security_session_resolver"
        )

    router = APIRouter(tags=["fleet-portal"])

    if readiness_probe is not None:

        @router.get("/fleet/readyz", include_in_schema=False)
        def production_readiness() -> JSONResponse:
            try:
                readiness = readiness_probe()
            except Exception:
                readiness = FleetPortalReadiness(
                    auth_config_ready=False,
                    store_ready=False,
                )
            payload = {
                "ready": readiness.ready,
                "process_ready": True,
                "auth_config_ready": readiness.auth_config_ready,
                "store_ready": readiness.store_ready,
                "evidence_verified": False,
                "health_asserted": False,
            }
            return JSONResponse(
                status_code=(
                    status.HTTP_200_OK
                    if readiness.ready
                    else status.HTTP_503_SERVICE_UNAVAILABLE
                ),
                content=payload,
                headers=_SECURITY_HEADERS,
            )

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

    if admin_service is not None and security_session_resolver is not None:

        @router.post("/fleet/bff/v1/devices/{device_id}/actions/{action}")
        async def mutate_device(
            request: Request,
            device_id: str,
            action: FleetAdminAction,
        ) -> JSONResponse:
            principal = _require_principal(request, principal_resolver)
            security_session = _require_security_session(
                request,
                security_session_resolver,
            )
            if mutation_rate_limiter is not None and not mutation_rate_limiter(
                principal,
                action,
            ):
                _raise_sanitized(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "ETS_FLEET_MUTATION_RATE_LIMITED",
                )

            csrf_token = request.headers.get("X-CSRF-Token", "")
            idempotency_key = request.headers.get("Idempotency-Key", "")
            body = await _bounded_body(request, _MAX_MUTATION_BODY_BYTES)
            try:
                payload = FleetMutationBody.model_validate_json(body or b"{}")
            except ValidationError:
                _raise_sanitized(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "ETS_FLEET_MUTATION_INVALID",
                )

            try:
                result = admin_service.mutate(
                    principal=principal,
                    security_session=security_session,
                    action=action,
                    device_id=device_id,
                    idempotency_key=idempotency_key,
                    csrf_token=csrf_token,
                    confirmation=payload.confirmation,
                    replacement_enrollment_id=payload.replacement_enrollment_id,
                    overlap_expires_at_utc=payload.overlap_expires_at_utc,
                )
            except FleetAdminNotFound:
                _raise_sanitized(
                    status.HTTP_404_NOT_FOUND,
                    "ETS_FLEET_DEVICE_NOT_FOUND",
                )
            except FleetAdminStepUpRequired:
                _raise_sanitized(
                    status.HTTP_403_FORBIDDEN,
                    "ETS_FLEET_STEP_UP_REQUIRED",
                )
            except FleetAdminForbidden:
                _raise_sanitized(
                    status.HTTP_403_FORBIDDEN,
                    "ETS_FLEET_MUTATION_FORBIDDEN",
                )
            except FleetAdminIdempotencyConflict:
                _raise_sanitized(
                    status.HTTP_409_CONFLICT,
                    "ETS_FLEET_IDEMPOTENCY_CONFLICT",
                )
            except FleetAdminMutationPending:
                _raise_sanitized(
                    status.HTTP_409_CONFLICT,
                    "ETS_FLEET_RECONCILIATION_REQUIRED",
                )
            except FleetAdminConfirmationError:
                _raise_sanitized(
                    status.HTTP_409_CONFLICT,
                    "ETS_FLEET_CONFIRMATION_REQUIRED",
                )
            except EnrollmentStoreConflict:
                _raise_sanitized(
                    status.HTTP_409_CONFLICT,
                    "ETS_FLEET_CONCURRENT_UPDATE",
                )
            except EnrollmentValidationError:
                _raise_sanitized(
                    status.HTTP_409_CONFLICT,
                    "ETS_FLEET_LIFECYCLE_CONFLICT",
                )
            except FleetAdminDurabilityError:
                _raise_sanitized(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "ETS_FLEET_DURABILITY_UNAVAILABLE",
                )
            except ValueError:
                _raise_sanitized(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "ETS_FLEET_MUTATION_INVALID",
                )
            return _json(result.model_dump(mode="json"))

        @router.get("/fleet/bff/v1/audit")
        def audit_export(
            request: Request,
            limit: int = Query(default=200, ge=1, le=1000),
        ) -> JSONResponse:
            principal = _require_principal(request, principal_resolver)
            try:
                records = admin_service.audit_export(principal, limit=limit)
            except FleetAdminDurabilityError:
                _raise_sanitized(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "ETS_FLEET_DURABILITY_UNAVAILABLE",
                )
            except ValueError:
                _raise_sanitized(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "ETS_FLEET_QUERY_INVALID",
                )
            return _json(
                {
                    "schema_version": "ets.fleet.admin.audit-export.v1",
                    "records": [item.model_dump(mode="json") for item in records],
                }
            )

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


def _require_security_session(
    request: Request,
    resolver: SecuritySessionResolver,
) -> FleetSecuritySession:
    try:
        security_session = resolver(request)
    except (TypeError, ValueError):
        security_session = None
    if security_session is None:
        _raise_sanitized(
            status.HTTP_401_UNAUTHORIZED,
            "ETS_FLEET_SESSION_REQUIRED",
        )
    return security_session


async def _bounded_body(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > limit:
                _raise_sanitized(
                    status.HTTP_413_CONTENT_TOO_LARGE,
                    "ETS_FLEET_MUTATION_TOO_LARGE",
                )
        except ValueError:
            _raise_sanitized(
                status.HTTP_400_BAD_REQUEST,
                "ETS_FLEET_CONTENT_LENGTH_INVALID",
            )
    body = await request.body()
    if len(body) > limit:
        _raise_sanitized(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "ETS_FLEET_MUTATION_TOO_LARGE",
        )
    return body


def _raise_sanitized(status_code: int, code: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={"code": code},
        headers=dict(_SECURITY_HEADERS),
    )


def _json(content: object) -> JSONResponse:
    return JSONResponse(content=content, headers=_SECURITY_HEADERS)
