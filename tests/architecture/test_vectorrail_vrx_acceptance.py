from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ets.ranger.vectorrail_acceptance import (
    VectorRailAcceptanceError,
    verify_vectorrail_acceptance,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/ranger/vectorrail-vrx-acceptance.v0.1.schema.json"
EXAMPLES = ROOT / "docs/research/ranger/examples"


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _fixture(name: str) -> dict[str, object]:
    return _load(EXAMPLES / name)


def test_acceptance_schema_and_examples_are_valid() -> None:
    schema = _load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for name in (
        "vectorrail-vrx-acceptance-qualified.json",
        "vectorrail-vrx-acceptance-not-qualified.json",
    ):
        validator.validate(_fixture(name))


def test_qualified_fixture_passes_semantic_verifier() -> None:
    record = _fixture("vectorrail-vrx-acceptance-qualified.json")
    assert record["qualification"] == "QUALIFIED"
    assert verify_vectorrail_acceptance(record) is True


def test_not_qualified_fixture_is_valid_fail_closed_evidence() -> None:
    record = _fixture("vectorrail-vrx-acceptance-not-qualified.json")
    assert record["qualification"] == "NOT_QUALIFIED"
    assert record["final_safe_state"] == "UNKNOWN"
    assert verify_vectorrail_acceptance(record) is True


def test_qualified_record_cannot_hide_failed_gate() -> None:
    record = deepcopy(_fixture("vectorrail-vrx-acceptance-qualified.json"))
    g4 = next(gate for gate in record["gates"] if gate["gate_id"] == "G4")
    g4["status"] = "FAIL"
    g4["checks"][0]["status"] = "FAIL"
    with pytest.raises(VectorRailAcceptanceError, match="QUALIFIED requires"):
        verify_vectorrail_acceptance(record)


def test_gate_pass_cannot_hide_failed_constituent_check() -> None:
    record = deepcopy(_fixture("vectorrail-vrx-acceptance-qualified.json"))
    g3 = next(gate for gate in record["gates"] if gate["gate_id"] == "G3")
    g3["checks"][0]["status"] = "FAIL"
    with pytest.raises(VectorRailAcceptanceError, match="cannot PASS"):
        verify_vectorrail_acceptance(record)


def test_qualification_requires_all_seven_unique_gates() -> None:
    record = deepcopy(_fixture("vectorrail-vrx-acceptance-qualified.json"))
    record["gates"] = record["gates"][:-1]
    with pytest.raises(VectorRailAcceptanceError, match="exactly G0-G6"):
        verify_vectorrail_acceptance(record)


def test_qualification_requires_every_fault_dry_run() -> None:
    record = deepcopy(_fixture("vectorrail-vrx-acceptance-qualified.json"))
    record["dry_runs"] = [
        item for item in record["dry_runs"] if item["scenario"] != "INTERLOCK_REJECTION"
    ]
    with pytest.raises(VectorRailAcceptanceError, match="seven required dry-run"):
        verify_vectorrail_acceptance(record)


def test_unknown_final_safe_state_can_never_be_qualified() -> None:
    record = deepcopy(_fixture("vectorrail-vrx-acceptance-qualified.json"))
    record["final_safe_state"] = "UNKNOWN"
    with pytest.raises(VectorRailAcceptanceError, match="final_safe_state CONFIRMED"):
        verify_vectorrail_acceptance(record)


def test_failed_independent_verifier_can_never_be_qualified() -> None:
    record = deepcopy(_fixture("vectorrail-vrx-acceptance-qualified.json"))
    record["verifier"] = dict(record["verifier"])
    record["verifier"]["status"] = "FAILED"
    record["verifier"]["reason"] = "Synthetic integrity failure."
    with pytest.raises(VectorRailAcceptanceError, match="verifier VERIFIED"):
        verify_vectorrail_acceptance(record)


def test_all_pass_conditions_cannot_be_labeled_not_qualified() -> None:
    record = deepcopy(_fixture("vectorrail-vrx-acceptance-qualified.json"))
    record["qualification"] = "NOT_QUALIFIED"
    with pytest.raises(VectorRailAcceptanceError, match="internally inconsistent"):
        verify_vectorrail_acceptance(record)


def test_schema_has_no_launcher_performance_fields() -> None:
    schema = _load(SCHEMA_PATH)

    def property_names(node: object) -> set[str]:
        names: set[str] = set()
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                names.update(str(name).lower() for name in properties)
            for value in node.values():
                names.update(property_names(value))
        elif isinstance(node, list):
            for value in node:
                names.update(property_names(value))
        return names

    forbidden = {
        "range",
        "penetration",
        "muzzle_velocity",
        "muzzle_energy",
        "projectile_velocity",
        "projectile_energy",
    }
    assert property_names(schema).isdisjoint(forbidden)
