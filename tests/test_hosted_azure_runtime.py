from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from ets.api.app import _create_azure_key_vault_signer, create_app_from_env


def test_create_app_from_env_composes_azure_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Mock()
    store.list_entries.return_value = []
    signer = Mock()
    monkeypatch.setenv("ETS_STORAGE_PROVIDER", "azure_table")
    monkeypatch.setenv("ETS_AZURE_TABLE_ENDPOINT", "https://example.table.core.windows.net")
    monkeypatch.setenv("ETS_AZURE_TABLE_NAME", "ETSEvents")
    monkeypatch.setenv("ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID", "identity-client-id")
    monkeypatch.setenv("ETS_LOG_ID", "hosted-log")
    monkeypatch.setenv("ETS_SIGNING_MODE", "azure_key_vault")
    monkeypatch.setenv("ETS_AZURE_KEY_VAULT_URL", "https://ets.vault.azure.net/")
    monkeypatch.setenv("ETS_AZURE_KEY_NAME", "ets-tree-head")

    with (
        patch("ets.api.app.create_azure_table_event_store", return_value=store) as store_factory,
        patch("ets.api.app._create_azure_key_vault_signer", return_value=signer) as signer_factory,
    ):
        app = create_app_from_env()

    store_factory.assert_called_once_with(
        endpoint="https://example.table.core.windows.net",
        table_name="ETSEvents",
        log_id="hosted-log",
        managed_identity_client_id="identity-client-id",
    )
    signer_factory.assert_called_once_with(
        vault_url="https://ets.vault.azure.net/",
        key_name="ets-tree-head",
        managed_identity_client_id="identity-client-id",
    )
    assert app.state.event_log is store
    assert app.state.signing_mode == "azure_key_vault"


def test_create_azure_key_vault_signer_pins_resolved_key_version() -> None:
    credential = object()
    credential_factory = Mock(return_value=credential)
    key_client = Mock()
    key_client.get_key.return_value = SimpleNamespace(
        id="https://ets.vault.azure.net/keys/ets-tree-head/version-1"
    )
    key_client_factory = Mock(return_value=key_client)
    crypto_client = Mock()
    crypto_client_factory = Mock(return_value=crypto_client)
    identity_module = SimpleNamespace(ManagedIdentityCredential=credential_factory)
    key_module = SimpleNamespace(KeyClient=key_client_factory)
    crypto_module = SimpleNamespace(
        CryptographyClient=crypto_client_factory,
        SignatureAlgorithm=SimpleNamespace(ps256="ps256"),
    )

    with patch(
        "ets.api.app.importlib.import_module",
        side_effect=[identity_module, key_module, crypto_module],
    ):
        signer = _create_azure_key_vault_signer(
            vault_url="https://ets.vault.azure.net/",
            key_name="ets-tree-head",
            managed_identity_client_id="identity-client-id",
        )

    credential_factory.assert_called_once_with(client_id="identity-client-id")
    key_client_factory.assert_called_once_with(
        vault_url="https://ets.vault.azure.net/",
        credential=credential,
    )
    key_client.get_key.assert_called_once_with("ets-tree-head")
    crypto_client_factory.assert_called_once_with(
        "https://ets.vault.azure.net/keys/ets-tree-head/version-1",
        credential,
    )
    assert signer.public_key_id == "https://ets.vault.azure.net/keys/ets-tree-head/version-1"
