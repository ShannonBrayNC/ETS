from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ets.core.artifact_registry import (
    ArtifactRegistryError,
    DurableArtifactRegistry,
    load_artifact_registry,
)
from ets.core.artifacts import ArtifactRecord, create_artifact_record
from ets.core.log import InMemoryAppendOnlyLog
from ets.core.models import EvidenceEvent


def artifact_event(
    artifact_id: str = "artifact-001",
    *,
    metadata: dict[str, object] | None = None,
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=f"artifact_registered:{artifact_id}",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        evidence_id=artifact_id,
        event_type="evidence.registered",
        subject_ref=f"ets://artifact/{artifact_id}",
        content_hash="a" * 64,
        content_hash_alg="sha256",
        metadata=metadata
        or {
            "artifact_id": artifact_id,
            "content_type": "text/plain",
            "byte_size": 12,
            "metadata": {"case": "alpha"},
        },
        created_at_utc=datetime(2026, 7, 3, 4, 0, tzinfo=UTC),
        external_refs={"reference_uri": f"ets://artifact/{artifact_id}"},
    )


def test_load_artifact_registry_rebuilds_records_without_raw_bytes() -> None:
    log = InMemoryAppendOnlyLog()
    log.append(artifact_event())

    registry = load_artifact_registry(log.list_entries())

    record = registry["artifact-001"]
    assert record.artifact_hash == "a" * 64
    assert record.reference_uri == "ets://artifact/artifact-001"
    assert record.byte_size == 12
    assert "artifact_base64" not in record.metadata


def test_load_artifact_registry_rejects_corrupt_metadata() -> None:
    log = InMemoryAppendOnlyLog()
    log.append(artifact_event(metadata={"artifact_id": "artifact-001", "byte_size": 12}))

    with pytest.raises(ArtifactRegistryError, match="content_type"):
        load_artifact_registry(log.list_entries())


def test_load_artifact_registry_rejects_duplicate_artifacts() -> None:
    first_log = InMemoryAppendOnlyLog()
    first = first_log.append(artifact_event("artifact-001"))
    second_log = InMemoryAppendOnlyLog()
    second = second_log.append(artifact_event("artifact-001"))

    with pytest.raises(ArtifactRegistryError, match="duplicate artifact_id"):
        load_artifact_registry([first, second])


def test_registry_recovers_replica_cache_miss_from_canonical_event() -> None:
    log = InMemoryAppendOnlyLog()
    stale_replica = DurableArtifactRegistry({}, log)
    entry = log.append(artifact_event())

    assert "artifact-001" in stale_replica
    assert stale_replica["artifact-001"].event_id == entry.event.event_id
    assert stale_replica["artifact-001"].log_index == entry.log_index


def test_projection_failure_does_not_hide_committed_registration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class ProjectionFailureLog(InMemoryAppendOnlyLog):
        def save_artifact_record(self, record: ArtifactRecord) -> None:
            raise RuntimeError("simulated projection failure")

    log = ProjectionFailureLog()
    entry = log.append(artifact_event())
    registry = DurableArtifactRegistry({}, log)
    record = create_artifact_record(
        artifact_id="artifact-001",
        artifact_hash=entry.event.content_hash,
        reference_uri="ets://artifact/artifact-001",
        content_type="text/plain",
        byte_size=12,
        metadata={"case": "alpha"},
        ingestion_timestamp_utc=entry.event.created_at_utc,
        event_id=entry.event.event_id,
        log_index=entry.log_index,
    )

    registry[record.artifact_id] = record

    assert registry[record.artifact_id] == record
    assert "projection failed after canonical event commit" in caplog.text
