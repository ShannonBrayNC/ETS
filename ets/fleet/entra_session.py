"""Production Microsoft Entra session boundary for ETS Fleet C3B.

This module does not validate bearer-token signatures itself. Production hosting
must first authenticate the request and construct ``TrustedEntraIdentityContext``
from validated server-side identity/session state. Fleet then revalidates the
issuer/audience/tenant/time/role/session standing that it depends on and resolves
ETS scope only from a server-owned mapping.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.fleet.models import ScopeBinding, normalize_time
from ets.fleet.portal import FleetPrincipal, FleetRole, principal_from_entra_claims
from ets.fleet.portal_admin import FleetSecuritySession


class StrictProductionAuthModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProductionFleetAuthConfig(StrictProductionAuthModel):
    """Required production Entra values. Missing configuration fails startup."""

    issuer: str = Field(min_length=8, max_length=512)
    audience: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=1, max_length=128)
    trusted_context_state_key: str = Field(
        default="ets_fleet_entra_context",
        min_length=1,
        max_length=128,
    )
    max_clock_skew_seconds: int = Field(default=60, ge=0, le=300)

    @field_validator("issuer")
    @classmethod
    def require_https_issuer(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("production Fleet Entra issuer must use HTTPS")
        return normalized

    @field_validator("audience", "tenant_id", "trusted_context_state_key")
    @classmethod
    def strip_required_values(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("production Fleet authentication value is required")
        return normalized


class TrustedEntraIdentityContext(StrictProductionAuthModel):
    """Already-validated identity/session context supplied by trusted hosting code."""

    issuer: str = Field(min_length=8, max_length=512)
    audience: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=1, max_length=128)
    oid: str | None = Field(default=None, min_length=1, max_length=256)
    sub: str | None = Field(default=None, min_length=1, max_length=256)
    roles: tuple[str, ...] = Field(min_length=1, max_length=3)
    expires_at_utc: datetime
    authenticated_at_utc: datetime
    session_id: str = Field(min_length=16, max_length=256)
    session_generation: int = Field(ge=1)
    csrf_token: str = Field(min_length=32, max_length=256)
    step_up_at_utc: datetime | None = None

    @field_validator("expires_at_utc", "authenticated_at_utc", "step_up_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_time(value)

    @model_validator(mode="after")
    def require_stable_subject(self) -> TrustedEntraIdentityContext:
        if not (self.oid and self.oid.strip()) and not (self.sub and self.sub.strip()):
            raise ValueError("trusted Entra context requires oid or sub")
        return self

    @property
    def stable_subject(self) -> str:
        value = self.oid or self.sub
        assert value is not None
        return value.strip()


class FleetSessionStanding(StrictProductionAuthModel):
    """Current server-side session standing used to invalidate stale browser state."""

    active: bool
    generation: int = Field(ge=1)
    roles: tuple[FleetRole, ...] = Field(min_length=1, max_length=3)
    not_before_utc: datetime

    @field_validator("not_before_utc")
    @classmethod
    def normalize_not_before(cls, value: datetime) -> datetime:
        return normalize_time(value)


class FleetScopeResolver(Protocol):
    """Resolve ETS scope from server-owned subject/tenant authorization state."""

    def resolve_scopes(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
    ) -> tuple[ScopeBinding, ...]: ...


class FleetSessionStandingResolver(Protocol):
    """Resolve current revocation/role/session generation from the server side."""

    def resolve_standing(
        self,
        *,
        subject: str,
        session_id: str,
    ) -> FleetSessionStanding | None: ...


class FleetProductionAuthenticationError(PermissionError):
    pass


class FleetSessionCookiePolicy(StrictProductionAuthModel):
    """Mandatory production session-cookie posture owned by the hosting layer."""

    name: str = "__Host-ets-fleet"
    secure: bool = True
    httponly: bool = True
    samesite: str = "strict"
    path: str = "/"
    domain: str | None = None

    @model_validator(mode="after")
    def enforce_host_cookie(self) -> FleetSessionCookiePolicy:
        if not self.name.startswith("__Host-"):
            raise ValueError("production Fleet cookie must use the __Host- prefix")
        if not self.secure or not self.httponly:
            raise ValueError("production Fleet cookie must be Secure and HttpOnly")
        if self.samesite.lower() not in {"strict", "lax"}:
            raise ValueError("production Fleet cookie SameSite must be Strict or Lax")
        if self.path != "/" or self.domain is not None:
            raise ValueError("__Host- Fleet cookie requires Path=/ and no Domain")
        return self


FLEET_PRODUCTION_COOKIE_POLICY = FleetSessionCookiePolicy()


class ProductionFleetSessionAdapter:
    """Resolve Fleet principal/security session from a trusted Entra context."""

    def __init__(
        self,
        *,
        config: ProductionFleetAuthConfig,
        scope_resolver: FleetScopeResolver,
        standing_resolver: FleetSessionStandingResolver,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._scope_resolver = scope_resolver
        self._standing_resolver = standing_resolver
        self._clock = clock or (lambda: datetime.now(UTC))

    def resolve(
        self,
        context: TrustedEntraIdentityContext,
    ) -> tuple[FleetPrincipal, FleetSecuritySession]:
        now = normalize_time(self._clock())
        skew = timedelta(seconds=self._config.max_clock_skew_seconds)
        if context.issuer.rstrip("/") != self._config.issuer:
            raise FleetProductionAuthenticationError("Fleet Entra issuer mismatch")
        if context.audience != self._config.audience:
            raise FleetProductionAuthenticationError("Fleet Entra audience mismatch")
        if context.tenant_id != self._config.tenant_id:
            raise FleetProductionAuthenticationError("Fleet Entra tenant mismatch")
        if context.expires_at_utc + skew <= now:
            raise FleetProductionAuthenticationError("Fleet Entra identity context expired")
        if context.authenticated_at_utc - skew > now:
            raise FleetProductionAuthenticationError("Fleet authentication time is in the future")

        roles = self._validated_roles(context.roles)
        standing = self._standing_resolver.resolve_standing(
            subject=context.stable_subject,
            session_id=context.session_id,
        )
        if standing is None or not standing.active:
            raise FleetProductionAuthenticationError("Fleet session is revoked or unknown")
        if standing.generation != context.session_generation:
            raise FleetProductionAuthenticationError("Fleet session generation is stale")
        if context.authenticated_at_utc < standing.not_before_utc:
            raise FleetProductionAuthenticationError("Fleet session predates current authorization")
        if set(roles) != set(standing.roles):
            raise FleetProductionAuthenticationError("Fleet app roles changed after session issuance")

        scopes = self._scope_resolver.resolve_scopes(
            subject=context.stable_subject,
            entra_tenant_id=context.tenant_id,
        )
        if not scopes:
            raise FleetProductionAuthenticationError("Fleet principal has no server-owned ETS scope")

        principal = principal_from_entra_claims(
            {
                "oid": context.oid,
                "sub": context.sub,
                "roles": [role.value for role in roles],
            },
            scope_bindings=scopes,
        )
        security_session = FleetSecuritySession(
            session_id=context.session_id,
            csrf_token=context.csrf_token,
            authenticated_at_utc=context.authenticated_at_utc,
            step_up_at_utc=context.step_up_at_utc,
        )
        return principal, security_session

    @staticmethod
    def _validated_roles(raw_roles: tuple[str, ...]) -> tuple[FleetRole, ...]:
        roles: list[FleetRole] = []
        for value in raw_roles:
            try:
                role = FleetRole(value)
            except ValueError as exc:
                raise FleetProductionAuthenticationError(
                    "trusted Entra context contains an unsupported Fleet app role"
                ) from exc
            if role not in roles:
                roles.append(role)
        if not roles:
            raise FleetProductionAuthenticationError("Fleet app role is required")
        return tuple(roles)


class ProductionFleetRequestResolvers:
    """FastAPI resolver pair that reads only trusted request-state context.

    Browser headers, query parameters, request bodies, and cookies are never
    interpreted as issuer/audience/tenant/scope/role/step-up authority here.
    The hosting authentication layer owns creation of the typed trusted context.
    """

    _CACHE_KEY = "_ets_fleet_resolved_session"

    def __init__(
        self,
        *,
        config: ProductionFleetAuthConfig,
        adapter: ProductionFleetSessionAdapter,
    ) -> None:
        self._config = config
        self._adapter = adapter

    def principal(self, request: Request) -> FleetPrincipal | None:
        resolved = self._resolve_request(request)
        return None if resolved is None else resolved[0]

    def security_session(self, request: Request) -> FleetSecuritySession | None:
        resolved = self._resolve_request(request)
        return None if resolved is None else resolved[1]

    def _resolve_request(
        self,
        request: Request,
    ) -> tuple[FleetPrincipal, FleetSecuritySession] | None:
        cached = getattr(request.state, self._CACHE_KEY, None)
        if isinstance(cached, tuple) and len(cached) == 2:
            principal, session = cached
            if isinstance(principal, FleetPrincipal) and isinstance(session, FleetSecuritySession):
                return principal, session

        raw_context = getattr(request.state, self._config.trusted_context_state_key, None)
        if not isinstance(raw_context, TrustedEntraIdentityContext):
            return None
        try:
            resolved = self._adapter.resolve(raw_context)
        except FleetProductionAuthenticationError:
            return None
        setattr(request.state, self._CACHE_KEY, resolved)
        return resolved
