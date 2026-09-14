from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.qualification.hardware import HardwareQualificationReport
from ets.qualification.index import (
    QualificationClaim,
    QualificationIndex,
    load_qualification_index,
    validate_claim_against_evidence,
)
from ets.qualification.verifier import verify_hardware_qualification_package

_ROOT = Path(__file__).parents[2]
_INDEX = _ROOT / "docs" / "qualification" / "qualification-index.json"
_VALID = _ROOT / "docs" / "qualification" / "fixtures" / "hqp2" / "valid"
_VERIFIER_BUILD = hashlib.sha256(b"hqp5-index-fixture-verifier").hexdigest()


def _artifact_payloads() -> dict[str, bytes]:
    mapping = json.loads((_VALID / "artifact-map.json").read_text(encoding="utf-8"))
    return {
        artifact_id: (_VALID / relative_path).read_bytes()
        for artifact_id, relative_path in mapping.items()
    }


def _verification():
    return verify_hardware_qualification_package(
        profile_bytes=(_VALID / "profile.json").read_bytes(),
        run_bytes=(_VALID / "run.json").read_bytes(),
        report_bytes=(_VALID / "report.json").read_bytes(),
        artifact_payloads=_artifact_payloads(),
        verifier_id="hqp5-index-fixture-verifier",
        verifier_build_digest_sha256=_VERIFIER_BUILD,
        independent_execution_context=True,
        challenge_nonce="hqp5-index-fixture",
    )


def _fixture_claim_payload() -> dict[str, object]:
    verification = _verification()
    return {
        "claim_id": "conformance-fixture-qualified-001",
        "publication_state": "active",
        "disposition": "qualified",
        "claim_text": "Conformance fixture only; not a physical product qualification claim.",
        "profile": {
            "profile_id": "ets.test.hardware-qualification.v1",
            "profile_version": "1.0.0-test",
            "profile_digest_sha256": (
                "077698897506f6dcd4d6484ddb8364bbda918704fc424493ba4e2e6e7e4c5b92"
            ),
            "profile_path": "docs/qualification/fixtures/hqp2/valid/profile.json",
        },
        "device": {
            "device_id": "dut-hqp2-001",
            "manufacturer": "ETS Lab",
            "model": "HQP2 Fixture",
            "hardware_revision": "rev-a",
            "serial_or_asset_id": "HQP2-001",
            "identity_digest_sha256": (
                "6a127c4cd32887ee18fc99a9d112ea4e7d448e66a4c6395924ffeb359b1bbd22"
            ),
        },
        "build": {
            "repository": "ShannonBrayNC/ETS",
            "commit_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "artifact_digest_sha256": (
                "39e88c17cc95ace5674274b1baeba67fe3b53446f124b47063889bae1d8914ae"
            ),
            "configuration_digest_sha256": (
                "9be1ed24983f256c74e3e6042ce2c85a933ff5420c476c3cee86d4f903f0d110"
            ),
            "sbom_artifact_id": None,
        },
        "package": {
            "run_id": "hqp2-fixture-run-001",
            "run_digest_sha256": (
                "c0782f8eda93f87b346cff2c57d7bf418f14ff47d7f40f9d412257cfd486f060"
            ),
            "report_id": "hqp2-fixture-run-001.report",
            "report_digest_sha256": (
                "873e919b669c95565768c20662ae49bac0df1778f972fc91eef91e90a2f561c5"
            ),
            "package_digest_sha256": hashlib.sha256(b"hqp5-fixture-package").hexdigest(),
            "retention_locator": "fixture://hqp2/valid",
            "evidence_object_ids": ["evidence-object-1"],
            "artifact_ids": [
                "artifact-start",
                "artifact-stimulus",
                "artifact-observation",
                "artifact-result",
                "artifact-evidence",
            ],
            "deviation_ids": [],
        },
        "verification": {
            "verification_id": verification.verification_id,
            "verification_digest_sha256": verification.verification_digest_sha256,
            "verifier_id": verification.verifier_id,
            "verifier_build_digest_sha256": verification.verifier_build_digest_sha256,
            "outcome": verification.outcome.value,
            "eligible_for_claimed_disposition": (
                verification.eligible_for_claimed_disposition
            ),
            "independent_execution_context": True,
        },
        "limitations": [
            "Conformance fixture only.",
            "Does not represent physical product qualification.",
        ],
        "validity": {
            "valid_from": "2026-09-13T20:05:00Z",
            "valid_until": None,
            "requalification_triggers": ["Any fixture profile/build/DUT change."],
        },
        "supersession": None,
        "roadmap": {
            "roadmap_path": "docs/PUBLIC_ROADMAP_STATUS.md",
            "product": "HQP conformance fixture",
            "capability_maturity": "test-only",
            "qualification_language": (
                "Conformance fixture; never publish as product qualification."
            ),
            "capability_maturity_is_independent": True,
        },
        "source_issue_refs": ["ShannonBrayNC/ETS#798"],
    }


def test_public_index_declares_no_current_physical_qualified_claims() -> None:
    index = load_qualification_index(_INDEX.read_bytes())

    assert index.published_claims == ()
    assert len(index.pending_targets) == 3
    assert {item.target_class_id for item in index.pending_targets} == {
        "EDGE-RT0",
        "ANDROID-PHASE1A-RT0",
        "LEGACY-NET-SYSLOG-RT0",
    }


def test_index_rejects_duplicate_pending_target_ids() -> None:
    raw = json.loads(_INDEX.read_text(encoding="utf-8"))
    raw["pending_targets"].append(dict(raw["pending_targets"][0]))

    with pytest.raises(ValidationError, match="pending qualification target identifiers"):
        QualificationIndex.model_validate_json(json.dumps(raw))


def test_positive_claim_requires_valid_eligible_independent_verification() -> None:
    raw = _fixture_claim_payload()
    raw["verification"] = dict(raw["verification"])
    raw["verification"]["outcome"] = "invalid"
    raw["verification"]["eligible_for_claimed_disposition"] = False

    with pytest.raises(ValidationError, match="valid HQP-2 verification"):
        QualificationClaim.model_validate_json(json.dumps(raw))


def test_superseded_claim_cannot_remain_active() -> None:
    raw = _fixture_claim_payload()
    raw["disposition"] = "superseded"
    raw["supersession"] = {
        "superseded_by_claim_id": "replacement-002",
        "effective_at": "2026-09-14T00:00:00Z",
        "reason": "Replacement conformance record.",
    }

    with pytest.raises(ValidationError, match="cannot remain active"):
        QualificationClaim.model_validate_json(json.dumps(raw))


def test_fixture_claim_cross_checks_against_hqp1_and_hqp2() -> None:
    claim = QualificationClaim.model_validate_json(json.dumps(_fixture_claim_payload()))
    report = HardwareQualificationReport.model_validate_json(
        (_VALID / "report.json").read_bytes()
    )
    verification = _verification()

    validate_claim_against_evidence(claim, report, verification)


def test_cross_check_rejects_mutated_build_commit() -> None:
    raw = _fixture_claim_payload()
    raw["build"] = dict(raw["build"])
    raw["build"]["commit_sha"] = "b" * 40
    claim = QualificationClaim.model_validate_json(json.dumps(raw))
    report = HardwareQualificationReport.model_validate_json(
        (_VALID / "report.json").read_bytes()
    )

    with pytest.raises(ValueError, match="build commit"):
        validate_claim_against_evidence(claim, report, _verification())
