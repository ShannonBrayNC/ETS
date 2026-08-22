"""Fail-closed production composition for the ETS Fleet C3B control plane."""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import FastAPI

from ets.fleet.entra_session import (
    ProductionFleetAuthConfig,
    ProductionFleetRequestResolvers,
    ProductionFleetSessionAdapter,
)
from ets.fleet.models import (
    DeviceEnrollmentRecord,
    EnrollmentErrorCode,
    EnrollmentValidationError,
)
from ets.fleet.portal import FleetPortalService
from ets.fleet.portal_admin_durable import DurableFleetPortalAdminService
from ets.fleet.portal_api import FleetPortalReadiness, build_fleet_portal_router
from ets.fleet.postgres import (
    AzureManagedIdentityPostgresFactory,
    PostgresEnrollmentStore,
    PostgresFleetAdminMutationJournal,
)
from ets.fleet.postgres_auth import PostgresFleetAuthorizationState
from ets.fleet.service import DeviceEnrollmentService


class _RejectPortalEnrollmentSubmission:
    """The operator portal never validates or submits new device credentials."""

    def validate(self, record: DeviceEnrollmentRecord, *, now: datetime) -> None:
        del record, now
        raise EnrollmentValidationError(
            EnrollmentErrorCode.IDENTITY_VALIDATION_FAILED,
            "production Fleet portal cannot submit device enrollment credentials",
        )


class _UnknownPresence:
    """C3B does not fabricate presence when no shared presence source is composed."""

    def snapshot(self, device_id: str, *, now: datetime) -> None:
        del device_id, now
        return None


def create_production_fleet_app() -> FastAPI:
    """Create the private C3B Fleet BFF from required production environment state.

    The request identity context itself is intentionally not reconstructed from
    browser headers here. C3C must bind a protected hosting adapter that places a
    ``TrustedEntraIdentityContext`` in request state after cryptographic/platform
    authentication. Until that bridge exists, portal routes remain 401 fail-closed.
    """

    host = _required_env("ETS_FLEET_POSTGRES_HOST")
    database = _required_env("ETS_FLEET_POSTGRES_DATABASE")
    database_user = _required_env("ETS_FLEET_POSTGRES_USER")
    auth_config = ProductionFleetAuthConfig(
        issuer=_required_env("ETS_FLEET_ENTRA_ISSUER"),
        audience=_required_env("ETS_FLEET_ENTRA_AUDIENCE"),
        tenant_id=_required_env("ETS_FLEET_ENTRA_TENANT_ID"),
    )

    connection_factory = AzureManagedIdentityPostgresFactory(
        host=host,
        database=database,
        user=database_user,
    )
    enrollment_store = PostgresEnrollmentStore(connection_factory)
    mutation_journal = PostgresFleetAdminMutationJournal(connection_factory)
    authorization_state = PostgresFleetAuthorizationState(connection_factory)

    if not enrollment_store.check_ready() or not authorization_state.check_ready():
        raise RuntimeError("Fleet PostgreSQL schema is not ready")

    enrollment_service = DeviceEnrollmentService(
        enrollment_store,
        _RejectPortalEnrollmentSubmission(),
    )
    portal_service = FleetPortalService(
        enrollment_reader=enrollment_store,
        presence_reader=_UnknownPresence(),
    )
    admin_service = DurableFleetPortalAdminService(
        enrollment_service=enrollment_service,
        enrollment_store=enrollment_store,
        journal=mutation_journal,
    )
    session_adapter = ProductionFleetSessionAdapter(
        config=auth_config,
        scope_resolver=authorization_state,
        standing_resolver=authorization_state,
    )
    request_resolvers = ProductionFleetRequestResolvers(
        config=auth_config,
        adapter=session_adapter,
    )

    def readiness() -> FleetPortalReadiness:
        return FleetPortalReadiness(
            auth_config_ready=True,
            store_ready=(
                enrollment_store.check_ready() and authorization_state.check_ready()
            ),
        )

    app = FastAPI(
        title="ETS Fleet Control Plane",
        version="c3b",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(
        build_fleet_portal_router(
            service=portal_service,
            principal_resolver=request_resolvers.principal,
            admin_service=admin_service,
            security_session_resolver=request_resolvers.security_session,
            readiness_probe=readiness,
        )
    )
    return app


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required for Fleet production configuration")
    return value.strip()
