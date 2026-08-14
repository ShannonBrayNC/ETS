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


def instance(instance_id: str = "api-source") -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=instance_id,
        connector_id="synthetic.poll",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
        source=ConnectorSource(name=instance_id, environment="test"),
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
        can_manage = request.headers.get("x-manage", "true") == "true"
        read_header = request.headers.get("x-read")
        can_read = can_manage if read_header is None else read_header == "true"
        return ConnectorManagementPrincipal(
            actor_id=request.headers.get("x-actor", "api-admin"),
            tenant_id=request.headers.get("x-tenant", "tenant-a"),
            workspace_id=request.headers.get("x-workspace", "workspace-a"),
            can_read=can_read,
            can_manage=can_manage,
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


def test_catalog_and_instance_list_require_read_or_management_authority(tmp_path: Path) -> None:
    api = client(tmp_path)
    headers = {"x-manage": "false", "x-read": "false"}

    catalog = api.get("/gateway/connectors/v1/catalog", headers=headers)
    listed = api.get("/gateway/connectors/v1/instances", headers=headers)

    assert catalog.status_code == 403
    assert listed.status_code == 403


def test_read_only_principal_can_inspect_but_cannot_mutate(tmp_path: Path) -> None:
    api = client(tmp_path)
    payload = instance().model_dump(mode="json")
    assert api.post("/gateway/connectors/v1/instances", json=payload).status_code == 201

    read_only = {"x-manage": "false", "x-read": "true"}
    assert api.get("/gateway/connectors/v1/catalog", headers=read_only).status_code == 200
    assert api.get("/gateway/connectors/v1/instances", headers=read_only).status_code == 200
    assert (
        api.get("/gateway/connectors/v1/instances/api-source", headers=read_only).status_code
        == 200
    )
    assert (
        api.get(
            "/gateway/connectors/v1/instances/api-source/runtime",
            headers=read_only,
        ).status_code
        == 200
    )

    create_denied = api.post(
        "/gateway/connectors/v1/instances",
        json=instance("read-only-new").model_dump(mode="json"),
        headers=read_only,
    )
    disable_denied = api.post(
        "/gateway/connectors/v1/instances/api-source/disable",
        json={"expected_revision": 1},
        headers=read_only,
    )
    validate_denied = api.post(
        "/gateway/connectors/v1/validate",
        json=payload,
        headers=read_only,
    )
    test_denied = api.post(
        "/gateway/connectors/v1/instances/api-source/test-connection",
        headers=read_only,
    )
    checkpoint_denied = api.put(
        "/gateway/connectors/v1/instances/api-source/runtime/checkpoint",
        json={
            "checkpoint": None,
            "expected_checkpoint_revision": 0,
            "observation_state": "unknown_observation",
            "gap_open": False,
            "last_success_at_utc": None,
        },
        headers=read_only,
    )
    gap_denied = api.post(
        "/gateway/connectors/v1/instances/api-source/gaps/detect",
        headers=read_only,
    )

    assert create_denied.status_code == 403
    assert disable_denied.status_code == 403
    assert validate_denied.status_code == 403
    assert test_denied.status_code == 403
    assert checkpoint_denied.status_code == 403
    assert gap_denied.status_code == 403


def test_read_only_principal_remains_scope_bound(tmp_path: Path) -> None:
    api = client(tmp_path)
    assert (
        api.post(
            "/gateway/connectors/v1/instances",
            json=instance().model_dump(mode="json"),
        ).status_code
        == 201
    )
    foreign_scope = {
        "x-manage": "false",
        "x-read": "true",
        "x-tenant": "other-tenant",
    }

    response = api.get(
        "/gateway/connectors/v1/instances/api-source",
        headers=foreign_scope,
    )
    assert response.status_code == 403


def test_invalid_gap_checkpoint_is_422_without_persisted_mutation(tmp_path: Path) -> None:
    api = client(tmp_path)
    created = api.post(
        "/gateway/connectors/v1/instances",
        json=instance().model_dump(mode="json"),
    )
    assert created.status_code == 201

    invalid = api.put(
        "/gateway/connectors/v1/instances/api-source/runtime/checkpoint",
        json={
            "checkpoint": None,
            "expected_checkpoint_revision": 0,
            "observation_state": "collection_gap",
            "gap_open": False,
            "last_success_at_utc": None,
        },
    )
    assert invalid.status_code == 422

    runtime = api.get("/gateway/connectors/v1/instances/api-source/runtime")
    assert runtime.status_code == 200
    assert runtime.json()["checkpoint_revision"] == 0
    assert runtime.json()["observation_state"] == "unknown_observation"
    assert runtime.json()["gap_open"] is False


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
            can_read=False,
            can_manage=False,
        )

    app = FastAPI()
    app.include_router(create_connector_management_router(service, reject))
    response = TestClient(app).post(
        "/gateway/connectors/v1/instances",
        json=instance().model_dump(mode="json"),
    )
    assert response.status_code == 403
