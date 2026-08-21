"""Durable-state contracts and reference stores for ETS Black Box."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from ets.black_box.models import (
    BlackBoxBackendCapabilities,
    BlackBoxSegment,
    RecorderState,
    SignedBlackBoxFrame,
)


class BlackBoxStoreError(RuntimeError):
    """Base error for incident-recorder state failures."""


class BlackBoxStateConflict(BlackBoxStoreError):
    """Raised when persistent recorder state would be overwritten inconsistently."""


class BlackBoxSegmentAlreadyExists(BlackBoxStoreError):
    """Raised if a sealed segment identifier already exists."""


class BlackBoxSegmentNotFound(BlackBoxStoreError):
    """Raised when a sealed segment cannot be found."""


class BlackBoxStore(Protocol):
    provider_name: str
    capabilities: BlackBoxBackendCapabilities

    def load_state(self) -> RecorderState | None: ...
    def initialize_state(self, state: RecorderState) -> None: ...
    def update_state(self, state: RecorderState) -> None: ...
    def commit_frame(self, frame: SignedBlackBoxFrame, state: RecorderState) -> None: ...
    def list_live_frames(self) -> list[SignedBlackBoxFrame]: ...
    def prune_live_before(self, minimum_sequence: int) -> None: ...
    def seal_segment(self, segment: BlackBoxSegment, state: RecorderState) -> None: ...
    def get_segment(self, segment_id: str) -> BlackBoxSegment: ...
    def list_segments(self) -> list[BlackBoxSegment]: ...


class InMemoryBlackBoxStore:
    """Deterministic semantic backend for tests; never a production recorder boundary."""

    provider_name = "memory"
    capabilities = BlackBoxBackendCapabilities(
        atomic_frame_state_commit=True,
        crash_consistent=False,
        durable_write=False,
        write_once_sealed_segments=True,
        encryption_at_rest=False,
        power_loss_protection=False,
        hardware_backed_keys=False,
        measured_boot=False,
        tamper_detection=False,
        enforcement_boundary="test",
    )

    def __init__(self) -> None:
        self._state: RecorderState | None = None
        self._live: dict[int, SignedBlackBoxFrame] = {}
        self._segments: dict[str, BlackBoxSegment] = {}

    def load_state(self) -> RecorderState | None:
        return self._state

    def initialize_state(self, state: RecorderState) -> None:
        if self._state is not None:
            raise BlackBoxStateConflict("recorder state already initialized")
        self._state = state

    def update_state(self, state: RecorderState) -> None:
        if self._state is None:
            raise BlackBoxStateConflict("recorder state is not initialized")
        self._state = state

    def commit_frame(self, frame: SignedBlackBoxFrame, state: RecorderState) -> None:
        if self._state is None:
            raise BlackBoxStateConflict("recorder state is not initialized")
        if frame.sequence in self._live:
            raise BlackBoxStateConflict("frame sequence already exists")
        if self._state.last_sequence != frame.sequence - 1:
            raise BlackBoxStateConflict("frame does not extend persisted sequence")
        self._live[frame.sequence] = frame
        self._state = state

    def list_live_frames(self) -> list[SignedBlackBoxFrame]:
        return [self._live[key] for key in sorted(self._live)]

    def prune_live_before(self, minimum_sequence: int) -> None:
        self._live = {key: value for key, value in self._live.items() if key >= minimum_sequence}

    def seal_segment(self, segment: BlackBoxSegment, state: RecorderState) -> None:
        segment_id = segment.manifest.segment_id
        if segment_id in self._segments:
            raise BlackBoxSegmentAlreadyExists(segment_id)
        self._segments[segment_id] = segment
        self.update_state(state)

    def get_segment(self, segment_id: str) -> BlackBoxSegment:
        try:
            return self._segments[segment_id]
        except KeyError as exc:
            raise BlackBoxSegmentNotFound(segment_id) from exc

    def list_segments(self) -> list[BlackBoxSegment]:
        return list(self._segments.values())


class SQLiteBlackBoxStore:
    """Crash-consistent software reference store using SQLite FULL synchronous transactions.

    This backend is useful for restart/recovery qualification. It does not claim encrypted media,
    hardware-enforced write-once semantics, power-loss-protected storage, measured boot, or
    hardware-backed signing keys and therefore intentionally fails production qualification.
    """

    provider_name = "sqlite"
    capabilities = BlackBoxBackendCapabilities(
        atomic_frame_state_commit=True,
        crash_consistent=True,
        durable_write=True,
        write_once_sealed_segments=True,
        encryption_at_rest=False,
        power_loss_protection=False,
        hardware_backed_keys=False,
        measured_boot=False,
        tamper_detection=False,
        enforcement_boundary="software",
    )

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS recorder_state (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                state_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS live_frames (
                sequence INTEGER PRIMARY KEY,
                frame_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sealed_segments (
                segment_id TEXT PRIMARY KEY,
                segment_json TEXT NOT NULL
            );
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def load_state(self) -> RecorderState | None:
        row = self._connection.execute(
            "SELECT state_json FROM recorder_state WHERE singleton = 1"
        ).fetchone()
        return None if row is None else RecorderState.model_validate_json(row[0])

    def initialize_state(self, state: RecorderState) -> None:
        try:
            with self._connection:
                self._connection.execute(
                    "INSERT INTO recorder_state(singleton, state_json) VALUES(1, ?)",
                    (state.model_dump_json(),),
                )
        except sqlite3.IntegrityError as exc:
            raise BlackBoxStateConflict("recorder state already initialized") from exc

    def update_state(self, state: RecorderState) -> None:
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE recorder_state SET state_json = ? WHERE singleton = 1",
                (state.model_dump_json(),),
            )
            if cursor.rowcount != 1:
                raise BlackBoxStateConflict("recorder state is not initialized")

    def commit_frame(self, frame: SignedBlackBoxFrame, state: RecorderState) -> None:
        with self._connection:
            current_row = self._connection.execute(
                "SELECT state_json FROM recorder_state WHERE singleton = 1"
            ).fetchone()
            if current_row is None:
                raise BlackBoxStateConflict("recorder state is not initialized")
            current = RecorderState.model_validate_json(current_row[0])
            if current.last_sequence != frame.sequence - 1:
                raise BlackBoxStateConflict("frame does not extend persisted sequence")
            try:
                self._connection.execute(
                    "INSERT INTO live_frames(sequence, frame_json) VALUES(?, ?)",
                    (frame.sequence, frame.model_dump_json()),
                )
            except sqlite3.IntegrityError as exc:
                raise BlackBoxStateConflict("frame sequence already exists") from exc
            self._connection.execute(
                "UPDATE recorder_state SET state_json = ? WHERE singleton = 1",
                (state.model_dump_json(),),
            )

    def list_live_frames(self) -> list[SignedBlackBoxFrame]:
        rows = self._connection.execute(
            "SELECT frame_json FROM live_frames ORDER BY sequence"
        ).fetchall()
        return [SignedBlackBoxFrame.model_validate_json(row[0]) for row in rows]

    def prune_live_before(self, minimum_sequence: int) -> None:
        with self._connection:
            self._connection.execute(
                "DELETE FROM live_frames WHERE sequence < ?", (minimum_sequence,)
            )

    def seal_segment(self, segment: BlackBoxSegment, state: RecorderState) -> None:
        try:
            with self._connection:
                self._connection.execute(
                    "INSERT INTO sealed_segments(segment_id, segment_json) VALUES(?, ?)",
                    (segment.manifest.segment_id, segment.model_dump_json()),
                )
                cursor = self._connection.execute(
                    "UPDATE recorder_state SET state_json = ? WHERE singleton = 1",
                    (state.model_dump_json(),),
                )
                if cursor.rowcount != 1:
                    raise BlackBoxStateConflict("recorder state is not initialized")
        except sqlite3.IntegrityError as exc:
            raise BlackBoxSegmentAlreadyExists(segment.manifest.segment_id) from exc

    def get_segment(self, segment_id: str) -> BlackBoxSegment:
        row = self._connection.execute(
            "SELECT segment_json FROM sealed_segments WHERE segment_id = ?", (segment_id,)
        ).fetchone()
        if row is None:
            raise BlackBoxSegmentNotFound(segment_id)
        return BlackBoxSegment.model_validate_json(row[0])

    def list_segments(self) -> list[BlackBoxSegment]:
        rows = self._connection.execute(
            "SELECT segment_json FROM sealed_segments ORDER BY rowid"
        ).fetchall()
        return [BlackBoxSegment.model_validate_json(row[0]) for row in rows]
