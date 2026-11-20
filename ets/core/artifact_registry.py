"""Durable artifact registry reconstruction helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC
from typing import Any, Protocol, TypeGuard, cast

from ets.core.artifacts import ArtifactRecord, build_artifact_event_id, create_artifact_record
from ets.core.log import EventNotFoundError, LogEntry

logger = logging.getLogger(__name__)


class ArtifactRegistryError(ValueError):
    """Raised when persisted artifact metadata cannot be reconstructed safely."""


class ArtifactRecordStore(Protocol):
    """Storage contract for artifact metadata persistence."""

    def save_artifact_record(self, record: ArtifactRecord) -> None:
        """Persist one artifact metadata record."""


class EventListingStore(Protocol):
    """Storage contract for rebuilding artifact metadata from log entries."""

    def list_entries(self) -> list[LogEntry]:
        """Return all log entries in index order."""


class EventLookupStore(Protocol):
    """Storage contract for recovering one artifact from its canonical event."""

    def get_by_event_id(self, event_id: str) -> LogEntry:
        """Return one log entry by its deterministic event identifier."""


class DurableArtifactRegistry(dict[str, ArtifactRecord]):
    """Replica-local artifact cache backed by canonical registration events.

    The append-only event is the registration commit. The optional artifact-record table is a
    convenience projection, so a projection failure must not hide or roll back an event that has
    already committed. Cache misses are recovered by deterministic event ID so replicas started
    before another replica's registration do not remain stale.
    """

    def __init__(self, records: dict[str, ArtifactRecord], store: object) -> None:
        super().__init__(records)
        self._store = store

    def __setitem__(self, artifact_id: str, record: ArtifactRecord) -> None:
        if artifact_id != record.artifact_id:
            raise ArtifactRegistryError("artifact registry key does not match record")
        super().__setitem__(artifact_id, record)
        if _supports_artifact_record_persistence(self._store):
            try:
                self._store.save_artifact_record(record)
            except Exception:
                logger.warning(
                    "artifact record projection failed after canonical event commit: %s",
                    record.event_id,
                    exc_info=True,
                )

    def __contains__(self, artifact_id: object) -> bool:
        if dict.__contains__(self, artifact_id):
            return True
        if not isinstance(artifact_id, str):
            return False
        return self._recover(artifact_id) is not None

    def __getitem__(self, artifact_id: str) -> ArtifactRecord:
        try:
            return dict.__getitem__(self, artifact_id)
        except KeyError:
            record = self._recover(artifact_id)
            if record is None:
                raise
            return record

    def _recover(self, artifact_id: str) -> ArtifactRecord | None:
        if not _supports_event_lookup(self._store):
            return None
        try:
            entry = self._store.get_by_event_id(build_artifact_event_id(artifact_id))
        except EventNotFoundError:
            return None
        record = artifact_record_from_log_entry(entry)
        if record is None:
            raise ArtifactRegistryError("artifact event ID does not identify a registration")
        if record.artifact_id != artifact_id:
            raise ArtifactRegistryError("artifact event does not match requested artifact_id")
        dict.__setitem__(self, artifact_id, record)
        return record


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
    if artifact_id is None and not event.event_id.startswith("artifact_registered:"):
        return None

    content_type = metadata.get("content_type")
    byte_size = metadata.get("byte_size")
    artifact_metadata = metadata.get("metadata", {})

    if not isinstance(artifact_id, str) or not artifact_id:
        raise ArtifactRegistryError("artifact registration event is missing artifact_id")
    if event.event_id != build_artifact_event_id(artifact_id):
        raise ArtifactRegistryError("artifact registration event_id does not match artifact_id")
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



def _supports_artifact_record_persistence(value: object) -> TypeGuard[ArtifactRecordStore]:
    if not hasattr(value, "save_artifact_record"):
        return False
    return callable(cast(Any, value).save_artifact_record)


def _supports_event_listing(value: object) -> TypeGuard[EventListingStore]:
    if not hasattr(value, "list_entries"):
        return False
    return callable(cast(Any, value).list_entries)


def _supports_event_lookup(value: object) -> TypeGuard[EventLookupStore]:
    if not hasattr(value, "get_by_event_id"):
        return False
    return callable(cast(Any, value).get_by_event_id)


