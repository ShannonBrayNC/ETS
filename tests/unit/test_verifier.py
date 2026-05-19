from datetime import UTC, datetime

from ets.core import (
    EvidenceEvent,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    canonical_sha256,
    generate_inclusion_proof,
)
from ets.core.merkle import EMPTY_TREE_ROOT
from ets.verifier import compare_tree_heads, compute_event_hash, verify_event_hash, verify_inclusion
from ets.verifier.cli import main


def make_event(event_id: str = "evt_001") -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="d" * 64,
        content_hash_alg="sha256",
        metadata={"case": "alpha"},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    )


def make_tree_head(
    tree_size: int,
    root_hash: str,
    created_at_utc: datetime = datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    log_id: str = "ets-local-dev",
) -> SignedTreeHead:
    return SignedTreeHead(
        tree_size=tree_size,
        root_hash=root_hash,
        created_at_utc=created_at_utc,
        log_id=log_id,
    )


def test_compute_event_hash_accepts_model_and_mapping():
    event = make_event()
    expected = canonical_sha256(event.hashable_payload())

    assert compute_event_hash(event) == expected
    assert compute_event_hash(event.model_dump(mode="json")) == expected


def test_verify_event_hash_reports_match_and_mismatch():
    event = make_event()
    expected = compute_event_hash(event)

    assert verify_event_hash(event, expected).valid is True

    mismatch = verify_event_hash(event, "0" * 64)
    assert mismatch.valid is False
    assert mismatch.reason == "event hash does not match expected hash"


def test_verify_inclusion_accepts_mapping_payload():
    log = InMemoryAppendOnlyLog()
    log.append(make_event("evt_001"))
    log.append(make_event("evt_002"))
    proof = generate_inclusion_proof(log.list_entries(), 1)

    result = verify_inclusion(proof.model_dump(mode="json"))

    assert result.valid is True
    assert result.reason == "ok"


def test_compare_tree_heads_accepts_same_checkpoint_and_growth():
    previous = make_tree_head(0, EMPTY_TREE_ROOT)
    latest = make_tree_head(1, "1" * 64)

    assert compare_tree_heads(previous, previous).valid is True

    result = compare_tree_heads(previous.model_dump(mode="json"), latest.model_dump(mode="json"))
    assert result.valid is True
    assert result.reason == "tree size advanced"
    assert result.previous_tree_size == 0
    assert result.latest_tree_size == 1


def test_compare_tree_heads_rejects_rollback_and_equivocation():
    previous = make_tree_head(2, "2" * 64)
    rollback = make_tree_head(1, "1" * 64)
    equivocation = make_tree_head(2, "3" * 64)

    assert compare_tree_heads(previous, rollback).reason == "tree size regressed"
    assert compare_tree_heads(previous, equivocation).reason == "same tree size has different roots"


def test_compare_tree_heads_rejects_log_and_timestamp_mismatch():
    previous = make_tree_head(1, "1" * 64)
    other_log = make_tree_head(2, "2" * 64, log_id="other")
    older_timestamp = make_tree_head(
        2,
        "2" * 64,
        created_at_utc=datetime(2026, 5, 18, 12, 29, tzinfo=UTC),
    )

    assert compare_tree_heads(previous, other_log).reason == "log IDs do not match"
    assert compare_tree_heads(previous, older_timestamp).reason == "tree head timestamp regressed"


def test_cli_event_hash_prints_json(tmp_path, capsys):
    event_path = tmp_path / "event.json"
    event_path.write_text(make_event().model_dump_json(), encoding="utf-8")

    exit_code = main(["event-hash", str(event_path)])

    assert exit_code == 0
    assert compute_event_hash(make_event()) in capsys.readouterr().out


def test_cli_inclusion_proof_returns_nonzero_for_tampered_proof(tmp_path, capsys):
    log = InMemoryAppendOnlyLog()
    log.append(make_event("evt_001"))
    log.append(make_event("evt_002"))
    proof = generate_inclusion_proof(log.list_entries(), 1).model_copy(
        update={"root_hash": "0" * 64}
    )
    proof_path = tmp_path / "proof.json"
    proof_path.write_text(proof.model_dump_json(), encoding="utf-8")

    exit_code = main(["inclusion-proof", str(proof_path)])

    assert exit_code == 1
    assert '"valid": false' in capsys.readouterr().out


def test_cli_tree_head_compare_returns_nonzero_for_rollback(tmp_path, capsys):
    previous_path = tmp_path / "previous.json"
    latest_path = tmp_path / "latest.json"
    previous_path.write_text(make_tree_head(2, "2" * 64).model_dump_json(), encoding="utf-8")
    latest_path.write_text(make_tree_head(1, "1" * 64).model_dump_json(), encoding="utf-8")

    exit_code = main(["tree-head", str(previous_path), str(latest_path)])

    assert exit_code == 1
    assert "tree size regressed" in capsys.readouterr().out
