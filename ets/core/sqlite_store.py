"""SQLite-backed ETS event and artifact metadata store."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from pydantic import ValidationError

from ets.core.artifacts import ArtifactRecord, create_artifact_record
from ets.core.canonical_json import canonical_sha256
from ets.core.log import DuplicateEventError, EventNotFoundError, LogEntry
from ets.core.merkle import leaf_hash_for_event_hash
from ets.core.models import EvidenceEvent
from ets.core.storage import StorageValidationError

SCHEMA_VERSION = 2


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

    def save_artifact_record(self, record: ArtifactRecord) -> None:
        """Persist artifact metadata without storing raw artifact bytes."""

        metadata_json = json.dumps(record.metadata, sort_keys=True, separators=(",", ":"))
        timestamp = record.ingestion_timestamp_utc.astimezone(UTC).isoformat().replace(
            "+00:00", "Z"
        )
        with self._lock:
            try:
                self._connection.execute(
                    """
                    INSERT INTO artifact_records (
                        artifact_id,
                        artifact_hash,
                        reference_uri,
                        content_type,
                        byte_size,
                        metadata_json,
                        ingestion_timestamp_utc,
                        event_id,
                        log_index
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.artifact_id,
                        record.artifact_hash,
                        record.reference_uri,
                        record.content_type,
                        record.byte_size,
                        metadata_json,
                        timestamp,
                        record.event_id,
                        record.log_index,
                    ),
                )
                self._connection.commit()
            except sqlite3.IntegrityError as exc:
                raise DuplicateEventError(
                    f"artifact_id already exists: {record.artifact_id}"
                ) from exc

    def get_artifact_record(self, artifact_id: str) -> ArtifactRecord:
        """Read one artifact metadata record and fail closed on corruption."""

        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    artifact_id,
                    artifact_hash,
                    reference_uri,
                    content_type,
                    byte_size,
                    metadata_json,
                    ingestion_timestamp_utc,
                    event_id,
                    log_index
                FROM artifact_records
                WHERE artifact_id = ?
                """,
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise EventNotFoundError(f"artifact_id not found: {artifact_id}")
        return self._row_to_artifact_record(row)

    def list_artifact_records(self) -> list[ArtifactRecord]:
        """Return persisted artifact metadata in append order."""

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT
                    artifact_id,
                    artifact_hash,
                    reference_uri,
                    content_type,
                    byte_size,
                    metadata_json,
                    ingestion_timestamp_utc,
                    event_id,
                    log_index
                FROM artifact_records
                ORDER BY log_index ASC, artifact_id ASC
                """
            ).fetchall()
        return [self._row_to_artifact_record(row) for row in rows]

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

                CREATE TABLE IF NOT EXISTS artifact_records (
                    artifact_id TEXT PRIMARY KEY,
                    artifact_hash TEXT NOT NULL,
                    reference_uri TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
                    metadata_json TEXT NOT NULL,
                    ingestion_timestamp_utc TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    log_index INTEGER NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(event_id)
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

    def _row_to_artifact_record(self, row: sqlite3.Row) -> ArtifactRecord:
        try:
            metadata = json.loads(str(row["metadata_json"]))
        except json.JSONDecodeError as exc:
            raise StorageValidationError("stored artifact metadata failed JSON parsing") from exc
        if not isinstance(metadata, dict):
            raise StorageValidationError("stored artifact metadata must be a JSON object")

        timestamp = _parse_utc_timestamp(str(row["ingestion_timestamp_utc"]))
        return create_artifact_record(
            artifact_id=str(row["artifact_id"]),
            artifact_hash=str(row["artifact_hash"]),
            reference_uri=str(row["reference_uri"]),
            content_type=str(row["content_type"]),
            byte_size=int(row["byte_size"]),
            metadata=metadata,
            ingestion_timestamp_utc=timestamp,
            event_id=str(row["event_id"]),
            log_index=int(row["log_index"]),
        )


def _parse_utc_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StorageValidationError("stored timestamp failed datetime parsing") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StorageValidationError("stored timestamp must be timezone-aware")
    return parsed.astimezone(UTC)
