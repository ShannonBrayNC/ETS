from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

import pytest

from ets.fleet.container_apps_auth import (
    ContainerAppsEasyAuthError,
    trusted_context_from_container_apps_principal,
)
from ets.fleet.entra_session import ProductionFleetAuthConfig
from ets.fleet.portal import FleetRole
from ets.fleet.production_runtime import create_production_fleet_app

ISSUER = "https://login.microsoftonline.com/tenant-id/v2.0"
AUDIENCE = "api://ets-fleet"
TENANT_ID = "tenant-id"
OID = "11111111-2222-3333-4444-555555555555"
SID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
AUTH_TIME = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)
EXPIRES = datetime(2026, 8, 22, 7, 0, tzinfo=UTC)


def _config() -> ProductionFleetAuthConfig:
    return ProductionFleetAuthConfig(
        issuer=ISSUER,
        audience=AUDIENCE,
        tenant_id=TENANT_ID,
    )


def _principal_header(
    *,
    auth_type: str = "aad",
    claims: list[dict[str, str]] | None = None,
) -> str:
    values = claims or [
        {"typ": "iss", "val": ISSUER},
        {"typ": "aud", "val": AUDIENCE},
        {
            "typ": "http://schemas.microsoft.com/identity/claims/tenantid",
            "val": TENANT_ID,
        },
        {
            "typ": "http://schemas.microsoft.com/identity/claims/objectidentifier",
            "val": OID,
        },
        {"typ": "roles", "val": FleetRole.OPERATOR.value},
        {"typ": "exp", "val": str(int(EXPIRES.timestamp()))},
        {"typ": "auth_time", "val": str(int(AUTH_TIME.timestamp()))},
        {"typ": "sid", "val": SID},
        {"typ": "acrs", "val": "c1"},
    ]
    payload = {
        "auth_typ": auth_type,
        "name_typ": "name",
        "role_typ": "roles",
        "claims": values,
    }
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(encoded).decode("ascii")


def test_platform_principal_builds_typed_context_and_step_up() -> None:
    context = trusted_context_from_container_apps_principal(
        _principal_header(),
        config=_config(),
        step_up_auth_context_id="c1",
    )

    assert context.issuer == ISSUER
    assert context.audience == AUDIENCE
    assert context.tenant_id == TENANT_ID
    assert context.oid == OID
    assert context.roles == (FleetRole.OPERATOR.value,)
    assert context.expires_at_utc == EXPIRES
    assert context.authenticated_at_utc == AUTH_TIME
    assert context.session_id == SID
    assert context.session_generation == 1
    assert context.step_up_at_utc == AUTH_TIME
    assert len(context.csrf_token) == 64
    assert SID not in context.csrf_token


def test_missing_required_auth_context_never_claims_step_up() -> None:
    claims = [
        item
        for item in json.loads(
            base64.b64decode(_principal_header()).decode("utf-8")
        )["claims"]
        if item["typ"] != "acrs"
    ]
    context = trusted_context_from_container_apps_principal(
        _principal_header(claims=claims),
        config=_config(),
        step_up_auth_context_id="c1",
    )
    assert context.step_up_at_utc is None


def test_json_array_acrs_is_supported_without_relaxing_role_validation() -> None:
    claims = [
        item
        for item in json.loads(
            base64.b64decode(_principal_header()).decode("utf-8")
        )["claims"]
        if item["typ"] != "acrs"
    ]
    claims.append({"typ": "acrs", "val": '["c1","c2"]'})
    context = trusted_context_from_container_apps_principal(
        _principal_header(claims=claims),
        config=_config(),
        step_up_auth_context_id="c2",
    )
    assert context.step_up_at_utc == AUTH_TIME
    assert context.roles == (FleetRole.OPERATOR.value,)


@pytest.mark.parametrize(
    "header",
    [
        "not-base64",
        _principal_header(auth_type="github"),
    ],
)
def test_malformed_or_non_entra_platform_principal_fails_closed(header: str) -> None:
    with pytest.raises(ContainerAppsEasyAuthError):
        trusted_context_from_container_apps_principal(
            header,
            config=_config(),
            step_up_auth_context_id="c1",
        )


def test_typed_context_validation_failure_is_normalized_to_auth_failure() -> None:
    payload = json.loads(base64.b64decode(_principal_header()).decode("utf-8"))
    claims = payload["claims"]
    claims.extend(
        [
            {"typ": "roles", "val": "Fleet.ExtraOne"},
            {"typ": "roles", "val": "Fleet.ExtraTwo"},
            {"typ": "roles", "val": "Fleet.ExtraThree"},
        ]
    )
    with pytest.raises(ContainerAppsEasyAuthError, match="trusted-context contract"):
        trusted_context_from_container_apps_principal(
            _principal_header(claims=claims),
            config=_config(),
            step_up_auth_context_id="c1",
        )


def test_ambiguous_security_critical_claim_fails_closed() -> None:
    payload = json.loads(base64.b64decode(_principal_header()).decode("utf-8"))
    claims = payload["claims"]
    claims.append({"typ": "tid", "val": "attacker-tenant"})
    with pytest.raises(ContainerAppsEasyAuthError, match="exactly one tid"):
        trusted_context_from_container_apps_principal(
            _principal_header(claims=claims),
            config=_config(),
            step_up_auth_context_id="c1",
        )


def test_missing_session_identifier_fails_closed() -> None:
    claims = [
        item
        for item in json.loads(
            base64.b64decode(_principal_header()).decode("utf-8")
        )["claims"]
        if item["typ"] != "sid"
    ]
    with pytest.raises(ContainerAppsEasyAuthError, match="sid"):
        trusted_context_from_container_apps_principal(
            _principal_header(claims=claims),
            config=_config(),
            step_up_auth_context_id="c1",
        )


def test_production_startup_requires_explicit_protected_auth_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = {
        "ETS_FLEET_POSTGRES_HOST": "fleet.postgres.database.azure.com",
        "ETS_FLEET_POSTGRES_DATABASE": "fleet",
        "ETS_FLEET_POSTGRES_USER": "ets-fleet-runtime",
        "ETS_FLEET_ENTRA_ISSUER": ISSUER,
        "ETS_FLEET_ENTRA_AUDIENCE": AUDIENCE,
        "ETS_FLEET_ENTRA_TENANT_ID": TENANT_ID,
    }
    for name, value in configured.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ETS_FLEET_AUTH_BRIDGE", raising=False)

    with pytest.raises(RuntimeError, match="ETS_FLEET_AUTH_BRIDGE is required"):
        create_production_fleet_app()
