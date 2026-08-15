from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ets.api.azure_signing import AzureManagedIdentitySignerAdapter
from ets.core.signing import verify_tree_head_signature
from tests.unit.test_tree_head_signing_envelope import _tree_head


@dataclass(frozen=True)
class FakeSignResult:
    signature: bytes


class FakeCryptoClient:
    def __init__(self, private_key: Ed25519PrivateKey, observed_key_ids: list[str]) -> None:
        self._private_key = private_key
        self._observed_key_ids = observed_key_ids

    def sign(self, algorithm: str, digest: bytes) -> FakeSignResult:
        assert algorithm == "EdDSA"
        return FakeSignResult(signature=self._private_key.sign(digest))


def test_azure_managed_identity_signer_adapter_builds_tree_head_signer_from_env() -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    observed_key_ids: list[str] = []

    def crypto_client_factory(key_id: str) -> FakeCryptoClient:
        observed_key_ids.append(key_id)
        return FakeCryptoClient(private_key, observed_key_ids)

    adapter = AzureManagedIdentitySignerAdapter.from_env(
        {
            "ETS_AZURE_MANAGED_IDENTITY_ENABLED": "true",
            "ETS_AZURE_KEY_VAULT_URL": "https://ets-hosted.vault.azure.net/",
            "ETS_AZURE_KEY_NAME": "ets-tree-head",
            "ETS_AZURE_KEY_VERSION": "version-002",
        },
        crypto_client_factory=crypto_client_factory,
    )

    signer = adapter.as_tree_head_signer()
    signed = signer.sign(_tree_head())

    assert observed_key_ids == ["https://ets-hosted.vault.azure.net/keys/ets-tree-head/version-002"]
    assert signed.public_key_id == observed_key_ids[0]
    assert verify_tree_head_signature(signed, public_key_hex)


def test_azure_managed_identity_signer_adapter_resolves_latest_version_when_omitted() -> None:
    observed_key_ids: list[str] = []

    class ReadyCryptoClient:
        def sign(self, algorithm: str, digest: bytes) -> FakeSignResult:
            return FakeSignResult(signature=b"signature")

    def crypto_client_factory(key_id: str) -> ReadyCryptoClient:
        observed_key_ids.append(key_id)
        return ReadyCryptoClient()

    adapter = AzureManagedIdentitySignerAdapter.from_env(
        {
            "ETS_AZURE_KEY_VAULT_URL": "https://ets-hosted.vault.azure.net/",
            "ETS_AZURE_KEY_NAME": "ets-tree-head",
        },
        crypto_client_factory=crypto_client_factory,
        key_version_resolver=lambda vault_url, key_name: "resolved-version-003",
    )

    assert adapter.key_id.endswith("/resolved-version-003")
    adapter.check_ready()
    assert observed_key_ids == [adapter.key_id]


def test_azure_managed_identity_signer_adapter_requires_managed_identity() -> None:
    with pytest.raises(RuntimeError, match="managed identity"):
        AzureManagedIdentitySignerAdapter.from_env(
            {
                "ETS_AZURE_MANAGED_IDENTITY_ENABLED": "false",
                "ETS_AZURE_KEY_VAULT_URL": "https://ets-hosted.vault.azure.net/",
                "ETS_AZURE_KEY_NAME": "ets-tree-head",
                "ETS_AZURE_KEY_VERSION": "version-002",
            },
            crypto_client_factory=lambda key_id: None,  # type: ignore[arg-type]
        )


def test_azure_managed_identity_signer_adapter_requires_signer_configuration() -> None:
    with pytest.raises(RuntimeError, match="ETS_AZURE_KEY_NAME"):
        AzureManagedIdentitySignerAdapter.from_env(
            {
                "ETS_AZURE_KEY_VAULT_URL": "https://ets-hosted.vault.azure.net/",
                "ETS_AZURE_KEY_VERSION": "version-002",
            },
            crypto_client_factory=lambda key_id: None,  # type: ignore[arg-type]
        )


def test_azure_managed_identity_signer_adapter_rejects_invalid_signature_result() -> None:
    class EmptyCryptoClient:
        def sign(self, algorithm: str, digest: bytes) -> dict[str, bytes]:
            return {"signature": b""}

    adapter = AzureManagedIdentitySignerAdapter.from_env(
        {
            "ETS_AZURE_MANAGED_IDENTITY_ENABLED": "true",
            "ETS_AZURE_KEY_VAULT_URL": "https://ets-hosted.vault.azure.net/",
            "ETS_AZURE_KEY_NAME": "ets-tree-head",
            "ETS_AZURE_KEY_VERSION": "version-002",
        },
        crypto_client_factory=lambda key_id: EmptyCryptoClient(),
    )

    with pytest.raises(RuntimeError, match="invalid signature"):
        adapter.as_tree_head_signer().sign(_tree_head())


def test_runtime_azure_sdk_factory_uses_managed_identity(monkeypatch) -> None:
    from ets.api import azure_signing

    observed_credentials: list[object] = []

    class FakeManagedIdentityCredential:
        def __init__(self, *, client_id: str | None = None) -> None:
            self.client_id = client_id

    class FakeCryptographyClient:
        def __init__(self, key_id: str, *, credential: object) -> None:
            self.key_id = key_id
            self.credential = credential
            observed_credentials.append(credential)

        def sign(self, algorithm: str, digest: bytes) -> FakeSignResult:
            return FakeSignResult(signature=b"signed")

    def fake_import_module(name: str) -> object:
        if name == "azure.identity":
            return SimpleNamespace(ManagedIdentityCredential=FakeManagedIdentityCredential)
        if name == "azure.keyvault.keys.crypto":
            return SimpleNamespace(CryptographyClient=FakeCryptographyClient)
        raise AssertionError(name)

    monkeypatch.setattr(azure_signing.importlib, "import_module", fake_import_module)

    factory = azure_signing.create_managed_identity_crypto_client_factory(
        {"ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID": "client-id-from-ci-secret"}
    )
    client = factory("https://ets-hosted.vault.azure.net/keys/ets-tree-head/version-002")

    assert isinstance(client, FakeCryptographyClient)
    assert client.key_id.endswith("/version-002")
    assert observed_credentials[0].client_id == "client-id-from-ci-secret"


def test_runtime_key_version_resolver_uses_latest_version(monkeypatch) -> None:
    from ets.api import azure_signing

    class FakeManagedIdentityCredential:
        def __init__(self, *, client_id: str | None = None) -> None:
            self.client_id = client_id

    class FakeKeyClient:
        def __init__(self, *, vault_url: str, credential: object) -> None:
            self.vault_url = vault_url
            self.credential = credential

        def get_key(self, name: str, version: str | None = None) -> object:
            assert name == "ets-tree-head"
            assert version is None
            return SimpleNamespace(properties=SimpleNamespace(version="version-latest"))

    def fake_import_module(name: str) -> object:
        if name == "azure.identity":
            return SimpleNamespace(ManagedIdentityCredential=FakeManagedIdentityCredential)
        if name == "azure.keyvault.keys":
            return SimpleNamespace(KeyClient=FakeKeyClient)
        raise AssertionError(name)

    monkeypatch.setattr(azure_signing.importlib, "import_module", fake_import_module)
    resolver = azure_signing.create_managed_identity_key_version_resolver({})

    assert resolver("https://ets-hosted.vault.azure.net/", "ets-tree-head") == "version-latest"


def test_signing_rbac_validation_requires_least_privilege_roles() -> None:
    from ets.api.azure_signing import (
        required_signing_rbac_roles,
        validate_signing_rbac_roles,
    )

    assert required_signing_rbac_roles() == ("Key Vault Crypto User",)
    assert required_signing_rbac_roles(managed_hsm=True) == ("Managed HSM Crypto User",)
    validate_signing_rbac_roles(["Key Vault Crypto User"])
    validate_signing_rbac_roles(["Managed HSM Crypto User"], managed_hsm=True)

    with pytest.raises(RuntimeError, match="Key Vault Crypto User"):
        validate_signing_rbac_roles(["Reader"])
