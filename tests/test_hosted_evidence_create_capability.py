from __future__ import annotations

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from ets.api import hosted_runtime
from ets.api.app import create_app
from ets.api.auth import AuthContext, AuthError, AuthPolicy
from ets.api.authorization import AuthCapability, AuthRole
from ets.core import InMemoryAppendOnlyLog


class StaticAuthPolicy(AuthPolicy):
    def __init__(self, context: AuthContext) -> None:
        self._context = context

    def authenticate(self, request: Request) -> AuthContext:
        del request
        return self._context


class RejectingAuthPolicy(AuthPolicy):
    def authenticate(self, request: Request) -> AuthContext:
        del request
        raise AuthError("missing bearer token")


def _client(policy: AuthPolicy) -> TestClient:
    app = create_app(
        log=InMemoryAppendOnlyLog(),
        auth_policy=policy,
        auth_mode="production_jwks",
    )
    hosted_runtime._install_hosted_capability_guard(app, policy)
    return TestClient(app)


def _context(
    *,
    roles: tuple[AuthRole, ...],
    capabilities: tuple[AuthCapability, ...],
) -> AuthContext:
    return AuthContext(
        subject="test-principal",
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
        roles=roles,
        capabilities=capabilities,
        authorization_profile="production",
    )


@pytest.mark.parametrize("path", ["/api/v1/events", "/evidence", "/evidence/register"])
def test_hosted_ingestion_rejects_authenticated_principal_without_create_capability(
    path: str,
) -> None:
    client = _client(_context(roles=("viewer",), capabilities=("evidence.read",)))

    response = client.post(path, json={})

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "ETS_AUTH_FORBIDDEN",
            "message": "authenticated principal lacks evidence.create capability",
        }
    }


@pytest.mark.parametrize("path", ["/api/v1/events", "/evidence", "/evidence/register"])
def test_hosted_ingestion_allows_evidence_producer_through_capability_guard(path: str) -> None:
    client = _client(
        _context(
            roles=("evidence_producer",),
            capabilities=(
                "evidence.read",
                "evidence.create",
                "evidence.verify",
                "evidence.export",
            ),
        )
    )

    response = client.post(path, json={})

    # The invalid body reaches normal validation rather than the capability denial path.
    assert response.status_code == 422


def test_hosted_capability_guard_preserves_existing_authentication_failure_shape() -> None:
    client = _client(RejectingAuthPolicy())

    response = client.post("/api/v1/events", json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ETS_AUTH_REQUIRED"


def test_hosted_capability_guard_does_not_convert_reads_into_create_checks() -> None:
    client = _client(_context(roles=("viewer",), capabilities=("evidence.read",)))

    response = client.get("/api/v1/events")

    assert response.status_code == 200
    assert response.json()["items"] == []
