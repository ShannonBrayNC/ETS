from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_BICEP = ROOT / "infra" / "azure" / "ets-hosted.bicep"
IDENTITY_BICEP = ROOT / "infra" / "azure" / "ets-gateway-identity.bicep"
GATEWAY_BICEP = ROOT / "infra" / "azure" / "ets-gateway.bicep"


def test_core_bicep_exposes_server_owned_app_scope_mapping() -> None:
    text = CORE_BICEP.read_text(encoding="utf-8")

    for term in (
        "param authTenantId string = ''",
        "param authAppScopeMapJson string = ''",
        "name: 'ETS_AUTH_TENANT_ID'",
        "value: authTenantId",
        "name: 'ETS_AUTH_APP_SCOPE_MAP_JSON'",
        "value: authAppScopeMapJson",
    ):
        assert term in text


def test_gateway_identity_prebootstrap_matches_gateway_deterministic_name() -> None:
    identity = IDENTITY_BICEP.read_text(encoding="utf-8")
    gateway = GATEWAY_BICEP.read_text(encoding="utf-8")

    shared_terms = (
        "uniqueString(resourceGroup().id, environmentName, connectorInstanceId)",
        "take('ets-${resourceToken}-gw-id', 128)",
        "Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31",
    )
    for term in shared_terms:
        assert term in identity
        assert term in gateway


def test_gateway_identity_prebootstrap_outputs_only_identity_metadata() -> None:
    text = IDENTITY_BICEP.read_text(encoding="utf-8")
    outputs = [line.strip() for line in text.splitlines() if line.startswith("output ")]

    assert outputs
    joined = "\n".join(outputs).lower()
    assert "gatewaymanagedidentityclientid" in joined
    assert "gatewaymanagedidentityprincipalid" in joined
    for prohibited in ("secret", "password", "token", "credential"):
        assert prohibited not in joined
