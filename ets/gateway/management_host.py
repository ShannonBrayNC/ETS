"""Authenticated Gateway management host for Connector Console and administration."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from ets.api.auth import AuthContext, AuthError, AuthPolicy, LocalHeaderAuthPolicy
from ets.api.authorization import AuthCapability, AuthorizationProfile, AuthRole
from ets.gateway.connector_management import (
    ConnectorManagementAuthorizationError,
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.connector_management_api import create_connector_management_router
from ets.gateway.microsoft_operational_posture_api import (
    GatewayMicrosoftOperationalPostureService,
    create_microsoft_operational_posture_router,
)


class GatewayAuthorizationContextV2(BaseModel):
    """Server-derived identity and authorization context consumed by production Console."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.gateway.authorization_context.v2"]
    mode: str
    subject: str
    tenant_id: str
    workspace_id: str
    roles: tuple[AuthRole, ...]
    capabilities: tuple[AuthCapability, ...]
    authorization_profile: AuthorizationProfile


def create_gateway_management_app(
    service: ConnectorManagementService,
    *,
    auth_policy: AuthPolicy | None = None,
    auth_mode: str = "local_header",
    microsoft_posture_service: GatewayMicrosoftOperationalPostureService | None = None,
) -> FastAPI:
    """Create the authenticated Gateway connector-management application."""

    request_auth_policy = auth_policy or LocalHeaderAuthPolicy()
    app = FastAPI(
        title="ETS Gateway Management API",
        version="0.1.0-g2c",
        description="Authenticated management surface for ETS Gateway connector instances.",
    )

    def auth_context(request: Request) -> AuthContext:
        try:
            return request_auth_policy.authenticate(request)
        except AuthError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    def principal(request: Request) -> ConnectorManagementPrincipal:
        context = auth_context(request)
        subject, tenant_id, workspace_id = _resolved_identity_scope(request, context)
        return ConnectorManagementPrincipal(
            actor_id=subject,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            can_read=context.has_capability("connector.read"),
            can_manage=context.has_capability("connector.manage"),
        )

    @app.get("/api/v2/auth/context", response_model=GatewayAuthorizationContextV2, tags=["auth"])
    def authorization_context(request: Request) -> GatewayAuthorizationContextV2:
        context = auth_context(request)
        try:
            subject, tenant_id, workspace_id = _resolved_identity_scope(request, context)
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return GatewayAuthorizationContextV2(
            schema_version="ets.gateway.authorization_context.v2",
            mode=auth_mode,
            subject=subject,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            roles=context.roles,
            capabilities=context.capabilities,
            authorization_profile=context.authorization_profile,
        )

    app.include_router(create_connector_management_router(service, principal))
    if microsoft_posture_service is not None:
        app.include_router(
            create_microsoft_operational_posture_router(microsoft_posture_service, principal)
        )
    return app


def _resolved_identity_scope(request: Request, context: AuthContext) -> tuple[str, str, str]:
    subject = context.subject
    tenant_id = context.tenant_id
    workspace_id = context.workspace_id

    if context.authorization_profile == "local_nonproduction":
        tenant_id = tenant_id or request.headers.get("X-ETS-Tenant")
        workspace_id = workspace_id or request.headers.get("X-ETS-Workspace")
    else:
        _reject_scope_override(request, "X-ETS-Tenant", tenant_id)
        _reject_scope_override(request, "X-ETS-Workspace", workspace_id)

    if subject is None or tenant_id is None or workspace_id is None:
        raise ConnectorManagementAuthorizationError(
            "Gateway management requires authenticated subject, tenant, and workspace scope"
        )
    return subject, tenant_id, workspace_id


def _reject_scope_override(request: Request, header_name: str, authoritative: str | None) -> None:
    supplied = request.headers.get(header_name)
    if supplied is not None and supplied != authoritative:
        raise ConnectorManagementAuthorizationError(
            "browser-supplied scope does not match server-derived authorization scope"
        )
