"""Versioned FastAPI router for governed Gateway connector management."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @router.get("/catalog")
    def catalog(request: Request) -> tuple[object, ...]:
        try:
            definitions = service.catalog(principal(request))
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return tuple(item.model_dump(mode="json") for item in definitions)

    @router.get("/instances", response_model=ConnectorInstanceListResponse)
    def list_instances(request: Request) -> ConnectorInstanceListResponse:
        try:
            items = service.list_instances(principal(request))
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
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
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except (ConnectorRegistryError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @router.get("/instances/{instance_id}", response_model=ConnectorInstanceRecordV1)
    def get_instance(request: Request, instance_id: str) -> ConnectorInstanceRecordV1:
        try:
            return service.get_instance(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @router.put("/instances/{instance_id}", response_model=ConnectorInstanceRecordV1)
    def update_instance(
        request: Request,
        instance_id: str,
        update: ConnectorInstanceUpdateRequest,
    ) -> ConnectorInstanceRecordV1:
        if update.instance.instance_id != instance_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="path instance id does not match request body",
            )
        try:
            return service.update_instance(
                principal(request),
                update.instance,
                expected_revision=update.expected_revision,
            )
        except ConnectorInstanceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorRevisionConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except (ConnectorRegistryError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorRevisionConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @router.post("/validate", response_model=ConnectorHealthV1)
    def validate_config(request: Request, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        try:
            return service.validate_config(principal(request), instance)
        except (ConnectorRegistryError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @router.post("/instances/{instance_id}/test-connection", response_model=ConnectorHealthV1)
    def test_connection(request: Request, instance_id: str) -> ConnectorHealthV1:
        try:
            return service.test_connection(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    @router.get("/instances/{instance_id}/runtime", response_model=ConnectorRuntimeStateV1)
    def get_runtime(request: Request, instance_id: str) -> ConnectorRuntimeStateV1:
        try:
            return service.get_runtime(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorRevisionConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    @router.post("/instances/{instance_id}/gaps/detect", response_model=ConnectorRuntimeStateV1)
    def mark_gap(request: Request, instance_id: str) -> ConnectorRuntimeStateV1:
        try:
            return service.mark_gap(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @router.post("/instances/{instance_id}/gaps/reconcile", response_model=ConnectorRuntimeStateV1)
    def reconcile_gap(request: Request, instance_id: str) -> ConnectorRuntimeStateV1:
        try:
            return service.reconcile_gap(principal(request), instance_id)
        except ConnectorInstanceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ConnectorManagementAuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return router
