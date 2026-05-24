from __future__ import annotations

from datetime import UTC, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ets.core import EvidenceEvent, SignedTreeHead, canonical_sha256
from ets.core.redaction import REDACTION_MARKER, apply_redaction_profile
from ets.core.signing import Ed25519TreeHeadSigner, NoOpTreeHeadSigner, verify_tree_head_signature


def make_event() -> EvidenceEvent:
    return EvidenceEvent(
        event_id="evt_001",
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id="evidence_001",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="f" * 64,
        content_hash_alg="sha256",
        metadata={
            "email": "person@example.test",
            "nested": {"token": "secret-token", "case": "alpha"},
        },
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        redaction_profile="basic_pii",
    )


def test_basic_pii_redaction_is_deterministic_and_hashable() -> None:
    event = make_event()
    redacted = apply_redaction_profile(event)

    assert redacted.metadata["email"] == REDACTION_MARKER
    assert redacted.metadata["nested"]["token"] == REDACTION_MARKER
    assert redacted.metadata["nested"]["case"] == "alpha"
    assert canonical_sha256(redacted.hashable_payload()) == canonical_sha256(
        apply_redaction_profile(event).hashable_payload()
    )
    assert canonical_sha256(redacted.hashable_payload()) != canonical_sha256(
        event.hashable_payload()
    )


def test_noop_signer_marks_tree_head_unsigned() -> None:
    tree_head = SignedTreeHead(
        tree_size=0,
        root_hash="0" * 64,
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        log_id="ets-local-dev",
        signature_alg="placeholder",
        signature="placeholder",
        public_key_id="placeholder",
    )

    signed = NoOpTreeHeadSigner().sign(tree_head)

    assert signed.signature_alg is None
    assert signed.signature is None
    assert signed.public_key_id is None


def test_ed25519_signer_signs_verifiable_tree_head() -> None:
    private_key = Ed25519PrivateKey.generate()
    private_key_hex = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    tree_head = SignedTreeHead(
        tree_size=0,
        root_hash="0" * 64,
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        log_id="ets-local-dev",
    )

    signed = Ed25519TreeHeadSigner(private_key_hex, "test-key").sign(tree_head)

    assert signed.signature_alg == "ed25519"
    assert signed.public_key_id == "test-key"
    assert verify_tree_head_signature(signed, public_key_hex)
