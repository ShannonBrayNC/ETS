from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from ets.ranger.electromagnetic_actuation import trial_digest
from ets.ranger.electromagnetic_actuation_evidence_adapter import (
    electromagnetic_actuation_trial_to_evidence_object,
)
from ets.ranger.vectorrail_consequence_custody import (
    verify_vectorrail_consequence_custody,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/research/ranger/examples"
ACCEPTANCE = EXAMPLES / "vectorrail-vrx-acceptance-qualified.json"
BASELINE = EXAMPLES / "electromagnetic-actuation-baseline.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sealed_baseline() -> dict[str, Any]:
    trial = _load(BASELINE)
    trial["trial_digest"] = trial_digest(trial)
    return trial


def test_nominal_trial_reconstructs_full_consequence_custody_chain() -> None:
    result = verify_vectorrail_consequence_custody(
        _sealed_baseline(),
        _load(ACCEPTANCE),
    )

    assert result.conclusion == "VERIFIED_CONSISTENT"
    assert result.authority_state == "AUTHORIZED"
    assert result.command_state == "ISSUED"
    assert result.electrical_response == "OBSERVED"
    assert result.mechanical_response == "OBSERVED"
    assert result.thermal_response == "OBSERVED"
    assert result.final_safe_state == "CONFIRMED"
    assert result.trial_semantics_valid is True
    assert result.trial_digest_valid is True
    assert result.trial_evidence_object_valid is True
    assert result.trial_projection_conservative is True
    assert result.physical_observation_backing_valid is True
    assert result.raw_evidence_refs_bound is True
    assert result.acceptance_links_trial is True
    assert result.acceptance_evidence_object_valid is True
    assert result.acceptance_independent_verifier_valid is True
    assert result.trial_object_hash is not None
    assert result.acceptance_object_hash is not None
    assert {"electrical-b", "motion-a", "thermal-a"}.issubset(
        set(result.independent_observation_groups)
    )
    assert result.truth_claim_supported is False


def test_trial_evidence_object_binds_raw_measurement_artifact() -> None:
    trial = _sealed_baseline()
    evidence = electromagnetic_actuation_trial_to_evidence_object(trial)
    targets = {item.target_evidence_ref for item in evidence.relationships}

    assert "artifact-em-baseline-001" in targets


def test_post_seal_consequence_tampering_is_integrity_failure() -> None:
    trial = _sealed_baseline()
    trial["result"] = dict(trial["result"])
    trial["result"]["mechanical_response"] = "UNKNOWN"

    result = verify_vectorrail_consequence_custody(trial, _load(ACCEPTANCE))

    assert result.conclusion == "INTEGRITY_FAILURE"
    assert result.trial_digest_valid is False
    assert result.trial_evidence_object_valid is False


def test_command_log_cannot_substitute_for_physical_position_evidence() -> None:
    trial = _sealed_baseline()
    trial["observations"] = [
        item for item in trial["observations"] if item["kind"] != "ARMATURE_POSITION"
    ]
    trial["trial_digest"] = trial_digest(trial)

    result = verify_vectorrail_consequence_custody(trial, _load(ACCEPTANCE))

    assert result.conclusion == "SEMANTIC_INCONSISTENCY"
    assert result.command_state == "ISSUED"
    assert result.mechanical_response == "OBSERVED"
    assert result.physical_observation_backing_valid is False


def test_acceptance_must_explicitly_depend_on_the_verified_trial() -> None:
    trial = _sealed_baseline()
    acceptance = deepcopy(_load(ACCEPTANCE))
    baseline = next(
        item for item in acceptance["dry_runs"] if item["scenario"] == "BASELINE"
    )
    baseline["trial_ref"] = "em-trial-different-001"

    result = verify_vectorrail_consequence_custody(trial, acceptance)

    assert result.conclusion == "ACCEPTANCE_CHAIN_FAILURE"
    assert result.acceptance_links_trial is False
    assert result.acceptance_evidence_object_valid is True


def test_evidence_object_projection_does_not_promote_unknown_observation() -> None:
    trial = _sealed_baseline()
    current = next(
        item for item in trial["observations"] if item["kind"] == "ACTUATION_CURRENT"
    )
    current["measurement"] = {
        "state": "NOT_AVAILABLE",
        "value": None,
        "unit": "A",
        "uncertainty": None,
        "reason": "synthetic verifier test",
    }
    current["quality"] = "DEGRADED"
    trial["result"] = dict(trial["result"])
    trial["result"]["electrical_response"] = "UNKNOWN"
    trial["trial_digest"] = trial_digest(trial)

    result = verify_vectorrail_consequence_custody(trial, _load(ACCEPTANCE))

    assert result.conclusion == "VERIFIED_WITH_OBSERVABILITY_LIMIT"
    assert result.trial_projection_conservative is True
    assert result.truth_claim_supported is False
