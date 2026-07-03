"""Durable artifact registry reconstruction helpers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC

from ets.core.artifacts import ArtifactRecord, create_artifact_record
from ets.core.log import LogEntry


class ArtifactRegistryError(ValueError):
    """Raised when persisted artifact metadata cannot be reconstructed safely."""


def artifact_record_from_log_entry(entry: LogEntry) -> ArtifactRecord | None:
    """Reconstruct an artifact record from a persisted log entry.

    Raw artifact bytes are intentionally not stored in the event log. The registry is rebuilt
    from event metadata, content hash, event id, and log index.
    """

    event = entry.event
    if event.event_type != "evidence.registered":
        return None

    metadata = event.metadata
    artifact_id = metadata.get("artifact_id")
    content_type = metadata.get("content_type")
    byte_size = metadata.get("byte_size")
    artifact_metadata = metadata.get("metadata", {})

    if not isinstance(artifact_id, str) or not artifact_id:
        raise ArtifactRegistryError("artifact registration event is missing artifact_id")
    if not isinstance(content_type, str) or not content_type:
        raise ArtifactRegistryError("artifact registration event is missing content_type")
    if not isinstance(byte_size, int) or byte_size < 0:
        raise ArtifactRegistryError("artifact registration event has invalid byte_size")
    if not isinstance(artifact_metadata, dict):
        raise ArtifactRegistryError("artifact registration event has invalid metadata")

    reference_uri = None
    if event.external_refs is not None:
        raw_reference_uri = event.external_refs.get("reference_uri")
        if raw_reference_uri is not None and not isinstance(raw_reference_uri, str):
            raise ArtifactRegistryError("artifact registration event has invalid reference_uri")
        reference_uri = raw_reference_uri

    return create_artifact_record(
        artifact_id=artifact_id,
        artifact_hash=event.content_hash,
        reference_uri=reference_uri or event.subject_ref or f"ets://artifact/{artifact_id}",
        content_type=content_type,
        byte_size=byte_size,
        metadata=artifact_metadata,
        ingestion_timestamp_utc=event.created_at_utc.astimezone(UTC),
        event_id=entry.event.event_id,
        log_index=entry.log_index,
    )


def load_artifact_registry(entries: Iterable[LogEntry]) -> dict[str, ArtifactRecord]:
    """Build an artifact registry from persisted log entries."""

    records: dict[str, ArtifactRecord] = {}
    for entry in entries:
        record = artifact_record_from_log_entry(entry)
        if record is None:
            continue
        if record.artifact_id in records:
            raise ArtifactRegistryError(f"duplicate artifact_id in event log: {record.artifact_id}")
        records[record.artifact_id] = record
    return records
