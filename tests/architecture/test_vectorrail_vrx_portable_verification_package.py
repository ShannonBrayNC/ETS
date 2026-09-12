from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from ets.ranger.electromagnetic_actuation import trial_digest
from ets.ranger.vectorrail_consequence_custody_package import (
    build_vectorrail_consequence_custody_package,
    execute_vectorrail_replay_manifest,
    package_digest,
    verify_vectorrail_consequence_custody_package,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/research/ranger/examples"
BASELINE = EXAMPLES / "electromagnetic-actuation-baseline.json"
ACCEPTANCE = EXAMPLES / "vectorrail-vrx-acceptance-qualified.json"
MANIFEST = ROOT / "experiments/scenarios/vectorrail-vrx-consequence-custody-replay.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sealed_baseline() -> dict[str, Any]:
    trial = _load(BASELINE)
    trial["trial_digest"] = trial_digest(trial)
    return trial


def _package() -> dict[str, Any]:
    return build_vectorrail_consequence_custody_package(
        _sealed_baseline(),
        _load(ACCEPTANCE),
    )


def _reseal(package: dict[str, Any]) -> None:
    package["package_digest"] = package_digest(package)


def test_portable_package_is_deterministic_and_self_verifying() -> None:
    first = _package()
    second = _package()

    assert first == second
    assert first["package_digest"] == package_digest(first)

    result = verify_vectorrail_consequence_custody_package(first)
    assert result.conclusion == "VERIFIED_REPLAYABLE"
    assert result.chain_conclusion == "VERIFIED_CONSISTENT"
    assert result.package_digest_valid is True
    assert result.trial_record_digest_valid is True
    assert result.acceptance_record_digest_valid is True
    assert result.trial_object_hash_valid is True
    assert result.acceptance_object_hash_valid is True
    assert result.dependency_graph_valid is True
    assert result.replay_receipt_matches is True
    assert result.observability_boundary_conserved is True
    assert result.network_required is False
    assert result.truth_claim_supported is False


def test_package_carries_trial_acceptance_and_raw_artifact_dependencies() -> None:
    package = _package()
    edges = {
        (
            item["source_evidence_id"],
            item["relationship_type"],
            item["target_evidence_ref"],
        )
        for item in package["dependency_edges"]
    }

    assert (
        "em-trial-baseline-001",
        "depends_on",
        "artifact-em-baseline-001",
    ) in edges
    assert (
        "vrx-acceptance-001",
        "depends_on",
        "em-trial-baseline-001",
    ) in edges


def test_unresealed_package_mutation_is_integrity_failure() -> None:
    package = _package()
    package["verification_receipt"]["conclusion"] = "VERIFIED_FAIL_CLOSED"

    result = verify_vectorrail_consequence_custody_package(package)
    assert result.conclusion == "PACKAGE_INTEGRITY_FAILURE"
    assert result.package_digest_valid is False


def test_resealed_receipt_mutation_is_replay_mismatch() -> None:
    package = _package()
    package["verification_receipt"]["conclusion"] = "VERIFIED_FAIL_CLOSED"
    _reseal(package)

    result = verify_vectorrail_consequence_custody_package(package)
    assert result.conclusion == "REPLAY_MISMATCH"
    assert result.package_digest_valid is True
    assert result.replay_receipt_matches is False


def test_resealed_embedded_evidence_object_mutation_breaks_object_binding() -> None:
    package = _package()
    identity = package["trial"]["evidence_object"]["identity"]
    identity["version"] = 2
    _reseal(package)

    result = verify_vectorrail_consequence_custody_package(package)
    assert result.conclusion == "OBJECT_BINDING_FAILURE"
    assert result.trial_object_hash_valid is False


def test_resealed_dependency_edge_removal_is_detected() -> None:
    package = _package()
    package["dependency_edges"] = package["dependency_edges"][1:]
    _reseal(package)

    result = verify_vectorrail_consequence_custody_package(package)
    assert result.conclusion == "DEPENDENCY_GRAPH_FAILURE"
    assert result.dependency_graph_valid is False


def test_resealed_observability_strengthening_is_rejected() -> None:
    package = _package()
    package["observability"]["truth_claim_supported"] = True
    _reseal(package)

    result = verify_vectorrail_consequence_custody_package(package)
    assert result.conclusion == "OBSERVABILITY_BOUNDARY_FAILURE"
    assert result.observability_boundary_conserved is False
    assert result.truth_claim_supported is False


def test_resealed_trial_record_tampering_breaks_record_binding() -> None:
    package = _package()
    trial = package["trial"]["record"]
    trial["result"] = deepcopy(trial["result"])
    trial["result"]["mechanical_response"] = "UNKNOWN"
    _reseal(package)

    result = verify_vectorrail_consequence_custody_package(package)
    assert result.conclusion == "RECORD_BINDING_FAILURE"
    assert result.trial_record_digest_valid is False
    assert result.chain_conclusion == "INTEGRITY_FAILURE"


def test_repo_replay_manifest_emits_offline_portable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "vrx-portable-package.json"
    result = execute_vectorrail_replay_manifest(MANIFEST, output_path=output)

    assert result.conclusion == "VERIFIED_REPLAYABLE"
    assert result.chain_conclusion == "VERIFIED_CONSISTENT"
    assert output.exists()

    package = _load(output)
    replay = verify_vectorrail_consequence_custody_package(package)
    assert replay.conclusion == "VERIFIED_REPLAYABLE"
    assert replay.network_required is False
