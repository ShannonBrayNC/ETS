"""SignalForge-owned Azure signing adapter contracts for hosted ETS."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, cast

from ets.core.signing import AzureKeyVaultTreeHeadSigner


class AzureCryptoClient(Protocol):
    """Minimal Azure Key Vault / Managed HSM crypto client surface."""

    def sign(self, algorithm: str, digest: bytes) -> Any:
        """Sign bytes with a key identified by the hosting adapter."""


class AzureKeyClient(Protocol):
    """Minimal Azure Key Vault key client surface used to resolve a concrete version."""

    def get_key(self, name: str, version: str | None = None) -> Any: ...


KEY_VAULT_SIGN_ROLE = "Key Vault Crypto User"
MANAGED_HSM_SIGN_ROLE = "Managed HSM Crypto User"


class AzureManagedIdentitySignerAdapter:
    """Adapter boundary for Managed Identity-backed Azure signing clients.

    The adapter owns no credentials and accepts client factories supplied by the
    deployment layer. This keeps ETS free of committed tenant IDs, client IDs,
    tokens, secrets, and private key material.
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
        crypto_client_factory: Callable[[str], AzureCryptoClient] | None = None,
        key_version_resolver: Callable[[str, str], str] | None = None,
    ) -> AzureManagedIdentitySignerAdapter:
        env = environ or os.environ
        managed_identity_enabled = env.get("ETS_AZURE_MANAGED_IDENTITY_ENABLED")
        if managed_identity_enabled is not None and managed_identity_enabled != "true":
            raise RuntimeError("Azure signer requires managed identity to be enabled")

        vault_url = _required_env(env, "ETS_AZURE_KEY_VAULT_URL")
        key_name = _required_env(env, "ETS_AZURE_KEY_NAME")
        key_version = (env.get("ETS_AZURE_KEY_VERSION") or "").strip()
        if not key_version:
            resolver = key_version_resolver or create_managed_identity_key_version_resolver(env)
            key_version = resolver(vault_url, key_name)
            if not key_version:
                raise RuntimeError("Azure signer could not resolve a concrete key version")

        resolved_factory = crypto_client_factory or create_managed_identity_crypto_client_factory(
            env
        )
        return cls(
            vault_url=vault_url,
            key_name=key_name,
            key_version=key_version,
            crypto_client_factory=resolved_factory,
        )

    def as_tree_head_signer(self) -> AzureKeyVaultTreeHeadSigner:
        return self._tree_head_signer

    def check_ready(self) -> None:
        """Fail closed unless a cryptography client can be constructed for the resolved key."""

        self._crypto_client_factory(self.key_id)

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
    return value.strip()


def _managed_identity_credential(environ: Mapping[str, str]) -> object:
    identity_module = importlib.import_module("azure.identity")
    managed_identity_credential = identity_module.ManagedIdentityCredential
    client_id = environ.get("ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID") or None
    return managed_identity_credential(client_id=client_id)


def create_managed_identity_key_version_resolver(
    environ: Mapping[str, str] | None = None,
) -> Callable[[str, str], str]:
    """Resolve the latest Key Vault key to a concrete version using Managed Identity."""

    env = environ or os.environ
    keys_module = importlib.import_module("azure.keyvault.keys")
    key_client_factory = keys_module.KeyClient
    credential = _managed_identity_credential(env)

    def resolve(vault_url: str, key_name: str) -> str:
        client = cast(
            AzureKeyClient,
            key_client_factory(vault_url=vault_url, credential=credential),
        )
        key = client.get_key(key_name)
        properties = getattr(key, "properties", None)
        version = getattr(properties, "version", None)
        if not isinstance(version, str) or not version:
            raise RuntimeError("Azure signer could not resolve a concrete key version")
        return version

    return resolve


def create_managed_identity_crypto_client_factory(
    environ: Mapping[str, str] | None = None,
) -> Callable[[str], AzureCryptoClient]:
    """Create an Azure SDK crypto client factory using Managed Identity.

    Azure SDK modules are loaded at runtime so local ETS development does not
    require Azure dependencies unless the hosted signer path is used.
    """

    env = environ or os.environ
    crypto_module = importlib.import_module("azure.keyvault.keys.crypto")
    cryptography_client = crypto_module.CryptographyClient
    credential = _managed_identity_credential(env)

    def create_client(key_id: str) -> AzureCryptoClient:
        return cast(AzureCryptoClient, cryptography_client(key_id, credential=credential))

    return create_client


def required_signing_rbac_roles(*, managed_hsm: bool = False) -> tuple[str, ...]:
    """Return least-privilege Azure roles required for hosted signing."""

    return (MANAGED_HSM_SIGN_ROLE if managed_hsm else KEY_VAULT_SIGN_ROLE,)


def validate_signing_rbac_roles(
    assigned_roles: Sequence[str],
    *,
    managed_hsm: bool = False,
) -> None:
    """Fail closed unless the managed identity has the signing role required."""

    missing = set(required_signing_rbac_roles(managed_hsm=managed_hsm)) - set(assigned_roles)
    if missing:
        raise RuntimeError(f"missing Azure signing RBAC roles: {', '.join(sorted(missing))}")
