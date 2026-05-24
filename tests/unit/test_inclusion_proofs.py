from datetime import UTC, datetime

from ets.core.log import InMemoryAppendOnlyLog
from ets.core.models import EvidenceEvent
from ets.core.proofs import InclusionProof, generate_inclusion_proof, verify_inclusion_proof


def make_event(event_id: str) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id=f"evidence_{event_id}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="b" * 64,
        content_hash_alg="sha256",
        metadata={"event": event_id},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    )


def make_log() -> InMemoryAppendOnlyLog:
    log = InMemoryAppendOnlyLog()
    for index in range(4):
        log.append(make_event(f"evt_00{index}"))
    return log


def test_generated_proof_validates_against_current_root():
    log = make_log()
    proof = generate_inclusion_proof(
        log.list_entries(),
        2,
        generated_at_utc=datetime(2026, 5, 18, 13, 0, tzinfo=UTC),
    )

    result = verify_inclusion_proof(proof)

    assert result.valid is True
    assert result.reason == "ok"
    assert result.root_hash == proof.root_hash


def test_proof_is_json_serializable():
    proof = generate_inclusion_proof(make_log().list_entries(), 1)

    dumped = proof.model_dump_json()

    assert InclusionProof.model_validate_json(dumped) == proof


def test_tampered_leaf_hash_fails_verification():
    proof = generate_inclusion_proof(make_log().list_entries(), 2)
    tampered = proof.model_copy(update={"leaf_hash": "0" * 64})

    result = verify_inclusion_proof(tampered)

    assert result.valid is False
    assert "computed root" in result.reason


def test_tampered_audit_path_fails_verification():
    proof = generate_inclusion_proof(make_log().list_entries(), 2)
    data = proof.model_dump()
    data["audit_path"][0]["hash"] = "0" * 64
    tampered = InclusionProof.model_validate(data)

    result = verify_inclusion_proof(tampered)

    assert result.valid is False
    assert "computed root" in result.reason


def test_tampered_index_fails_when_path_positions_no_longer_match():
    proof = generate_inclusion_proof(make_log().list_entries(), 2)
    tampered = proof.model_copy(update={"leaf_index": 1})

    result = verify_inclusion_proof(tampered)

    assert result.valid is False
    assert "audit path" in result.reason


def test_tampered_index_fails_when_outside_tree_size():
    proof = generate_inclusion_proof(make_log().list_entries(), 2)
    tampered = proof.model_copy(update={"leaf_index": proof.tree_size})

    result = verify_inclusion_proof(tampered)

    assert result.valid is False
    assert "leaf index" in result.reason


def test_tampered_root_fails_verification():
    proof = generate_inclusion_proof(make_log().list_entries(), 2)
    tampered = proof.model_copy(update={"root_hash": "f" * 64})

    result = verify_inclusion_proof(tampered)

    assert result.valid is False
    assert "computed root" in result.reason
