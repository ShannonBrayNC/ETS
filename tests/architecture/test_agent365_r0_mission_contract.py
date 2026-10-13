from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/demos/agent365-r0-mission-event.v1.schema.json"
DOC_PATH = ROOT / "docs/demos/AGENT365_R0_MISSION_CONTRACT.md"
EXAMPLE_PATH = ROOT / "docs/demos/examples/agent365-r0-gateway-command.json"


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_p0_mission_schema_requires_one_canonical_mission_id() -> None:
    schema = _load(SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    required = schema["required"]
    assert isinstance(required, list)
    assert "mission_id" in required

    properties = schema["properties"]
    assert isinstance(properties, dict)
    mission_id = properties["mission_id"]
    assert isinstance(mission_id, dict)
    assert mission_id["type"] == "string"
    assert mission_id["pattern"] == (
        "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )


def test_p0_scenario_id_is_frozen() -> None:
    schema = _load(SCHEMA_PATH)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    scenario = properties["scenario_id"]
    assert isinstance(scenario, dict)
    assert scenario["const"] == "agent365-r0-forward-stop-v1"

    text = DOC_PATH.read_text(encoding="utf-8")
    assert "move forward toward the marked stopping point" in text
    assert "MUST NOT add turning" in text
    assert "CONTINUE_AROUND_OBSTACLE" in text


def test_p0_example_preserves_mission_id_and_scenario() -> None:
    example = _load(EXAMPLE_PATH)
    assert example["mission_id"] == "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
    assert example["scenario_id"] == "agent365-r0-forward-stop-v1"
    assert example["source_domain"] == "ets.gateway"
    assert example["correlation_basis"] == "authorization_artifact"


def test_contract_separates_source_evidence_from_ets_correlation() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "MUST NOT be injected into" in text
    assert "preserve the exact raw source payload and its digest" in text
    assert "ETS-assigned mission correlation" in text


def test_contract_requires_evidence_object_context_binding_and_extension() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert '"binding_type": "context"' in text
    assert '"contract_id": "lantern.demo.agent365-r0.mission.v1"' in text
    assert '"mission_id": "4db39caa-3794-47f7-9bf0-bf5cf79fb912"' in text
    assert "They MUST agree. A mismatch is a verification failure." in text
