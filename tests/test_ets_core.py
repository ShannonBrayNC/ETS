from ets.core.ets_core.hashing import hash_payload
from ets.core.ets_core.merkle import merkle_root, inclusion_proof, verify_inclusion
from ets.core.ets_core.service import TransparencyLogService


def test_hash_payload_is_stable():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert hash_payload(a) == hash_payload(b)


def test_merkle_proof_round_trip():
    leaves = [
        "00" * 32,
        "11" * 32,
        "22" * 32,
        "33" * 32
    ]
    root = merkle_root(leaves)
    proof = inclusion_proof(leaves, 2)
    assert verify_inclusion(leaves[2], proof, root) is True


def test_append_and_verify(tmp_path):
    db_path = tmp_path / "ets.db"
    svc = TransparencyLogService(str(db_path))

    payload = {"doc": "hello", "version": 1}
    result = svc.append_event(payload=payload, event_type="document")

    verify = svc.verify_payload_against_event(result["event_id"], payload)
    assert verify is not None
    assert verify["payload_hash_matches"] is True
    assert verify["included_in_tree"] is True
