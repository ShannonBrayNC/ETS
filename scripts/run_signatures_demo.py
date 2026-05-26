from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ets.core.signing import Ed25519TreeHeadSigner, verify_tree_head_signature  # noqa: E402
from ets.core.tree_head import SignedTreeHead  # noqa: E402


def make_demo_keypair() -> tuple[str, str]:
    private_key = Ed25519PrivateKey.from_private_bytes(bytes([7]) * 32)
    private_key_hex = private_key.private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    ).hex()
    public_key_hex = private_key.public_key().public_bytes(
        Encoding.Raw,
        PublicFormat.Raw,
    ).hex()
    return private_key_hex, public_key_hex


def make_demo_tree_head() -> SignedTreeHead:
    return SignedTreeHead(
        tree_size=2,
        root_hash="a" * 64,
        created_at_utc=datetime(2026, 5, 26, 15, 0, tzinfo=UTC),
        log_id="ets-signature-demo",
    )


def run_demo() -> dict[str, object]:
    private_key_hex, public_key_hex = make_demo_keypair()
    signer = Ed25519TreeHeadSigner(private_key_hex, "demo-key")
    signed = signer.sign(make_demo_tree_head())
    tampered = signed.model_copy(update={"root_hash": "b" * 64})
    wrong_private_key = Ed25519PrivateKey.from_private_bytes(bytes([8]) * 32)
    wrong_public_key_hex = wrong_private_key.public_key().public_bytes(
        Encoding.Raw,
        PublicFormat.Raw,
    ).hex()

    return {
        "demo": "signatures",
        "tree_head": signed.model_dump(mode="json"),
        "valid_signature": verify_tree_head_signature(signed, public_key_hex),
        "tampered_signature": verify_tree_head_signature(tampered, public_key_hex),
        "wrong_signer": verify_tree_head_signature(signed, wrong_public_key_hex),
    }


def main() -> int:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
