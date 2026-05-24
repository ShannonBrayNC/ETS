"""Tree head signing abstractions."""

from __future__ import annotations

from typing import Protocol

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
