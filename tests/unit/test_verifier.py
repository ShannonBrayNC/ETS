from datetime import UTC, datetime

from ets.core import (
    EvidenceEvent,
    InMemoryAppendOnlyLog,
    canonical_sha256,
    generate_inclusion_proof,
)
from ets.verifier import compute_event_hash, verify_event_hash, verify_inclusion
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
