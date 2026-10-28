"""Smoke the shipped SDK example through real core and strict CLI code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ets.core.bundle import EvidenceProofBundle
from ets.verifier.service import TreeHeadTrustStore, verify_offline_bundle
from examples.sdk.python.offline_roundtrip import RECIPES, create_example, verify_exports


@pytest.mark.parametrize("industry", sorted(RECIPES))
def test_offline_example_strict_roundtrip_and_failure_reports(
    tmp_path: Path, industry: str
) -> None:
    output = tmp_path / "sample with spaces"
    summary = create_example(output, deterministic_smoke=True, industry=industry)
    assert summary["synthetic_only"] and summary["public_test_key"]
    assert summary["private_key_saved"] is False
    assert verify_exports(output) == {
        "signed": "valid",
        "tampered": "invalid",
        "missing-trust": "indeterminate",
    }
    event = json.loads((output / "event.json").read_text())
    assert (
        event["content_hash"]
        == hashlib.sha256((output / "synthetic-artifact.txt").read_bytes()).hexdigest()
    )
    report = json.loads((output / "signed-report.json").read_text())
    assert report["outcome"]["standing_status"] == "checkpoint_only"
    assert report["outcome"]["continuity_verified"] is False
    assert not any("private" in p.name for p in output.iterdir())


def test_smoke_artifacts_are_deterministic_except_fresh_reports(tmp_path: Path) -> None:
    left, right = tmp_path / "one", tmp_path / "two"
    create_example(left, deterministic_smoke=True)
    create_example(right, deterministic_smoke=True)
    assert {p.name: p.read_bytes() for p in left.iterdir()} == {
        p.name: p.read_bytes() for p in right.iterdir()
    }


def test_normal_example_uses_fresh_ephemeral_sample_key(tmp_path: Path) -> None:
    left, right = tmp_path / "one", tmp_path / "two"
    create_example(left)
    create_example(right)
    assert (left / "sample-trust.json").read_bytes() != (right / "sample-trust.json").read_bytes()
    bundle = EvidenceProofBundle.model_validate_json((left / "bundle.json").read_text())
    wrong_trust = TreeHeadTrustStore.model_validate_json((right / "sample-trust.json").read_text())
    assert not verify_offline_bundle(bundle, trust_store=wrong_trust).valid


def test_example_refuses_existing_directory_and_protects_files(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    protected = output / "bundle.json"
    protected.write_text("keep")
    with pytest.raises(FileExistsError):
        create_example(output)
    assert protected.read_text() == "keep"
