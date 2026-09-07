from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas" / "ranger" / "cyber-physical-state.v0.1.schema.json"


def _schema() -> dict[str, object]:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_schema_identity_is_stable_and_strict() -> None:
    schema = _schema()
    assert (
        schema["$id"]
        == "https://lanternprotocol.net/schemas/ranger/cyber-physical-state.v0.1.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == "ranger.cyber-physical-state.v0.1"


def test_measurement_preserves_quality_and_observability_context() -> None:
    measurement = _schema()["$defs"]["measurement"]
    properties = measurement["properties"]
    for field in (
        "state",
        "source_id",
        "method",
        "captured_at",
        "freshness_ms",
        "uncertainty",
        "confidence",
        "coordinate_frame",
        "calibration_ref",
        "health_ref",
        "dependency_refs",
        "reason",
    ):
        assert field in properties


def test_non_known_measurements_require_reason() -> None:
    measurement = _schema()["$defs"]["measurement"]
    rule = measurement["allOf"][1]
    assert set(rule["if"]["properties"]["state"]["enum"]) == {
        "NOT_OBSERVED",
        "NOT_AVAILABLE",
        "UNKNOWN",
        "INDETERMINATE",
        "CONTRADICTED",
    }
    assert "reason" in rule["then"]["required"]


def test_capability_state_is_independent_from_measurement_state() -> None:
    schema = _schema()
    capability = schema["$defs"]["capability"]
    assert capability["properties"]["state"]["$ref"] == "#/$defs/capabilityState"
    assert schema["$defs"]["capabilityState"]["enum"] == [
        "AVAILABLE",
        "DEGRADED",
        "NOT_AVAILABLE",
        "FAILED",
        "UNKNOWN",
    ]


def test_command_and_result_stages_are_not_collapsed() -> None:
    actuation = _schema()["$defs"]["actuation"]
    assert set(actuation["properties"]) == {
        "selected_action",
        "issued_command",
        "command_acknowledgement",
        "actuator_response",
    }
    assert "does not imply another" in actuation["description"]


def test_consequence_requires_supporting_and_contradicting_refs() -> None:
    consequence = _schema()["$defs"]["consequence"]
    assert set(consequence["required"]) == {
        "state",
        "supporting_measurement_refs",
        "contradicting_measurement_refs",
    }


def test_clock_uncertainty_and_measurement_freshness_are_explicit() -> None:
    schema = _schema()
    assert "uncertainty_ms" in schema["$defs"]["clockState"]["properties"]
    assert "freshness_ms" in schema["$defs"]["measurement"]["properties"]
