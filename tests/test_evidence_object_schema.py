from __future__ import annotations

import json
from pathlib import Path

from ets.evidence_object import EvidenceObject

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/evidence-object/v1/evidence-object.schema.json"
SCHEMA_ID = "https://lanternprotocol.org/schemas/ets/evidence-object/v1"


def generated_schema() -> dict[str, object]:
    schema = EvidenceObject.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = SCHEMA_ID
    return schema


def test_checked_in_schema_preserves_stable_contract() -> None:
    checked_in = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    generated = generated_schema()

    assert checked_in["$id"] == generated["$id"]
    assert checked_in["$schema"] == generated["$schema"]
    assert checked_in["additionalProperties"] is False
    assert checked_in["required"] == generated["required"]
    assert set(checked_in["properties"]) == set(generated["properties"])
    assert set(checked_in["$defs"]) == set(generated["$defs"])

    for definition in checked_in["$defs"].values():
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False

    for enum_name in (
        "HashAlgorithm",
        "LifecycleState",
        "RelationshipType",
        "VerificationResult",
    ):
        assert checked_in["$defs"][enum_name]["enum"] == generated["$defs"][enum_name]["enum"]


def test_schema_has_stable_identity_and_strict_root() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$id"] == SCHEMA_ID
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
