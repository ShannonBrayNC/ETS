from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCapabilities,
    ConnectorCheckpointPolicy,
    ConnectorCollection,
    ConnectorConfigurationSchema,
    ConnectorDefinitionV1,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime_store import ConnectorRuntimeStore
from ets.gateway.connector_management import (
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.connector_management_api import create_connector_management_router

NOW = datetime(2026, 8, 14, 2, 30, tzinfo=UTC)


def definition() -> ConnectorDefinitionV1:
    return ConnectorDefinitionV1(
        schema_version="ets.connector.definition.v1",
        connector_id="synthetic.poll",
        display_name="Synthetic Poll",
        description="Synthetic management API fixture.",
        implementation_class="generic",
        source_classes=("synthetic",),
        adapter_version="1.0",
        sdk_contract_version="ets.connector.sdk.v1",
        capture_envelope_versions=("ets.capture.v1",),
        gateway_host_versions=("ets.gateway.connector-host.v1",),
        capabilities=ConnectorCapabilities(
            delivery_modes=("poll",),
            authentication_methods=("none",),
            checkpointing=True,
            reconciliation=True,
        ),
        configuration_schema=ConnectorConfigurationSchema(
            instance_schema="ets.connector.instance.v1"
        ),
    )


def instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id="api-source",
        connector_id="synthetic.poll",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
        source=ConnectorSource(name="api-source", environment="test"),
        authentication=ConnectorAuthentication(method="none", credential_ref=None),
        collection=ConnectorCollection(mode="poll", interval_seconds=60),
        checkpoint=ConnectorCheckpointPolicy(strategy="source_cursor", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.synthetic.v1",
            normalization_profile="normalize.synthetic.v1",
        ),
        retry=ConnectorRetryPolicy(),
        gap_detection=ConnectorGapPolicy(),
        settings={},
    )


def client(tmp_path: Path) -> TestClient:
    registry = ConnectorRegistry([definition()])
    service = ConnectorManagementService(
        registry=registry,
        store=ConnectorRuntimeStore(tmp_path / "management.db"),
        now=lambda: NOW,
    )

    def resolve(request: Request) -> ConnectorManagementPrincipal:
        return ConnectorManagementPrincipal(
            actor_id=request.headers.get("x-actor", "api-admin"),
            tenant_id=request.headers.get("x-tenant", "tenant-a"),
            workspace_id=request.headers.get("x-workspace", "workspace-a"),
            can_manage=request.headers.get("x-manage", "true") == "true",
        )

    app = FastAPI()
    app.include_router(create_connector_management_router(service, resolve))
    return TestClient(app)


def test_management_api_crud_runtime_and_revision_conflict(tmp_path: Path) -> None:
    api = client(tmp_path)
    payload = instance().model_dump(mode="json")

    created = api.post("/gateway/connectors/v1/instances", json=payload)
    assert created.status_code == 201
    assert created.json()["revision"] == 1

    listed = api.get("/gateway/connectors/v1/instances")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    runtime = api.get("/gateway/connectors/v1/instances/api-source/runtime")
    assert runtime.status_code == 200
    assert runtime.json()["observation_state"] == "unknown_observation"

    disabled = api.post(
        "/gateway/connectors/v1/instances/api-source/disable",
        json={"expected_revision": 1},
    )
    assert disabled.status_code == 200
    assert disabled.json()["instance"]["enabled"] is False

    conflict = api.post(
        "/gateway/connectors/v1/instances/api-source/enable",
        json={"expected_revision": 1},
    )
    assert conflict.status_code == 409


def test_management_api_enforces_injected_scope_authorization(tmp_path: Path) -> None:
    api = client(tmp_path)
    payload = instance().model_dump(mode="json")

    denied = api.post(
        "/gateway/connectors/v1/instances",
        json=payload,
        headers={"x-tenant": "other-tenant"},
    )
    assert denied.status_code == 403


def test_management_api_does_not_supply_an_anonymous_auth_fallback(tmp_path: Path) -> None:
    registry = ConnectorRegistry([definition()])
    service = ConnectorManagementService(
        registry=registry,
        store=ConnectorRuntimeStore(tmp_path / "no-auth.db"),
        now=lambda: NOW,
    )

    def reject(_request: Request) -> ConnectorManagementPrincipal:
        return ConnectorManagementPrincipal(
            actor_id="anonymous",
            tenant_id="tenant-a",
            workspace_id="workspace-a",
            can_manage=False,
        )

    app = FastAPI()
    app.include_router(create_connector_management_router(service, reject))
    response = TestClient(app).post(
        "/gateway/connectors/v1/instances",
        json=instance().model_dump(mode="json"),
    )
    assert response.status_code == 403
