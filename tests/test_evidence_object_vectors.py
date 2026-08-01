from __future__ import annotations

import json
from pathlib import Path

from ets.evidence_object import EvidenceObject, canonical_bytes, object_hash


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "schemas/evidence-object/v1/examples/software-release.json"
VECTOR = ROOT / "schemas/evidence-object/v1/vectors/software-release.sha256.json"


def test_software_release_vector_is_stable() -> None:
    evidence = EvidenceObject.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    vector = json.loads(VECTOR.read_text(encoding="utf-8"))

    assert len(canonical_bytes(evidence)) == vector["canonical_byte_length"]
    assert object_hash(evidence) == vector["expected_hash"]
    assert vector["profile"] == "ets.evidence-object.canonical-json.sha256.v1"


def test_normative_example_round_trips() -> None:
    evidence = EvidenceObject.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    reparsed = EvidenceObject.model_validate_json(
        evidence.model_dump_json(exclude_none=True)
    )

    assert reparsed == evidence
    assert canonical_bytes(reparsed) == canonical_bytes(evidence)
