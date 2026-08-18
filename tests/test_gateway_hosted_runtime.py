from __future__ import annotations

import json

import pytest

from ets.gateway.hosted_runtime import HostedMicrosoftGatewaySettings, _connector_instance


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID": "11111111-1111-1111-1111-111111111111",
        "ETS_GATEWAY_CORE_BASE_URL": "https://core.internal.example",
        "ETS_GATEWAY_CORE_SCOPE": "api://ets-core/.default",
        "ETS_GATEWAY_TENANT_ID": "tenant_echo",
        "ETS_GATEWAY_WORKSPACE_ID": "workspace_echo",
        "ETS_GATEWAY_INSTANCE_ID": "echomedia-sharepoint",
        "ETS_GATEWAY_SOURCE_ID": "echomedia-sharepoint-prod",
        "ETS_GATEWAY_SOURCE_PRINCIPAL": "gateway://microsoft/sharepoint",
        "ETS_GATEWAY_MICROSOFT_TENANT_ID": "22222222-2222-2222-2222-222222222222",
        "ETS_GATEWAY_MICROSOFT_APPLICATION_ID": "11111111-1111-1111-1111-111111111111",
        "ETS_GATEWAY_SHAREPOINT_DRIVE_ID": "drive-1",
        "ETS_AUTH_JWKS_JSON": '{"keys":[]}',
        "ETS_AUTH_ISSUER": "https://issuer.example/",
        "ETS_AUTH_AUDIENCE": "api://ets-gateway",
        "ETS_AUTH_TENANT_ID": "22222222-2222-2222-2222-222222222222",
        "ETS_AUTH_APP_SCOPE_MAP_JSON": json.dumps(
            {
                "33333333-3333-3333-3333-333333333333": {
                    "tenant_id": "tenant_echo",
                    "workspace_id": "workspace_echo",
                }
            }
        ),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ETS_AUTH_JWKS_URL", raising=False)
    monkeypatch.delenv("ETS_GATEWAY_GRAPH_SUBSCRIPTION_JSON", raising=False)
    monkeypatch.delenv("ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON", raising=False)


def test_settings_require_production_jwks_and_server_scope_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)

    settings = HostedMicrosoftGatewaySettings.from_env()

    assert settings.auth_jwks_json == '{"keys":[]}'
    assert settings.auth_jwks_url is None
    assert settings.auth_app_scope_map[
        "33333333-3333-3333-3333-333333333333"
    ] == ("tenant_echo", "workspace_echo")
    assert settings.poll_interval_seconds == 60


def test_settings_reject_ambiguous_jwks_source(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ETS_AUTH_JWKS_URL", "https://issuer.example/jwks")

    with pytest.raises(RuntimeError, match="exactly one"):
        HostedMicrosoftGatewaySettings.from_env()


def test_settings_require_graph_subscription_and_policy_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv(
        "ETS_GATEWAY_GRAPH_SUBSCRIPTION_JSON",
        json.dumps(
            {
                "schema_version": "ets.connector.microsoft.graph_subscription_state.v1",
                "subscription_id": "subscription-1",
                "tenant_id": "22222222-2222-2222-2222-222222222222",
                "cloud": "global",
                "resource": "drives/drive-1/root",
                "client_state_sha256": "0" * 64,
                "expiration_date_time": "2026-08-21T12:00:00Z",
                "status": "active",
                "gap_state": "none",
            }
        ),
    )

    with pytest.raises(RuntimeError, match="configured together"):
        HostedMicrosoftGatewaySettings.from_env()


def test_connector_instance_uses_deployment_authoritative_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    settings = HostedMicrosoftGatewaySettings.from_env()

    instance = _connector_instance(settings, "1.0.0")

    assert instance.scope.tenant_id == "tenant_echo"
    assert instance.scope.workspace_id == "workspace_echo"
    assert instance.authentication.credential_ref == "azure-mi://microsoft-graph"
    assert instance.checkpoint.strategy == "source_cursor"
    assert instance.settings == {
        "tenant_profile_id": "hosted-microsoft",
        "scope": "drive",
        "drive_id": "drive-1",
    }


@pytest.mark.parametrize("value", ["29", "3601", "not-an-int"])
def test_poll_interval_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ETS_GATEWAY_POLL_INTERVAL_SECONDS", value)

    with pytest.raises(RuntimeError):
        HostedMicrosoftGatewaySettings.from_env()
