"""Durable Microsoft Graph subscription lifecycle state for the hosted Gateway."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path
from threading import RLock

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
    apply_graph_lifecycle_event,
)


class MicrosoftGraphSubscriptionStateStoreError(RuntimeError):
    """Raised when durable Graph subscription state cannot be read or written."""


class SQLiteMicrosoftGraphSubscriptionStore:
    """Restart-safe SQLite implementation of the Graph webhook state boundary.

    Subscription identity, tenant, resource, and client-state hash are immutable once
    registered. Lifecycle transitions may update only operational status, gap state,
    and expiration. The client-state secret itself is never persisted; only its hash
    contained in ``MicrosoftGraphSubscriptionStateV1`` is stored.
    """

    def __init__(self, database: str | Path) -> None:
        self._database = str(database)
        if self._database != ":memory:":
            Path(self._database).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        try:
            self._connection = sqlite3.connect(
                self._database,
                check_same_thread=False,
                isolation_level=None,
            )
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=FULL")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    client_state_sha256 TEXT NOT NULL
                )
                """
            )
        except sqlite3.Error as exc:
            raise MicrosoftGraphSubscriptionStateStoreError(
                "unable to initialize Graph subscription state store"
            ) from exc

    def register(self, state: MicrosoftGraphSubscriptionStateV1) -> None:
        """Insert a subscription or refresh its mutable lifecycle fields."""

        with self._lock:
            try:
                row = self._connection.execute(
                    """
                    SELECT tenant_id, resource, client_state_sha256, state_json
                    FROM graph_subscriptions
                    WHERE subscription_id = ?
                    """,
                    (state.subscription_id,),
                ).fetchone()
                if row is not None:
                    tenant_id, resource, client_state_sha256, existing_json = row
                    if (
                        tenant_id != state.tenant_id
                        or resource != state.resource
                        or client_state_sha256 != state.client_state_sha256
                    ):
                        raise MicrosoftGraphSubscriptionStateStoreError(
                            "Graph subscription identity changed during registration"
                        )
                    existing = self._decode(existing_json)
                    refreshed = existing.model_copy(
                        update={
                            "expiration_date_time": state.expiration_date_time,
                            "status": state.status,
                        }
                    )
                    self._write(refreshed)
                    return
                self._write(state)
            except MicrosoftGraphSubscriptionStateStoreError:
                raise
            except sqlite3.Error as exc:
                raise MicrosoftGraphSubscriptionStateStoreError(
                    "unable to register Graph subscription state"
                ) from exc

    def get(self, subscription_id: str) -> MicrosoftGraphSubscriptionStateV1 | None:
        """Return one durable subscription state, or ``None`` if unknown."""

        with self._lock:
            try:
                row = self._connection.execute(
                    "SELECT state_json FROM graph_subscriptions WHERE subscription_id = ?",
                    (subscription_id,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise MicrosoftGraphSubscriptionStateStoreError(
                    "unable to read Graph subscription state"
                ) from exc
            return None if row is None else self._decode(row[0])

    def snapshot(self) -> Mapping[str, MicrosoftGraphSubscriptionStateV1]:
        """Return a validated snapshot suitable for webhook notification parsing."""

        with self._lock:
            try:
                rows = self._connection.execute(
                    "SELECT subscription_id, state_json FROM graph_subscriptions "
                    "ORDER BY subscription_id"
                ).fetchall()
            except sqlite3.Error as exc:
                raise MicrosoftGraphSubscriptionStateStoreError(
                    "unable to read Graph subscription state snapshot"
                ) from exc
            return {subscription_id: self._decode(payload) for subscription_id, payload in rows}

    def apply_lifecycle(
        self,
        notification: MicrosoftGraphNotificationV1,
    ) -> MicrosoftGraphSubscriptionStateV1:
        """Apply one qualified lifecycle notification atomically."""

        with self._lock:
            try:
                row = self._connection.execute(
                    "SELECT state_json FROM graph_subscriptions WHERE subscription_id = ?",
                    (notification.subscription_id,),
                ).fetchone()
                if row is None:
                    raise MicrosoftGraphSubscriptionStateStoreError(
                        "Graph lifecycle notification references an unknown subscription"
                    )
                current = self._decode(row[0])
                if notification.tenant_id.casefold() != current.tenant_id.casefold():
                    raise MicrosoftGraphSubscriptionStateStoreError(
                        "Graph lifecycle notification tenant does not match subscription state"
                    )
                updated = apply_graph_lifecycle_event(current, notification)
                self._connection.execute("BEGIN IMMEDIATE")
                try:
                    self._write(updated)
                    self._connection.execute("COMMIT")
                except Exception:
                    self._connection.execute("ROLLBACK")
                    raise
                return updated
            except MicrosoftGraphSubscriptionStateStoreError:
                raise
            except sqlite3.Error as exc:
                raise MicrosoftGraphSubscriptionStateStoreError(
                    "unable to persist Graph lifecycle state"
                ) from exc

    def close(self) -> None:
        """Close the SQLite connection."""

        with self._lock:
            self._connection.close()

    def _write(self, state: MicrosoftGraphSubscriptionStateV1) -> None:
        payload = state.model_dump_json()
        self._connection.execute(
            """
            INSERT INTO graph_subscriptions (
                subscription_id, state_json, tenant_id, resource, client_state_sha256
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(subscription_id) DO UPDATE SET
                state_json = excluded.state_json,
                tenant_id = excluded.tenant_id,
                resource = excluded.resource,
                client_state_sha256 = excluded.client_state_sha256
            """,
            (
                state.subscription_id,
                payload,
                state.tenant_id,
                state.resource,
                state.client_state_sha256,
            ),
        )

    @staticmethod
    def _decode(payload: str) -> MicrosoftGraphSubscriptionStateV1:
        try:
            return MicrosoftGraphSubscriptionStateV1.model_validate_json(payload)
        except (TypeError, ValueError) as exc:
            raise MicrosoftGraphSubscriptionStateStoreError(
                "persisted Graph subscription state is invalid"
            ) from exc
