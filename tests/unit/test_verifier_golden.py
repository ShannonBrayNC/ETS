from __future__ import annotations

from datetime import UTC, datetime

from ets.core import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    generate_inclusion_proof,
)
from ets.reports import create_certificate
from ets.verifier import verify_bundle, verify_inclusion
from ets.verifier.cli import main


def _event(event_id: str = "evt_golden_001") -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_demo",
        workspace_id="workspace_alpha",
        evidence_id="evidence_golden_001",
        event_type="evidence.registered",
        subject_ref="case:golden-001",
        content_hash="b" * 64,
        content_hash_alg="sha256",
        metadata={"case": "golden", "sequence": 1},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
        source_system="ets-fixture",
    )


def _golden_bundle() -> EvidenceProofBundle:
    log = InMemoryAppendOnlyLog()
    entry = log.append(_event())
    proof = generate_inclusion_proof(log.list_entries(), 0)
    result = verify_inclusion(proof)
    return EvidenceProofBundle(
        event=entry.event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=SignedTreeHead(
            tree_size=1,
            root_hash=proof.root_hash,
            created_at_utc=datetime(2026, 5, 18, 12, 31, tzinfo=UTC),
            log_id="ets-local-dev",
        ),
        inclusion_proof=proof,
        verification_result=result,
    )


def test_golden_bundle_verifies_offline() -> None:
    bundle = _golden_bundle()

    result = verify_bundle(bundle.model_dump(mode="json"))

    assert result.valid is True
    assert result.reason == "ok"


def test_golden_bundle_cli_accepts_valid_bundle(tmp_path, capsys) -> None:
    bundle_path = tmp_path / "golden-bundle.json"
    bundle_path.write_text(_golden_bundle().model_dump_json(), encoding="utf-8")

    exit_code = main(["bundle", str(bundle_path)])

    assert exit_code == 0
    assert '"valid": true' in capsys.readouterr().out


def test_golden_bundle_cli_rejects_tampered_event_hash(tmp_path, capsys) -> None:
    bundle = _golden_bundle().model_copy(update={"event_hash": "0" * 64})
    bundle_path = tmp_path / "tampered-bundle.json"
    bundle_path.write_text(bundle.model_dump_json(), encoding="utf-8")

    exit_code = main(["bundle", str(bundle_path)])

    assert exit_code == 1
    assert '"valid": false' in capsys.readouterr().out


def test_golden_certificates_include_expected_status() -> None:
    bundle = _golden_bundle()

    json_certificate = create_certificate(bundle, "json")
    markdown_certificate = create_certificate(bundle, "markdown")
    html_certificate = create_certificate(bundle, "html")

    assert '"event_id": "evt_golden_001"' in json_certificate
    assert '"proof_valid": true' in json_certificate
    assert "# ETS Verification Certificate" in markdown_certificate
    assert "evt_golden_001" in markdown_certificate
    assert "ETS Verification Certificate" in html_certificate
    assert "evt_golden_001" in html_certificate
