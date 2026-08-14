from __future__ import annotations

import time

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ets.api.auth import LocalHeaderAuthPolicy, ProductionJWTAuthPolicy, make_hs256_token
from ets.api.authorization import AuthRoleError, capabilities_for_roles, parse_role_claim


def test_role_claim_maps_to_server_controlled_capabilities() -> None:
    roles = parse_role_claim(["auditor", "operator", "operator"])

    assert roles == ("auditor", "operator")
    capabilities = capabilities_for_roles(roles)
    assert "connector.manage" in capabilities
    assert "audit.read" in capabilities
    assert "admin.manage" not in capabilities


def test_role_claim_rejects_unknown_role() -> None:
    with pytest.raises(AuthRoleError, match="unsupported ETS role"):
        parse_role_claim(["browser_supplied_superuser"])


def test_local_header_profile_is_explicitly_nonproduction() -> None:
    app = FastAPI()
    policy = LocalHeaderAuthPolicy()

    @app.get("/context")
    def context(request: Request) -> dict[str, object]:
        result = policy.authenticate(request)
        return {
            "subject": result.subject,
            "roles": result.roles,
            "capabilities": result.capabilities,
            "authorization_profile": result.authorization_profile,
        }

    response = TestClient(app).get("/context")

    assert response.status_code == 200
    assert response.json()["subject"] == "local-header"
    assert response.json()["roles"] == ["administrator"]
    assert "connector.manage" in response.json()["capabilities"]
    assert response.json()["authorization_profile"] == "local_nonproduction"


def test_production_policy_ignores_arbitrary_capability_claim() -> None:
    secret = "s" * 32
    policy = ProductionJWTAuthPolicy(secret)
    token = make_hs256_token(
        {
            "sub": "alice",
            "tenant_id": "tenant-a",
            "workspace_id": "workspace-a",
            "roles": ["viewer"],
            "capabilities": ["admin.manage", "connector.manage"],
            "exp": int(time.time()) + 3600,
        },
        secret,
    )
    app = FastAPI()

    @app.get("/context")
    def context(request: Request) -> dict[str, object]:
        result = policy.authenticate(request)
        return {
            "roles": result.roles,
            "capabilities": result.capabilities,
            "authorization_profile": result.authorization_profile,
        }

    response = TestClient(app).get(
        "/context",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["roles"] == ["viewer"]
    assert response.json()["capabilities"] == ["evidence.read"]
    assert response.json()["authorization_profile"] == "production"
