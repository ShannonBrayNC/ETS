"""Tree head signing abstractions."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Protocol
from urllib.parse import urlparse

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

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
    """Ed25519 signer for production-configured local tree heads."""

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
    """RSA-PSS/SHA-256 signer for Azure Key Vault or Managed HSM adapters.

    Azure Key Vault signs digests rather than arbitrary raw payloads. ETS therefore
    hashes the canonical tree-head signing payload with SHA-256 and delegates only
    that digest to the external signing adapter. Private key material never enters
    ETS process memory.
    """

    signature_alg = "ps256"

    def __init__(
        self,
        *,
        vault_url: str,
        key_name: str,
        key_version: str,
        sign_digest: Callable[[bytes], bytes],
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
        self._sign_digest = sign_digest

    @property
    def public_key_id(self) -> str:
        return f"{self._vault_url}/keys/{self._key_name}/{self._key_version}"

    def sign(self, tree_head: SignedTreeHead) -> SignedTreeHead:
        payload = tree_head_signature_payload(tree_head)
        digest = hashlib.sha256(payload).digest()
        signature = self._sign_digest(digest).hex()
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
    """Verify a supported tree-head signature using caller-supplied public key bytes.

    Ed25519 keys are the existing 32-byte raw public key encoded as hex. PS256 keys
    are DER SubjectPublicKeyInfo bytes encoded as hex.
    """

    if tree_head.signature is None:
        return False
    if tree_head.signature_alg == Ed25519TreeHeadSigner.signature_alg:
        return _verify_ed25519_tree_head_signature(tree_head, public_key_hex)
    if tree_head.signature_alg == AzureKeyVaultTreeHeadSigner.signature_alg:
        return _verify_ps256_tree_head_signature(tree_head, public_key_hex)
    return False


def _verify_ed25519_tree_head_signature(tree_head: SignedTreeHead, public_key_hex: str) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(
            bytes.fromhex(tree_head.signature or ""),
            tree_head_signature_payload(tree_head),
        )
    except (InvalidSignature, ValueError):
        return False
    return True


def _verify_ps256_tree_head_signature(tree_head: SignedTreeHead, public_key_hex: str) -> bool:
    try:
        public_key = serialization.load_der_public_key(bytes.fromhex(public_key_hex))
        if not isinstance(public_key, rsa.RSAPublicKey):
            return False
        digest = hashlib.sha256(tree_head_signature_payload(tree_head)).digest()
        public_key.verify(
            bytes.fromhex(tree_head.signature or ""),
            digest,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=hashes.SHA256().digest_size,
            ),
            Prehashed(hashes.SHA256()),
        )
    except (InvalidSignature, TypeError, ValueError):
        return False
    return True
