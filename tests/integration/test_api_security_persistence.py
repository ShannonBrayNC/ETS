from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from ets.api.app import create_app, create_app_from_env
from ets.api.auth import (
    LocalAPIKeyAuthPolicy,
    ProductionJWKSAuthPolicy,
    ProductionJWTAuthPolicy,
    make_hs256_token,
    make_rs256_token,
    rsa_public_jwk,
)
from ets.core import EvidenceEvent, SignedTreeHead, SQLiteEventStore
from ets.core.signing import verify_tree_head_signature


def make_event(
    event_id: str = "evt_001",
    *,
    tenant_id: str = "tenant_a",
    workspace_id: str = "workspace_a",
    metadata: dict[str, object] | None = None,
    redaction_profile: str | None = None,
) -> dict[str, object]:
    event = EvidenceEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="a" * 64,
        content_hash_alg="sha256",
        metadata=metadata or {"case": "alpha"},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        redaction_profile=redaction_profile,
    )
    return event.model_dump(mode="json")


def test_sqlite_api_persists_across_app_instances(tmp_path) -> None:
    path = tmp_path / "ets.db"
    first_client = TestClient(create_app(log=SQLiteEventStore(path)))

    append_response = first_client.post("/api/v1/events", json=make_event())

    assert append_response.status_code == 201

    second_client = TestClient(create_app(log=SQLiteEventStore(path)))
    read_response = second_client.get("/api/v1/events/evt_001")

    assert read_response.status_code == 200
    assert read_response.json()["event"]["event_id"] == "evt_001"
    assert second_client.get("/ready").json()["storage"] == "sqlite"


def test_create_app_from_env_uses_sqlite_provider(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ETS_STORAGE_PROVIDER", "sqlite")
    monkeypatch.setenv("ETS_SQLITE_PATH", str(tmp_path / "ets.db"))

    client = TestClient(create_app_from_env())

    assert client.get("/ready").json()["storage"] == "sqlite"


def test_create_app_from_env_rejects_production_signing_without_signer(monkeypatch) -> None:
    monkeypatch.setenv("ETS_SIGNING_MODE", "production")

    with pytest.raises(RuntimeError, match="Ed25519 signing requires"):
        create_app_from_env()


def test_create_app_from_env_rejects_production_auth_without_secret(monkeypatch) -> None:
    monkeypatch.setenv("ETS_AUTH_MODE", "production_jwt")

    with pytest.raises(RuntimeError, match="production auth requires"):
        create_app_from_env()


def test_production_jwt_auth_requires_bearer_token_and_enforces_claim_scope() -> None:
    secret = "s" * 32
    client = TestClient(
        create_app(
            auth_policy=ProductionJWTAuthPolicy(secret),
            auth_mode="production_jwt",
        )
    )
    token = make_hs256_token(
        {
            "sub": "alice",
            "tenant_id": "tenant_a",
            "workspace_id": "workspace_a",
            "exp": 4_102_444_800,
        },
        secret,
    )

    unauthenticated = client.get("/api/v1/events")
    authenticated = client.post(
        "/api/v1/events",
        json=make_event(),
        headers={"Authorization": f"Bearer {token}"},
    )
    mismatch = client.get(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {token}", "X-ETS-Tenant": "tenant_b"},
    )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 201
    assert mismatch.status_code == 404


def test_production_jwks_auth_verifies_rs256_token_and_enforces_audience() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = {"keys": [rsa_public_jwk(private_key.public_key(), kid="auth-key-1")]}
    client = TestClient(
        create_app(
            auth_policy=ProductionJWKSAuthPolicy(
                jwks,
                issuer="https://issuer.example",
                audience="ets-api",
            ),
            auth_mode="production_jwks",
        )
    )
    token = make_rs256_token(
        {
            "sub": "alice",
            "tenant_id": "tenant_a",
            "workspace_id": "workspace_a",
            "iss": "https://issuer.example",
            "aud": "ets-api",
            "exp": 4_102_444_800,
        },
        private_key,
        kid="auth-key-1",
    )
    wrong_audience = make_rs256_token(
        {
            "sub": "alice",
            "iss": "https://issuer.example",
            "aud": "other-api",
            "exp": 4_102_444_800,
        },
        private_key,
        kid="auth-key-1",
    )

    authorized = client.post(
        "/api/v1/events",
        json=make_event(),
        headers={"Authorization": f"Bearer {token}"},
    )
    rejected = client.get(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {wrong_audience}"},
    )

    assert authorized.status_code == 201
    assert rejected.status_code == 401


def test_create_app_from_env_supports_static_jwks_json(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = {"keys": [rsa_public_jwk(private_key.public_key(), kid="auth-key-1")]}
    monkeypatch.setenv("ETS_AUTH_MODE", "production_jwks")
    monkeypatch.setenv("ETS_AUTH_JWKS_JSON", json.dumps(jwks))
    monkeypatch.setenv("ETS_AUTH_ISSUER", "https://issuer.example")
    monkeypatch.setenv("ETS_AUTH_AUDIENCE", "ets-api")
    token = make_rs256_token(
        {
            "sub": "alice",
            "iss": "https://issuer.example",
            "aud": "ets-api",
            "exp": 4_102_444_800,
        },
        private_key,
        kid="auth-key-1",
    )

    client = TestClient(create_app_from_env())
    response = client.get("/api/v1/events", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_local_api_key_auth_mode_requires_key() -> None:
    client = TestClient(
        create_app(
            auth_policy=LocalAPIKeyAuthPolicy("local-secret-key"),
            auth_mode="local_api_key",
        )
    )

    missing = client.get("/api/v1/events")
    authorized = client.get("/api/v1/events", headers={"X-ETS-API-Key": "local-secret-key"})

    assert missing.status_code == 401
    assert authorized.status_code == 200


def test_create_app_from_env_rejects_local_api_key_mode_without_key(monkeypatch) -> None:
    monkeypatch.setenv("ETS_AUTH_MODE", "local_api_key")

    with pytest.raises(RuntimeError, match="local API key auth requires"):
        create_app_from_env()


def test_ed25519_tree_head_signing_from_env(tmp_path, monkeypatch) -> None:
    private_key = Ed25519PrivateKey.generate()
    private_key_hex = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    monkeypatch.setenv("ETS_STORAGE_PROVIDER", "sqlite")
    monkeypatch.setenv("ETS_SQLITE_PATH", str(tmp_path / "ets.db"))
    monkeypatch.setenv("ETS_SIGNING_MODE", "ed25519")
    monkeypatch.setenv("ETS_SIGNING_PRIVATE_KEY_HEX", private_key_hex)
    monkeypatch.setenv("ETS_SIGNING_PUBLIC_KEY_ID", "test-key")
    client = TestClient(create_app_from_env())

    response = client.get("/api/v1/log/head")

    assert response.status_code == 200
    body = response.json()
    assert body["signature_alg"] == "ed25519"
    assert body["public_key_id"] == "test-key"
    tree_head = SignedTreeHead.model_validate_json(response.text)
    assert verify_tree_head_signature(tree_head, public_key_hex)


def test_tenant_workspace_headers_scope_reads_lists_and_proofs() -> None:
    client = TestClient(create_app())
    client.post("/api/v1/events", json=make_event("evt_a", tenant_id="tenant_a"))
    client.post("/api/v1/events", json=make_event("evt_b", tenant_id="tenant_b"))

    headers = {"X-ETS-Tenant": "tenant_a", "X-ETS-Workspace": "workspace_a"}
    list_response = client.get("/api/v1/events", headers=headers)
    wrong_read = client.get("/api/v1/events/evt_b", headers=headers)
    wrong_proof = client.get("/api/v1/proofs/inclusion/evt_b", headers=headers)

    assert [item["event"]["event_id"] for item in list_response.json()["items"]] == ["evt_a"]
    assert wrong_read.status_code == 404
    assert wrong_proof.status_code == 404
    assert "tenant_b" not in wrong_read.text


def test_append_rejects_tenant_header_mismatch() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/events",
        json=make_event(tenant_id="tenant_b"),
        headers={"X-ETS-Tenant": "tenant_a"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ETS_EVENT_NOT_FOUND"


def test_api_redacts_metadata_before_hashing_storage_and_response() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/events",
        json=make_event(
            metadata={"email": "person@example.test", "nested": {"token": "secret-token"}},
            redaction_profile="basic_pii",
        ),
    )

    assert response.status_code == 201
    read_response = client.get("/api/v1/events/evt_001")
    body = read_response.json()
    assert body["event"]["metadata"]["email"] == "[REDACTED]"
    assert body["event"]["metadata"]["nested"]["token"] == "[REDACTED]"
    assert "person@example.test" not in read_response.text
    assert "secret-token" not in read_response.text


def test_api_records_none_redaction_profile_by_default() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/events", json=make_event())

    assert response.status_code == 201
    body = client.get("/api/v1/events/evt_001").json()
    assert body["event"]["redaction_profile"] == "none"


def test_oversized_event_body_is_rejected() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/events",
        content=b"{" + b'"x":' + b'"a"' * (256 * 1024) + b"}",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "ETS_REQUEST_TOO_LARGE"


def test_audit_log_omits_sensitive_metadata(caplog) -> None:
    client = TestClient(create_app())
    caplog.set_level(logging.INFO, logger="ets.audit")

    response = client.post(
        "/api/v1/events",
        json=make_event(
            metadata={"email": "person@example.test"},
            redaction_profile="basic_pii",
        ),
        headers={"X-Correlation-ID": "corr_001"},
    )

    assert response.status_code == 201
    audit_payloads = [json.loads(record.message) for record in caplog.records]
    assert any(payload["operation"] == "event_appended" for payload in audit_payloads)
    assert "person@example.test" not in caplog.text
    assert "corr_001" in caplog.text
