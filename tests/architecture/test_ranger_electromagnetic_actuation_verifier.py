from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ets.ranger.electromagnetic_actuation import trial_digest
from ets.ranger.electromagnetic_actuation_evidence_adapter import (
    electromagnetic_actuation_trial_to_evidence_object,
)
from ets.ranger.electromagnetic_actuation_verifier import (
    ElectromagneticActuationVerificationError,
    verify_trial_semantics,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/research/ranger/examples"


def _load(name: str) -> dict[str, object]:
    value = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sealed(name: str) -> dict[str, object]:
    trial = _load(name)
    trial["trial_digest"] = trial_digest(trial)
    return trial


def test_interlock_rejection_is_fail_closed() -> None:
    trial = _load("electromagnetic-actuation-interlock-rejected.json")
    assert trial["safety_state"]["safe_to_actuate"] is False
    assert trial["safety_state"]["interlock_state"] == "OPEN"
    assert trial["command"]["command_state"] == "REJECTED"
    assert trial["result"]["electrical_response"] == "NOT_OBSERVED"
    assert trial["result"]["mechanical_response"] == "NOT_OBSERVED"
    assert verify_trial_semantics(trial) is True


def test_degraded_current_sensor_preserves_unknown_electrical_result() -> None:
    trial = _load("electromagnetic-actuation-degraded-sensor.json")
    current = next(
        item for item in trial["observations"] if item["kind"] == "ACTUATION_CURRENT"
    )
    assert current["quality"] == "DEGRADED"
    assert current["measurement"]["state"] == "NOT_AVAILABLE"
    assert trial["result"]["electrical_response"] == "UNKNOWN"
    assert trial["result"]["mechanical_response"] == "OBSERVED"
    assert verify_trial_semantics(trial) is True


def test_contradictory_independent_position_sources_do_not_become_known_result() -> None:
    trial = _load("electromagnetic-actuation-contradictory-observation.json")
    positions = [item for item in trial["observations"] if item["kind"] == "ARMATURE_POSITION"]
    groups = {item["independence_group"] for item in positions}
    assert {"motion-encoder", "motion-optical"} <= groups
    derived = next(item for item in positions if item["measurement"]["state"] == "CONTRADICTED")
    assert len(derived["source_ancestry"]) == 2
    assert trial["result"]["mechanical_response"] == "UNKNOWN"
    assert verify_trial_semantics(trial) is True


def test_verifier_rejects_issued_command_when_interlock_is_open() -> None:
    trial = _load("electromagnetic-actuation-interlock-rejected.json")
    trial["command"] = dict(trial["command"])
    trial["command"]["command_state"] = "ISSUED"
    with pytest.raises(ElectromagneticActuationVerificationError, match="interlock|unsafe"):
        verify_trial_semantics(trial)


def test_verifier_rejects_claimed_motion_without_known_position_evidence() -> None:
    trial = _load("electromagnetic-actuation-degraded-sensor.json")
    trial["observations"] = [
        item for item in trial["observations"] if item["kind"] != "ARMATURE_POSITION"
    ]
    with pytest.raises(ElectromagneticActuationVerificationError, match="position"):
        verify_trial_semantics(trial)


def test_trial_digest_changes_when_consequence_changes() -> None:
    trial = _load("electromagnetic-actuation-degraded-sensor.json")
    original = trial_digest(trial)
    changed = deepcopy(trial)
    changed["result"] = dict(changed["result"])
    changed["result"]["mechanical_response"] = "UNKNOWN"
    assert trial_digest(changed) != original


def test_evidence_object_adapter_preserves_epistemic_conservation() -> None:
    evidence = electromagnetic_actuation_trial_to_evidence_object(
        _sealed("electromagnetic-actuation-degraded-sensor.json")
    )
    predicates = {claim.predicate for claim in evidence.claims}
    assert "actuation.armature_position" in predicates
    assert "actuation.temperature" in predicates
    assert "actuation.actuation_current" not in predicates

    extension = evidence.extensions[
        "org.lanternprotocol.ranger.electromagnetic-actuation-trial.v0.1"
    ]
    trial = extension["trial"]
    current = next(
        item for item in trial["observations"] if item["kind"] == "ACTUATION_CURRENT"
    )
    assert current["measurement"]["state"] == "NOT_AVAILABLE"


def test_evidence_object_adapter_keeps_contradiction_in_extension_not_core_claims() -> None:
    evidence = electromagnetic_actuation_trial_to_evidence_object(
        _sealed("electromagnetic-actuation-contradictory-observation.json")
    )
    extension = evidence.extensions[
        "org.lanternprotocol.ranger.electromagnetic-actuation-trial.v0.1"
    ]
    contradicted = [
        item
        for item in extension["trial"]["observations"]
        if item["measurement"]["state"] == "CONTRADICTED"
    ]
    assert len(contradicted) == 1
    assert all(claim.claim_id != contradicted[0]["observation_id"] for claim in evidence.claims)
