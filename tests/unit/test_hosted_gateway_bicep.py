from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BICEP = ROOT / "infra" / "azure" / "ets-gateway.bicep"


def _template() -> str:
    return BICEP.read_text(encoding="utf-8")


def test_gateway_bicep_uses_single_internal_container_app() -> None:
    text = _template()

    required = [
        "Microsoft.App/containerApps@2026-01-01",
        "activeRevisionsMode: 'Single'",
        "external: false",
        "allowInsecure: false",
        "minReplicas: 1",
        "maxReplicas: 1",
        "path: '/health'",
        "path: '/ready'",
        "path: '/version'",
        "'ets.gateway.container_entrypoint'",
    ]
    for term in required:
        assert term in text


def test_gateway_bicep_mounts_bounded_q1_state_without_container_secret() -> None:
    text = _template()

    required = [
        "Microsoft.App/managedEnvironments/storages@2026-01-01",
        "accountKeyVaultProperties:",
        "identity: gatewayIdentity.id",
        "storageType: 'AzureFile'",
        "mountOptions: 'nobrl'",
        "ets-gateway-state-q1-v2",
        "mountPath: '/var/lib/ets'",
        "minReplicas: 1",
        "maxReplicas: 1",
        "4633458b-17de-408a-b874-0445c86b69e6",
        "Microsoft.KeyVault/vaults/secrets@2025-05-01",
        "#445 replaces SQLite-on-network-files before production",
    ]
    for term in required:
        assert term in text

    marker = "resource gateway 'Microsoft.App/containerApps@2026-01-01'"
    container_section = text.split(marker, 1)[1]
    assert "accountKey:" not in container_section
    assert "storageAccount.listKeys()" not in container_section


def test_gateway_bicep_separates_runtime_and_acr_pull_identities() -> None:
    text = _template()

    required = [
        "gatewayIdentity",
        "registryPullIdentity",
        "identity: gatewayIdentity.id",
        "lifecycle: 'Main'",
        "identity: registryPullIdentity.id",
        "lifecycle: 'None'",
        "identity: registryPullIdentity.id",
        "gatewayManagedIdentityClientId",
    ]
    for term in required:
        assert term in text


def test_gateway_bicep_pins_production_auth_and_server_scope_configuration() -> None:
    text = _template()

    required = [
        "ETS_AUTH_MODE",
        "value: 'production_jwks'",
        "ETS_AUTH_JWKS_URL",
        "ETS_AUTH_ISSUER",
        "ETS_AUTH_AUDIENCE",
        "ETS_AUTH_TENANT_ID",
        "ETS_AUTH_APP_SCOPE_MAP_JSON",
        "ETS_GATEWAY_TENANT_ID",
        "ETS_GATEWAY_WORKSPACE_ID",
        "ETS_GATEWAY_MICROSOFT_TENANT_ID",
        "ETS_GATEWAY_SHAREPOINT_DRIVE_ID",
    ]
    for term in required:
        assert term in text


def test_gateway_bicep_outputs_no_secret_material() -> None:
    text = _template()
    outputs = [line.strip() for line in text.splitlines() if line.startswith("output ")]

    assert outputs
    joined = "\n".join(outputs).lower()
    for prohibited in ("secret", "password", "token", "accountkey", "jwks", "issuer"):
        assert prohibited not in joined
