"""Durable Gateway-to-Core synchronization worker.

The Gateway commits evidence locally before synchronization. This worker joins each
queued synchronization record back to that immutable local event and relays the
exact EvidenceEvent to ETS Core. Tenant/workspace scope is carried by the scoped
bearer credential, never by caller-controlled ETS tenant/workspace headers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from ets.core import EventNotFoundError, EventStore, LogEntry
from ets.runtime.sync_queue import SyncQueue, SyncRecord


class CoreRelayError(RuntimeError):
    """Base Gateway-to-Core relay failure."""


class CoreRelayRetryableError(CoreRelayError):
    """Upstream failure that may succeed on a later bounded retry."""


class CoreRelayTerminalError(CoreRelayError):
    """Upstream or local invariant failure that must not be retried automatically."""


class ScopedBearerLease(Protocol):
    """Short-lived scoped bearer material with deterministic cleanup."""

    def reveal(self) -> bytes: ...

    def close(self) -> None: ...

    def __enter__(self) -> ScopedBearerLease: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class ScopedBearerTokenProvider(Protocol):
    """Acquire a bearer credential scoped to one ETS tenant/workspace relay operation."""

    def acquire(self, *, tenant_id: str, workspace_id: str) -> ScopedBearerLease: ...


class CoreRelayClient(Protocol):
    """Submit one already-committed Gateway event to ETS Core."""

    def relay(
        self,
        entry: LogEntry,
        record: SyncRecord,
        token_provider: ScopedBearerTokenProvider,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class CoreRelayBatchResult:
    claimed: int
    synchronized: int
    retryable_failure: int
    terminal_failure: int


class GatewayCoreRelayWorker:
    """Drain the durable Gateway queue into Core without reinterpreting evidence."""

    def __init__(
        self,
        *,
        event_log: EventStore,
        sync_queue: SyncQueue,
        client: CoreRelayClient,
        token_provider: ScopedBearerTokenProvider,
    ) -> None:
        self._event_log = event_log
        self._sync_queue = sync_queue
        self._client = client
        self._token_provider = token_provider

    def run_once(self, *, limit: int = 50) -> CoreRelayBatchResult:
        """Claim and process one bounded batch from the restart-safe synchronization queue."""

        records = self._sync_queue.claim_batch(limit)
        synchronized = 0
        retryable = 0
        terminal = 0

        for record in records:
            try:
                entry = self._load_and_validate_local_entry(record)
                acknowledgement = self._client.relay(
                    entry,
                    record,
                    self._token_provider,
                )
                self._sync_queue.mark_synchronized(record.idempotency_key, acknowledgement)
            except CoreRelayRetryableError:
                retryable += 1
                self._sync_queue.mark_retryable(
                    record.idempotency_key,
                    "ETS Core relay failed with a retryable upstream condition",
                )
            except CoreRelayTerminalError:
                terminal += 1
                self._sync_queue.mark_terminal(
                    record.idempotency_key,
                    "ETS Core relay failed a terminal integrity or authorization check",
                )
            else:
                synchronized += 1

        if retryable:
            self._sync_queue.set_upstream_status("degraded")
        elif terminal:
            self._sync_queue.set_upstream_status("integrity_failure")
        elif records:
            self._sync_queue.set_upstream_status("healthy")

        return CoreRelayBatchResult(
            claimed=len(records),
            synchronized=synchronized,
            retryable_failure=retryable,
            terminal_failure=terminal,
        )

    def _load_and_validate_local_entry(self, record: SyncRecord) -> LogEntry:
        try:
            entry = self._event_log.get_by_event_id(record.event_id)
        except EventNotFoundError as exc:
            raise CoreRelayTerminalError(
                "queued synchronization record has no corresponding local event"
            ) from exc

        if entry.event_hash != record.event_hash:
            raise CoreRelayTerminalError(
                "queued synchronization record does not match local event hash"
            )
        if entry.event.tenant_id != record.tenant_id:
            raise CoreRelayTerminalError(
                "queued synchronization record does not match local event tenant"
            )
        if entry.event.workspace_id != record.workspace_id:
            raise CoreRelayTerminalError(
                "queued synchronization record does not match local event workspace"
            )
        return entry


def core_event_json(entry: LogEntry) -> bytes:
    """Serialize the already-committed local EvidenceEvent for the Core API."""

    payload = entry.event.model_dump(mode="json")
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")