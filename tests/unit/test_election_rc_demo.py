import json

from ets.election.rc_demo import (
    build_election_demo_payload,
    main,
    write_election_demo_artifacts,
)


def test_build_election_demo_payload_is_public_safe_and_verifiable() -> None:
    payload = build_election_demo_payload()

    assert payload["storyboard"] == [
        "Import fictional election setup package",
        "Register logic and accuracy evidence",
        "Register ballot batch custody transfers",
        "Generate milestone Merkle root",
        "Publish public proof",
        "Verify valid evidence packet",
        "Demonstrate tampered artifact rejection",
        "Export audit package",
    ]
    assert payload["root_manifest"]["tree_size"] == 3
    assert payload["root_manifest"]["generated_at_utc"] == "2026-05-04T12:00:00Z"
    assert payload["verification"]["valid"] is True
    assert payload["verification"]["reason"] == "ok"
    assert payload["chain_integrity"]["valid"] is True
    assert payload["tamper_demo"]["valid"] is False
    assert payload["tamper_demo"]["reason"] == "leaf hash does not match event hash"
    assert payload["privacy_boundary"]["stores_raw_ballots"] is False
    assert payload["privacy_boundary"]["stores_voter_records"] is False


def test_write_election_demo_artifacts_writes_expected_files(tmp_path) -> None:
    artifacts = write_election_demo_artifacts(tmp_path)

    for path in (
        artifacts.manifest_path,
        artifacts.audit_log_path,
        artifacts.proof_path,
        artifacts.verification_path,
        artifacts.tamper_path,
        artifacts.walkthrough_path,
    ):
        assert path.exists()

    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    proof = json.loads(artifacts.proof_path.read_text(encoding="utf-8"))
    verification = json.loads(artifacts.verification_path.read_text(encoding="utf-8"))
    tamper = json.loads(artifacts.tamper_path.read_text(encoding="utf-8"))
    walkthrough = artifacts.walkthrough_path.read_text(encoding="utf-8")

    assert manifest["merkle_root"] == proof["root_manifest"]["merkle_root"]
    assert verification["valid"] is True
    assert tamper["valid"] is False
    assert "Tamper Demonstration" in walkthrough
    assert "not voting or tabulation software" in walkthrough


def test_election_demo_main_writes_default_artifacts(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert exit_code == 0
    assert output["output_dir"] == "artifacts/election-rc-demo"
    assert (tmp_path / output["walkthrough"]).exists()
