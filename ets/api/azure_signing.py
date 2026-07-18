"""SignalForge-owned Azure signing adapter contracts for hosted ETS."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from ets.core.signing import AzureKeyVaultTreeHeadSigner


class AzureCryptoClient(Protocol):
    """Minimal Azure Key Vault / Managed HSM crypto client surface."""

    def sign(self, algorithm: str, digest: bytes) -> Any:
        """Sign bytes with a key identified by the hosting adapter."""


class AzureManagedIdentitySignerAdapter:
    """Adapter boundary for Managed Identity-backed Azure signing clients.

    The adapter owns no credentials and accepts a client factory supplied by the
    SignalForge deployment layer. This keeps ETS free of committed tenant IDs,
    client IDs, tokens, secrets, and private key material.
    """

    algorithm = "EdDSA"

    def __init__(
        self,
        *,
        vault_url: str,
        key_name: str,
        key_version: str,
        crypto_client_factory: Callable[[str], AzureCryptoClient],
    ) -> None:
        self._tree_head_signer = AzureKeyVaultTreeHeadSigner(
            vault_url=vault_url,
            key_name=key_name,
            key_version=key_version,
            sign_payload=self.sign,
        )
        self._crypto_client_factory = crypto_client_factory

    @property
    def key_id(self) -> str:
        return self._tree_head_signer.public_key_id

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        crypto_client_factory: Callable[[str], AzureCryptoClient],
    ) -> AzureManagedIdentitySignerAdapter:
        env = environ or os.environ
        if env.get("ETS_AZURE_MANAGED_IDENTITY_ENABLED") != "true":
            raise RuntimeError("Azure signer requires managed identity to be enabled")
        return cls(
            vault_url=_required_env(env, "ETS_AZURE_KEY_VAULT_URL"),
            key_name=_required_env(env, "ETS_AZURE_KEY_NAME"),
            key_version=_required_env(env, "ETS_AZURE_KEY_VERSION"),
            crypto_client_factory=crypto_client_factory,
        )

    def as_tree_head_signer(self) -> AzureKeyVaultTreeHeadSigner:
        return self._tree_head_signer

    def sign(self, payload: bytes) -> bytes:
        result = self._crypto_client_factory(self.key_id).sign(self.algorithm, payload)
        signature = getattr(result, "signature", None)
        if signature is None and isinstance(result, dict):
            signature = result.get("signature")
        if not isinstance(signature, bytes) or not signature:
            raise RuntimeError("Azure signer returned an invalid signature")
        return signature


def _required_env(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required for Azure signer configuration")
    return value
