"""Authentication policy for ETS API modes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, cast
from urllib.request import urlopen

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import Request


class AuthError(PermissionError):
    """Raised when API authentication fails."""


@dataclass(frozen=True)
class AuthContext:
    subject: str | None = None
    tenant_id: str | None = None
    workspace_id: str | None = None


class AuthPolicy:
    def authenticate(self, request: Request) -> AuthContext:
        """Return the authenticated request context."""
        return AuthContext()


class LocalHeaderAuthPolicy(AuthPolicy):
    """Development auth mode; tenant/workspace scoping comes from headers."""


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
        return AuthContext(subject="local-api-key")


class ProductionJWTAuthPolicy(AuthPolicy):
    """Fail-closed HS256 JWT bearer auth for production-like deployments."""

    def __init__(self, secret: str, issuer: str | None = None) -> None:
        if len(secret) < 32:
            raise RuntimeError("ETS_AUTH_HS256_SECRET must be at least 32 characters")
        self._secret = secret.encode("utf-8")
        self._issuer = issuer

    def authenticate(self, request: Request) -> AuthContext:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("missing bearer token")

        claims = self._decode_token(token)
        tenant_id = _optional_str(claims.get("tenant_id"), "tenant_id")
        workspace_id = _optional_str(claims.get("workspace_id"), "workspace_id")
        subject = _optional_str(claims.get("sub"), "sub")
        return AuthContext(subject=subject, tenant_id=tenant_id, workspace_id=workspace_id)

    def _decode_token(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError("invalid bearer token")

        signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
        expected = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        actual = _b64decode(parts[2])
        if not hmac.compare_digest(expected, actual):
            raise AuthError("invalid bearer token signature")

        header = json.loads(_b64decode(parts[0]))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise AuthError("unsupported bearer token header")

        claims = cast(dict[str, Any], json.loads(_b64decode(parts[1])))
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
    ) -> None:
        keys = jwks.get("keys")
        if not isinstance(keys, list) or not keys:
            raise RuntimeError("JWKS must contain at least one key")
        self._keys = {
            _required_str(key.get("kid"), "kid"): key for key in keys if isinstance(key, dict)
        }
        if not self._keys:
            raise RuntimeError("JWKS must contain at least one key with a kid")
        self._issuer = issuer
        self._audience = audience

    @classmethod
    def from_json(
        cls,
        jwks_json: str,
        *,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> ProductionJWKSAuthPolicy:
        return cls(cast(dict[str, Any], json.loads(jwks_json)), issuer=issuer, audience=audience)

    @classmethod
    def from_url(
        cls,
        jwks_url: str,
        *,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> ProductionJWKSAuthPolicy:
        with urlopen(jwks_url, timeout=5) as response:
            jwks = cast(dict[str, Any], json.loads(response.read().decode("utf-8")))
        return cls(jwks, issuer=issuer, audience=audience)

    def authenticate(self, request: Request) -> AuthContext:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("missing bearer token")

        claims = self._decode_token(token)
        return AuthContext(
            subject=_optional_str(claims.get("sub"), "sub"),
            tenant_id=_optional_str(claims.get("tenant_id"), "tenant_id"),
            workspace_id=_optional_str(claims.get("workspace_id"), "workspace_id"),
        )

    def _decode_token(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError("invalid bearer token")
        header = cast(dict[str, Any], json.loads(_b64decode(parts[0])))
        if header.get("alg") != "RS256" or header.get("typ") != "JWT":
            raise AuthError("unsupported bearer token header")
        kid = _required_str(header.get("kid"), "kid")
        jwk = self._keys.get(kid)
        if jwk is None:
            raise AuthError("bearer token key not trusted")

        signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
        signature = _b64decode(parts[2])
        public_key = _rsa_public_key_from_jwk(jwk)
        try:
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
        except Exception as exc:
            raise AuthError("invalid bearer token signature") from exc

        claims = cast(dict[str, Any], json.loads(_b64decode(parts[1])))
        _validate_registered_claims(claims, issuer=self._issuer, audience=self._audience)
        return claims


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


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


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


def _audience_matches(value: Any, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, list):
        return expected in value
    return False


def _rsa_public_key_from_jwk(jwk: dict[str, Any]) -> rsa.RSAPublicKey:
    if jwk.get("kty") != "RSA" or jwk.get("alg") not in {None, "RS256"}:
        raise AuthError("unsupported JWKS key")
    n = int.from_bytes(_b64decode(_required_str(jwk.get("n"), "n")), "big")
    e = int.from_bytes(_b64decode(_required_str(jwk.get("e"), "e")), "big")
    return rsa.RSAPublicNumbers(e=e, n=n).public_key()


def _int_to_bytes(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")
