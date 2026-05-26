from datetime import UTC, datetime

from ets.core.anchors import anchor_export_payload, build_anchor_export, verify_anchor_export
from ets.core.tree_head import SignedTreeHead


def make_tree_head() -> SignedTreeHead:
    return SignedTreeHead(
        tree_size=3,
        root_hash="a" * 64,
        created_at_utc=datetime(2026, 5, 26, 15, 0, tzinfo=UTC),
        log_id="ets-test-log",
        signature_alg="ed25519",
        signature="b" * 128,
        public_key_id="fixture-key",
    )


def test_build_anchor_export_derives_deterministic_id_and_hash():
    tree_head = make_tree_head()
    exported_at = datetime(2026, 5, 26, 15, 5, tzinfo=UTC)

    first = build_anchor_export(
        target="github_release",
        tree_head=tree_head,
        latest_block_hash="c" * 64,
        exported_at_utc=exported_at,
        notes=("release asset",),
    )
    second = build_anchor_export(
        target="github_release",
        tree_head=tree_head,
        latest_block_hash="c" * 64,
        exported_at_utc=exported_at,
        notes=("release asset",),
    )

    assert first == second
    assert first.anchor_id.startswith("ets-anchor:github_release:ets-test-log:3:")
    assert first.anchor_hash != "0" * 64
    assert first.merkle_root == tree_head.root_hash
    assert first.source_log_id == tree_head.log_id


def test_anchor_export_payload_excludes_identifier_and_hash():
    anchor = build_anchor_export(
        target="azure_immutable_storage",
        tree_head=make_tree_head(),
        latest_block_hash="d" * 64,
        exported_at_utc=datetime(2026, 5, 26, 15, 5, tzinfo=UTC),
    )

    payload = anchor_export_payload(anchor)

    assert "anchor_id" not in payload
    assert "anchor_hash" not in payload
    assert payload["target"] == "azure_immutable_storage"
    assert payload["signed_tree_head"] == anchor.signed_tree_head.model_dump(mode="json")


def test_verify_anchor_export_accepts_untampered_export():
    anchor = build_anchor_export(
        target="local_file",
        tree_head=make_tree_head(),
        latest_block_hash="e" * 64,
        exported_at_utc=datetime(2026, 5, 26, 15, 5, tzinfo=UTC),
    )

    result = verify_anchor_export(anchor)

    assert result.valid is True
    assert result.reason == "ok"
    assert result.anchor_id == anchor.anchor_id


def test_verify_anchor_export_rejects_tampered_merkle_root():
    anchor = build_anchor_export(
        target="local_file",
        tree_head=make_tree_head(),
        latest_block_hash="e" * 64,
        exported_at_utc=datetime(2026, 5, 26, 15, 5, tzinfo=UTC),
    )
    tampered = anchor.model_copy(update={"merkle_root": "0" * 64})

    result = verify_anchor_export(tampered)

    assert result.valid is False
    assert result.reason == "merkle root does not match tree head"


def test_verify_anchor_export_rejects_tampered_anchor_hash():
    anchor = build_anchor_export(
        target="local_file",
        tree_head=make_tree_head(),
        latest_block_hash="e" * 64,
        exported_at_utc=datetime(2026, 5, 26, 15, 5, tzinfo=UTC),
    )
    tampered = anchor.model_copy(update={"anchor_hash": "f" * 64})

    result = verify_anchor_export(tampered)

    assert result.valid is False
    assert result.reason == "anchor hash does not match contents"
