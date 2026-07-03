from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from ets.core import DuplicateEventError, create_artifact_record
from ets.core.sqlite_store import SQLiteEventStore
from ets.core.storage import StorageValidationError


def make_artifact_record(artifact_id: str = "artifact_001"):
    return create_artifact_record(
        artifact_id=artifact_id,
        artifact_hash="a" * 64,
        reference_uri=f"ets://artifact/{artifact_id}",
        content_type="application/json",
        byte_size=42,
        metadata={"case": "alpha"},
        ingestion_timestamp_utc=datetime(2026, 5, 18, 12, 31, tzinfo=UTC),
        event_id=f"artifact_registered:{artifact_id}",
        log_index=0,
    )


def test_sqlite_artifact_registry_survives_restart_without_content_bytes(tmp_path) -> None:
    path = tmp_path / "ets.db"
    store = SQLiteEventStore(path)
    record = make_artifact_record()
    store.save_artifact_record(record)
    store.close()

    reopened = SQLiteEventStore(path)
    persisted = reopened.get_artifact_record("artifact_001")

    assert persisted == record
    assert reopened.list_artifact_records() == [record]

    connection = sqlite3.connect(path)
    columns = [row[1] for row in connection.execute("PRAGMA table_info(artifact_records)")]
    rows = connection.execute("SELECT * FROM artifact_records").fetchall()
    connection.close()

    assert "artifact_base64" not in columns
    assert "content_bytes" not in columns
    assert rows


def test_sqlite_duplicate_artifact_check_survives_restart(tmp_path) -> None:
    path = tmp_path / "ets.db"
    store = SQLiteEventStore(path)
    store.save_artifact_record(make_artifact_record())
    store.close()

    reopened = SQLiteEventStore(path)

    with pytest.raises(DuplicateEventError):
        reopened.save_artifact_record(make_artifact_record())


def test_sqlite_artifact_metadata_corruption_fails_closed(tmp_path) -> None:
    path = tmp_path / "ets.db"
    store = SQLiteEventStore(path)
    store.save_artifact_record(make_artifact_record())
    store.close()

    connection = sqlite3.connect(path)
    connection.execute("UPDATE artifact_records SET metadata_json = ?", ("not-json",))
    connection.commit()
    connection.close()

    reopened = SQLiteEventStore(path)
    with pytest.raises(StorageValidationError):
        reopened.get_artifact_record("artifact_001")
