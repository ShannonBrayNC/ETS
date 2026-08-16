"""Authentication policy for ETS API modes."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast
from urllib.request import urlopen

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import Request

from ets.api.authorization import (
    ALL_CAPABILITIES,
    AuthCapability,
    AuthorizationProfile,
    AuthRole,
    AuthRoleError,
    capabilities_for_roles,
    parse_role_claim,
)

AppScopeMap = dict[str, tuple[str, str]]


class AuthError(PermissionError):
    """Raised when API authentication fails."""


@dataclass(frozen=True)
class AuthContext:
    subject: str | None = None
    tenant_id: str | None = None
    workspace_id: str | None = None
    roles: tuple[AuthRole, ...] = ()
    capabilities: tuple[AuthCapability, ...] = ()
    authorization_profile: AuthorizationProfile = "local_nonproduction"

    def has_capability(self, capability: AuthCapability) -> bool:
        return capability in self.capabilities


class AuthPolicy:
    def authenticate(self, request: Request) -> AuthContext:
        """Return the authenticated request context."""
        return AuthContext()


class LocalHeaderAuthPolicy(AuthPolicy):
    """Development auth mode; tenant/workspace scoping comes from headers."""

    def authenticate(self, request: Request) -> AuthContext:
        return AuthContext(
            subject="local-header",
            roles=("administrator",),
            capabilities=ALL_CAPABILITIES,
            authorization_profile="local_nonproduction",
        )


class LocalAPIKeyAuthPolicy(AuthPolicy):
    """Local shared-key auth for non-production deployments."""

    def __init__(self, api_key: str) -> None:
        if len(api_key) < 16:
            raise RuntimeError("ETS_LOCAL_API_KEY must be at least 16 characters")
        self._api_key = api_key

    def authenticate(self, request: Request) -> AuthContext:
        provided = request.headers.get("X-ETS-API-Key")
        if provided is None or not hmac.compare_digest(provided, self._api_key):
            raise AuthError("invalid API key")
        return AuthContext(
            subject="local-api-key",
            roles=("administrator",),
            capabilities=ALL_CAPABILITIES,
            authorization_profile="local_nonproduction",
        )


class ProductionJWTAuthPolicy(AuthPolicy):
    """Fail-closed HS256 JWT bearer auth for production-like deployments."""

    def __init__(self, secret: str, issuer: str | None = None) -> None:
        if len(secret) < 32:
            raise RuntimeError("ETS_AUTH_HS256_SECRET must be at least 32 characters")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer

    def authenticate(self, request: Request) -> AuthContext:
        _reject_production_scope_headers(request)
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("missing bearer token")

        claims = self._decode_token(token)
        return _context_from_production_claims(claims)

    def _decode_token(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError("invalid bearer token")

        signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
        expected = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        actual = _decode_segment(parts[2], "bearer token signature")
        if not hmac.compare_digest(expected, actual):
            raise AuthError("invalid bearer token signature")

        header = _decode_json_object(parts[0], "bearer token header")
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise AuthError("unsupported bearer token header")

        claims = _decode_json_object(parts[1], "bearer token claims")
        now = int(time.time())
        exp = claims.get("exp")
        if not isinstance(exp, int) or exp <= now:
            raise AuthError("bearer token expired")
        nbf = claims.get("nbf")
        if isinstance(nbf, int) and nbf > now:
            raise AuthError("bearer token not yet valid")
        if self._issuer is not None and claims.get("iss") != self._issuer:
            raise AuthError("bearer token issuer mismatch")
        return claims


class ProductionJWKSAuthPolicy(AuthPolicy):
    """Fail-closed RS256 JWT bearer auth using a configured JWKS."""

    def __init__(
        self,
        jwks: dict[str, Any],
        *,
        issuer: str | None = None,
        audience: str | None = None,
        tenant_id: str | None = None,
        app_scope_map: AppScopeMap | None = None,
        jwks_loader: Callable[[], dict[str, Any]] | None = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self._keys = _keys_from_jwks(jwks)
        self._issuer = issuer
        self._audience = audience
        self._tenant_id = tenant_id
        self._app_scope_map = _normalize_app_scope_map(app_scope_map)
        self._jwks_loader = jwks_loader
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_expires_at = int(time.time()) + cache_ttl_seconds

    @classmethod
    def from_json(
        cls,
        jwks_json: str,
        *,
        issuer: str | None = None,
        audience: str | None = None,
        tenant_id: str | None = None,
        app_scope_map: AppScopeMap | None = None,
    ) -> ProductionJWKSAuthPolicy:
        return cls(
            cast(dict[str, Any], json.loads(jwks_json)),
            issuer=issuer,
            audience=audience,
            tenant_id=tenant_id,
            app_scope_map=app_scope_map,
        )

    @classmethod
    def from_url(
        cls,
        jwks_url: str,
        *,
        issuer: str | None = None,
        audience: str | None = None,
        tenant_id: str | None = None,
        app_scope_map: AppScopeMap | None = None,
    ) -> ProductionJWKSAuthPolicy:
        def load_jwks() -> dict[str, Any]:
            return _load_jwks_from_url(jwks_url)

        return cls(
            load_jwks(),
            issuer=issuer,
            audience=audience,
            tenant_id=tenant_id,
            app_scope_map=app_scope_map,
            jwks_loader=load_jwks,
        )

    def authenticate(self, request: Request) -> AuthContext:
        _reject_production_scope_headers(request)
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("missing bearer token")

        claims = self._decode_token(token)
        return _context_from_production_claims(
            claims,
            app_scope_map=self._app_scope_map,
        )

    def _decode_token(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError("invalid bearer token")

        header = _decode_json_object(parts[0], "bearer token header")
        if header.get("alg") != "RS256" or header.get("typ") != "JWT":
            raise AuthError("unsupported bearer token header")
        kid = _required_str(header.get("kid"), "kid")
        jwk = self._trusted_key(kid)

        signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
        signature = _decode_segment(parts[2], "bearer token signature")
        public_key = _rsa_public_key_from_jwk(jwk)
        try:
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
        except Exception as exc:
            raise AuthError("invalid bearer token signature") from exc

        claims = _decode_json_object(parts[1], "bearer token claims")
        _validate_registered_claims(
            claims,
            issuer=self._issuer,
            audience=self._audience,
            tenant_id=self._tenant_id,
        )
        return claims

    def _trusted_key(self, kid: str) -> dict[str, Any]:
        now = int(time.time())
        if self._jwks_loader is not None and now >= self._cache_expires_at:
            self._refresh_keys(now)

        jwk = self._keys.get(kid)
        if jwk is None and self._jwks_loader is not None:
            self._refresh_keys(now)
            jwk = self._keys.get(kid)
        if jwk is None:
            raise AuthError("bearer token key not trusted")
        return jwk

    def _refresh_keys(self, now: int | None = None) -> None:
        if self._jwks_loader is None:
            return
        try:
            self._keys = _keys_from_jwks(self._jwks_loader())
            self._cache_expires_at = (now or int(time.time())) + self._cache_ttl_seconds
        except Exception as exc:
            raise AuthError("could not refresh JWKS") from exc


def make_hs256_token(claims: dict[str, Any], secret: str) -> str:
    """Create an HS256 JWT for tests and local tooling."""

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    claims_b64 = _b64encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{claims_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{claims_b64}.{_b64encode(signature)}"


def make_rs256_token(
    claims: dict[str, Any],
    private_key: rsa.RSAPrivateKey,
    *,
    kid: str,
) -> str:
    """Create an RS256 JWT for tests and local tooling."""

    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    claims_b64 = _b64encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{claims_b64}".encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{header_b64}.{claims_b64}.{_b64encode(signature)}"


def rsa_public_jwk(public_key: rsa.RSAPublicKey, *, kid: str) -> dict[str, str]:
    """Return a minimal RSA public JWK for tests and static deployments."""

    numbers = public_key.public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
        "n": _b64encode(_int_to_bytes(numbers.n)),
        "e": _b64encode(_int_to_bytes(numbers.e)),
    }


def _reject_production_scope_headers(request: Request) -> None:
    """Require production tenant/workspace scope to come only from authenticated claims."""

    if (
        request.headers.get("X-ETS-Tenant") is not None
        or request.headers.get("X-ETS-Workspace") is not None
    ):
        raise AuthError("production tenant/workspace scope must come from bearer token claims")


def _context_from_production_claims(
    claims: dict[str, Any],
    *,
    app_scope_map: AppScopeMap | None = None,
) -> AuthContext:
    try:
        roles = parse_role_claim(claims.get("roles"))
    except AuthRoleError as exc:
        raise AuthError(str(exc)) from exc

    tenant_id = _optional_str(claims.get("tenant_id"), "tenant_id")
    workspace_id = _optional_str(claims.get("workspace_id"), "workspace_id")
    if (tenant_id is None) != (workspace_id is None):
        raise AuthError("bearer token must provide tenant_id and workspace_id claims together")
    if tenant_id is None or workspace_id is None:
        tenant_id, workspace_id = _mapped_app_scope(claims, app_scope_map)

    return AuthContext(
        subject=_optional_str(claims.get("sub"), "sub"),
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        roles=roles,
        capabilities=capabilities_for_roles(roles),
        authorization_profile="production",
    )


def _mapped_app_scope(
    claims: dict[str, Any],
    app_scope_map: AppScopeMap | None,
) -> tuple[str, str]:
    if not app_scope_map:
        raise AuthError("bearer token tenant_id and workspace_id claims are required")
    if claims.get("idtyp") != "app":
        raise AuthError("server-mapped ETS scope requires an app-only bearer token")

    azp = _optional_str(claims.get("azp"), "azp")
    appid = _optional_str(claims.get("appid"), "appid")
    if azp is not None and appid is not None and azp.casefold() != appid.casefold():
        raise AuthError("bearer token application identity claims disagree")
    client_id = azp or appid
    if client_id is None:
        raise AuthError("app-only bearer token is missing azp/appid identity")
    scope = app_scope_map.get(client_id.casefold())
    if scope is None:
        raise AuthError("bearer token application is not authorized for an ETS scope")
    return scope


def _normalize_app_scope_map(app_scope_map: AppScopeMap | None) -> AppScopeMap:
    if app_scope_map is None:
        return {}
    normalized: AppScopeMap = {}
    for client_id, scope in app_scope_map.items():
        if not isinstance(client_id, str) or not client_id.strip():
            raise RuntimeError("production app scope map requires non-empty client IDs")
        if not isinstance(scope, tuple) or len(scope) != 2:
            raise RuntimeError("production app scope map values must be tenant/workspace tuples")
        tenant_id, workspace_id = scope
        if not tenant_id or not workspace_id:
            raise RuntimeError(
                "production app scope map requires non-empty tenant/workspace values"
            )
        normalized[client_id.strip().casefold()] = (tenant_id, workspace_id)
    return normalized


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _decode_segment(value: str, label: str) -> bytes:
    try:
        return _b64decode(value)
    except (binascii.Error, ValueError) as exc:
        raise AuthError(f"invalid {label}") from exc


def _decode_json_object(value: str, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_decode_segment(value, label))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuthError(f"invalid {label}") from exc
    if not isinstance(decoded, dict):
        raise AuthError(f"invalid {label}")
    return cast(dict[str, Any], decoded)


def _optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise AuthError(f"bearer token {field_name} claim must be a non-empty string")
    return value


def _required_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise AuthError(f"bearer token {field_name} must be a non-empty string")
    return value


def _validate_registered_claims(
    claims: dict[str, Any],
    *,
    issuer: str | None,
    audience: str | None,
    tenant_id: str | None = None,
) -> None:
    now = int(time.time())
    exp = claims.get("exp")
    if not isinstance(exp, int) or exp <= now:
        raise AuthError("bearer token expired")
    nbf = claims.get("nbf")
    if isinstance(nbf, int) and nbf > now:
        raise AuthError("bearer token not yet valid")
    if issuer is not None and claims.get("iss") != issuer:
        raise AuthError("bearer token issuer mismatch")
    if audience is not None and not _audience_matches(claims.get("aud"), audience):
        raise AuthError("bearer token audience mismatch")
    if tenant_id is not None and claims.get("tid") != tenant_id:
        raise AuthError("bearer token tenant mismatch")


def _audience_matches(value: Any, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, list):
        return expected in value
    return False


def _keys_from_jwks(jwks: dict[str, Any]) -> dict[str, dict[str, Any]]:
    keys = jwks.get("keys")
    if not isinstance(keys, list) or not keys:
        raise RuntimeError("JWKS must contain at least one key")
    trusted_keys = {
        _required_str(key.get("kid"), "kid"): key for key in keys if isinstance(key, dict)
    }
    if not trusted_keys:
        raise RuntimeError("JWKS must contain at least one key with a kid")
    return trusted_keys


def _load_jwks_from_url(jwks_url: str) -> dict[str, Any]:
    with urlopen(jwks_url, timeout=5) as response:
        return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))


def _rsa_public_key_from_jwk(jwk: dict[str, Any]) -> rsa.RSAPublicKey:
    if (
        jwk.get("kty") != "RSA"
        or jwk.get("alg") not in {None, "RS256"}
        or jwk.get("use") not in {None, "sig"}
    ):
        raise AuthError("unsupported JWKS key")
    n = int.from_bytes(_b64decode(_required_str(jwk.get("n"), "n")), "big")
    e = int.from_bytes(_b64decode(_required_str(jwk.get("e"), "e")), "big")
    return rsa.RSAPublicNumbers(e=e, n=n).public_key()


def _int_to_bytes(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")