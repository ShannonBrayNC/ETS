"""Durable bounded synchronization queue shared by ETS product runtimes."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class SyncState(StrEnum):
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    SYNCHRONIZED = "synchronized"
    RETRYABLE_FAILURE = "retryable_failure"
    TERMINAL_FAILURE = "terminal_failure"


class QueueCapacityError(RuntimeError):
    """Raised when bounded queue capacity would be exceeded."""


class SyncConflictError(RuntimeError):
    """Raised when an idempotency key maps to conflicting immutable state."""


@dataclass(frozen=True)
class SyncRecord:
    idempotency_key: str
    event_id: str
    event_hash: str
    tenant_id: str
    workspace_id: str
    payload: dict[str, Any]
    payload_bytes: int
    state: SyncState
    attempts: int
    created_at_utc: str
    updated_at_utc: str
    last_error: str | None
    acknowledgement_hash: str | None
    synchronized_at_utc: str | None


@dataclass(frozen=True)
class SyncQueueStatus:
    queue_depth: int
    queue_bytes: int
    pending: int
    in_flight: int
    retryable_failure: int
    terminal_failure: int
    synchronized: int
    max_items: int
    max_bytes: int
    oldest_pending_age_seconds: float | None
    last_successful_sync: str | None
    last_failure: str | None
    upstream_status: str


class SyncQueue:
    """SQLite-backed bounded queue with durable synchronization state."""

    def __init__(
        self,
        path: str | Path,
        *,
        max_items: int = 10_000,
        max_bytes: int = 128 * 1024 * 1024,
    ) -> None:
        if max_items < 1:
            raise ValueError("max_items must be positive")
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.path = Path(path)
        self.max_items = max_items
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self._recover_in_flight()

    def ensure_capacity(self, reserve_bytes: int = 0) -> None:
        if reserve_bytes < 0:
            raise ValueError("reserve_bytes must not be negative")
        with self._connect() as connection:
            count, used_bytes = self._capacity_usage(connection)
        if count >= self.max_items:
            raise QueueCapacityError("sync queue item capacity reached")
        if used_bytes + reserve_bytes > self.max_bytes:
            raise QueueCapacityError("sync queue byte capacity reached")

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        normalized = _canonical_json(payload)
        payload_bytes = len(normalized.encode("utf-8"))
        required = _required_payload_fields(payload)
        now = _utc_now()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM sync_queue WHERE idempotency_key = ?",
                (required["idempotency_key"],),
            ).fetchone()
            if existing is not None:
                if (
                    existing["event_hash"] != required["event_hash"]
                    or existing["payload_json"] != normalized
                ):
                    raise SyncConflictError(
                        "idempotency key already exists with different immutable content"
                    )
                return _row_to_record(existing)

            count, used_bytes = self._capacity_usage(connection)
            if count >= self.max_items:
                raise QueueCapacityError("sync queue item capacity reached")
            if used_bytes + payload_bytes > self.max_bytes:
                raise QueueCapacityError("sync queue byte capacity reached")

            connection.execute(
                """
                INSERT INTO sync_queue (
                    idempotency_key, event_id, event_hash, tenant_id, workspace_id,
                    payload_json, payload_bytes, state, attempts, created_at_utc,
                    updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    required["idempotency_key"],
                    required["event_id"],
                    required["event_hash"],
                    required["tenant_id"],
                    required["workspace_id"],
                    normalized,
                    payload_bytes,
                    SyncState.PENDING.value,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM sync_queue WHERE idempotency_key = ?",
                (required["idempotency_key"],),
            ).fetchone()
        if row is None:
            raise RuntimeError("failed to load enqueued sync record")
        return _row_to_record(row)

    def claim_batch(self, limit: int = 50) -> list[SyncRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")
        now = _utc_now()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM sync_queue
                WHERE state IN (?, ?)
                ORDER BY id ASC
                LIMIT ?
                """,
                (SyncState.PENDING.value, SyncState.RETRYABLE_FAILURE.value, limit),
            ).fetchall()
            keys = [row["idempotency_key"] for row in rows]
            for key in keys:
                connection.execute(
                    """
                    UPDATE sync_queue
                    SET state = ?, attempts = attempts + 1, updated_at_utc = ?, last_error = NULL
                    WHERE idempotency_key = ?
                    """,
                    (SyncState.IN_FLIGHT.value, now, key),
                )
            claimed = [
                connection.execute(
                    "SELECT * FROM sync_queue WHERE idempotency_key = ?",
                    (key,),
                ).fetchone()
                for key in keys
            ]
        return [_row_to_record(row) for row in claimed if row is not None]

    def mark_retryable(self, idempotency_key: str, error: str) -> SyncRecord:
        return self._mark_failure(idempotency_key, error, SyncState.RETRYABLE_FAILURE)

    def mark_terminal(self, idempotency_key: str, error: str) -> SyncRecord:
        return self._mark_failure(idempotency_key, error, SyncState.TERMINAL_FAILURE)

    def mark_synchronized(
        self, idempotency_key: str, acknowledgement: dict[str, Any]
    ) -> SyncRecord:
        acknowledgement_json = _canonical_json(acknowledgement)
        acknowledgement_hash = hashlib.sha256(acknowledgement_json.encode("utf-8")).hexdigest()
        now = _utc_now()
        with self._connect() as connection:
            row = self._require_row(connection, idempotency_key)
            if row["state"] == SyncState.SYNCHRONIZED.value:
                if row["acknowledgement_hash"] != acknowledgement_hash:
                    raise SyncConflictError(
                        "synchronized record received a conflicting acknowledgement"
                    )
                return _row_to_record(row)
            connection.execute(
                """
                UPDATE sync_queue
                SET state = ?, acknowledgement_hash = ?, synchronized_at_utc = ?,
                    updated_at_utc = ?, last_error = NULL
                WHERE idempotency_key = ?
                """,
                (
                    SyncState.SYNCHRONIZED.value,
                    acknowledgement_hash,
                    now,
                    now,
                    idempotency_key,
                ),
            )
            self._set_meta(connection, "last_successful_sync", now)
            updated = self._require_row(connection, idempotency_key)
        return _row_to_record(updated)

    def get(self, idempotency_key: str) -> SyncRecord:
        with self._connect() as connection:
            row = self._require_row(connection, idempotency_key)
        return _row_to_record(row)

    def status(self, *, upstream_status: str = "unknown") -> SyncQueueStatus:
        with self._connect() as connection:
            counts = {
                state.value: self._count_state(connection, state) for state in SyncState
            }
            count, used_bytes = self._capacity_usage(connection)
            oldest_row = connection.execute(
                """
                SELECT MIN(created_at_utc) FROM sync_queue
                WHERE state IN (?, ?, ?, ?)
                """,
                (
                    SyncState.PENDING.value,
                    SyncState.IN_FLIGHT.value,
                    SyncState.RETRYABLE_FAILURE.value,
                    SyncState.TERMINAL_FAILURE.value,
                ),
            ).fetchone()
            oldest = None if oldest_row is None else oldest_row[0]
            last_success = self._get_meta(connection, "last_successful_sync")
            last_failure = self._get_meta(connection, "last_failure")
        age = None
        if oldest is not None:
            age = max(0.0, (datetime.now(UTC) - _parse_utc(oldest)).total_seconds())
        return SyncQueueStatus(
            queue_depth=count,
            queue_bytes=used_bytes,
            pending=counts[SyncState.PENDING.value],
            in_flight=counts[SyncState.IN_FLIGHT.value],
            retryable_failure=counts[SyncState.RETRYABLE_FAILURE.value],
            terminal_failure=counts[SyncState.TERMINAL_FAILURE.value],
            synchronized=counts[SyncState.SYNCHRONIZED.value],
            max_items=self.max_items,
            max_bytes=self.max_bytes,
            oldest_pending_age_seconds=age,
            last_successful_sync=last_success,
            last_failure=last_failure,
            upstream_status=upstream_status,
        )

    def set_upstream_status(self, status: str) -> None:
        with self._connect() as connection:
            self._set_meta(connection, "upstream_status", status)

    def get_upstream_status(self) -> str:
        with self._connect() as connection:
            return self._get_meta(connection, "upstream_status") or "unknown"

    def _mark_failure(self, idempotency_key: str, error: str, state: SyncState) -> SyncRecord:
        now = _utc_now()
        bounded_error = error[:2048]
        with self._connect() as connection:
            self._require_row(connection, idempotency_key)
            connection.execute(
                """
                UPDATE sync_queue
                SET state = ?, updated_at_utc = ?, last_error = ?
                WHERE idempotency_key = ?
                """,
                (state.value, now, bounded_error, idempotency_key),
            )
            self._set_meta(connection, "last_failure", f"{now} {bounded_error}")
            row = self._require_row(connection, idempotency_key)
        return _row_to_record(row)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    event_id TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_bytes INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    last_error TEXT,
                    acknowledgement_hash TEXT,
                    synchronized_at_utc TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_sync_queue_state_id ON sync_queue(state, id);
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def _recover_in_flight(self) -> None:
        now = _utc_now()
        with self._connect() as connection:
            changed = connection.execute(
                """
                UPDATE sync_queue
                SET state = ?, updated_at_utc = ?, last_error = ?
                WHERE state = ?
                """,
                (
                    SyncState.RETRYABLE_FAILURE.value,
                    now,
                    "recovered in-flight record after process restart",
                    SyncState.IN_FLIGHT.value,
                ),
            ).rowcount
            if changed:
                self._set_meta(
                    connection,
                    "last_failure",
                    f"{now} recovered {changed} in-flight record(s)",
                )

    def _capacity_usage(self, connection: sqlite3.Connection) -> tuple[int, int]:
        row = connection.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(payload_bytes), 0)
            FROM sync_queue
            WHERE state != ?
            """,
            (SyncState.SYNCHRONIZED.value,),
        ).fetchone()
        if row is None:
            return 0, 0
        return int(row[0]), int(row[1])

    def _count_state(self, connection: sqlite3.Connection, state: SyncState) -> int:
        row = connection.execute(
            "SELECT COUNT(*) FROM sync_queue WHERE state = ?", (state.value,)
        ).fetchone()
        return 0 if row is None else int(row[0])

    def _require_row(self, connection: sqlite3.Connection, idempotency_key: str) -> sqlite3.Row:
        row: sqlite3.Row | None = connection.execute(
            "SELECT * FROM sync_queue WHERE idempotency_key = ?", (idempotency_key,)
        ).fetchone()
        if row is None:
            raise KeyError(idempotency_key)
        return row

    def _set_meta(self, connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            """
            INSERT INTO sync_meta(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def _get_meta(self, connection: sqlite3.Connection, key: str) -> str | None:
        row = connection.execute("SELECT value FROM sync_meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection


def _required_payload_fields(payload: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for name in ("idempotency_key", "event_id", "event_hash", "tenant_id", "workspace_id"):
        value = payload.get(name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"sync payload requires non-empty string field: {name}")
        fields[name] = value
    return fields


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _row_to_record(row: sqlite3.Row) -> SyncRecord:
    payload = json.loads(row["payload_json"])
    if not isinstance(payload, dict):
        raise ValueError("stored sync payload is not an object")
    return SyncRecord(
        idempotency_key=str(row["idempotency_key"]),
        event_id=str(row["event_id"]),
        event_hash=str(row["event_hash"]),
        tenant_id=str(row["tenant_id"]),
        workspace_id=str(row["workspace_id"]),
        payload=payload,
        payload_bytes=int(row["payload_bytes"]),
        state=SyncState(str(row["state"])),
        attempts=int(row["attempts"]),
        created_at_utc=str(row["created_at_utc"]),
        updated_at_utc=str(row["updated_at_utc"]),
        last_error=None if row["last_error"] is None else str(row["last_error"]),
        acknowledgement_hash=(
            None if row["acknowledgement_hash"] is None else str(row["acknowledgement_hash"])
        ),
        synchronized_at_utc=(
            None if row["synchronized_at_utc"] is None else str(row["synchronized_at_utc"])
        ),
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
