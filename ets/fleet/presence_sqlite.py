"""Durable SQLite reference store for ETS Fleet presence and notification state."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from pydantic import ValidationError

from ets.fleet.models import normalize_time
from ets.fleet.presence import PresenceState
from ets.fleet.presence_ops import MaterialTransitionRecord, OperatorNotification


class SQLitePresenceStore:
    """Restart-safe reference store with atomic transport/state and notification writes."""

    provider_name = "sqlite"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self.path,
            timeout=10.0,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=FULL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        self._initialize()

    def get_state(self, device_id: str) -> PresenceState | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT state_json FROM presence_states WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            return PresenceState.model_validate_json(str(row["state_json"]))
        except ValidationError as exc:
            raise ValueError("stored Fleet presence state failed validation") from exc

    def put_state(self, state: PresenceState) -> None:
        with self._lock:
            self._upsert_state(state)
            self._connection.commit()

    def has_transport_event(self, event_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM transport_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return row is not None

    def remember_transport_event(self, event_id: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT OR IGNORE INTO transport_events (event_id) VALUES (?)",
                (event_id,),
            )
            self._connection.commit()

    def commit_transport_event(self, event_id: str, state: PresenceState) -> bool:
        """Atomically claim an accepted transport event and persist its resulting state."""

        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    "INSERT INTO transport_events (event_id) VALUES (?)",
                    (event_id,),
                )
                self._upsert_state(state)
                self._connection.commit()
            except sqlite3.IntegrityError:
                self._connection.rollback()
                return False
        return True

    def has_boot_session(self, device_id: str, boot_session_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1 FROM boot_sessions
                WHERE device_id = ? AND boot_session_id = ?
                """,
                (device_id, boot_session_id),
            ).fetchone()
        return row is not None

    def remember_boot_session(self, device_id: str, boot_session_id: str) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT OR IGNORE INTO boot_sessions (device_id, boot_session_id)
                VALUES (?, ?)
                """,
                (device_id, boot_session_id),
            )
            self._connection.commit()

    def commit_heartbeat_state(
        self,
        device_id: str,
        boot_session_id: str,
        state: PresenceState,
    ) -> None:
        """Atomically retain the observed boot session and accepted heartbeat state."""

        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO boot_sessions (device_id, boot_session_id)
                    VALUES (?, ?)
                    """,
                    (device_id, boot_session_id),
                )
                self._upsert_state(state)
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def has_transition(self, transition_key: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM material_transitions WHERE transition_key = ?",
                (transition_key,),
            ).fetchone()
        return row is not None

    def record_transition(
        self,
        transition: MaterialTransitionRecord,
        notification: OperatorNotification | None,
    ) -> bool:
        """Atomically record a unique material transition and optional notification outbox row."""

        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """
                    INSERT INTO material_transitions (
                        transition_key, device_id, occurred_at_utc, transition_json
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        transition.transition_key,
                        transition.device_id,
                        _iso(transition.occurred_at_utc),
                        transition.model_dump_json(),
                    ),
                )
                if notification is not None:
                    self._connection.execute(
                        """
                        INSERT INTO operator_notifications (
                            notification_id, transition_key, device_id,
                            created_at_utc, notification_json, delivered_at_utc
                        ) VALUES (?, ?, ?, ?, ?, NULL)
                        """,
                        (
                            notification.notification_id,
                            notification.transition_key,
                            notification.device_id,
                            _iso(notification.created_at_utc),
                            notification.model_dump_json(),
                        ),
                    )
                self._connection.commit()
            except sqlite3.IntegrityError:
                self._connection.rollback()
                return False
            except Exception:
                self._connection.rollback()
                raise
        return True

    def list_pending_notifications(self, *, limit: int = 100) -> list[OperatorNotification]:
        if limit < 1:
            return []
        bounded_limit = min(limit, 1000)
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT notification_json
                FROM operator_notifications
                WHERE delivered_at_utc IS NULL
                ORDER BY created_at_utc ASC, notification_id ASC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        notifications: list[OperatorNotification] = []
        for row in rows:
            try:
                notifications.append(
                    OperatorNotification.model_validate_json(str(row["notification_json"]))
                )
            except ValidationError as exc:
                raise ValueError("stored operator notification failed validation") from exc
        return notifications

    def mark_notification_delivered(
        self,
        notification_id: str,
        *,
        delivered_at_utc: datetime,
    ) -> None:
        with self._lock:
            cursor = self._connection.execute(
                """
                UPDATE operator_notifications
                SET delivered_at_utc = ?
                WHERE notification_id = ? AND delivered_at_utc IS NULL
                """,
                (_iso(delivered_at_utc), notification_id),
            )
            self._connection.commit()
        if cursor.rowcount != 1:
            raise KeyError(f"pending notification not found: {notification_id}")

    def count_notifications_since(self, device_id: str, *, since_utc: datetime) -> int:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT COUNT(*) AS item_count
                FROM operator_notifications
                WHERE device_id = ? AND created_at_utc >= ?
                """,
                (device_id, _iso(since_utc)),
            ).fetchone()
        return 0 if row is None else int(row["item_count"])

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _upsert_state(self, state: PresenceState) -> None:
        self._connection.execute(
            """
            INSERT INTO presence_states (device_id, state_json, updated_at_utc)
            VALUES (?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at_utc = excluded.updated_at_utc
            """,
            (
                state.device_id,
                state.model_dump_json(),
                _iso(datetime.now(UTC)),
            ),
        )

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS presence_states (
                    device_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transport_events (
                    event_id TEXT PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS boot_sessions (
                    device_id TEXT NOT NULL,
                    boot_session_id TEXT NOT NULL,
                    PRIMARY KEY (device_id, boot_session_id)
                );

                CREATE TABLE IF NOT EXISTS material_transitions (
                    transition_key TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    occurred_at_utc TEXT NOT NULL,
                    transition_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operator_notifications (
                    notification_id TEXT PRIMARY KEY,
                    transition_key TEXT NOT NULL UNIQUE,
                    device_id TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    notification_json TEXT NOT NULL,
                    delivered_at_utc TEXT NULL,
                    FOREIGN KEY (transition_key)
                        REFERENCES material_transitions(transition_key)
                );

                CREATE INDEX IF NOT EXISTS idx_operator_notifications_device_created
                ON operator_notifications(device_id, created_at_utc);
                """
            )
            self._connection.commit()


def _iso(value: datetime) -> str:
    return normalize_time(value).isoformat().replace("+00:00", "Z")
