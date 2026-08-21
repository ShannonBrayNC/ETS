from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ets.core import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    generate_consistency_proof,
    generate_inclusion_proof,
)
from ets.core.log import LogEntry
from ets.core.merkle import EMPTY_TREE_ROOT, merkle_root
from ets.core.proofs import verify_inclusion_proof
from ets.core.signing import Ed25519TreeHeadSigner
from ets.verifier.service import (
    TreeHeadTrustStore,
    TrustedTreeHeadKey,
    VerifierPolicy,
    verify_offline_bundle,
    verify_online_event,
)

LOG_ID = "ets-verifier-test"
KEY_ID = "ets-test-key-v1"
PRIVATE_KEY_HEX = "11" * 32
CHECKPOINT_TIME = datetime(2026, 8, 21, 5, 0, tzinfo=UTC)
LATEST_TIME = CHECKPOINT_TIME + timedelta(minutes=1)
VERIFY_TIME = LATEST_TIME + timedelta(minutes=1)

_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(PRIVATE_KEY_HEX))
PUBLIC_KEY_HEX = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
).hex()
SIGNER = Ed25519TreeHeadSigner(PRIVATE_KEY_HEX, KEY_ID)


def make_event(event_id: str) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="a" * 64,
        content_hash_alg="sha256",
        metadata={"source": "verifier-test"},
        created_at_utc=CHECKPOINT_TIME,
    )


def make_entries(count: int) -> list[LogEntry]:
    log = InMemoryAppendOnlyLog()
    for index in range(count):
        log.append(make_event(f"evt_{index + 1}"))
    return log.list_entries()


def make_signed_head(entries: list[LogEntry], created_at_utc: datetime) -> SignedTreeHead:
    unsigned = SignedTreeHead(
        tree_size=len(entries),
        root_hash=merkle_root([entry.leaf_hash for entry in entries]),
        created_at_utc=created_at_utc,
        log_id=LOG_ID,
    )
    return SIGNER.sign(unsigned)


def make_bundle(entries: list[LogEntry], index: int = 0) -> EvidenceProofBundle:
    entry = entries[index]
    proof = generate_inclusion_proof(entries, index, generated_at_utc=CHECKPOINT_TIME)
    return EvidenceProofBundle(
        event=entry.event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=make_signed_head(entries, CHECKPOINT_TIME),
        inclusion_proof=proof,
        verification_result=verify_inclusion_proof(proof),
    )


def make_trust_store(*, revoked_at_utc: datetime | None = None) -> TreeHeadTrustStore:
    return TreeHeadTrustStore(
        keys=[
            TrustedTreeHeadKey(
                key_id=KEY_ID,
                signature_alg="ed25519",
                public_key_hex=PUBLIC_KEY_HEX,
                not_before_utc=CHECKPOINT_TIME - timedelta(days=1),
                not_after_utc=CHECKPOINT_TIME + timedelta(days=1),
                revoked_at_utc=revoked_at_utc,
            )
        ]
    )


def make_policy(*, require_signature: bool = True) -> VerifierPolicy:
    return VerifierPolicy(
        require_tree_head_signature=require_signature,
        expected_log_id=LOG_ID,
    )


class FakeTransport:
    def __init__(
        self,
        *,
        bundle: EvidenceProofBundle,
        latest_head: SignedTreeHead,
        consistency: Mapping[str, Any] | None = None,
    ) -> None:
        self.bundle = bundle
        self.latest_head = latest_head
        self.consistency = consistency
        self.calls: list[str] = []

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> Mapping[str, Any]:
        self.calls.append(url)
        _ = headers, timeout_seconds, max_response_bytes
        path = urlsplit(url).path
        if "/api/v1/bundles/" in path:
            return self.bundle.model_dump(mode="json")
        if path.endswith("/api/v1/log/head"):
            return self.latest_head.model_dump(mode="json")
        if path.endswith("/api/v1/proofs/consistency") and self.consistency is not None:
            return self.consistency
        raise AssertionError(f"unexpected verifier URL: {url}")


def test_offline_verifier_accepts_signed_bundle_at_checkpoint():
    bundle = make_bundle(make_entries(1))

    result = verify_offline_bundle(
        bundle,
        trust_store=make_trust_store(),
        policy=make_policy(),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is True
    assert result.signature_verified is True
    assert result.continuity_verified is False
    assert result.standing_status == "checkpoint_only"
    assert all(check.passed for check in result.checks)


def test_offline_verifier_rejects_bundle_leaf_not_bound_to_event():
    bundle = make_bundle(make_entries(1)).model_copy(update={"leaf_hash": "0" * 64})

    result = verify_offline_bundle(
        bundle,
        trust_store=make_trust_store(),
        policy=make_policy(),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is False
    assert any(check.code == "leaf_binding" and not check.passed for check in result.checks)


def test_offline_verifier_rejects_untrusted_signing_key():
    bundle = make_bundle(make_entries(1))

    result = verify_offline_bundle(
        bundle,
        trust_store=TreeHeadTrustStore(),
        policy=make_policy(),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is False
    assert result.signature_verified is False
    assert "trust store" in result.reason


def test_offline_verifier_rejects_signature_at_or_after_revocation():
    bundle = make_bundle(make_entries(1))

    result = verify_offline_bundle(
        bundle,
        trust_store=make_trust_store(revoked_at_utc=CHECKPOINT_TIME),
        policy=make_policy(),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is False
    assert "revocation" in result.reason


def test_offline_verifier_can_explicitly_allow_unsigned_development_checkpoint():
    bundle = make_bundle(make_entries(1))
    unsigned_head = bundle.tree_head.model_copy(
        update={"signature_alg": None, "signature": None, "public_key_id": None}
    )
    unsigned_bundle = bundle.model_copy(update={"tree_head": unsigned_head})

    result = verify_offline_bundle(
        unsigned_bundle,
        trust_store=TreeHeadTrustStore(),
        policy=make_policy(require_signature=False),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is True
    assert result.signature_verified is False


def test_online_verifier_accepts_current_matching_checkpoint():
    entries = make_entries(1)
    bundle = make_bundle(entries)
    transport = FakeTransport(bundle=bundle, latest_head=bundle.tree_head)

    result = verify_online_event(
        "https://ets.example.test",
        bundle.event.event_id,
        trust_store=make_trust_store(),
        policy=make_policy(),
        transport=transport,
        allowed_hosts=("ets.example.test",),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is True
    assert result.signature_verified is True
    assert result.continuity_verified is True
    assert result.standing_status == "current_log"
    assert result.latest_tree_size == 1
    assert len(transport.calls) == 2


def test_online_verifier_verifies_consistency_when_log_has_grown():
    entries = make_entries(2)
    bundle = make_bundle(entries[:1])
    latest_head = make_signed_head(entries, LATEST_TIME)
    consistency = generate_consistency_proof(
        entries,
        previous_tree_size=1,
        generated_at_utc=LATEST_TIME,
    )
    transport = FakeTransport(
        bundle=bundle,
        latest_head=latest_head,
        consistency=consistency.model_dump(mode="json"),
    )

    result = verify_online_event(
        "https://ets.example.test",
        bundle.event.event_id,
        trust_store=make_trust_store(),
        policy=make_policy(),
        transport=transport,
        allowed_hosts=("ets.example.test",),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is True
    assert result.continuity_verified is True
    assert result.latest_tree_size == 2
    assert any("/api/v1/proofs/consistency?" in call for call in transport.calls)


def test_online_verifier_rejects_tree_size_rollback():
    entries = make_entries(1)
    bundle = make_bundle(entries)
    rollback_head = SIGNER.sign(
        SignedTreeHead(
            tree_size=0,
            root_hash=EMPTY_TREE_ROOT,
            created_at_utc=LATEST_TIME,
            log_id=LOG_ID,
        )
    )
    transport = FakeTransport(bundle=bundle, latest_head=rollback_head)

    result = verify_online_event(
        "https://ets.example.test",
        bundle.event.event_id,
        trust_store=make_trust_store(),
        policy=make_policy(),
        transport=transport,
        allowed_hosts=("ets.example.test",),
        verified_at_utc=VERIFY_TIME,
    )

    assert result.valid is False
    assert result.continuity_verified is False
    assert any(
        check.code == "append_only_continuity" and "regressed" in check.reason
        for check in result.checks
    )


def test_online_verifier_rejects_http_and_non_allowlisted_hosts():
    bundle = make_bundle(make_entries(1))
    transport = FakeTransport(bundle=bundle, latest_head=bundle.tree_head)

    with pytest.raises(ValueError, match="requires HTTPS"):
        verify_online_event(
            "http://ets.example.test",
            bundle.event.event_id,
            transport=transport,
        )

    with pytest.raises(ValueError, match="allowlist"):
        verify_online_event(
            "https://other.example.test",
            bundle.event.event_id,
            transport=transport,
            allowed_hosts=("ets.example.test",),
        )
