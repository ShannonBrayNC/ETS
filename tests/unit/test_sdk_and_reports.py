from datetime import UTC, datetime

from ets.core import EvidenceProofBundle, InMemoryAppendOnlyLog, SignedTreeHead
from ets.reports import create_certificate
from ets.sdk import (
    append_evidence,
    create_evidence,
    get_inclusion_proof,
    hash_evidence,
    verify_evidence,
    verify_inclusion_proof,
)
from ets.verifier import verify_inclusion
from ets.verifier.cli import main


def make_event(event_id: str = "evt_sdk_001") -> dict[str, object]:
    return {
        "event_id": event_id,
        "tenant_id": "tenant_a",
        "workspace_id": "workspace_a",
        "evidence_id": f"evidence_{event_id}",
        "event_type": "evidence.registered",
        "subject_ref": None,
        "content_hash": "e" * 64,
        "content_hash_alg": "sha256",
        "metadata": {"case": "sdk"},
        "created_at_utc": datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    }


def test_sdk_local_facade_hash_append_and_verify_proof():
    store = InMemoryAppendOnlyLog()
    event = create_evidence(make_event())
    event_hash = hash_evidence(event)

    entry = append_evidence(store, event)
    proof = get_inclusion_proof(store, event.event_id)

    assert entry.event_hash == event_hash
    assert verify_evidence(event, event_hash).valid is True
    assert verify_inclusion_proof(proof).valid is True


def test_report_certificate_formats_do_not_include_raw_metadata_values():
    store = InMemoryAppendOnlyLog()
    entry = append_evidence(store, make_event())
    proof = get_inclusion_proof(store, entry.event.event_id)
    result = verify_inclusion(proof)
    bundle = EvidenceProofBundle(
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

    json_certificate = create_certificate(bundle, "json")
    markdown_certificate = create_certificate(bundle, "markdown")
    html_certificate = create_certificate(bundle, "html")

    assert '"event_id": "evt_sdk_001"' in json_certificate
    assert "# ETS Verification Certificate" in markdown_certificate
    assert "<html>" in html_certificate
    assert '"metadata"' not in json_certificate
    assert '"case"' not in json_certificate


def test_cli_certificate_writes_output_file(tmp_path):
    store = InMemoryAppendOnlyLog()
    entry = append_evidence(store, make_event())
    proof = get_inclusion_proof(store, entry.event.event_id)
    bundle = EvidenceProofBundle(
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
        verification_result=verify_inclusion(proof),
    )
    bundle_path = tmp_path / "bundle.json"
    out_path = tmp_path / "certificate.md"
    bundle_path.write_text(bundle.model_dump_json(), encoding="utf-8")

    exit_code = main(
        ["certificate", str(bundle_path), "--format", "markdown", "--out", str(out_path)]
    )

    assert exit_code == 0
    assert "ETS Verification Certificate" in out_path.read_text(encoding="utf-8")
