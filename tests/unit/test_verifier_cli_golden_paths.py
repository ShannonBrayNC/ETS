from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "verifier"
CLI = [sys.executable, "-m", "ets.verifier.cli"]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*CLI, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(result.stdout)


def test_ets_verify_version_uses_installed_cli_entrypoint() -> None:
    result = _run("--version")

    assert result.returncode == 0
    assert result.stdout.startswith("ets-verify ")


def test_event_hash_fixture_computes_and_verifies_expected_hash() -> None:
    event_path = FIXTURES / "event.json"
    result = _run("event-hash", str(event_path))

    assert result.returncode == 0
    event_hash = _json_stdout(result)["event_hash"]
    assert isinstance(event_hash, str)
    assert len(event_hash) == 64

    verify_result = _run("event-hash", str(event_path), "--expected", event_hash)

    assert verify_result.returncode == 0
    payload = _json_stdout(verify_result)
    assert payload["valid"] is True
    assert payload["reason"] == "ok"


def test_inclusion_proof_fixture_verifies_with_primary_and_alias_commands() -> None:
    proof_path = FIXTURES / "inclusion-proof.json"

    for command in ["inclusion-proof", "verify-proof"]:
        result = _run(command, str(proof_path))

        assert result.returncode == 0
        payload = _json_stdout(result)
        assert payload["valid"] is True
        assert payload["reason"] == "ok"


def test_consistency_proof_fixture_verifies() -> None:
    result = _run("consistency-proof", str(FIXTURES / "consistency-proof.json"))

    assert result.returncode == 0
    payload = _json_stdout(result)
    assert payload["valid"] is True
    assert payload["reason"] == "ok"


def test_bundle_fixture_verifies_and_certificate_renders_boundaries(tmp_path: Path) -> None:
    bundle_path = FIXTURES / "bundle.json"
    bundle_result = _run("bundle", str(bundle_path))

    assert bundle_result.returncode == 0
    assert _json_stdout(bundle_result)["valid"] is True

    certificate_result = _run("certificate", str(bundle_path), "--format", "markdown")

    assert certificate_result.returncode == 0
    assert "# ETS Verification Certificate" in certificate_result.stdout
    assert "## What This Verifies" in certificate_result.stdout
    assert "## What This Does Not Verify" in certificate_result.stdout

    certificate_path = tmp_path / "certificate.json"
    out_result = _run(
        "certificate",
        str(bundle_path),
        "--format",
        "json",
        "--out",
        str(certificate_path),
    )

    assert out_result.returncode == 0
    assert out_result.stdout == ""
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    assert certificate["event_id"] == "evt_cli_golden_001"
    assert certificate["proof_valid"] is True
    assert certificate["what_this_verifies"]
    assert certificate["what_this_does_not_verify"]


def test_tree_head_fixtures_compare_as_append_only_growth() -> None:
    result = _run(
        "tree-head",
        str(FIXTURES / "tree-head-previous.json"),
        str(FIXTURES / "tree-head-latest.json"),
    )

    assert result.returncode == 0
    payload = _json_stdout(result)
    assert payload["valid"] is True
    assert payload["reason"] == "tree size advanced"


def test_election_proof_fixture_verifies_without_election_correctness_claim() -> None:
    result = _run("election-proof", str(FIXTURES / "election-proof.json"))

    assert result.returncode == 0
    payload = _json_stdout(result)
    assert payload["valid"] is True
    assert payload["reason"] == "ok"


def test_tampered_bundle_fixture_copy_fails_as_expected(tmp_path: Path) -> None:
    bundle = json.loads((FIXTURES / "bundle.json").read_text(encoding="utf-8"))
    bundle["event_hash"] = "0" * 64
    tampered_path = tmp_path / "tampered-bundle.json"
    tampered_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")

    result = _run("bundle", str(tampered_path))

    assert result.returncode == 1
    payload = _json_stdout(result)
    assert payload["valid"] is False
    assert payload["reason"] == "bundle event hash does not match event"


def test_cli_docs_reference_every_static_fixture() -> None:
    docs = (ROOT / "docs" / "verifier" / "GOLDEN_PATHS.md").read_text(encoding="utf-8")
    fixture_names = {
        path.name for path in FIXTURES.glob("*.json") if path.name != "tampered-bundle.json"
    }

    assert fixture_names == {
        "event.json",
        "inclusion-proof.json",
        "consistency-proof.json",
        "bundle.json",
        "tree-head-previous.json",
        "tree-head-latest.json",
        "election-proof.json",
    }
    for name in fixture_names:
        assert f"tests/fixtures/verifier/{name}" in docs
