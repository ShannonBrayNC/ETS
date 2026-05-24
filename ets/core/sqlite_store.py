"""SQLite-backed ETS event store."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from pydantic import ValidationError

from ets.core.canonical_json import canonical_sha256
from ets.core.log import DuplicateEventError, EventNotFoundError, LogEntry
from ets.core.merkle import leaf_hash_for_event_hash
from ets.core.models import EvidenceEvent
from ets.core.storage import StorageValidationError

SCHEMA_VERSION = 1


class SQLiteEventStore:
    """Append-only SQLite store for local durable ETS metadata."""

    provider_name = "sqlite"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def append(self, event: EvidenceEvent) -> LogEntry:
        event_json = event.model_dump_json()
        event_hash = canonical_sha256(event.hashable_payload())
        leaf_hash = leaf_hash_for_event_hash(event_hash)
        created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with self._lock:
            try:
                cursor = self._connection.execute(
                    """
                    INSERT INTO events (
                        event_id, event_json, event_hash, leaf_hash, created_at_utc
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (event.event_id, event_json, event_hash, leaf_hash, created_at),
                )
                self._connection.commit()
            except sqlite3.IntegrityError as exc:
                raise DuplicateEventError(f"event_id already exists: {event.event_id}") from exc

        row_id = cursor.lastrowid
        if row_id is None:
            raise StorageValidationError("SQLite append did not return a row id")

        return LogEntry(
            log_index=int(row_id) - 1,
            event=event,
            event_hash=event_hash,
            leaf_hash=leaf_hash,
        )

    def get_by_index(self, index: int) -> LogEntry:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT log_index, event_json, event_hash, leaf_hash
                FROM events
                WHERE log_index = ?
                """,
                (index + 1,),
            ).fetchone()
        if row is None:
            raise EventNotFoundError(f"log index not found: {index}")
        return self._row_to_entry(row)

    def get_by_event_id(self, event_id: str) -> LogEntry:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT log_index, event_json, event_hash, leaf_hash
                FROM events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
        if row is None:
            raise EventNotFoundError(f"event_id not found: {event_id}")
        return self._row_to_entry(row)

    def list_entries(self) -> list[LogEntry]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT log_index, event_json, event_hash, leaf_hash
                FROM events
                ORDER BY log_index ASC
                """
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def schema_version(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT version FROM schema_version WHERE id = 1"
            ).fetchone()
        if row is None:
            raise StorageValidationError("schema version is missing")
        return int(row["version"])

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    log_index INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    event_json TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    leaf_hash TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );
                """
            )
            self._connection.execute(
                """
                INSERT INTO schema_version (id, version)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET version = excluded.version
                """,
                (SCHEMA_VERSION,),
            )
            self._connection.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> LogEntry:
        try:
            event = EvidenceEvent.model_validate_json(str(row["event_json"]))
        except ValidationError as exc:
            raise StorageValidationError("stored event JSON failed validation") from exc

        event_hash = canonical_sha256(event.hashable_payload())
        leaf_hash = leaf_hash_for_event_hash(event_hash)
        if event_hash != row["event_hash"] or leaf_hash != row["leaf_hash"]:
            raise StorageValidationError("stored event hashes do not match event JSON")

        return LogEntry(
            log_index=int(row["log_index"]) - 1,
            event=event,
            event_hash=str(row["event_hash"]),
            leaf_hash=str(row["leaf_hash"]),
        )
