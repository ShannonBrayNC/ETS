from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from ets.fleet.entra_session import (
    FleetProductionAuthenticationError,
    FleetSessionCookiePolicy,
    FleetSessionStanding,
    ProductionFleetAuthConfig,
    ProductionFleetRequestResolvers,
    ProductionFleetSessionAdapter,
    TrustedEntraIdentityContext,
)
from ets.fleet.models import ScopeBinding
from ets.fleet.portal import FleetRole
from ets.fleet.production_runtime import create_production_fleet_app

NOW = datetime(2026, 8, 22, 6, 30, tzinfo=UTC)
ISSUER = "https://login.microsoftonline.com/tenant-id/v2.0"
AUDIENCE = "api://ets-fleet"
ENTRA_TENANT = "tenant-id"
SESSION = "session-0123456789abcdef"
CSRF = "csrf-" + "x" * 48


class StaticAuthorizationState:
    def __init__(
        self,
        *,
        scopes: tuple[ScopeBinding, ...] | None = None,
        standing: FleetSessionStanding | None = None,
    ) -> None:
        self.scopes = scopes or (
            ScopeBinding(tenant_id="ets-tenant", workspace_id="workspace-a"),
        )
        self.standing = standing or FleetSessionStanding(
            active=True,
            generation=7,
            roles=(FleetRole.SECURITY_ADMIN,),
            not_before_utc=NOW - timedelta(hours=2),
            step_up_not_before_utc=NOW - timedelta(minutes=10),
        )

    def resolve_scopes(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
    ) -> tuple[ScopeBinding, ...]:
        assert subject == "object-123"
        assert entra_tenant_id == ENTRA_TENANT
        return self.scopes

    def resolve_standing(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
        session_id: str,
    ) -> FleetSessionStanding | None:
        assert subject == "object-123"
        assert entra_tenant_id == ENTRA_TENANT
        assert session_id == SESSION
        return self.standing


def config() -> ProductionFleetAuthConfig:
    return ProductionFleetAuthConfig(
        issuer=ISSUER,
        audience=AUDIENCE,
        tenant_id=ENTRA_TENANT,
        max_clock_skew_seconds=0,
    )


def context(**updates: object) -> TrustedEntraIdentityContext:
    values: dict[str, object] = {
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "tenant_id": ENTRA_TENANT,
        "oid": "object-123",
        "roles": (FleetRole.SECURITY_ADMIN.value,),
        "expires_at_utc": NOW + timedelta(hours=1),
        "authenticated_at_utc": NOW - timedelta(hours=1),
        "session_id": SESSION,
        "session_generation": 7,
        "csrf_token": CSRF,
        "step_up_at_utc": NOW - timedelta(minutes=2),
    }
    values.update(updates)
    return TrustedEntraIdentityContext.model_validate(values)


def adapter(state: StaticAuthorizationState) -> ProductionFleetSessionAdapter:
    return ProductionFleetSessionAdapter(
        config=config(),
        scope_resolver=state,
        standing_resolver=state,
        clock=lambda: NOW,
    )


def test_valid_context_uses_only_server_owned_scope_and_current_standing() -> None:
    state = StaticAuthorizationState()
    principal, security_session = adapter(state).resolve(context())

    assert principal.subject == "object-123"
    assert principal.roles == (FleetRole.SECURITY_ADMIN,)
    assert principal.scope_bindings == state.scopes
    assert security_session.session_id == SESSION
    assert security_session.step_up_at_utc == NOW - timedelta(minutes=2)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"issuer": "https://issuer.invalid"}, "issuer"),
        ({"audience": "api://attacker"}, "audience"),
        ({"tenant_id": "other-tenant"}, "tenant"),
        ({"expires_at_utc": NOW}, "expired"),
        ({"session_generation": 6}, "generation"),
        ({"roles": (FleetRole.OPERATOR.value,)}, "roles"),
    ],
)
def test_wrong_issuer_audience_tenant_expiry_generation_or_roles_fail_closed(
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(FleetProductionAuthenticationError, match=message):
        adapter(StaticAuthorizationState()).resolve(context(**updates))


def test_unknown_or_forged_app_role_fails_closed() -> None:
    with pytest.raises(FleetProductionAuthenticationError, match="unsupported Fleet app role"):
        adapter(StaticAuthorizationState()).resolve(
            context(roles=("Fleet.Root",))
        )


def test_revoked_session_or_absent_server_scope_fails_closed() -> None:
    revoked = StaticAuthorizationState(
        standing=FleetSessionStanding(
            active=False,
            generation=7,
            roles=(FleetRole.SECURITY_ADMIN,),
            not_before_utc=NOW - timedelta(hours=2),
        )
    )
    with pytest.raises(FleetProductionAuthenticationError, match="revoked"):
        adapter(revoked).resolve(context())

    no_scope = StaticAuthorizationState(scopes=())
    no_scope.scopes = ()
    with pytest.raises(FleetProductionAuthenticationError, match="no server-owned ETS scope"):
        adapter(no_scope).resolve(context())


def test_old_step_up_is_discarded_after_server_side_step_up_epoch_change() -> None:
    state = StaticAuthorizationState(
        standing=FleetSessionStanding(
            active=True,
            generation=7,
            roles=(FleetRole.SECURITY_ADMIN,),
            not_before_utc=NOW - timedelta(hours=2),
            step_up_not_before_utc=NOW - timedelta(minutes=1),
        )
    )
    _principal, security_session = adapter(state).resolve(context())
    assert security_session.step_up_at_utc is None


def test_browser_headers_cannot_create_principal_scope_role_or_step_up() -> None:
    state = StaticAuthorizationState()
    session_adapter = adapter(state)
    resolvers = ProductionFleetRequestResolvers(
        config=config(),
        adapter=session_adapter,
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/fleet",
            "headers": [
                (b"x-ets-tenant", b"attacker"),
                (b"x-ets-workspace", b"attacker"),
                (b"x-ets-role", b"Fleet.SecurityAdmin"),
                (b"x-ets-step-up", b"true"),
            ],
        }
    )
    assert resolvers.principal(request) is None
    assert resolvers.security_session(request) is None

    request.state.ets_fleet_entra_context = context()
    principal = resolvers.principal(request)
    assert principal is not None
    assert principal.scope_bindings == state.scopes


def test_production_cookie_policy_rejects_insecure_or_non_host_cookie() -> None:
    with pytest.raises(ValidationError):
        FleetSessionCookiePolicy(name="ets-fleet")
    with pytest.raises(ValidationError):
        FleetSessionCookiePolicy(secure=False)
    with pytest.raises(ValidationError):
        FleetSessionCookiePolicy(domain="lanternprotocol.net")


def test_production_startup_fails_closed_when_required_configuration_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    required = (
        "ETS_FLEET_POSTGRES_HOST",
        "ETS_FLEET_POSTGRES_DATABASE",
        "ETS_FLEET_POSTGRES_USER",
        "ETS_FLEET_ENTRA_ISSUER",
        "ETS_FLEET_ENTRA_AUDIENCE",
        "ETS_FLEET_ENTRA_TENANT_ID",
    )
    for name in required:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="ETS_FLEET_POSTGRES_HOST is required"):
        create_production_fleet_app()
