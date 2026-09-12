from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ets.ranger.vectorrail_acceptance import (
    VectorRailAcceptanceError,
    verify_vectorrail_acceptance,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/ranger/vectorrail-vrx-acceptance.v0.1.schema.json"
EXAMPLES = ROOT / "docs/research/ranger/examples"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _fixture(name: str) -> dict[str, Any]:
    return _load(EXAMPLES / name)


def test_acceptance_schema_declares_draft_2020_12_and_strict_root_contract() -> None:
    schema = _load(SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == (
        "https://lanternprotocol.net/schemas/ranger/"
        "vectorrail-vrx-acceptance.v0.1.schema.json"
    )
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schema_version",
        "acceptance_id",
        "vrx_device_id",
        "configuration_digest",
        "reviewed_at",
        "reviewer_id",
        "gates",
        "dry_runs",
        "final_safe_state",
        "verifier",
        "qualification",
    }
    assert schema["properties"]["schema_version"] == {
        "const": "ranger.vectorrail-vrx-acceptance.v0.1"
    }


@pytest.mark.parametrize(
    "name",
    [
        "vectorrail-vrx-acceptance-qualified.json",
        "vectorrail-vrx-acceptance-not-qualified.json",
    ],
)
def test_acceptance_examples_match_machine_contract(name: str) -> None:
    record = _fixture(name)
    assert record["schema_version"] == "ranger.vectorrail-vrx-acceptance.v0.1"
    assert {gate["gate_id"] for gate in record["gates"]} == {
        "G0",
        "G1",
        "G2",
        "G3",
        "G4",
        "G5",
        "G6",
    }
    assert len(record["gates"]) == 7
    assert {item["scenario"] for item in record["dry_runs"]} == {
        "BASELINE",
        "INTERLOCK_REJECTION",
        "CONTROLLER_RESET_FAULT",
        "REQUIRED_SENSOR_UNAVAILABLE",
        "CONTRADICTORY_OBSERVATIONS",
        "BLOCKED_MECHANICAL_RESPONSE",
        "FINAL_SAFE_STATE_FAILURE",
    }
    assert verify_vectorrail_acceptance(record) is True


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
