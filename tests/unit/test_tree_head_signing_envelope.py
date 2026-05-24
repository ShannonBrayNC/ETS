from __future__ import annotations

from datetime import UTC, datetime

from ets.core.signing import (
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
