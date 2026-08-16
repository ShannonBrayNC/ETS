from __future__ import annotations

import time

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Request

from ets.api.auth import (
    AuthError,
    LocalHeaderAuthPolicy,
    ProductionJWKSAuthPolicy,
    ProductionJWTAuthPolicy,
    make_hs256_token,
    make_rs256_token,
    rsa_public_jwk,
)

SECRET = "production-test-secret-material-at-least-32-bytes"
ISSUER = "https://issuer.example.test"
AUDIENCE = "ets-api"
TENANT_ID = "11111111-2222-3333-4444-555555555555"
GATEWAY_CLIENT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def request(*headers: tuple[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/api/v1/events",
            "raw_path": b"/api/v1/events",
            "query_string": b"",
            "headers": [
                (name.lower().encode("ascii"), value.encode("ascii"))
                for name, value in headers
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("core.internal", 443),
        }
    )


def hs256_token(**overrides: object) -> str:
    claims: dict[str, object] = {
        "sub": "gateway-relay",
        "tenant_id": "tenant-demo",
        "workspace_id": "workspace-demo",
        "roles": ["administrator"],
        "iss": ISSUER,
        "exp": int(time.time()) + 300,
    }
    claims.update(overrides)
    return make_hs256_token(claims, SECRET)


def test_production_hs256_requires_tenant_and_workspace_claims() -> None:
    policy = ProductionJWTAuthPolicy(SECRET, issuer=ISSUER)

    context = policy.authenticate(request(("Authorization", f"Bearer {hs256_token()}")))

    assert context.authorization_profile == "production"
    assert context.tenant_id == "tenant-demo"
    assert context.workspace_id == "workspace-demo"

    with pytest.raises(AuthError, match="provide tenant_id and workspace_id claims together"):
        policy.authenticate(
            request(("Authorization", f"Bearer {hs256_token(tenant_id=None)}"))
        )

    with pytest.raises(AuthError, match="provide tenant_id and workspace_id claims together"):
        policy.authenticate(
            request(("Authorization", f"Bearer {hs256_token(workspace_id=None)}"))
        )


def test_production_hs256_rejects_caller_scope_headers_even_when_matching() -> None:
    policy = ProductionJWTAuthPolicy(SECRET, issuer=ISSUER)
    token = hs256_token()

    with pytest.raises(AuthError, match="must come from bearer token claims"):
        policy.authenticate(
            request(
                ("Authorization", f"Bearer {token}"),
                ("X-ETS-Tenant", "tenant-demo"),
            )
        )

    with pytest.raises(AuthError, match="must come from bearer token claims"):
        policy.authenticate(
            request(
                ("Authorization", f"Bearer {token}"),
                ("X-ETS-Workspace", "workspace-demo"),
            )
        )


def _jwks_policy(private_key: rsa.RSAPrivateKey, kid: str) -> ProductionJWKSAuthPolicy:
    return ProductionJWKSAuthPolicy(
        {"keys": [rsa_public_jwk(private_key.public_key(), kid=kid)]},
        issuer=ISSUER,
        audience=AUDIENCE,
        tenant_id=TENANT_ID,
        app_scope_map={GATEWAY_CLIENT_ID: ("tenant-demo", "workspace-demo")},
    )


def _rs256_token(
    private_key: rsa.RSAPrivateKey,
    kid: str,
    **overrides: object,
) -> str:
    claims: dict[str, object] = {
        "sub": "gateway-managed-identity-object",
        "roles": ["evidence_producer"],
        "iss": ISSUER,
        "aud": AUDIENCE,
        "tid": TENANT_ID,
        "exp": int(time.time()) + 300,
    }
    claims.update(overrides)
    return make_rs256_token(claims, private_key, kid=kid)


def test_production_jwks_accepts_explicit_claim_scope_and_rejects_headers() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    kid = "scope-test-key"
    policy = _jwks_policy(private_key, kid)
    token = _rs256_token(
        private_key,
        kid,
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
    )

    context = policy.authenticate(request(("Authorization", f"Bearer {token}")))
    assert context.tenant_id == "tenant-demo"
    assert context.workspace_id == "workspace-demo"

    with pytest.raises(AuthError, match="must come from bearer token claims"):
        policy.authenticate(
            request(
                ("Authorization", f"Bearer {token}"),
                ("X-ETS-Tenant", "tenant-demo"),
                ("X-ETS-Workspace", "workspace-demo"),
            )
        )


def test_production_jwks_maps_only_approved_app_only_principal() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    kid = "app-scope-key"
    policy = _jwks_policy(private_key, kid)
    token = _rs256_token(
        private_key,
        kid,
        idtyp="app",
        azp=GATEWAY_CLIENT_ID,
    )

    context = policy.authenticate(request(("Authorization", f"Bearer {token}")))

    assert context.tenant_id == "tenant-demo"
    assert context.workspace_id == "workspace-demo"
    assert context.roles == ("evidence_producer",)
    assert context.has_capability("evidence.create") is True
    assert context.has_capability("connector.manage") is False


def test_app_scope_mapping_rejects_wrong_tenant_user_token_and_unknown_application() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    kid = "reject-app-scope-key"
    policy = _jwks_policy(private_key, kid)

    wrong_tenant = _rs256_token(
        private_key,
        kid,
        idtyp="app",
        azp=GATEWAY_CLIENT_ID,
        tid="99999999-8888-7777-6666-555555555555",
    )
    with pytest.raises(AuthError, match="tenant mismatch"):
        policy.authenticate(request(("Authorization", f"Bearer {wrong_tenant}")))

    user_token = _rs256_token(
        private_key,
        kid,
        idtyp="user",
        azp=GATEWAY_CLIENT_ID,
    )
    with pytest.raises(AuthError, match="app-only"):
        policy.authenticate(request(("Authorization", f"Bearer {user_token}")))

    unknown_app = _rs256_token(
        private_key,
        kid,
        idtyp="app",
        azp="bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    )
    with pytest.raises(AuthError, match="not authorized for an ETS scope"):
        policy.authenticate(request(("Authorization", f"Bearer {unknown_app}")))


def test_local_header_mode_remains_available_for_nonproduction() -> None:
    context = LocalHeaderAuthPolicy().authenticate(
        request(
            ("X-ETS-Tenant", "tenant-local"),
            ("X-ETS-Workspace", "workspace-local"),
        )
    )

    assert context.authorization_profile == "local_nonproduction"