from __future__ import annotations

import base64
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from ets.api.app import create_app
from ets.api.auth import ProductionJWKSAuthPolicy, make_rs256_token, rsa_public_jwk
from ets.core.log import InMemoryAppendOnlyLog
from ets.core.models import EvidenceEvent


@dataclass(frozen=True)
class Case:
    method: str
    template: str
    path: str
    capability: str | None
    payload: str | None = None
    scoped: bool = False


# Independent policy oracle: do not generate expectations from the production role map.
ROLE_CAPABILITIES = {
    "viewer": {"evidence.read"},
    "evidence_producer": {"evidence.read", "evidence.create", "evidence.verify", "evidence.export"},
    "auditor": {"evidence.read", "evidence.verify", "evidence.export"},
    "operator": {"evidence.read", "evidence.create", "evidence.verify", "evidence.export"},
    "administrator": {
        "evidence.read",
        "evidence.create",
        "evidence.verify",
        "evidence.export",
        "admin.read",
    },
    "no_role": set(),
}

CASES = [
    Case("GET", "/health", "/health", None),
    Case("GET", "/version", "/version", None),
    Case("GET", "/ready", "/ready", None),
    Case("GET", "/healthz", "/healthz", None),
    Case("GET", "/api/v1/auth/context", "/api/v1/auth/context", "authenticated"),
    Case("GET", "/api/v1/metrics", "/api/v1/metrics", "admin.read"),
    Case("GET", "/api/v1/log/head", "/api/v1/log/head", "evidence.read"),
    Case("GET", "/tree-head/latest", "/tree-head/latest", "evidence.read"),
    Case("GET", "/tree-head/{tree_head_id}", "/tree-head/latest", "evidence.read"),
    Case("GET", "/tree-head", "/tree-head", "evidence.read"),
    Case("GET", "/log/root", "/log/root", "evidence.read"),
    Case("GET", "/log/size", "/log/size", "evidence.read"),
    Case("GET", "/anchors/latest", "/anchors/latest", "evidence.export"),
    Case("GET", "/anchors/history", "/anchors/history", "evidence.export"),
    Case("POST", "/verify/anchor", "/verify/anchor", "evidence.verify", "anchor"),
    Case("GET", "/api/v1/events", "/api/v1/events", "evidence.read"),
    Case("POST", "/api/v1/events", "/api/v1/events", "evidence.create", "event", True),
    Case("POST", "/evidence", "/evidence", "evidence.create", "event", True),
    Case("POST", "/evidence/register", "/evidence/register", "evidence.create", "register", True),
    Case(
        "GET",
        "/evidence/{artifact_id}/proof",
        "/evidence/seed-artifact/proof",
        "evidence.export",
        scoped=True,
    ),
    Case("POST", "/evidence/verify", "/evidence/verify", "evidence.verify", "artifact", True),
    Case("GET", "/api/v1/events/{event_id}", "/api/v1/events/seed", "evidence.read", scoped=True),
    Case("GET", "/evidence/{event_id}", "/evidence/seed", "evidence.read", scoped=True),
    Case(
        "GET",
        "/api/v1/events/by-index/{index}",
        "/api/v1/events/by-index/0",
        "evidence.read",
        scoped=True,
    ),
    Case(
        "GET", "/evidence/sequence/{sequence}", "/evidence/sequence/0", "evidence.read", scoped=True
    ),
    Case(
        "GET",
        "/api/v1/proofs/inclusion/{event_id}",
        "/api/v1/proofs/inclusion/seed",
        "evidence.read",
        scoped=True,
    ),
    Case(
        "GET", "/proof/inclusion/{event_id}", "/proof/inclusion/seed", "evidence.read", scoped=True
    ),
    Case("GET", "/proofs/event/{event_id}", "/proofs/event/seed", "evidence.read", scoped=True),
    Case(
        "GET", "/api/v1/bundles/{event_id}", "/api/v1/bundles/seed", "evidence.export", scoped=True
    ),
    Case(
        "GET",
        "/api/v1/proofs/consistency",
        "/api/v1/proofs/consistency?from_size=0",
        "evidence.read",
    ),
    Case(
        "POST",
        "/api/v1/verify/inclusion",
        "/api/v1/verify/inclusion",
        "evidence.verify",
        "inclusion",
    ),
    Case("POST", "/verify/inclusion", "/verify/inclusion", "evidence.verify", "inclusion"),
    Case(
        "POST", "/verify/proof/inclusion", "/verify/proof/inclusion", "evidence.verify", "inclusion"
    ),
    Case("POST", "/verify/proof", "/verify/proof", "evidence.verify", "inclusion"),
    Case("POST", "/verify/signature", "/verify/signature", "evidence.verify", "signature"),
    Case("POST", "/verify/evidence", "/verify/evidence", "evidence.verify", "verify_event"),
    Case(
        "POST",
        "/api/v1/verify/consistency",
        "/api/v1/verify/consistency",
        "evidence.verify",
        "consistency",
    ),
    Case(
        "POST",
        "/api/v1/federation/assess",
        "/api/v1/federation/assess",
        "evidence.verify",
        "federation",
    ),
    Case("POST", "/reports/certificate", "/reports/certificate", "evidence.export", "certificate"),
]


def event(event_id: str) -> dict[str, Any]:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        evidence_id="synthetic-evidence",
        event_type="synthetic.test",
        subject_ref=None,
        content_hash="a" * 64,
        content_hash_alg="sha256",
        metadata={},
        created_at_utc=datetime.now(UTC),
    ).model_dump(mode="json")


@pytest.fixture(scope="module")
def auth_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def headers(key: rsa.RSAPrivateKey, role: str, workspace: str = "workspace-a") -> dict[str, str]:
    claims: dict[str, Any] = {
        "sub": "synthetic-user",
        "iss": "https://issuer.invalid",
        "aud": "ets-api",
        "tenant_id": "tenant-a",
        "workspace_id": workspace,
        "exp": int(time.time()) + 300,
        "capabilities": ["evidence.create", "evidence.export", "admin.read"],
    }
    if role != "no_role":
        claims["roles"] = [role]
    return {"Authorization": "Bearer " + make_rs256_token(claims, key, kid="auth-key")}


@pytest.fixture
def environment(auth_key: rsa.RSAPrivateKey) -> Iterator[tuple[TestClient, dict[str, Any]]]:
    log = InMemoryAppendOnlyLog()
    with TestClient(create_app(log=log)) as seed:
        assert seed.post("/api/v1/events", json=event("seed")).status_code == 201
        assert (
            seed.post(
                "/evidence/register",
                json={
                    "artifact_id": "seed-artifact",
                    "artifact_base64": base64.b64encode(b"synthetic").decode(),
                    "tenant_id": "tenant-a",
                    "workspace_id": "workspace-a",
                    "content_type": "text/plain",
                },
            ).status_code
            == 201
        )
    policy = ProductionJWKSAuthPolicy(
        {"keys": [rsa_public_jwk(auth_key.public_key(), kid="auth-key")]},
        issuer="https://issuer.invalid",
        audience="ets-api",
    )
    with TestClient(create_app(log=log, auth_policy=policy, auth_mode="production_jwks")) as client:
        admin = headers(auth_key, "administrator")

        def get(path: str) -> Any:
            response = client.get(path, headers=admin)
            assert response.status_code == 200
            return response.json()

        bundle = get("/api/v1/bundles/seed")
        payloads = {
            "event": event("new-event"),
            "register": {
                "artifact_id": "new-artifact",
                "artifact_base64": "c3ludGhldGlj",
                "tenant_id": "tenant-a",
                "workspace_id": "workspace-a",
                "content_type": "text/plain",
            },
            "artifact": {"artifact_id": "seed-artifact", "artifact_base64": "c3ludGhldGlj"},
            "anchor": get("/anchors/latest"),
            "inclusion": bundle["inclusion_proof"],
            "signature": {"tree_head": bundle["tree_head"], "public_key_hex": "0" * 64},
            "verify_event": {"event": bundle["event"], "expected_event_hash": bundle["event_hash"]},
            "consistency": get("/api/v1/proofs/consistency?from_size=0"),
            "federation": {"observations": [], "threshold": 1},
            "certificate": {"bundle": bundle, "format": "json"},
        }
        yield client, payloads


def storage_snapshot(client: TestClient) -> tuple[Any, ...]:
    state = client.app.state  # type: ignore[union-attr]
    return (
        [entry.event_hash for entry in state.event_log.list_entries()],
        list(state.artifact_records),
        list(state.anchor_history),
    )


@pytest.mark.parametrize("role", list(ROLE_CAPABILITIES))
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.method + " " + case.template)
def test_route_role_matrix(
    environment: tuple[TestClient, dict[str, Any]],
    auth_key: rsa.RSAPrivateKey,
    case: Case,
    role: str,
) -> None:
    client, payloads = environment
    before = storage_snapshot(client)
    response = client.request(
        case.method, case.path, headers=headers(auth_key, role), json=payloads.get(case.payload)
    )
    allowed = (
        case.capability in {None, "authenticated"} or case.capability in ROLE_CAPABILITIES[role]
    )
    if allowed:
        assert response.status_code in {200, 201}, response.text
    else:
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "ETS_AUTH_FORBIDDEN"
        assert storage_snapshot(client) == before


@pytest.mark.parametrize("role", list(ROLE_CAPABILITIES))
@pytest.mark.parametrize(
    "case",
    [case for case in CASES if case.scoped],
    ids=lambda case: case.method + " " + case.template,
)
def test_scope_mismatch_and_capability_precedence(
    environment: tuple[TestClient, dict[str, Any]],
    auth_key: rsa.RSAPrivateKey,
    case: Case,
    role: str,
) -> None:
    client, payloads = environment
    before = storage_snapshot(client)
    response = client.request(
        case.method,
        case.path,
        headers=headers(auth_key, role, "other-workspace"),
        json=payloads.get(case.payload),
    )
    expected = 404 if case.capability in ROLE_CAPABILITIES[role] else 403
    assert response.status_code == expected, response.text
    assert storage_snapshot(client) == before


def test_all_core_routes_have_a_reviewed_policy(
    environment: tuple[TestClient, dict[str, Any]],
) -> None:
    client, _ = environment
    excluded = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    actual = {
        (method, route.path)
        for route in client.app.routes  # type: ignore[union-attr]
        if route.path not in excluded
        for method in route.methods
    }
    assert actual == {(case.method, case.template) for case in CASES}


@pytest.mark.parametrize("path", ["/api/v1/events", "/api/v1/auth/context", "/api/v1/metrics"])
def test_missing_or_unknown_identity_rejected(
    environment: tuple[TestClient, dict[str, Any]],
    auth_key: rsa.RSAPrivateKey,
    path: str,
) -> None:
    client, _ = environment
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers(auth_key, "unknown-role")).status_code == 401


def test_artifact_read_alias_cannot_bypass_missing_role(
    environment: tuple[TestClient, dict[str, Any]],
    auth_key: rsa.RSAPrivateKey,
) -> None:
    client, _ = environment
    assert (
        client.get("/evidence/seed-artifact", headers=headers(auth_key, "viewer")).status_code
        == 200
    )
    assert (
        client.get("/evidence/seed-artifact", headers=headers(auth_key, "no_role")).status_code
        == 403
    )
