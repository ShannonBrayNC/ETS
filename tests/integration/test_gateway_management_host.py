from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from ets.api.auth import ProductionJWTAuthPolicy, make_hs256_token
from ets.connectors.models import (
    ConnectorCapabilities,
    ConnectorConfigurationSchema,
    ConnectorDefinitionV1,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime_store import ConnectorRuntimeStore
from ets.gateway.connector_management import ConnectorManagementService
from ets.gateway.management_host import create_gateway_management_app


def _definition() -> ConnectorDefinitionV1:
    return ConnectorDefinitionV1(
        schema_version="ets.connector.definition.v1",
        connector_id="synthetic.management",
        display_name="Synthetic Management Connector",
        description="Management host authorization fixture.",
        implementation_class="generic",
        source_classes=("synthetic",),
        adapter_version="1.0",
        sdk_contract_version="ets.connector.sdk.v1",
        capture_envelope_versions=("ets.capture.v1",),
        gateway_host_versions=("ets.gateway.connector-host.v1",),
        capabilities=ConnectorCapabilities(
            delivery_modes=("poll",),
            authentication_methods=("none",),
        ),
        configuration_schema=ConnectorConfigurationSchema(
            instance_schema="ets.connector.instance.v1"
        ),
    )


def _service(tmp_path: Path) -> ConnectorManagementService:
    return ConnectorManagementService(
        registry=ConnectorRegistry([_definition()]),
        store=ConnectorRuntimeStore(tmp_path / "connector-management.db"),
    )


def _production_client(tmp_path: Path) -> tuple[TestClient, str]:
    secret = "s" * 32
    app = create_gateway_management_app(
        _service(tmp_path),
        auth_policy=ProductionJWTAuthPolicy(secret),
        auth_mode="production_jwt",
    )
    return TestClient(app), secret


def _token(secret: str, role: str) -> str:
    return make_hs256_token(
        {
            "sub": "alice",
            "tenant_id": "tenant-a",
            "workspace_id": "workspace-a",
            "roles": [role],
            "exp": int(time.time()) + 3600,
        },
        secret,
    )


def test_local_gateway_management_context_is_visibly_nonproduction(tmp_path: Path) -> None:
    client = TestClient(create_gateway_management_app(_service(tmp_path)))

    response = client.get(
        "/api/v2/auth/context",
        headers={"X-ETS-Tenant": "tenant-a", "X-ETS-Workspace": "workspace-a"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "local-header"
    assert body["roles"] == ["administrator"]
    assert "connector.manage" in body["capabilities"]
    assert body["authorization_profile"] == "local_nonproduction"


def test_local_gateway_management_requires_explicit_scope(tmp_path: Path) -> None:
    client = TestClient(create_gateway_management_app(_service(tmp_path)))

    response = client.get("/api/v2/auth/context")

    assert response.status_code == 403


def test_production_context_uses_signed_scope_and_rejects_browser_override(tmp_path: Path) -> None:
    client, secret = _production_client(tmp_path)
    token = _token(secret, "operator")
    authorization = {"Authorization": f"Bearer {token}"}

    context = client.get("/api/v2/auth/context", headers=authorization)
    tampered = client.get(
        "/api/v2/auth/context",
        headers={**authorization, "X-ETS-Tenant": "browser-selected-tenant"},
    )

    assert context.status_code == 200
    assert context.json()["tenant_id"] == "tenant-a"
    assert context.json()["workspace_id"] == "workspace-a"
    assert context.json()["authorization_profile"] == "production"
    assert tampered.status_code == 403


def test_auditor_can_read_connector_catalog_without_management_authority(tmp_path: Path) -> None:
    client, secret = _production_client(tmp_path)
    viewer = _token(secret, "viewer")
    auditor = _token(secret, "auditor")
    operator = _token(secret, "operator")

    viewer_denied = client.get(
        "/gateway/connectors/v1/catalog",
        headers={"Authorization": f"Bearer {viewer}"},
    )
    auditor_allowed = client.get(
        "/gateway/connectors/v1/catalog",
        headers={"Authorization": f"Bearer {auditor}"},
    )
    operator_allowed = client.get(
        "/gateway/connectors/v1/catalog",
        headers={"Authorization": f"Bearer {operator}"},
    )

    assert viewer_denied.status_code == 403
    assert auditor_allowed.status_code == 200
    assert auditor_allowed.json()[0]["connector_id"] == "synthetic.management"
    assert operator_allowed.status_code == 200


def test_unknown_signed_role_fails_closed(tmp_path: Path) -> None:
    client, secret = _production_client(tmp_path)
    token = _token(secret, "superuser")

    response = client.get(
        "/api/v2/auth/context",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert "unsupported ETS role" in response.json()["detail"]
