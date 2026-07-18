"""Tree head signing abstractions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from urllib.parse import urlparse

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from ets.core.canonical_json import canonicalize
from ets.core.tree_head import SignedTreeHead


class TreeHeadSigner(Protocol):
    def sign(self, tree_head: SignedTreeHead) -> SignedTreeHead:
        """Return a tree head with signing fields populated or explicitly empty."""


class NoOpTreeHeadSigner:
    """Local unsigned signer used when production signing is not configured."""

    def sign(self, tree_head: SignedTreeHead) -> SignedTreeHead:
        return tree_head.model_copy(
            update={"signature_alg": None, "signature": None, "public_key_id": None}
        )


class Ed25519TreeHeadSigner:
    """Ed25519 signer for production-configured tree heads."""

    signature_alg = "ed25519"

    def __init__(self, private_key_hex: str, public_key_id: str) -> None:
        if not public_key_id:
            raise RuntimeError("public_key_id is required for Ed25519 signing")
        self._private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
        self._public_key_id = public_key_id

    def sign(self, tree_head: SignedTreeHead) -> SignedTreeHead:
        payload = tree_head_signature_payload(tree_head)
        signature = self._private_key.sign(payload).hex()
        return tree_head.model_copy(
            update={
                "signature_alg": self.signature_alg,
                "signature": signature,
                "public_key_id": self._public_key_id,
            }
        )



class AzureKeyVaultTreeHeadSigner:
    """Tree-head signer abstraction for Azure Key Vault or Managed HSM adapters.

    The adapter is injected so the ETS core never stores Azure credentials, client
    IDs, tenant IDs, access tokens, or private key material. Production deployments
    should supply an adapter that signs the canonical payload through Managed
    Identity.
    """

    signature_alg = Ed25519TreeHeadSigner.signature_alg

    def __init__(
        self,
        *,
        vault_url: str,
        key_name: str,
        key_version: str,
        sign_payload: Callable[[bytes], bytes],
    ) -> None:
        parsed = urlparse(vault_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise RuntimeError("Azure signer vault_url must be an HTTPS URL")
        if not key_name:
            raise RuntimeError("Azure signer key_name is required")
        if not key_version:
            raise RuntimeError("Azure signer key_version is required")
        self._vault_url = vault_url.rstrip("/")
        self._key_name = key_name
        self._key_version = key_version
        self._sign_payload = sign_payload

    @property
    def public_key_id(self) -> str:
        return f"{self._vault_url}/keys/{self._key_name}/{self._key_version}"

    def sign(self, tree_head: SignedTreeHead) -> SignedTreeHead:
        payload = tree_head_signature_payload(tree_head)
        signature = self._sign_payload(payload).hex()
        if not signature:
            raise RuntimeError("Azure signer returned an empty signature")
        return tree_head.model_copy(
            update={
                "signature_alg": self.signature_alg,
                "signature": signature,
                "public_key_id": self.public_key_id,
            }
        )

def tree_head_signature_payload(tree_head: SignedTreeHead) -> bytes:
    """Return canonical bytes signed by tree-head signers."""

    payload = tree_head.model_dump(mode="json")
    payload["signature_alg"] = None
    payload["signature"] = None
    payload["public_key_id"] = None
    return canonicalize(payload)


def verify_tree_head_signature(tree_head: SignedTreeHead, public_key_hex: str) -> bool:
    if (
        tree_head.signature_alg != Ed25519TreeHeadSigner.signature_alg
        or tree_head.signature is None
    ):
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(
            bytes.fromhex(tree_head.signature),
            tree_head_signature_payload(tree_head),
        )
    except (InvalidSignature, ValueError):
        return False
    return True
