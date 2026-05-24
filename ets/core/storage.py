"""Storage contracts shared by ETS append-only log providers."""

from __future__ import annotations

from typing import Protocol

from ets.core.log import LogEntry
from ets.core.models import EvidenceEvent


class StorageValidationError(ValueError):
    """Raised when persisted event data fails ETS validation."""


class EventStore(Protocol):
    provider_name: str

    def append(self, event: EvidenceEvent) -> LogEntry:
        """Append an event and return its immutable log entry."""

    def get_by_index(self, index: int) -> LogEntry:
        """Return an entry by monotonic zero-based log index."""

    def get_by_event_id(self, event_id: str) -> LogEntry:
        """Return an entry by event ID."""

    def list_entries(self) -> list[LogEntry]:
        """Return all entries in index order."""
