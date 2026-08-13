from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.evidence_object.canonical_v2 import (
    canonical_identity_bytes,
    identity_hash,
)
from ets.evidence_object.models_v2 import EvidenceObjectV2

ROOT = Path(__file__).parents[1]
VECTOR = ROOT / "schemas/evidence-object/v2/vectors/minimal.sha256.json"


def test_v2_reference_vector_is_byte_exact() -> None:
    vector = json.loads(VECTOR.read_text(encoding="utf-8"))
    evidence = EvidenceObjectV2.model_validate_json(json.dumps(vector["object"]))
    assert canonical_identity_bytes(evidence).hex() == vector["canonical_hex"]
    assert identity_hash(evidence) == vector["identity_hash"]


def test_reference_vector_has_independent_stdlib_hash() -> None:
    vector = json.loads(VECTOR.read_text(encoding="utf-8"))
    payload = {
        key: value
        for key, value in vector["object"].items()
        if key != "proof_material"
    }
    independent = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert independent.hex() == vector["canonical_hex"]
    assert hashlib.sha256(independent).hexdigest() == vector["identity_hash"]


def test_unknown_proof_material_does_not_change_identity() -> None:
    vector = json.loads(VECTOR.read_text(encoding="utf-8"))
    baseline = EvidenceObjectV2.model_validate_json(json.dumps(vector["object"]))
    future = EvidenceObjectV2.model_validate_json(
        json.dumps({
            **vector["object"],
            "proof_material": [
                {
                    "proof_type": "vendor.future-proof.v9",
                    "profile": "vendor.example.experimental",
                    "material": {"opaque": [1, 2, 3], "new_field": True},
                }
            ],
        })
    )
    assert identity_hash(future) == identity_hash(baseline)


def test_unknown_normative_core_field_fails_closed() -> None:
    vector = json.loads(VECTOR.read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        EvidenceObjectV2.model_validate_json(
            json.dumps({**vector["object"], "future_core": {}})
        )


def test_generated_schema_matches_normative_artifact() -> None:
    actual = EvidenceObjectV2.model_json_schema(ref_template="#/$defs/{model}")
    expected = json.loads(
        (ROOT / "schemas/evidence-object/v2/evidence-object.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert actual == expected
