from datetime import UTC, datetime

from ets.core.api import (
    EvidenceEvent,
    EvidenceProofBundle,
    InMemoryAppendOnlyLog,
    SignedTreeHead,
    generate_inclusion_proof,
    merkle_root,
    verify_inclusion_proof,
)


def test_public_facade_supports_edge_runtime_proof_bundle() -> None:
    event = EvidenceEvent(
        event_id="event-001",
        tenant_id="tenant-001",
        workspace_id="workspace-001",
        evidence_id="evidence-001",
        event_type="capture",
        subject_ref=None,
        content_hash="0" * 64,
        content_hash_alg="sha256",
        metadata={},
        created_at_utc=datetime(2026, 8, 3, tzinfo=UTC),
    )
    log = InMemoryAppendOnlyLog()
    entry = log.append(event)
    entries = log.list_entries()
    proof = generate_inclusion_proof(entries, entry.log_index)
    result = verify_inclusion_proof(proof)
    tree_head = SignedTreeHead(
        tree_size=len(entries),
        root_hash=merkle_root([item.leaf_hash for item in entries]),
        created_at_utc=datetime(2026, 8, 3, tzinfo=UTC),
        log_id="edge-test",
    )

    bundle = EvidenceProofBundle(
        event=event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=tree_head,
        inclusion_proof=proof,
        verification_result=result,
    )

    assert bundle.verification_result.valid is True
    assert bundle.inclusion_proof.root_hash == bundle.tree_head.root_hash
