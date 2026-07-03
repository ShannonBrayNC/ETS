"""Durable artifact registry reconstruction helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC
from typing import Any, Protocol, TypeGuard

from ets.core.artifacts import ArtifactRecord, create_artifact_record
from ets.core.log import LogEntry


class ArtifactRegistryError(ValueError):
    """Raised when persisted artifact metadata cannot be reconstructed safely."""


class ArtifactRecordStore(Protocol):
    """Storage contract for artifact metadata persistence."""

    def save_artifact_record(self, record: ArtifactRecord) -> None:
        """Persist one artifact metadata record."""


class DurableArtifactRegistry(dict[str, ArtifactRecord]):
    """Dict-compatible registry that persists new artifact records when supported."""

    def __init__(self, records: dict[str, ArtifactRecord], store: object) -> None:
        super().__init__(records)
        self._store = store

    def __setitem__(self, artifact_id: str, record: ArtifactRecord) -> None:
        if _supports_artifact_record_persistence(self._store):
            self._store.save_artifact_record(record)
        super().__setitem__(artifact_id, record)


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


def install_fastapi_artifact_registry_hook() -> None:
    """Hydrate FastAPI app state artifact registries from durable event stores.

    ``ets.api.app.create_app`` still assigns ``app.state.artifact_records`` as a
    dict for in-memory mode. This hook keeps that public state contract intact while
    replacing the empty dict with a durable, dict-compatible registry when the app
    was created with a store that can list events and persist artifact metadata.
    """

    try:
        from starlette.datastructures import State
    except ImportError:
        return

    if getattr(State, "_ets_artifact_registry_hook_installed", False):
        return

    original_setattr: Callable[[Any, str, Any], None] = State.__setattr__

    def ets_setattr(self: Any, key: str, value: Any) -> None:
        if key == "artifact_records" and value == {}:
            event_log = getattr(self, "event_log", None)
            if _supports_event_listing(event_log):
                value = DurableArtifactRegistry(
                    load_artifact_registry(event_log.list_entries()),
                    event_log,
                )
        original_setattr(self, key, value)

    State.__setattr__ = ets_setattr  # type: ignore[method-assign]
    setattr(State, "_ets_artifact_registry_hook_installed", True)


def _supports_artifact_record_persistence(value: object) -> TypeGuard[ArtifactRecordStore]:
    return callable(getattr(value, "save_artifact_record", None))


def _supports_event_listing(value: object) -> TypeGuard[Any]:
    return callable(getattr(value, "list_entries", None))


install_fastapi_artifact_registry_hook()
