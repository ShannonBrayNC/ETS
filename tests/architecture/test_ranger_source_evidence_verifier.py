from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ets.ranger.decision_event import decision_event_digest
from ets.ranger.evidence_object_adapter import ranger_decision_event_to_evidence_object
from ets.ranger.source_evidence_verifier import verify_ranger_source_evidence

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs/research/ranger/examples/decision-event-unknown.json"


def _fixture() -> tuple[object, dict[str, bytes]]:
    event = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    camera = b"camera-observation-fixture"
    enrollment = b"enrollment-set-fixture"
    artifacts = {
        "evidence-camera-001": camera,
        "evidence-enrollment-set-001": enrollment,
    }
    digest_by_id = {
        evidence_id: "sha256:" + hashlib.sha256(data).hexdigest()
        for evidence_id, data in artifacts.items()
    }
    for ref in event["evidence"]:
        ref["digest"] = digest_by_id[ref["evidence_id"]]
    event["event_digest"] = decision_event_digest(event)
    return ranger_decision_event_to_evidence_object(event), artifacts


def test_all_referenced_source_artifacts_can_be_independently_verified() -> None:
    evidence, artifacts = _fixture()
    result = verify_ranger_source_evidence(evidence, artifacts=artifacts)

    assert result.overall_status == "VERIFIED"
    assert result.referenced_count == 2
    assert result.available_count == 2
    assert result.verified_count == 2
    assert result.missing_count == 0
    assert result.mismatch_count == 0
    assert all(item.digest_status == "MATCH" for item in result.findings)
    assert result.truth_claim_supported is False


def test_missing_artifact_is_incomplete_not_negative_observation() -> None:
    evidence, artifacts = _fixture()
    artifacts.pop("evidence-camera-001")

    result = verify_ranger_source_evidence(evidence, artifacts=artifacts)

    assert result.overall_status == "INCOMPLETE"
    assert result.missing_count == 1
    missing = next(item for item in result.findings if item.evidence_id == "evidence-camera-001")
    assert missing.availability_status == "MISSING"
    assert missing.digest_status == "NOT_VERIFIED"


def test_tampered_artifact_reports_digest_mismatch() -> None:
    evidence, artifacts = _fixture()
    artifacts["evidence-camera-001"] = b"tampered-camera-observation"

    result = verify_ranger_source_evidence(evidence, artifacts=artifacts)

    assert result.overall_status == "DIGEST_MISMATCH"
    assert result.mismatch_count == 1
    mismatch = next(item for item in result.findings if item.evidence_id == "evidence-camera-001")
    assert mismatch.availability_status == "AVAILABLE"
    assert mismatch.digest_status == "MISMATCH"
    assert mismatch.actual_digest != mismatch.expected_digest


def test_extra_unreferenced_artifacts_do_not_create_evidence() -> None:
    evidence, artifacts = _fixture()
    artifacts["unreferenced"] = b"not part of the event"

    result = verify_ranger_source_evidence(evidence, artifacts=artifacts)

    assert result.overall_status == "VERIFIED"
    assert result.referenced_count == 2
    assert {item.evidence_id for item in result.findings} == {
        "evidence-camera-001",
        "evidence-enrollment-set-001",
    }
