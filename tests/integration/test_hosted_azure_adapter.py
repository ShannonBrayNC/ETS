from __future__ import annotations

from dataclasses import dataclass

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
    with pytest.raises(RuntimeError, match="ETS_AZURE_KEY_VERSION"):
        AzureManagedIdentitySignerAdapter.from_env(
            {
                "ETS_AZURE_MANAGED_IDENTITY_ENABLED": "true",
                "ETS_AZURE_KEY_VAULT_URL": "https://ets-hosted.vault.azure.net/",
                "ETS_AZURE_KEY_NAME": "ets-tree-head",
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
