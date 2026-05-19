import sqlite3
from pathlib import Path
from typing import cast

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    timestamp_utc TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    leaf_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
"""


class EventStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(SCHEMA_SQL)
            conn.commit()

    def insert_event(
        self,
        event_id: str,
        timestamp_utc: str,
        event_type: str,
        payload_json: str,
        payload_hash: str,
        leaf_hash: str,
        metadata_json: str,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO events (
                    event_id,
                    timestamp_utc,
                    type,
                    payload_json,
                    payload_hash,
                    leaf_hash,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    timestamp_utc,
                    event_type,
                    payload_json,
                    payload_hash,
                    leaf_hash,
                    metadata_json,
                ),
            )
            conn.commit()
            if cur.lastrowid is None:
                raise RuntimeError("SQLite did not return an inserted row id")
            return cur.lastrowid

    def get_event_by_event_id(self, event_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            return cast(sqlite3.Row | None, cur.fetchone())

    def list_events(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM events ORDER BY id ASC")
            return cast(list[sqlite3.Row], cur.fetchall())
