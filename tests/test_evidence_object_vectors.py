from __future__ import annotations

import json
from pathlib import Path

import pytest

from ets.evidence_object import EvidenceObject, canonical_bytes, object_hash

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas/evidence-object/v1"
VECTOR_NAMES = (
    "minimal",
    "software-release",
    "edge-observation",
    "correction",
)


@pytest.mark.parametrize("name", VECTOR_NAMES)
def test_normative_hash_vector_is_stable(name: str) -> None:
    example = SCHEMA_ROOT / "examples" / f"{name}.json"
    vector_path = SCHEMA_ROOT / "vectors" / f"{name}.sha256.json"

    evidence = EvidenceObject.model_validate_json(example.read_text(encoding="utf-8"))
    vector = json.loads(vector_path.read_text(encoding="utf-8"))

    assert len(canonical_bytes(evidence)) == vector["canonical_byte_length"]
    assert object_hash(evidence) == vector["expected_hash"]
    assert vector["profile"] == "ets.evidence-object.canonical-json.sha256.v1"


@pytest.mark.parametrize("name", VECTOR_NAMES)
def test_normative_example_round_trips(name: str) -> None:
    example = SCHEMA_ROOT / "examples" / f"{name}.json"
    evidence = EvidenceObject.model_validate_json(example.read_text(encoding="utf-8"))
    reparsed = EvidenceObject.model_validate_json(
        evidence.model_dump_json(exclude_none=True)
    )

    assert reparsed == evidence
    assert canonical_bytes(reparsed) == canonical_bytes(evidence)
