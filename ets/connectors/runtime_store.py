"""Durable connector instance and runtime state store for Gateway G2C."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

from ets.connectors.models import ConnectorCheckpointV1, ConnectorInstanceV1
from ets.connectors.runtime import (
    CONNECTOR_ADMIN_AUDIT_SCHEMA_VERSION,
    CONNECTOR_INSTANCE_RECORD_SCHEMA_VERSION,
    CONNECTOR_RUNTIME_SCHEMA_VERSION,
    ConnectorAdminAuditEventV1,
    ConnectorAuditResult,
    ConnectorInstanceRecordV1,
    ConnectorObservationState,
    ConnectorRuntimeStateV1,
)

ReconciledObservationState = Literal[
    "healthy_observation",
    "degraded_observation",
    "unknown_observation",
]
_VALID_OBSERVATION_STATES = frozenset(
    {
        "healthy_observation",
        "degraded_observation",
        "collection_gap",
        "unknown_observation",
    }
)


class ConnectorRuntimeStoreError(RuntimeError):
    """Base error for connector runtime persistence."""


class ConnectorInstanceExistsError(ConnectorRuntimeStoreError):
    """Raised when an instance id is already present."""


class ConnectorInstanceNotFoundError(ConnectorRuntimeStoreError):
    """Raised when an instance id is unknown."""


class ConnectorRevisionConflictError(ConnectorRuntimeStoreError):
    """Raised when a revisioned update loses a compare-and-set race."""


class ConnectorRuntimeStore:
    """SQLite-backed connector state isolated from ETS canonical/Merkle persistence."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create_instance(
        self,
        instance: ConnectorInstanceV1,
        *,
        actor_id: str,
        now: datetime,
    ) -> ConnectorInstanceRecordV1:
        current = _utc(now)
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO connector_instances(
                        instance_id, payload_json, revision, created_at_utc, updated_at_utc
                    ) VALUES (?, ?, 1, ?, ?)
                    """,
                    (
                        instance.instance_id,
                        instance.model_dump_json(),
                        _time(current),
                        _time(current),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConnectorInstanceExistsError(
                    f"connector instance already exists: {instance.instance_id}"
                ) from exc
            connection.execute(
                """
                INSERT INTO connector_runtime(
                    instance_id, checkpoint_json, checkpoint_revision, retry_count,
                    next_attempt_at_utc, last_success_at_utc, observation_state,
                    gap_open, lease_owner, lease_expires_at_utc, updated_at_utc
                ) VALUES (?, NULL, 0, 0, NULL, NULL, 'unknown_observation', 0, NULL, NULL, ?)
                """,
                (instance.instance_id, _time(current)),
            )
            self._append_audit(
                connection,
                action="connector.created",
                instance=instance,
                actor_id=actor_id,
                result="success",
                revision=1,
                message=None,
                now=current,
            )
        return self.get_instance(instance.instance_id)

    def get_instance(self, instance_id: str) -> ConnectorInstanceRecordV1:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json, revision, created_at_utc, updated_at_utc
                FROM connector_instances WHERE instance_id = ?
                """,
                (instance_id,),
            ).fetchone()
        if row is None:
            raise ConnectorInstanceNotFoundError(f"unknown connector instance: {instance_id}")
        instance = ConnectorInstanceV1.model_validate_json(str(row["payload_json"]))
        return ConnectorInstanceRecordV1(
            schema_version=CONNECTOR_INSTANCE_RECORD_SCHEMA_VERSION,
            instance=instance,
            revision=int(row["revision"]),
            created_at_utc=_parse_time(str(row["created_at_utc"])),
            updated_at_utc=_parse_time(str(row["updated_at_utc"])),
        )

    def list_instances(self) -> tuple[ConnectorInstanceRecordV1, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT instance_id FROM connector_instances ORDER BY instance_id"
            ).fetchall()
        return tuple(self.get_instance(str(row["instance_id"])) for row in rows)

    def replace_instance(
        self,
        instance: ConnectorInstanceV1,
        *,
        expected_revision: int,
        actor_id: str,
        action: str = "connector.updated",
        now: datetime,
    ) -> ConnectorInstanceRecordV1:
        current = _utc(now)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE connector_instances
                SET payload_json = ?, revision = revision + 1, updated_at_utc = ?
                WHERE instance_id = ? AND revision = ?
                """,
                (
                    instance.model_dump_json(),
                    _time(current),
                    instance.instance_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                self._raise_instance_or_revision(connection, instance.instance_id)
            revision = expected_revision + 1
            self._append_audit(
                connection,
                action=action,
                instance=instance,
                actor_id=actor_id,
                result="success",
                revision=revision,
                message=None,
                now=current,
            )
        return self.get_instance(instance.instance_id)

    def get_runtime(self, instance_id: str) -> ConnectorRuntimeStateV1:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM connector_runtime WHERE instance_id = ?",
                (instance_id,),
            ).fetchone()
        if row is None:
            raise ConnectorInstanceNotFoundError(f"unknown connector instance: {instance_id}")
        checkpoint_json = row["checkpoint_json"]
        checkpoint = (
            None
            if checkpoint_json is None
            else ConnectorCheckpointV1.model_validate_json(str(checkpoint_json))
        )
        return ConnectorRuntimeStateV1(
            schema_version=CONNECTOR_RUNTIME_SCHEMA_VERSION,
            instance_id=instance_id,
            checkpoint=checkpoint,
            checkpoint_revision=int(row["checkpoint_revision"]),
            retry_count=int(row["retry_count"]),
            next_attempt_at_utc=_optional_time(row["next_attempt_at_utc"]),
            last_success_at_utc=_optional_time(row["last_success_at_utc"]),
            observation_state=_observation_state(row["observation_state"]),
            gap_open=bool(row["gap_open"]),
            lease_owner=None if row["lease_owner"] is None else str(row["lease_owner"]),
            lease_expires_at_utc=_optional_time(row["lease_expires_at_utc"]),
            updated_at_utc=_parse_time(str(row["updated_at_utc"])),
        )

    def set_checkpoint(
        self,
        instance_id: str,
        checkpoint: ConnectorCheckpointV1 | None,
        *,
        expected_checkpoint_revision: int,
        observation_state: ConnectorObservationState,
        gap_open: bool,
        last_success_at_utc: datetime | None,
        now: datetime,
    ) -> ConnectorRuntimeStateV1:
        if observation_state == "collection_gap" and not gap_open:
            raise ValueError("collection_gap requires gap_open before checkpoint persistence")
        current = _utc(now)
        last_success = None if last_success_at_utc is None else _utc(last_success_at_utc)
        checkpoint_json = None if checkpoint is None else checkpoint.model_dump_json()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE connector_runtime
                SET checkpoint_json = ?, checkpoint_revision = checkpoint_revision + 1,
                    last_success_at_utc = ?, observation_state = ?, gap_open = ?,
                    retry_count = 0, next_attempt_at_utc = NULL, updated_at_utc = ?
                WHERE instance_id = ? AND checkpoint_revision = ?
                """,
                (
                    checkpoint_json,
                    None if last_success is None else _time(last_success),
                    observation_state,
                    int(gap_open),
                    _time(current),
                    instance_id,
                    expected_checkpoint_revision,
                ),
            )
            if cursor.rowcount != 1:
                self._raise_runtime_or_revision(connection, instance_id)
        return self.get_runtime(instance_id)

    def mark_gap(
        self,
        instance_id: str,
        *,
        now: datetime,
    ) -> ConnectorRuntimeStateV1:
        current = _utc(now)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE connector_runtime
                SET observation_state = 'collection_gap', gap_open = 1, updated_at_utc = ?
                WHERE instance_id = ?
                """,
                (_time(current), instance_id),
            )
            if cursor.rowcount != 1:
                raise ConnectorInstanceNotFoundError(
                    f"unknown connector instance: {instance_id}"
                )
        return self.get_runtime(instance_id)

    def reconcile_gap(
        self,
        instance_id: str,
        *,
        observation_state: ReconciledObservationState = "healthy_observation",
        now: datetime,
    ) -> ConnectorRuntimeStateV1:
        current = _utc(now)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE connector_runtime
                SET observation_state = ?, gap_open = 0, updated_at_utc = ?
                WHERE instance_id = ?
                """,
                (observation_state, _time(current), instance_id),
            )
            if cursor.rowcount != 1:
                raise ConnectorInstanceNotFoundError(
                    f"unknown connector instance: {instance_id}"
                )
        return self.get_runtime(instance_id)

    def schedule_retry(
        self,
        instance_id: str,
        *,
        next_attempt_at_utc: datetime,
        now: datetime,
    ) -> ConnectorRuntimeStateV1:
        current = _utc(now)
        next_attempt = _utc(next_attempt_at_utc)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE connector_runtime
                SET retry_count = retry_count + 1, next_attempt_at_utc = ?,
                    observation_state = 'degraded_observation', updated_at_utc = ?
                WHERE instance_id = ?
                """,
                (_time(next_attempt), _time(current), instance_id),
            )
            if cursor.rowcount != 1:
                raise ConnectorInstanceNotFoundError(
                    f"unknown connector instance: {instance_id}"
                )
        return self.get_runtime(instance_id)

    def claim_due(
        self,
        *,
        owner: str,
        now: datetime,
        lease_seconds: int,
        limit: int,
        instance_ids: tuple[str, ...] | None = None,
    ) -> tuple[str, ...]:
        if not 1 <= len(owner) <= 200:
            raise ValueError("lease owner must be 1-200 characters")
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be 1-3600")
        if not 1 <= limit <= 1000:
            raise ValueError("claim limit must be 1-1000")
        if instance_ids is not None:
            if not instance_ids:
                raise ValueError("instance_ids must not be empty when supplied")
            if len(instance_ids) != len(set(instance_ids)):
                raise ValueError("instance_ids must be unique")
            if any(not 1 <= len(instance_id) <= 128 for instance_id in instance_ids):
                raise ValueError("instance_ids contain an invalid connector instance id")
        current = _utc(now)
        lease_expires = current + timedelta(seconds=lease_seconds)
        instance_filter = ""
        instance_parameters: tuple[object, ...] = ()
        if instance_ids is not None:
            placeholders = ", ".join("?" for _ in instance_ids)
            instance_filter = f"AND r.instance_id IN ({placeholders})"
            instance_parameters = tuple(instance_ids)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                f"""
                SELECT r.instance_id
                FROM connector_runtime r
                JOIN connector_instances i ON i.instance_id = r.instance_id
                WHERE json_extract(i.payload_json, '$.enabled') = 1
                  AND (r.next_attempt_at_utc IS NULL OR r.next_attempt_at_utc <= ?)
                  AND (r.lease_expires_at_utc IS NULL OR r.lease_expires_at_utc <= ?)
                  {instance_filter}
                ORDER BY r.instance_id
                LIMIT ?
                """,
                (_time(current), _time(current), *instance_parameters, limit),
            ).fetchall()
            claimed = tuple(str(row["instance_id"]) for row in rows)
            for claimed_instance_id in claimed:
                connection.execute(
                    """
                    UPDATE connector_runtime
                    SET lease_owner = ?, lease_expires_at_utc = ?, updated_at_utc = ?
                    WHERE instance_id = ?
                    """,
                    (
                        owner,
                        _time(lease_expires),
                        _time(current),
                        claimed_instance_id,
                    ),
                )
        return claimed

    def release_lease(
        self,
        instance_id: str,
        *,
        owner: str,
        now: datetime,
    ) -> ConnectorRuntimeStateV1:
        current = _utc(now)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE connector_runtime
                SET lease_owner = NULL, lease_expires_at_utc = NULL, updated_at_utc = ?
                WHERE instance_id = ? AND lease_owner = ?
                """,
                (_time(current), instance_id, owner),
            )
            if cursor.rowcount != 1:
                raise ConnectorRevisionConflictError(
                    "connector runtime lease is not owned by the requested worker"
                )
        return self.get_runtime(instance_id)

    def recover_expired_leases(self, *, now: datetime) -> int:
        current = _utc(now)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE connector_runtime
                SET lease_owner = NULL, lease_expires_at_utc = NULL, updated_at_utc = ?
                WHERE lease_expires_at_utc IS NOT NULL AND lease_expires_at_utc <= ?
                """,
                (_time(current), _time(current)),
            )
            return max(cursor.rowcount, 0)

    def list_audit_events(self, instance_id: str) -> tuple[ConnectorAdminAuditEventV1, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM connector_admin_audit
                WHERE instance_id = ? ORDER BY audit_id
                """,
                (instance_id,),
            ).fetchall()
        return tuple(
            ConnectorAdminAuditEventV1.model_validate_json(str(row["payload_json"]))
            for row in rows
        )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS connector_instances(
                    instance_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS connector_runtime(
                    instance_id TEXT PRIMARY KEY,
                    checkpoint_json TEXT,
                    checkpoint_revision INTEGER NOT NULL,
                    retry_count INTEGER NOT NULL,
                    next_attempt_at_utc TEXT,
                    last_success_at_utc TEXT,
                    observation_state TEXT NOT NULL,
                    gap_open INTEGER NOT NULL,
                    lease_owner TEXT,
                    lease_expires_at_utc TEXT,
                    updated_at_utc TEXT NOT NULL,
                    FOREIGN KEY(instance_id) REFERENCES connector_instances(instance_id)
                );
                CREATE TABLE IF NOT EXISTS connector_admin_audit(
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_connector_runtime_due
                    ON connector_runtime(next_attempt_at_utc, lease_expires_at_utc);
                CREATE INDEX IF NOT EXISTS idx_connector_admin_instance
                    ON connector_admin_audit(instance_id, audit_id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _raise_instance_or_revision(
        self,
        connection: sqlite3.Connection,
        instance_id: str,
    ) -> None:
        row = connection.execute(
            "SELECT revision FROM connector_instances WHERE instance_id = ?",
            (instance_id,),
        ).fetchone()
        if row is None:
            raise ConnectorInstanceNotFoundError(f"unknown connector instance: {instance_id}")
        raise ConnectorRevisionConflictError(
            f"connector instance revision conflict: current={int(row['revision'])}"
        )

    def _raise_runtime_or_revision(
        self,
        connection: sqlite3.Connection,
        instance_id: str,
    ) -> None:
        row = connection.execute(
            "SELECT checkpoint_revision FROM connector_runtime WHERE instance_id = ?",
            (instance_id,),
        ).fetchone()
        if row is None:
            raise ConnectorInstanceNotFoundError(f"unknown connector instance: {instance_id}")
        raise ConnectorRevisionConflictError(
            "connector checkpoint revision conflict: "
            f"current={int(row['checkpoint_revision'])}"
        )

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        *,
        action: str,
        instance: ConnectorInstanceV1,
        actor_id: str,
        result: ConnectorAuditResult,
        revision: int | None,
        message: str | None,
        now: datetime,
    ) -> None:
        event = ConnectorAdminAuditEventV1(
            schema_version=CONNECTOR_ADMIN_AUDIT_SCHEMA_VERSION,
            action=action,
            instance_id=instance.instance_id,
            actor_id=actor_id,
            tenant_id=instance.scope.tenant_id,
            workspace_id=instance.scope.workspace_id,
            result=result,
            revision=revision,
            message=message,
            created_at_utc=now,
        )
        connection.execute(
            "INSERT INTO connector_admin_audit(instance_id, payload_json) VALUES (?, ?)",
            (instance.instance_id, event.model_dump_json()),
        )


def _observation_state(value: object) -> ConnectorObservationState:
    state = str(value)
    if state not in _VALID_OBSERVATION_STATES:
        raise ConnectorRuntimeStoreError(f"invalid persisted observation state: {state}")
    return cast(ConnectorObservationState, state)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("connector runtime timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _time(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    return _utc(datetime.fromisoformat(candidate))


def _optional_time(value: object) -> datetime | None:
    return None if value is None else _parse_time(str(value))
