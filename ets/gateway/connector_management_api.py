"""Versioned FastAPI router for governed Gateway connector management."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from ets.connectors.models import ConnectorCheckpointV1, ConnectorHealthV1, ConnectorInstanceV1
from ets.connectors.registry import ConnectorRegistryError
from ets.connectors.runtime import (
    ConnectorInstanceRecordV1,
    ConnectorObservationState,
    ConnectorRuntimeStateV1,
)
from ets.connectors.runtime_store import (
    ConnectorInstanceExistsError,
    ConnectorInstanceNotFoundError,
    ConnectorRevisionConflictError,
)
from ets.gateway.connector_management import (
    ConnectorManagementAuthorizationError,
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)

ConnectorPrincipalResolver = Callable[[Request], ConnectorManagementPrincipal]
ConnectorDiagnosticCategory = Literal[
    "authorization",
    "configuration_policy",
    "source_authentication",
    "source_availability",
    "collection_continuity",
    "gateway_runtime",
    "upstream_sync",
]

CONNECTOR_DIAGNOSTIC_SCHEMA_VERSION = "ets.connector.diagnostic.v1"
_DIAGNOSTIC_SCHEMA_HEADER = "X-ETS-Connector-Diagnostic-Schema"
_DIAGNOSTIC_CATEGORY_HEADER = "X-ETS-Connector-Diagnostic-Category"
_DIAGNOSTIC_CODE_HEADER = "X-ETS-Connector-Diagnostic-Code"


class StrictManagementModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ConnectorInstanceListResponse(StrictManagementModel):
    items: tuple[ConnectorInstanceRecordV1, ...]


class ConnectorInstanceUpdateRequest(StrictManagementModel):
    instance: ConnectorInstanceV1
    expected_revision: int = Field(ge=1)


class ConnectorRevisionRequest(StrictManagementModel):
    expected_revision: int = Field(ge=1)


class ConnectorCheckpointUpdateRequest(StrictManagementModel):
    checkpoint: ConnectorCheckpointV1 | None = None
    expected_checkpoint_revision: int = Field(ge=0)
    observation_state: ConnectorObservationState
    gap_open: bool
    last_success_at_utc: datetime | None = None


def _diagnostic_exception(
    *,
    status_code: int,
    detail: str,
    category: ConnectorDiagnosticCategory,
    code: str,
) -> HTTPException:
    """Preserve the existing response body while adding bounded machine-readable diagnostics."""

    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={
            _DIAGNOSTIC_SCHEMA_HEADER: CONNECTOR_DIAGNOSTIC_SCHEMA_VERSION,
            _DIAGNOSTIC_CATEGORY_HEADER: category,
            _DIAGNOSTIC_CODE_HEADER: code,
        },
    )


def create_connector_management_router(
    service: ConnectorManagementService,
    principal_resolver: ConnectorPrincipalResolver,
) -> APIRouter:
    """Create the G2C router with authentication supplied by the outer Gateway host."""

    router = APIRouter(prefix="/gateway/connectors/v1", tags=["gateway-connectors"])

    def principal(request: Request) -> ConnectorManagementPrincipal:
        try:
            return principal_resolver(request)
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.get("/catalog")
    def catalog(request: Request) -> tuple[object, ...]:
        try:
            definitions = service.catalog(principal(request))
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc
        return tuple(item.model_dump(mode="json") for item in definitions)

    @router.get("/instances", response_model=ConnectorInstanceListResponse)
    def list_instances(request: Request) -> ConnectorInstanceListResponse:
        try:
            items = service.list_instances(principal(request))
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc
        return ConnectorInstanceListResponse(items=items)

    @router.post(
        "/instances",
        response_model=ConnectorInstanceRecordV1,
        status_code=status.HTTP_201_CREATED,
    )
    def create_instance(
        request: Request,
        instance: ConnectorInstanceV1,
    ) -> ConnectorInstanceRecordV1:
        try:
            return service.create_instance(principal(request), instance)
        except ConnectorInstanceExistsError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
                category="configuration_policy",
                code="instance_exists",
            ) from exc
        except (ConnectorRegistryError, ValueError) as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
                category="configuration_policy",
                code="invalid_config",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.get("/instances/{instance_id}", response_model=ConnectorInstanceRecordV1)
    def get_instance(request: Request, instance_id: str) -> ConnectorInstanceRecordV1:
        try:
            return service.get_instance(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.put("/instances/{instance_id}", response_model=ConnectorInstanceRecordV1)
    def update_instance(
        request: Request,
        instance_id: str,
        update: ConnectorInstanceUpdateRequest,
    ) -> ConnectorInstanceRecordV1:
        if update.instance.instance_id != instance_id:
            raise _diagnostic_exception(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="path instance id does not match request body",
                category="configuration_policy",
                code="invalid_config",
            )
        try:
            return service.update_instance(
                principal(request),
                update.instance,
                expected_revision=update.expected_revision,
            )
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorRevisionConflictError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
                category="gateway_runtime",
                code="revision_conflict",
            ) from exc
        except (ConnectorRegistryError, ValueError) as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
                category="configuration_policy",
                code="invalid_config",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.post("/instances/{instance_id}/enable", response_model=ConnectorInstanceRecordV1)
    def enable_instance(
        request: Request,
        instance_id: str,
        revision: ConnectorRevisionRequest,
    ) -> ConnectorInstanceRecordV1:
        return _set_enabled(request, instance_id, revision.expected_revision, True)

    @router.post("/instances/{instance_id}/disable", response_model=ConnectorInstanceRecordV1)
    def disable_instance(
        request: Request,
        instance_id: str,
        revision: ConnectorRevisionRequest,
    ) -> ConnectorInstanceRecordV1:
        return _set_enabled(request, instance_id, revision.expected_revision, False)

    def _set_enabled(
        request: Request,
        instance_id: str,
        expected_revision: int,
        enabled: bool,
    ) -> ConnectorInstanceRecordV1:
        try:
            return service.set_enabled(
                principal(request),
                instance_id,
                enabled=enabled,
                expected_revision=expected_revision,
            )
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorRevisionConflictError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
                category="gateway_runtime",
                code="revision_conflict",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.post("/validate", response_model=ConnectorHealthV1)
    def validate_config(request: Request, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        try:
            return service.validate_config(principal(request), instance)
        except (ConnectorRegistryError, ValueError) as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
                category="configuration_policy",
                code="invalid_config",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.post("/instances/{instance_id}/test-connection", response_model=ConnectorHealthV1)
    def test_connection(request: Request, instance_id: str) -> ConnectorHealthV1:
        try:
            return service.test_connection(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc
        except RuntimeError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
                category="gateway_runtime",
                code="management_dependency_unavailable",
            ) from exc

    @router.get("/instances/{instance_id}/runtime", response_model=ConnectorRuntimeStateV1)
    def get_runtime(request: Request, instance_id: str) -> ConnectorRuntimeStateV1:
        try:
            return service.get_runtime(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.put(
        "/instances/{instance_id}/runtime/checkpoint",
        response_model=ConnectorRuntimeStateV1,
    )
    def update_checkpoint(
        request: Request,
        instance_id: str,
        update: ConnectorCheckpointUpdateRequest,
    ) -> ConnectorRuntimeStateV1:
        try:
            return service.update_checkpoint(
                principal(request),
                instance_id,
                update.checkpoint,
                expected_checkpoint_revision=update.expected_checkpoint_revision,
                observation_state=update.observation_state,
                gap_open=update.gap_open,
                last_success_at_utc=update.last_success_at_utc,
            )
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorRevisionConflictError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
                category="gateway_runtime",
                code="revision_conflict",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc
        except ValueError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
                category="collection_continuity",
                code="invalid_checkpoint",
            ) from exc

    @router.post("/instances/{instance_id}/gaps/detect", response_model=ConnectorRuntimeStateV1)
    def mark_gap(request: Request, instance_id: str) -> ConnectorRuntimeStateV1:
        try:
            return service.mark_gap(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    @router.post("/instances/{instance_id}/gaps/reconcile", response_model=ConnectorRuntimeStateV1)
    def reconcile_gap(request: Request, instance_id: str) -> ConnectorRuntimeStateV1:
        try:
            return service.reconcile_gap(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
                category="configuration_policy",
                code="instance_not_found",
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise _diagnostic_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                category="authorization",
                code="access_denied",
            ) from exc

    return router
