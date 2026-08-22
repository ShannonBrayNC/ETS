"""Trusted Azure Container Apps EasyAuth bridge for Fleet C3C.

Azure Container Apps authentication validates Microsoft Entra tokens before the
request reaches the application and injects ``X-MS-CLIENT-PRINCIPAL``. Microsoft
documents that external requests cannot set the injected identity headers. Fleet
still treats that platform assertion as an input to its own stricter issuer,
audience, tenant, role, scope, revocation, and step-up standing checks.

This bridge never reads or retains access tokens, refresh tokens, EasyAuth
cookies, database credentials, or Azure management credentials.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime

from fastapi import Request
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from ets.fleet.entra_session import (
    ProductionFleetAuthConfig,
    TrustedEntraIdentityContext,
)

_CLIENT_PRINCIPAL_HEADER = "x-ms-client-principal"
_ROLE_CLAIM = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
_OID_CLAIM = "http://schemas.microsoft.com/identity/claims/objectidentifier"
_TENANT_CLAIM = "http://schemas.microsoft.com/identity/claims/tenantid"
_ALLOWED_AUTH_TYPES = frozenset({"aad", "azureactivedirectory"})


class ContainerAppsEasyAuthError(ValueError):
    """The platform-injected principal is missing required trusted claims."""


def trusted_context_from_container_apps_principal(
    encoded_principal: str,
    *,
    config: ProductionFleetAuthConfig,
    step_up_auth_context_id: str,
) -> TrustedEntraIdentityContext:
    """Convert one EasyAuth client-principal header into Fleet trusted context.

    The caller must only use this function behind Azure Container Apps built-in
    authentication with direct public origin access disabled. It does not make a
    browser-supplied header trustworthy on its own.
    """

    payload = _decode_principal(encoded_principal)
    auth_type = payload.get("auth_typ")
    if not isinstance(auth_type, str) or auth_type.lower() not in _ALLOWED_AUTH_TYPES:
        raise ContainerAppsEasyAuthError("Fleet requires the Entra EasyAuth provider")

    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise ContainerAppsEasyAuthError("EasyAuth principal has no claims")
    claims = _normalize_claims(raw_claims)

    issuer = _one_claim(claims, "iss").rstrip("/")
    audience = _one_claim(claims, "aud")
    tenant_id = _one_claim(claims, "tid", _TENANT_CLAIM)
    if issuer != config.issuer:
        raise ContainerAppsEasyAuthError(
            "EasyAuth issuer does not match Fleet configuration"
        )
    if audience != config.audience:
        raise ContainerAppsEasyAuthError(
            "EasyAuth audience does not match Fleet configuration"
        )
    if tenant_id != config.tenant_id:
        raise ContainerAppsEasyAuthError(
            "EasyAuth tenant does not match Fleet configuration"
        )

    oid = _optional_one_claim(claims, "oid", _OID_CLAIM)
    sub = _optional_one_claim(claims, "sub")
    if oid is None and sub is None:
        raise ContainerAppsEasyAuthError("EasyAuth principal has no stable subject")

    role_type = payload.get("role_typ")
    if role_type is not None and not isinstance(role_type, str):
        raise ContainerAppsEasyAuthError("EasyAuth role claim type is invalid")
    roles = _multi_claim(
        claims,
        *(item for item in (role_type, "roles", _ROLE_CLAIM) if item),
    )
    if not roles:
        raise ContainerAppsEasyAuthError("EasyAuth principal has no Fleet app role")

    expires_at = _unix_claim(claims, "exp")
    authenticated_at = _unix_claim(claims, "auth_time")
    session_id = _one_claim(claims, "sid")
    auth_contexts = _expanded_multi_claim(claims, "acrs")
    step_up_at = (
        authenticated_at
        if step_up_auth_context_id in auth_contexts
        else None
    )

    stable_subject = oid or sub
    assert stable_subject is not None
    csrf_token = _csrf_token(
        session_id=session_id,
        subject=stable_subject,
        tenant_id=tenant_id,
    )

    try:
        return TrustedEntraIdentityContext(
            issuer=issuer,
            audience=audience,
            tenant_id=tenant_id,
            oid=oid,
            sub=sub,
            roles=tuple(roles),
            expires_at_utc=expires_at,
            authenticated_at_utc=authenticated_at,
            session_id=session_id,
            session_generation=1,
            csrf_token=csrf_token,
            step_up_at_utc=step_up_at,
        )
    except ValidationError as exc:
        raise ContainerAppsEasyAuthError(
            "EasyAuth principal does not satisfy the Fleet trusted-context contract"
        ) from exc


class ContainerAppsEasyAuthMiddleware(BaseHTTPMiddleware):
    """Populate Fleet request state from the platform-injected principal only."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        config: ProductionFleetAuthConfig,
        step_up_auth_context_id: str,
    ) -> None:
        super().__init__(app)
        normalized = step_up_auth_context_id.strip()
        if not normalized:
            raise ValueError("Fleet step-up Entra authentication context is required")
        self._config = config
        self._step_up_auth_context_id = normalized

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        encoded = request.headers.get(_CLIENT_PRINCIPAL_HEADER)
        if encoded:
            try:
                context = trusted_context_from_container_apps_principal(
                    encoded,
                    config=self._config,
                    step_up_auth_context_id=self._step_up_auth_context_id,
                )
            except ContainerAppsEasyAuthError:
                context = None
            if context is not None:
                setattr(
                    request.state,
                    self._config.trusted_context_state_key,
                    context,
                )
        return await call_next(request)


def _decode_principal(encoded: str) -> dict[str, object]:
    value = encoded.strip()
    if not value or len(value) > 64 * 1024:
        raise ContainerAppsEasyAuthError("EasyAuth principal is empty or oversized")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ContainerAppsEasyAuthError("EasyAuth principal is not valid base64") from exc
    if len(decoded) > 48 * 1024:
        raise ContainerAppsEasyAuthError("EasyAuth principal payload is oversized")
    try:
        payload = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContainerAppsEasyAuthError("EasyAuth principal is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ContainerAppsEasyAuthError("EasyAuth principal must be a JSON object")
    return payload


def _normalize_claims(raw_claims: list[object]) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, list[str]] = {}
    for raw in raw_claims:
        if not isinstance(raw, dict):
            raise ContainerAppsEasyAuthError("EasyAuth claim entry is invalid")
        claim_type = raw.get("typ")
        claim_value = raw.get("val")
        if not isinstance(claim_type, str) or not isinstance(claim_value, str):
            raise ContainerAppsEasyAuthError("EasyAuth claim type/value is invalid")
        claim_type = claim_type.strip()
        claim_value = claim_value.strip()
        if not claim_type or not claim_value:
            raise ContainerAppsEasyAuthError("EasyAuth claim type/value is empty")
        normalized.setdefault(claim_type, []).append(claim_value)
    return {key: tuple(values) for key, values in normalized.items()}


def _one_claim(claims: dict[str, tuple[str, ...]], *names: str) -> str:
    values = _multi_claim(claims, *names)
    if len(values) != 1:
        raise ContainerAppsEasyAuthError(
            f"EasyAuth principal requires exactly one {names[0]} claim"
        )
    return values[0]


def _optional_one_claim(
    claims: dict[str, tuple[str, ...]],
    *names: str,
) -> str | None:
    values = _multi_claim(claims, *names)
    if not values:
        return None
    if len(values) != 1:
        raise ContainerAppsEasyAuthError(
            f"EasyAuth principal has ambiguous {names[0]} claims"
        )
    return values[0]


def _multi_claim(
    claims: dict[str, tuple[str, ...]],
    *names: str,
) -> tuple[str, ...]:
    values: list[str] = []
    for name in names:
        for value in claims.get(name, ()):
            if value not in values:
                values.append(value)
    return tuple(values)


def _expanded_multi_claim(
    claims: dict[str, tuple[str, ...]],
    *names: str,
) -> tuple[str, ...]:
    values: list[str] = []
    for raw in _multi_claim(claims, *names):
        expanded: list[str]
        if raw.startswith("["):
            try:
                decoded = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ContainerAppsEasyAuthError(
                    "EasyAuth multi-value claim is malformed"
                ) from exc
            if not isinstance(decoded, list) or not all(
                isinstance(item, str) for item in decoded
            ):
                raise ContainerAppsEasyAuthError(
                    "EasyAuth multi-value claim must contain strings"
                )
            expanded = [item.strip() for item in decoded if item.strip()]
        else:
            expanded = [raw]
        for item in expanded:
            if item not in values:
                values.append(item)
    return tuple(values)


def _unix_claim(
    claims: dict[str, tuple[str, ...]],
    name: str,
) -> datetime:
    raw = _one_claim(claims, name)
    try:
        seconds = int(raw)
    except ValueError as exc:
        raise ContainerAppsEasyAuthError(
            f"EasyAuth {name} claim is not a Unix timestamp"
        ) from exc
    if seconds <= 0:
        raise ContainerAppsEasyAuthError(
            f"EasyAuth {name} claim must be positive"
        )
    try:
        return datetime.fromtimestamp(seconds, tz=UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise ContainerAppsEasyAuthError(
            f"EasyAuth {name} claim is out of range"
        ) from exc


def _csrf_token(*, session_id: str, subject: str, tenant_id: str) -> str:
    material = "\x00".join(
        ("ets-fleet-c3c-csrf-v1", session_id, subject, tenant_id)
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()
