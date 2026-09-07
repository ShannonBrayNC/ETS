from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/ranger/decision-event.v0.1.schema.json"
EXAMPLE_PATH = ROOT / "docs/research/ranger/examples/decision-event-unknown.json"

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


def test_ranger_decision_event_schema_has_stable_identity_and_strict_root() -> None:
    schema = _load(SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "https://lanternprotocol.net/schemas/ranger/decision-event.v0.1.schema.json"
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert isinstance(properties, dict)
    assert properties["schema_version"] == {"const": "ranger.decision-event.v0.1"}


def test_ranger_epistemic_states_are_explicit_and_complete() -> None:
    schema = _load(SCHEMA_PATH)
    defs = schema["$defs"]
    assert isinstance(defs, dict)
    epistemic = defs["epistemicState"]
    assert isinstance(epistemic, dict)
    assert set(epistemic["enum"]) == EXPECTED_EPISTEMIC_STATES


def test_non_known_claim_states_require_reason() -> None:
    schema = _load(SCHEMA_PATH)
    defs = schema["$defs"]
    assert isinstance(defs, dict)
    claim = defs["claim"]
    assert isinstance(claim, dict)
    rules = claim["allOf"]
    assert isinstance(rules, list)

    non_known_rule = rules[1]
    assert isinstance(non_known_rule, dict)
    condition = non_known_rule["if"]
    then = non_known_rule["then"]
    assert isinstance(condition, dict)
    assert isinstance(then, dict)
    state_enum = condition["properties"]["state"]["enum"]
    assert set(state_enum) == EXPECTED_EPISTEMIC_STATES - {"KNOWN"}
    assert "reason" in then["required"]


def test_known_claim_requires_a_value() -> None:
    schema = _load(SCHEMA_PATH)
    defs = schema["$defs"]
    assert isinstance(defs, dict)
    claim = defs["claim"]
    assert isinstance(claim, dict)
    known_rule = claim["allOf"][0]
    assert known_rule["if"]["properties"]["state"] == {"const": "KNOWN"}
    assert "value" in known_rule["then"]["required"]


def test_unknown_identity_example_is_policy_participating_evidence() -> None:
    example = _load(EXAMPLE_PATH)
    assert example["schema_version"] == "ranger.decision-event.v0.1"

    subject_context = example["subject_context"]
    assert isinstance(subject_context, list)
    subject = subject_context[0]
    assert isinstance(subject, dict)
    assert subject["subject_scope"] == "MISSION_PSEUDONYM"

    claims = subject["claims"]
    assert isinstance(claims, list)
    identity_claim = next(
        claim
        for claim in claims
        if isinstance(claim, dict) and claim.get("kind") == "subject.registered_principal"
    )
    assert identity_claim["state"] == "UNKNOWN"
    assert identity_claim["reason"]
    assert "value" not in identity_claim

    decision = example["decision"]
    assert isinstance(decision, dict)
    assert identity_claim["claim_id"] in decision["participating_claim_ids"]
    assert decision["selected_action"] == "maintain_distance"


def test_decision_contract_preserves_participating_and_excluded_claim_sets() -> None:
    schema = _load(SCHEMA_PATH)
    defs = schema["$defs"]
    assert isinstance(defs, dict)
    decision = defs["decision"]
    assert isinstance(decision, dict)
    properties = decision["properties"]
    assert isinstance(properties, dict)
    assert "participating_claim_ids" in decision["required"]
    assert properties["participating_claim_ids"]["uniqueItems"] is True
    assert properties["excluded_claim_ids"]["uniqueItems"] is True
