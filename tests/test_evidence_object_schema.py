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


def test_checked_in_schema_matches_pydantic_contract() -> None:
    checked_in = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert checked_in == generated_schema()


def test_schema_has_stable_identity_and_strict_root() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$id"] == SCHEMA_ID
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
