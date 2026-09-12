from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ets.evidence_object.canonical import object_hash
from ets.ranger.vectorrail_acceptance_evidence import (
    VectorRailAcceptanceEvidenceError,
    vectorrail_acceptance_digest,
    vectorrail_acceptance_to_evidence_object,
)
from ets.ranger.vectorrail_acceptance_evidence_verifier import (
    verify_vectorrail_acceptance_evidence_object,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/research/ranger/examples/vectorrail-vrx-acceptance-qualified.json"


def _record() -> dict[str, Any]:
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_acceptance_record_digest_is_deterministic_and_consequence_sensitive() -> None:
    record = _record()
    first = vectorrail_acceptance_digest(record)
    second = vectorrail_acceptance_digest(deepcopy(record))
    assert first == second
    changed = deepcopy(record)
    changed["qualification"] = "NOT_QUALIFIED"
    assert vectorrail_acceptance_digest(changed) != first


def test_qualified_acceptance_projects_to_evidence_object() -> None:
    record = _record()
    evidence = vectorrail_acceptance_to_evidence_object(record)

    assert evidence.identity.evidence_id == record["acceptance_id"]
    assert evidence.identity.evidence_type == "vectorrail-vrx-laboratory-acceptance"
    assert evidence.provenance is not None
    assert evidence.provenance.device_ref == record["vrx_device_id"]
    assert evidence.provenance.operator_ref == record["reviewer_id"]

    claim_by_predicate = {claim.predicate: claim for claim in evidence.claims}
    assert claim_by_predicate["vectorrail.qualification"].value == "QUALIFIED"
    assert claim_by_predicate["vectorrail.final_safe_state"].value == "CONFIRMED"
    assert claim_by_predicate["vectorrail.configuration_digest"].value == record[
        "configuration_digest"
    ]


def test_adapter_links_gate_evidence_and_dry_run_trials() -> None:
    evidence = vectorrail_acceptance_to_evidence_object(_record())
    targets = {relationship.target_evidence_ref for relationship in evidence.relationships}

    assert {f"artifact:g{i}" for i in range(7)}.issubset(targets)
    assert "em-trial-baseline-001" in targets
    assert "em-trial-blocked-001" in targets
    assert "em-trial-safe-state-failure-001" in targets


def test_adapter_binds_acceptance_configuration_and_evidence_package() -> None:
    record = _record()
    evidence = vectorrail_acceptance_to_evidence_object(record)
    bindings = {item.scope: item for item in evidence.integrity}

    assert bindings["vectorrail-vrx-acceptance-record"].digest == vectorrail_acceptance_digest(
        record
    ).removeprefix("sha256:")
    assert bindings["vectorrail-vrx-configuration"].digest == record[
        "configuration_digest"
    ].removeprefix("sha256:")
    assert bindings["vectorrail-vrx-acceptance-evidence-package"].digest == record["verifier"][
        "evidence_package_digest"
    ].removeprefix("sha256:")


def test_acceptance_verifier_recomputes_source_and_outer_integrity() -> None:
    evidence = vectorrail_acceptance_to_evidence_object(_record())
    outer_hash = object_hash(evidence)
    result = verify_vectorrail_acceptance_evidence_object(
        evidence,
        expected_object_hash=outer_hash,
    )

    assert result.acceptance_record_present is True
    assert result.acceptance_record_semantically_valid is True
    assert result.acceptance_record_digest_valid is True
    assert result.acceptance_integrity_binding_valid is True
    assert result.configuration_binding_valid is True
    assert result.evidence_package_binding_valid is True
    assert result.outer_object_hash_valid is True
    assert result.qualification == "QUALIFIED"
    assert result.final_safe_state == "CONFIRMED"
    assert result.verifier_status == "VERIFIED"
    assert result.supporting_relationship_count == 14
    assert result.truth_claim_supported is False


def test_tampered_embedded_record_breaks_source_digest_and_outer_hash_expectation() -> None:
    evidence = vectorrail_acceptance_to_evidence_object(_record())
    expected_outer_hash = object_hash(evidence)
    extension = deepcopy(evidence.extensions)
    namespace = "org.lanternprotocol.ranger.vectorrail-vrx-acceptance.v0.1"
    extension[namespace]["acceptance_record"]["notes"] = "tampered after qualification"
    tampered = evidence.model_copy(update={"extensions": extension})

    result = verify_vectorrail_acceptance_evidence_object(
        tampered,
        expected_object_hash=expected_outer_hash,
    )
    assert result.acceptance_record_digest_valid is False
    assert result.acceptance_integrity_binding_valid is False
    assert result.outer_object_hash_valid is False


def test_invalid_qualification_cannot_be_projected() -> None:
    record = _record()
    record["gates"][0]["status"] = "FAIL"
    record["gates"][0]["checks"][0]["status"] = "FAIL"

    with pytest.raises(VectorRailAcceptanceEvidenceError, match="QUALIFIED requires"):
        vectorrail_acceptance_to_evidence_object(record)


def test_evidence_object_does_not_strengthen_acceptance_beyond_source_record() -> None:
    evidence = vectorrail_acceptance_to_evidence_object(_record())
    assert all(claim.confidence is None for claim in evidence.claims)
    result = verify_vectorrail_acceptance_evidence_object(evidence)
    assert result.truth_claim_supported is False
    assert "do_not_prove_physical_truth" in result.truth_claim_boundary
