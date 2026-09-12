from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/ranger/electromagnetic-actuation-trial.v0.1.schema.json"
BASELINE_PATH = ROOT / "docs/research/ranger/examples/electromagnetic-actuation-baseline.json"
BLOCKED_PATH = ROOT / "docs/research/ranger/examples/electromagnetic-actuation-blocked.json"

EXPECTED_EPISTEMIC_STATES = {
    "KNOWN",
    "NOT_OBSERVED",
    "NOT_AVAILABLE",
    "UNKNOWN",
    "INDETERMINATE",
    "CONTRADICTED",
}


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_trial_schema_has_stable_identity_and_strict_root() -> None:
    schema = _load(SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == (
        "https://lanternprotocol.net/schemas/ranger/"
        "electromagnetic-actuation-trial.v0.1.schema.json"
    )
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert properties["schema_version"] == {
        "const": "ranger.electromagnetic-actuation-trial.v0.1"
    }


def test_trial_contract_preserves_epistemic_states() -> None:
    schema = _load(SCHEMA_PATH)
    defs = schema["$defs"]
    assert isinstance(defs, dict)
    epistemic = defs["epistemicState"]
    assert isinstance(epistemic, dict)
    assert set(epistemic["enum"]) == EXPECTED_EPISTEMIC_STATES


def test_non_known_measurements_require_reason() -> None:
    schema = _load(SCHEMA_PATH)
    measurement = schema["$defs"]["measurement"]
    rules = measurement["allOf"]
    non_known_rule = rules[1]
    states = non_known_rule["if"]["properties"]["state"]["enum"]
    assert set(states) == EXPECTED_EPISTEMIC_STATES - {"KNOWN"}
    assert "reason" in non_known_rule["then"]["required"]


def test_baseline_fixture_separates_command_and_physical_consequence() -> None:
    event = _load(BASELINE_PATH)
    assert event["command"]["command_state"] == "ISSUED"
    result = event["result"]
    assert result["electrical_response"] == "OBSERVED"
    assert result["mechanical_response"] == "OBSERVED"
    assert result["thermal_response"] == "OBSERVED"
    assert result["final_safe_state"] == "CONFIRMED"

    kinds = {item["kind"] for item in event["observations"]}
    assert {"SUPPLY_VOLTAGE", "ACTUATION_CURRENT", "ARMATURE_POSITION", "TEMPERATURE"} <= kinds


def test_blocked_fixture_proves_command_does_not_imply_motion() -> None:
    event = _load(BLOCKED_PATH)
    assert event["authority"]["authorization_state"] == "AUTHORIZED"
    assert event["command"]["command_state"] == "ISSUED"
    assert event["result"]["electrical_response"] == "OBSERVED"
    assert event["result"]["mechanical_response"] == "BLOCKED"
    assert event["result"]["final_safe_state"] == "CONFIRMED"

    position = next(
        item
        for item in event["observations"]
        if item["kind"] == "ARMATURE_POSITION"
    )
    assert position["measurement"]["state"] == "KNOWN"
    assert position["measurement"]["value"] == 0.0


def test_safety_boundary_is_first_class_evidence() -> None:
    schema = _load(SCHEMA_PATH)
    required = set(schema["required"])
    assert {"authority", "safety_state", "command", "observations", "result"} <= required

    safety = schema["$defs"]["safetyState"]
    assert set(safety["required"]) == {
        "enclosure_state",
        "interlock_state",
        "hardware_limit_state",
        "safe_to_actuate",
    }


def _property_names(node: object) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            names.update(str(name).lower() for name in properties)
        for value in node.values():
            names.update(_property_names(value))
    elif isinstance(node, list):
        for value in node:
            names.update(_property_names(value))
    return names


def test_contract_is_captive_actuation_specific() -> None:
    schema = _load(SCHEMA_PATH)
    command = schema["$defs"]["command"]
    requested_action = command["properties"]["requested_action"]
    assert requested_action == {"const": "captive_electromagnetic_actuation"}

    # Enforce the safety boundary structurally. Prose may legitimately explain that
    # launcher-performance concepts are outside scope; they must not become fields.
    property_names = _property_names(schema)
    forbidden_performance_fields = {
        "range",
        "penetration",
        "muzzle_velocity",
        "muzzle_energy",
        "projectile_velocity",
        "projectile_energy",
    }
    assert property_names.isdisjoint(forbidden_performance_fields)
