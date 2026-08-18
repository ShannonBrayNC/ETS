"""Read-only, scope-authorized Microsoft operational-posture management surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol

from fastapi import APIRouter, HTTPException, Request, status

from ets.connectors.enterprise.microsoft_health import MicrosoftOperationalPostureV1
from ets.connectors.models import ConnectorInstanceV1
from ets.connectors.runtime import ConnectorRuntimeStateV1
from ets.connectors.runtime_store import ConnectorInstanceNotFoundError
from ets.gateway.connector_management import (
    ConnectorManagementAuthorizationError,
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)

MicrosoftPosturePrincipalResolver = Callable[[Request], ConnectorManagementPrincipal]


class MicrosoftOperationalPostureProvider(Protocol):
    """Server-owned provider for one qualified Microsoft connector family."""

    def read(
        self,
        instance: ConnectorInstanceV1,
        runtime: ConnectorRuntimeStateV1,
    ) -> MicrosoftOperationalPostureV1: ...


class MicrosoftOperationalPostureUnavailableError(RuntimeError):
    """Raised when no qualified posture provider exists for a connector instance."""


class MicrosoftOperationalPostureScopeError(RuntimeError):
    """Raised when a provider returns posture for a different authoritative scope."""


class GatewayMicrosoftOperationalPostureService:
    """Authorize and return Microsoft posture without mutating connector runtime state."""

    def __init__(
        self,
        *,
        management: ConnectorManagementService,
        providers: Mapping[str, MicrosoftOperationalPostureProvider],
    ) -> None:
        self._management = management
        self._providers = dict(providers)
        if any(not connector_id for connector_id in self._providers):
            raise ValueError("Microsoft posture provider connector ids must not be empty")

    def get(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
    ) -> MicrosoftOperationalPostureV1:
        """Return one posture after existing connector read authorization and scope checks."""

        record = self._management.get_instance(principal, instance_id)
        runtime = self._management.get_runtime(principal, instance_id)
        instance = record.instance
        provider = self._providers.get(instance.connector_id)
        if provider is None:
            raise MicrosoftOperationalPostureUnavailableError(
                "Microsoft operational posture is not qualified for this connector"
            )
        posture = provider.read(instance, runtime)
        self._validate_returned_scope(principal, instance, runtime, posture)
        return posture

    @staticmethod
    def _validate_returned_scope(
        principal: ConnectorManagementPrincipal,
        instance: ConnectorInstanceV1,
        runtime: ConnectorRuntimeStateV1,
        posture: MicrosoftOperationalPostureV1,
    ) -> None:
        if posture.instance_id != instance.instance_id or posture.instance_id != runtime.instance_id:
            raise MicrosoftOperationalPostureScopeError(
                "Microsoft posture instance does not match authorized connector runtime"
            )
        if (
            posture.ets_tenant_id != instance.scope.tenant_id
            or posture.workspace_id != instance.scope.workspace_id
        ):
            raise MicrosoftOperationalPostureScopeError(
                "Microsoft posture tenant/workspace does not match authorized connector scope"
            )
        if (
            posture.ets_tenant_id != principal.tenant_id
            or posture.workspace_id != principal.workspace_id
        ):
            raise MicrosoftOperationalPostureScopeError(
                "Microsoft posture scope does not match authenticated management principal"
            )


def create_microsoft_operational_posture_router(
    service: GatewayMicrosoftOperationalPostureService,
    principal_resolver: MicrosoftPosturePrincipalResolver,
) -> APIRouter:
    """Create the read-only Microsoft posture route under the connector management prefix."""

    router = APIRouter(prefix="/gateway/connectors/v1", tags=["gateway-connectors"])

    def principal(request: Request) -> ConnectorManagementPrincipal:
        try:
            return principal_resolver(request)
        except ConnectorManagementAuthorizationError as exc:
            raise _exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.get(
        "/instances/{instance_id}/microsoft/posture",
        response_model=MicrosoftOperationalPostureV1,
    )
    def get_posture(request: Request, instance_id: str) -> MicrosoftOperationalPostureV1:
        try:
            return service.get(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise _exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc
        except MicrosoftOperationalPostureUnavailableError as exc:
            raise _exception(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
                category="configuration_policy",
                code="microsoft_posture_unavailable",
            ) from exc
        except MicrosoftOperationalPostureScopeError as exc:
            raise _exception(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
                category="gateway_runtime",
                code="microsoft_posture_scope_mismatch",
            ) from exc
        except RuntimeError as exc:
            raise _exception(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
                category="gateway_runtime",
                code="microsoft_posture_dependency_unavailable",
            ) from exc

    return router


def _exception(
    *,
    status_code: int,
    detail: str,
    category: str,
    code: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={
            "X-ETS-Connector-Diagnostic-Schema": "ets.connector.diagnostic.v1",
            "X-ETS-Connector-Diagnostic-Category": category,
            "X-ETS-Connector-Diagnostic-Code": code,
        },
    )
