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

    context = policy.authenticate(
        request(("Authorization", f"Bearer {hs256_token()}"))
    )

    assert context.authorization_profile == "production"
    assert context.tenant_id == "tenant-demo"
    assert context.workspace_id == "workspace-demo"

    with pytest.raises(AuthError, match="tenant_id claim"):
        policy.authenticate(
            request(
                (
                    "Authorization",
                    f"Bearer {hs256_token(tenant_id=None)}",
                )
            )
        )

    with pytest.raises(AuthError, match="workspace_id claim"):
        policy.authenticate(
            request(
                (
                    "Authorization",
                    f"Bearer {hs256_token(workspace_id=None)}",
                )
            )
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


def test_production_jwks_uses_the_same_claim_only_scope_boundary() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    kid = "scope-test-key"
    policy = ProductionJWKSAuthPolicy(
        {"keys": [rsa_public_jwk(private_key.public_key(), kid=kid)]},
        issuer=ISSUER,
        audience=AUDIENCE,
    )
    claims = {
        "sub": "gateway-relay",
        "tenant_id": "tenant-demo",
        "workspace_id": "workspace-demo",
        "roles": ["administrator"],
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 300,
    }
    token = make_rs256_token(claims, private_key, kid=kid)

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


def test_local_header_mode_remains_available_for_nonproduction() -> None:
    context = LocalHeaderAuthPolicy().authenticate(
        request(
            ("X-ETS-Tenant", "tenant-local"),
            ("X-ETS-Workspace", "workspace-local"),
        )
    )

    assert context.authorization_profile == "local_nonproduction"
