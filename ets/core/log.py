"""Append-only evidence event log contracts and in-memory implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ets.core.canonical_json import canonical_sha256
from ets.core.merkle import leaf_hash_for_event_hash
from ets.core.models import EvidenceEvent


class DuplicateEventError(ValueError):
    """Raised when an event ID is appended more than once."""


class EventNotFoundError(LookupError):
    """Raised when a log entry cannot be found."""


@dataclass(frozen=True)
class LogEntry:
    log_index: int
    event: EvidenceEvent
    event_hash: str
    leaf_hash: str


class AppendOnlyLog(Protocol):
    def append(self, event: EvidenceEvent) -> LogEntry:
        """Append an event and return its immutable log entry."""

    def get_by_index(self, index: int) -> LogEntry:
        """Return an entry by monotonic zero-based log index."""

    def get_by_event_id(self, event_id: str) -> LogEntry:
        """Return an entry by event ID."""

    def list_entries(self) -> list[LogEntry]:
        """Return all entries in index order."""


class InMemoryAppendOnlyLog:
    """Append-only in-memory log for tests and local demos."""

    provider_name = "in_memory"

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []
        self._event_id_index: dict[str, LogEntry] = {}

    def append(self, event: EvidenceEvent) -> LogEntry:
        if event.event_id in self._event_id_index:
            raise DuplicateEventError(f"event_id already exists: {event.event_id}")

        event_hash = canonical_sha256(event.hashable_payload())
        entry = LogEntry(
            log_index=len(self._entries),
            event=event,
            event_hash=event_hash,
            leaf_hash=leaf_hash_for_event_hash(event_hash),
        )
        self._entries.append(entry)
        self._event_id_index[event.event_id] = entry
        return entry

    def get_by_index(self, index: int) -> LogEntry:
        try:
            return self._entries[index]
        except IndexError as ex:
            raise EventNotFoundError(f"log index not found: {index}") from ex

    def get_by_event_id(self, event_id: str) -> LogEntry:
        try:
            return self._event_id_index[event_id]
        except KeyError as ex:
            raise EventNotFoundError(f"event_id not found: {event_id}") from ex

    def list_entries(self) -> list[LogEntry]:
        return list(self._entries)
