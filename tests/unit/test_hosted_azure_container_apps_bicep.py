from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BICEP = ROOT / "infra" / "azure" / "ets-hosted.bicep"


def _template() -> str:
    return BICEP.read_text(encoding="utf-8")


def test_hosted_bicep_deploys_internal_container_app_and_probes() -> None:
    text = _template()

    required = [
        "Microsoft.App/managedEnvironments@2026-01-01",
        "Microsoft.App/containerApps@2025-01-01",
        "type: 'UserAssigned'",
        "external: false",
        "allowInsecure: false",
        "activeRevisionsMode: 'Single'",
        "path: '/version'",
        "path: '/health'",
        "path: '/ready'",
        "type: 'Startup'",
        "type: 'Liveness'",
        "type: 'Readiness'",
        "minReplicas: 1",
        "maxReplicas: 1",
    ]
    for term in required:
        assert term in text


def test_hosted_bicep_uses_oauth_only_table_storage_and_table_scoped_rbac() -> None:
    text = _template()

    required = [
        "Microsoft.Storage/storageAccounts@2025-06-01",
        "Microsoft.Storage/storageAccounts/tableServices/tables@2025-06-01",
        "allowSharedKeyAccess: false",
        "defaultToOAuthAuthentication: true",
        "supportsHttpsTrafficOnly: true",
        "0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3",
        "scope: evidenceTable",
        "ETS_STORAGE_PROVIDER",
        "value: 'azure_table'",
        "ETS_AZURE_TABLE_ENDPOINT",
        "ETS_AZURE_TABLE_NAME",
    ]
    for term in required:
        assert term in text

    assert "listKeys(" not in text
    assert "sharedKey" not in text


def test_hosted_bicep_uses_non_exportable_rsa_signing_key_and_crypto_rbac() -> None:
    text = _template()

    required = [
        "Microsoft.KeyVault/vaults/keys@2025-05-01",
        "exportable: false",
        "'sign'",
        "'verify'",
        "kty: 'RSA'",
        "12338af0-0e69-4776-bea7-57ae8d297424",
        "scope: keyVault",
        "ETS_SIGNING_MODE",
        "value: 'azure_key_vault'",
        "ETS_AZURE_KEY_VAULT_URL",
        "ETS_AZURE_KEY_NAME",
        "ETS_AZURE_KEY_VERSION is intentionally omitted",
    ]
    for term in required:
        assert term in text

    assert "ETS_SIGNING_PRIVATE_KEY_HEX" not in text


def test_hosted_bicep_requires_production_jwks_and_managed_identity() -> None:
    text = _template()

    required = [
        "ETS_AUTH_MODE",
        "value: 'production_jwks'",
        "ETS_AUTH_JWKS_URL",
        "ETS_AUTH_ISSUER",
        "ETS_AUTH_AUDIENCE",
        "ETS_AZURE_MANAGED_IDENTITY_ENABLED",
        "ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID",
        "managedIdentity.properties.clientId",
    ]
    for term in required:
        assert term in text


def test_hosted_bicep_outputs_only_non_secret_infrastructure_references() -> None:
    text = _template()
    output_lines = [line.strip() for line in text.splitlines() if line.startswith("output ")]

    assert output_lines
    joined = "\n".join(output_lines).lower()
    for prohibited in (
        "token",
        "secret",
        "password",
        "private",
        "issuer",
        "audience",
        "jwks",
    ):
        assert prohibited not in joined
