from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from ets.ranger.electromagnetic_actuation import trial_digest
from ets.ranger.vectorrail_consequence_custody_package import (
    build_vectorrail_consequence_custody_package,
    verify_vectorrail_consequence_custody_package,
)

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "validation/releases/vectorrail-vrx/v0.1.0"
SUBJECT_COMMIT = "a50720ab5ba451c6c97008da63b401fcaf28b34f"
PACKAGE_DIGEST = "sha256:ae2e40b9a272f077cbe139930d353e7610212b2b1877f51e9fb1a87691b312c0"
PACKAGE_FILE_SHA256 = "a87bffbbf613ccf079b3be5eea07bc3ec0cce68aeb16976f730a29150540372c"
EXPECTED_CHALLENGES = {
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


def _baseline_package_bytes() -> bytes:
    compressed = (BUNDLE / "baseline/vectorrail-vrx-baseline-portable-package.json.gz").read_bytes()
    return gzip.decompress(compressed)


def test_release_metadata_freezes_exact_subject_and_claim_boundary() -> None:
    release = _load(BUNDLE / "RELEASE.json")
    assert release["release_version"] == "0.1.0"
    assert release["subject_commit"] == SUBJECT_COMMIT
    assert release["canonical_package_digest"] == PACKAGE_DIGEST
    assert release["expected_package_conclusion"] == "VERIFIED_REPLAYABLE"
    assert release["expected_chain_conclusion"] == "VERIFIED_CONSISTENT"
    assert release["network_required"] is False
    assert release["truth_claim_supported"] is False
    assert "sensor correctness" in str(release["claim_boundary"])


def test_canonical_baseline_package_reproduces_frozen_builder_output() -> None:
    package_bytes = _baseline_package_bytes()
    assert hashlib.sha256(package_bytes).hexdigest() == PACKAGE_FILE_SHA256
    package = json.loads(package_bytes)
    assert isinstance(package, dict)
    assert package["package_digest"] == PACKAGE_DIGEST

    verification = verify_vectorrail_consequence_custody_package(package)
    assert verification.conclusion == "VERIFIED_REPLAYABLE"
    assert verification.chain_conclusion == "VERIFIED_CONSISTENT"
    assert verification.network_required is False
    assert verification.truth_claim_supported is False

    trial = _load(BUNDLE / "baseline/electromagnetic-actuation-baseline.json")
    acceptance = _load(BUNDLE / "baseline/vectorrail-vrx-acceptance-qualified.json")
    if trial.get("trial_digest") is None:
        trial["trial_digest"] = trial_digest(trial)
    rebuilt = build_vectorrail_consequence_custody_package(trial, acceptance)
    assert rebuilt == package


def test_challenge_manifest_and_blank_report_are_pinned() -> None:
    manifest = _load(BUNDLE / "manifests/vectorrail-vrx-clean-room-challenges.v0.1.json")
    challenges = manifest["challenges"]
    assert isinstance(challenges, list)
    observed = {
        item["challenge_id"]: item["expected_package_conclusion"]
        for item in challenges
        if isinstance(item, dict)
    }
    assert observed == EXPECTED_CHALLENGES

    template = _load(BUNDLE / "templates/independent-validation-report.template.json")
    subject = template["subject"]
    implementation = template["implementation"]
    assert isinstance(subject, dict)
    assert isinstance(implementation, dict)
    assert subject["source_commit"] == SUBJECT_COMMIT
    assert subject["package_digest"] == PACKAGE_DIGEST
    assert implementation["copied_reference_source"] is False


def test_reviewer_readme_keeps_independence_and_claim_boundaries_explicit() -> None:
    readme = (BUNDLE / "README.md").read_text(encoding="utf-8")
    assert SUBJECT_COMMIT in readme
    assert PACKAGE_DIGEST in readme
    assert "does **not** constitute independent validation" in readme
    assert "sensor correctness" in readme
    assert "independent-human approval gate" in readme


def test_sha256_inventory_covers_every_distributed_payload() -> None:
    payload_files = sorted(
        path
        for path in BUNDLE.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    )
    expected = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(BUNDLE).as_posix()}\n"
        for path in payload_files
    )
    actual = (BUNDLE / "SHA256SUMS").read_text(encoding="utf-8")
    assert actual == expected, f"SHA256SUMS mismatch; replace with:\n{expected}"
