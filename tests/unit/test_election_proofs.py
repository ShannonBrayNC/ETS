import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.election import (
    ElectionInclusionProofBundle,
    ElectionRootManifest,
    create_election_batch_proof,
    create_election_inclusion_proof,
    create_election_root_manifest,
    export_election_proof_report,
    export_root_manifest_audit_summary,
    verify_election_batch_bundle,
    verify_election_inclusion_bundle,
)
from ets.election.demo import build_sample_ledger, run_proof_demo
from ets.verifier.cli import main

GENERATED_AT = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)


def test_root_manifest_is_deterministic_for_same_ledger() -> None:
    entries = build_sample_ledger().list_entries()

    left = create_election_root_manifest(
        entries,
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )
    right = create_election_root_manifest(
        entries,
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )

    assert left == right
    assert left.tree_size == 3
    assert left.event_ids == ["elx_evt_0001", "elx_evt_0002", "elx_evt_0003"]


def test_root_manifest_requires_event_ids_to_match_tree_size() -> None:
    with pytest.raises(ValidationError):
        ElectionRootManifest(
            election_id="mock-election-2026",
            jurisdiction="Fictional County",
            milestone="pre_election",
            tree_size=2,
            merkle_root="a" * 64,
            event_ids=["elx_evt_0001"],
            generated_at_utc=GENERATED_AT,
        )


def test_inclusion_proof_bundle_verifies_without_sealed_payload() -> None:
    entries = build_sample_ledger().list_entries()
    bundle = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )

    result = verify_election_inclusion_bundle(bundle)

    assert result.valid is True
    assert result.reason == "ok"
    assert bundle.payload_hash == "2" * 64
    assert "metadata" not in bundle.model_dump(mode="json")
    assert "signature" not in bundle.model_dump(mode="json")


def test_inclusion_proof_rejects_altered_leaf() -> None:
    entries = build_sample_ledger().list_entries()
    bundle = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )
    tampered = bundle.model_copy(update={"leaf_hash": "0" * 64}, deep=True)

    result = verify_election_inclusion_bundle(tampered)

    assert result.valid is False
    assert result.reason == "leaf hash does not match event hash"


def test_inclusion_proof_rejects_manifest_root_mismatch() -> None:
    entries = build_sample_ledger().list_entries()
    bundle = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )
    tampered_manifest = bundle.root_manifest.model_copy(update={"merkle_root": "0" * 64})
    tampered = bundle.model_copy(update={"root_manifest": tampered_manifest}, deep=True)

    result = verify_election_inclusion_bundle(tampered)

    assert result.valid is False
    assert result.reason == "manifest root does not match proof root"


def test_batch_proof_verifies_multiple_events() -> None:
    entries = build_sample_ledger().list_entries()
    batch = create_election_batch_proof(
        entries,
        ["elx_evt_0001", "elx_evt_0003"],
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )

    results = verify_election_batch_bundle(batch)

    assert [result.valid for result in results] == [True, True]
    assert batch.root_manifest.tree_size == 3
    assert [proof.event_id for proof in batch.proofs] == ["elx_evt_0001", "elx_evt_0003"]


def test_proof_report_is_human_and_machine_readable() -> None:
    entries = build_sample_ledger().list_entries()
    bundle = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )

    report = export_election_proof_report(bundle)

    assert report["event_id"] == "elx_evt_0002"
    assert report["milestone"] == "pre_election"
    assert report["valid"] is True
    assert report["merkle_root"] == bundle.root_manifest.merkle_root


def test_root_manifest_audit_summary_combines_manifest_and_audit_log() -> None:
    entries = build_sample_ledger().list_entries()

    summary = export_root_manifest_audit_summary(
        entries,
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )

    assert summary["root_manifest"]["tree_size"] == 3
    assert len(summary["audit_log"]) == 3


def test_proof_bundle_json_round_trips() -> None:
    entries = build_sample_ledger().list_entries()
    bundle = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )

    dumped = bundle.model_dump_json()

    assert ElectionInclusionProofBundle.model_validate_json(dumped) == bundle


def test_election_proof_cli_accepts_valid_bundle(tmp_path, capsys) -> None:
    entries = build_sample_ledger().list_entries()
    bundle = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    )
    proof_path = tmp_path / "election-proof.json"
    proof_path.write_text(bundle.model_dump_json(), encoding="utf-8")

    exit_code = main(["election-proof", str(proof_path)])

    assert exit_code == 0
    assert '"valid": true' in capsys.readouterr().out


def test_election_proof_cli_rejects_tampered_bundle(tmp_path, capsys) -> None:
    entries = build_sample_ledger().list_entries()
    bundle = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=GENERATED_AT,
    ).model_copy(update={"leaf_hash": "0" * 64}, deep=True)
    proof_path = tmp_path / "election-proof.json"
    proof_path.write_text(bundle.model_dump_json(), encoding="utf-8")

    exit_code = main(["election-proof", str(proof_path)])

    assert exit_code == 1
    assert "leaf hash does not match event hash" in capsys.readouterr().out


def test_run_proof_demo_reports_valid_and_tampered_outcomes() -> None:
    result = run_proof_demo()

    assert result["valid_proof"] is True
    assert result["tampered_proof"] is False
    assert result["tampered_reason"] == "leaf hash does not match event hash"
    json.dumps(result)
