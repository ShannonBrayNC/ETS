from __future__ import annotations

from pathlib import Path

BICEP = Path("infra/azure/ets-edge-virtual-demo-origin.bicep")
NGINX = Path("edge-demo/nginx.azure.conf")
DOCKERFILE = Path("edge-demo/Dockerfile.ui.azure")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_edge_virtual_origin_disables_environment_public_network_access() -> None:
    text = _text(BICEP)

    assert "publicNetworkAccess: 'Disabled'" in text
    assert "internal: true" in text
    assert "serviceName: 'Microsoft.App/environments'" in text


def test_edge_virtual_origin_has_no_application_runtime_identity() -> None:
    text = _text(BICEP)

    assert "registryPullIdentity" in text
    assert "lifecycle: 'None'" in text
    assert "runtimeIdentityCount int = 0" in text
    assert "ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID" not in text
    assert "ETS_AZURE_KEY_VAULT_URL" not in text


def test_edge_virtual_origin_is_synthetic_and_non_attested() -> None:
    text = _text(BICEP)

    assert "tenant_edge_demo" in text
    assert "workspace_edge_demo" in text
    assert "ets-edge-virtual-azure-demo" in text
    assert "ETS_EDGE_UI_ALLOWED_ORIGIN" in text
    assert "ETS_EDGE_SYSLOG_ENABLED" in text
    assert "value: '0'" in text


def test_hosted_ui_exposes_only_bff_and_static_surface() -> None:
    text = _text(NGINX)

    assert "location ^~ /edge/ui/v1/" in text
    assert "location = /afd-healthz" in text
    assert "proxy_pass http://127.0.0.1:8001$request_uri" in text
    assert "return 404;" in text
    assert "openapi\\.json" in text
    assert "edge/v1" in text
    assert "proxy_pass http://127.0.0.1:8000" not in text
    assert "proxy_pass http://127.0.0.1:8002" not in text


def test_hosted_ui_runs_unprivileged_and_has_no_external_asset_dependency() -> None:
    dockerfile = _text(DOCKERFILE)
    nginx = _text(NGINX)

    assert "USER nginx" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert "nginx.azure-main.conf" in dockerfile
    assert "script-src 'self'" in nginx
    assert "connect-src 'self'" in nginx
    assert "https://" not in nginx


def test_hosted_origin_uses_ephemeral_synthetic_storage_only() -> None:
    text = _text(BICEP)

    assert text.count("storageType: 'EmptyDir'") == 2
    assert "Microsoft.Storage/storageAccounts" not in text
    assert "AzureFile" not in text
    assert "azureFile" not in text
