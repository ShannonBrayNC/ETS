from __future__ import annotations

from datetime import UTC, datetime

from ets.core.signing import (
    Ed25519TreeHeadSigner,
    NoOpTreeHeadSigner,
    tree_head_signature_payload,
    verify_tree_head_signature,
)
from ets.core.tree_head import SignedTreeHead


def _tree_head() -> SignedTreeHead:
    return SignedTreeHead(
        tree_size=3,
        root_hash="c" * 64,
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        log_id="ets-local-dev",
    )


def test_noop_tree_head_signer_clears_signing_fields() -> None:
    signed = SignedTreeHead(
        tree_size=1,
        root_hash="a" * 64,
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        log_id="ets-local-dev",
        signature_alg="ed25519",
        signature="b" * 128,
        public_key_id="fixture-key",
    )

    unsigned = NoOpTreeHeadSigner().sign(signed)

    assert unsigned.signature_alg is None
    assert unsigned.signature is None
    assert unsigned.public_key_id is None


def test_tree_head_signature_payload_omits_signing_fields() -> None:
    tree_head = _tree_head().model_copy(
        update={
            "signature_alg": "ed25519",
            "signature": "b" * 128,
            "public_key_id": "fixture-key",
        }
    )

    payload = tree_head_signature_payload(tree_head).decode("utf-8")

    assert '"signature":null' in payload
    assert '"signature_alg":null' in payload
    assert '"public_key_id":null' in payload
    assert "fixture-key" not in payload


def test_signature_verifier_rejects_unsigned_tree_head() -> None:
    assert verify_tree_head_signature(_tree_head(), "0" * 64) is False


def test_signature_verifier_rejects_malformed_signature() -> None:
    tree_head = _tree_head().model_copy(
        update={
            "signature_alg": "ed25519",
            "signature": "not-hex",
            "public_key_id": "fixture-key",
        }
    )

    assert verify_tree_head_signature(tree_head, "0" * 64) is False


def test_ed25519_tree_head_signer_round_trips_fixture_key() -> None:
    signer = Ed25519TreeHeadSigner("07" * 32, "fixture-key")
    signed = signer.sign(_tree_head())

    assert signed.signature_alg == "ed25519"
    assert signed.public_key_id == "fixture-key"
    assert signed.signature is not None
    assert verify_tree_head_signature(
        signed,
        "ea4a6c63e29c520abef5507b132ec5f9954776aebebe7b92421eea691446d22c",
    )


def test_azure_key_vault_tree_head_signer_uses_external_signing_adapter() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from ets.core.signing import AzureKeyVaultTreeHeadSigner

    private_key = Ed25519PrivateKey.generate()
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    signer = AzureKeyVaultTreeHeadSigner(
        vault_url="https://ets-vault.vault.azure.net/",
        key_name="ets-tree-head",
        key_version="version-001",
        sign_payload=private_key.sign,
    )

    signed = signer.sign(_tree_head())

    assert signed.signature_alg == "ed25519"
    assert signed.public_key_id == "https://ets-vault.vault.azure.net/keys/ets-tree-head/version-001"
    assert signed.signature is not None
    assert verify_tree_head_signature(signed, public_key_hex)


def test_azure_key_vault_tree_head_signer_rejects_non_https_vault_url() -> None:
    import pytest

    from ets.core.signing import AzureKeyVaultTreeHeadSigner

    with pytest.raises(RuntimeError, match="HTTPS"):
        AzureKeyVaultTreeHeadSigner(
            vault_url="http://ets-vault.example",
            key_name="ets-tree-head",
            key_version="version-001",
            sign_payload=lambda payload: payload,
        )
