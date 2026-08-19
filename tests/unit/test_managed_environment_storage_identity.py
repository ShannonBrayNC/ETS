from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOSTED = ROOT / "infra" / "azure" / "ets-hosted.bicep"
GATEWAY = ROOT / "infra" / "azure" / "ets-gateway.bicep"


def test_hosted_environment_owns_system_identity_for_environment_services() -> None:
    text = HOSTED.read_text(encoding="utf-8")

    marker = "resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01'"
    start = text.index(marker)
    block = text[start : start + 500]

    assert "identity: {\n    type: 'SystemAssigned'\n  }" in block


def test_gateway_environment_storage_uses_environment_system_identity() -> None:
    text = GATEWAY.read_text(encoding="utf-8")

    assert "principalId: managedEnvironment.identity.principalId" in text
    assert "identity: 'System'" in text
    assert "name: guid(stateKeyVault.id, managedEnvironment.id, keyVaultSecretsUserRoleId)" in text

    account_key_vault = text.index("accountKeyVaultProperties")
    storage_block = text[account_key_vault : account_key_vault + 300]
    assert "gatewayIdentity.id" not in storage_block
