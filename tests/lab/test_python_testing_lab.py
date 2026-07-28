from fastapi.testclient import TestClient

from ets.lab.app import create_lab_app
from ets.lab.scenarios import list_components, list_scenarios, run_lab_scenario


def test_lab_components_cover_core_ets_pipeline() -> None:
    components = list_components()
    component_names = {component["name"] for component in components}
    assert "Canonicalization" in component_names
    assert "EvidenceEvent Validator" in component_names
    assert "Append-Only Log" in component_names
    assert "Merkle Tree" in component_names
    assert "Certificate Generator" in component_names
    assert "Policy Gate" in component_names
    assert "Audit Replay" in component_names


def test_lab_scenarios_are_available() -> None:
    scenarios = list_scenarios()
    scenario_ids = {str(scenario["scenario_id"]) for scenario in scenarios}
    assert {
        "full-pipeline",
        "canonical-hash",
        "inclusion-proof",
        "tamper-detection",
        "policy-routing",
        "civic-boundary",
    }.issubset(scenario_ids)


def test_full_pipeline_generates_claim_safe_certificate_preview() -> None:
    result = run_lab_scenario("full-pipeline")
    assert result.status == "passed"
    assert result.outputs["tree_size"] == 3
    assert result.outputs["routing"] == {
        "decision": "Human Review",
        "reason": "verified proof material is sensitive or externally visible",
        "required_state": "Public Release Restricted",
    }
    certificate_preview = result.outputs["certificate_preview"]
    assert isinstance(certificate_preview, list)
    assert any("What This Verifies" in str(line) for line in certificate_preview)


def test_tamper_detection_rejects_mutated_root() -> None:
    result = run_lab_scenario("tamper-detection")
    assert result.status == "passed"
    assert result.outputs["tamper_rejected"] is True
    verification = result.outputs["verification"]
    assert isinstance(verification, dict)
    assert verification["valid"] is False
    assert verification["reason"] == "computed root does not match proof root"


def test_lab_fastapi_ui_and_run_endpoints() -> None:
    client = TestClient(create_lab_app())

    ui_response = client.get("/lab")
    assert ui_response.status_code == 200
    assert "Break down ETS" in ui_response.text

    run_response = client.post("/lab/api/run/canonical-hash")
    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["status"] == "passed"
    assert payload["outputs"]["match"] is True

    tree_response = client.post("/lab/api/tree-head-progression")
    assert tree_response.status_code == 200
    tree_payload = tree_response.json()
    assert tree_payload["previous_tree_size"] == 2
    assert tree_payload["latest_tree_size"] == 4
    assert tree_payload["verification"]["valid"] is True
