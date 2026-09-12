from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHALLENGES = ROOT / "experiments/scenarios/vectorrail-vrx-clean-room-challenges.v0.1.json"
REPORT_SCHEMA = (
    ROOT / "schemas/ranger/vectorrail-vrx-independent-validation-report.v0.1.schema.json"
)
CONTRACT = ROOT / "docs/research/ranger/vectorrail-vrx-clean-room-verifier-contract.md"
PROTOCOL = ROOT / "docs/research/ranger/vectorrail-vrx-external-validation-protocol.md"

EXPECTED_RESULTS = {
    "VRX-CR-001": "VERIFIED_REPLAYABLE",
    "VRX-CR-002": "PACKAGE_INTEGRITY_FAILURE",
    "VRX-CR-003": "RECORD_BINDING_FAILURE",
    "VRX-CR-004": "OBJECT_BINDING_FAILURE",
    "VRX-CR-005": "DEPENDENCY_GRAPH_FAILURE",
    "VRX-CR-006": "REPLAY_MISMATCH",
    "VRX-CR-007": "OBSERVABILITY_BOUNDARY_FAILURE",
}


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_clean_room_challenge_manifest_is_complete_and_stable() -> None:
    manifest = _load(CHALLENGES)

    assert manifest["manifest_version"] == "ets.vectorrail.clean-room-challenges.v0.1"
    assert manifest["required"] is True
    assert manifest["baseline_manifest"] == (
        "experiments/scenarios/vectorrail-vrx-consequence-custody-replay.json"
    )

    challenges = manifest["challenges"]
    assert isinstance(challenges, list)
    assert len(challenges) == len(EXPECTED_RESULTS)

    observed = {}
    for challenge in challenges:
        assert isinstance(challenge, dict)
        challenge_id = challenge["challenge_id"]
        expected = challenge["expected_package_conclusion"]
        assert isinstance(challenge_id, str)
        assert isinstance(expected, str)
        observed[challenge_id] = expected

    assert observed == EXPECTED_RESULTS


def test_deeper_layer_challenges_reseal_outer_package() -> None:
    manifest = _load(CHALLENGES)
    challenges = manifest["challenges"]
    assert isinstance(challenges, list)

    by_id = {
        item["challenge_id"]: item
        for item in challenges
        if isinstance(item, dict) and isinstance(item.get("challenge_id"), str)
    }

    for challenge_id in ("VRX-CR-003", "VRX-CR-004", "VRX-CR-005", "VRX-CR-006", "VRX-CR-007"):
        mutation = by_id[challenge_id]["mutation"]
        assert isinstance(mutation, dict)
        assert mutation["recompute_outer_package_digest"] is True

    digest_tamper = by_id["VRX-CR-002"]["mutation"]
    assert isinstance(digest_tamper, dict)
    assert digest_tamper["recompute_outer_package_digest"] is False


def test_validation_report_schema_preserves_independence_gate() -> None:
    schema = _load(REPORT_SCHEMA)

    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert isinstance(properties, dict)

    implementation = properties["implementation"]
    assert isinstance(implementation, dict)
    implementation_properties = implementation["properties"]
    assert isinstance(implementation_properties, dict)
    copied_reference_source = implementation_properties["copied_reference_source"]
    assert isinstance(copied_reference_source, dict)
    assert copied_reference_source["const"] is False

    approval = properties["approval"]
    assert isinstance(approval, dict)
    approval_properties = approval["properties"]
    assert isinstance(approval_properties, dict)
    decision = approval_properties["decision"]
    assert isinstance(decision, dict)
    assert decision["enum"] == ["APPROVE", "REJECT", "INDETERMINATE"]


def test_handoff_docs_keep_claim_boundary_and_human_gate_explicit() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")
    protocol = PROTOCOL.read_text(encoding="utf-8")

    assert "do **not** satisfy the independent-human approval gate" in contract
    assert "truth_claim_supported = false" in contract
    assert "must not be labeled independent validation" in protocol
    assert "sensor correctness" in protocol
