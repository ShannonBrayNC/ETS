"""Source-scoped read-only telemetry for the durable Gateway synchronization queue."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from ets.runtime.sync_queue import SyncQueue, SyncState

GATEWAY_SYNC_SCHEMA = "ets.gateway.sync.v1"


class ScopedSyncQueueStatusError(RuntimeError):
    """Raised when scoped Gateway queue telemetry cannot be classified safely."""


@dataclass(frozen=True, slots=True)
class SourceScopedSyncQueueStatus:
    """Current queue posture for one authoritative Gateway source.

    ``latest_active_failure`` is intentionally not called ``last_failure``. The shared
    queue retains a global historical last-failure marker, but synchronized records
    clear their per-record error. A source-specific historical last failure therefore
    cannot be reconstructed from durable rows without inventing provenance.
    """

    tenant_id: str
    workspace_id: str
    source_id: str
    queue_depth: int
    queue_bytes: int
    pending: int
    in_flight: int
    retryable_failure: int
    terminal_failure: int
    synchronized: int
    shared_max_items: int
    shared_max_bytes: int
    oldest_unsynchronized_age_seconds: float | None
    last_successful_sync: str | None
    latest_active_failure: str | None
    upstream_status: str


@dataclass(frozen=True, slots=True)
class _ScopedSyncRow:
    state: SyncState
    payload_bytes: int
    created_at_utc: datetime
    updated_at_utc: datetime
    last_error: str | None
    synchronized_at_utc: datetime | None


def source_scoped_sync_queue_status(
    queue: SyncQueue,
    *,
    tenant_id: str,
    workspace_id: str,
    source_id: str,
    upstream_status: str = "unknown",
    now: datetime | None = None,
) -> SourceScopedSyncQueueStatus:
    """Return current queue posture for one authoritative Gateway source only.

    The shared queue can contain observations from many sources. Microsoft connector
    health must not inherit failures from an unrelated source, tenant, or workspace.
    This helper therefore scopes records before deriving backlog/failure posture.
    """

    _bounded_identity("tenant_id", tenant_id, 128)
    _bounded_identity("workspace_id", workspace_id, 128)
    _bounded_identity("source_id", source_id, 200)
    if not 1 <= len(upstream_status) <= 200:
        raise ValueError("upstream_status must be 1-200 characters")
    instant = datetime.now(UTC) if now is None else _aware_utc(now)

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(queue.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT payload_json, payload_bytes, state, created_at_utc, updated_at_utc,
                   last_error, synchronized_at_utc
            FROM sync_queue
            WHERE tenant_id = ? AND workspace_id = ?
            ORDER BY id ASC
            """,
            (tenant_id, workspace_id),
        ).fetchall()
    except sqlite3.Error as exc:
        raise ScopedSyncQueueStatusError("unable to read scoped synchronization posture") from exc
    finally:
        if connection is not None:
            connection.close()

    scoped = tuple(_classify_source_row(row, source_id) for row in rows)
    records = tuple(record for record in scoped if record is not None)
    counts: dict[SyncState, int] = {state: 0 for state in SyncState}
    queue_depth = 0
    queue_bytes = 0
    oldest: datetime | None = None
    last_success: datetime | None = None
    active_failure: tuple[datetime, str] | None = None

    for record in records:
        counts[record.state] += 1
        if record.state is not SyncState.SYNCHRONIZED:
            queue_depth += 1
            queue_bytes += record.payload_bytes
            if oldest is None or record.created_at_utc < oldest:
                oldest = record.created_at_utc
        synchronized = record.synchronized_at_utc
        if synchronized is not None and (last_success is None or synchronized > last_success):
            last_success = synchronized
        if record.last_error is not None:
            if active_failure is None or record.updated_at_utc > active_failure[0]:
                active_failure = (record.updated_at_utc, record.last_error)

    age = None if oldest is None else max(0.0, (instant - oldest).total_seconds())
    failure = None
    if active_failure is not None:
        failure = f"{_format_utc(active_failure[0])} {active_failure[1]}"

    return SourceScopedSyncQueueStatus(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        source_id=source_id,
        queue_depth=queue_depth,
        queue_bytes=queue_bytes,
        pending=counts[SyncState.PENDING],
        in_flight=counts[SyncState.IN_FLIGHT],
        retryable_failure=counts[SyncState.RETRYABLE_FAILURE],
        terminal_failure=counts[SyncState.TERMINAL_FAILURE],
        synchronized=counts[SyncState.SYNCHRONIZED],
        shared_max_items=queue.max_items,
        shared_max_bytes=queue.max_bytes,
        oldest_unsynchronized_age_seconds=age,
        last_successful_sync=None if last_success is None else _format_utc(last_success),
        latest_active_failure=failure,
        upstream_status=upstream_status,
    )


def _classify_source_row(row: sqlite3.Row, source_id: str) -> _ScopedSyncRow | None:
    try:
        decoded = json.loads(str(row["payload_json"]))
    except (TypeError, ValueError) as exc:
        raise ScopedSyncQueueStatusError("stored synchronization payload is invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise ScopedSyncQueueStatusError("stored synchronization payload is not an object")
    if decoded.get("sync_schema") != GATEWAY_SYNC_SCHEMA:
        return None
    capture = decoded.get("capture")
    if not isinstance(capture, dict):
        raise ScopedSyncQueueStatusError("Gateway synchronization payload has no capture object")
    stored_source = capture.get("source_id")
    if not isinstance(stored_source, str) or not 1 <= len(stored_source) <= 200:
        raise ScopedSyncQueueStatusError(
            "Gateway synchronization payload has invalid source identity"
        )
    if stored_source != source_id:
        return None

    try:
        state = SyncState(str(row["state"]))
        payload_bytes = int(row["payload_bytes"])
        created = _parse_utc(str(row["created_at_utc"]))
        updated = _parse_utc(str(row["updated_at_utc"]))
        synchronized = (
            None
            if row["synchronized_at_utc"] is None
            else _parse_utc(str(row["synchronized_at_utc"]))
        )
    except (TypeError, ValueError) as exc:
        raise ScopedSyncQueueStatusError("stored synchronization state is invalid") from exc
    if payload_bytes < 0:
        raise ScopedSyncQueueStatusError("stored synchronization payload size is invalid")
    error = None if row["last_error"] is None else str(row["last_error"])
    return _ScopedSyncRow(
        state=state,
        payload_bytes=payload_bytes,
        created_at_utc=created,
        updated_at_utc=updated,
        last_error=error,
        synchronized_at_utc=synchronized,
    )


def _bounded_identity(name: str, value: str, maximum: int) -> None:
    if not 1 <= len(value) <= maximum:
        raise ValueError(f"{name} must be 1-{maximum} characters")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("scoped queue posture timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _aware_utc(parsed)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
