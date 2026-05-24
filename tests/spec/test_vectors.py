from __future__ import annotations

import json
from pathlib import Path

from ets.core import EvidenceEvent, canonical_sha256, canonicalize
from ets.core.merkle import EMPTY_TREE_ROOT, leaf_hash_for_event_hash, merkle_root

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = REPO_ROOT / "ets" / "spec" / "test-vectors"


def test_merkle_vectors_match_implementation() -> None:
    vector = json.loads((VECTOR_ROOT / "merkle-vectors.json").read_text(encoding="utf-8"))
    leaves = vector["leaves"]
    roots = vector["roots"]

    assert roots["empty"] == EMPTY_TREE_ROOT
    assert merkle_root([]) == roots["empty"]
    assert merkle_root(leaves[:1]) == roots["single_leaf"]
    assert merkle_root(leaves[:2]) == roots["two_leaves"]
    assert merkle_root(leaves[:3]) == roots["three_leaves"]
    assert merkle_root(leaves[:4]) == roots["four_leaves"]


def test_v0_1_event_vector_matches_canonical_contract() -> None:
    vector = json.loads((VECTOR_ROOT / "v0.1" / "event-vectors.json").read_text(encoding="utf-8"))
    event = EvidenceEvent.model_validate_json(json.dumps(vector["event"]))
    expected = vector["expected"]

    payload = event.hashable_payload()
    event_hash = canonical_sha256(payload)

    assert canonicalize(payload).decode("utf-8") == expected["canonical_json"]
    assert event_hash == expected["event_hash"]
    assert leaf_hash_for_event_hash(event_hash) == expected["leaf_hash"]


def test_v0_1_event_vector_detects_tampered_payload() -> None:
    vector = json.loads((VECTOR_ROOT / "v0.1" / "event-vectors.json").read_text(encoding="utf-8"))
    event_data = vector["event"]
    event_data["metadata"] = dict(event_data["metadata"])
    event_data["metadata"]["sequence"] = 2

    event = EvidenceEvent.model_validate_json(json.dumps(event_data))
    event_hash = canonical_sha256(event.hashable_payload())

    assert event_hash != vector["expected"]["event_hash"]
