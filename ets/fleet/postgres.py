"""PostgreSQL production persistence for ETS Fleet C3B.

The Fleet domain remains provider-neutral. This module binds the existing
``EnrollmentStore`` and ``FleetAdminMutationJournal`` contracts to one shared
PostgreSQL database suitable for multiple BFF replicas.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Protocol, TypeVar, cast

from pydantic import BaseModel, ValidationError

from ets.fleet.models import DeviceEnrollmentRecord, RotationWindow, normalize_time
from ets.fleet.portal_admin import (
    FleetAdminIdempotencyConflict,
    FleetAdministrativeEvidence,
    FleetMutationResult,
)
from ets.fleet.portal_admin_durable import (
    FleetAdminDurabilityError,
    FleetAdminMutationPending,
)

_POSTGRES_SCHEMA_VERSION = 1
_POSTGRES_TOKEN_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"
_CONFLICT_SQLSTATES = frozenset({"23505", "40001", "40P01"})


class FleetStoreConflict(RuntimeError):
    """A concurrent authoritative Fleet write could not be serialized safely."""


class FleetStoreSchemaError(RuntimeError):
    """The shared Fleet schema is missing, corrupt, or unsupported."""


class _Cursor(Protocol):
    rowcount: int

    def fetchone(self) -> Mapping[str, object] | None: ...

    def fetchall(self) -> list[Mapping[str, object]]: ...


class PostgresConnection(Protocol):
    """Narrow DB-API shape used by the production adapter and integration tests."""

    def execute(
        self,
        query: str,
        params: Sequence[object] | None = None,
    ) -> _Cursor: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


PostgresConnectionFactory = Callable[[], PostgresConnection]


class _AccessToken(Protocol):
    token: str


class _TokenCredential(Protocol):
    def get_token(self, *scopes: str) -> _AccessToken: ...


class AzureManagedIdentityPostgresFactory:
    """Create TLS PostgreSQL connections using an Entra access token only.

    There is deliberately no password, secret, SAS, or connection-string
    fallback. PostgreSQL's wire protocol carries the short-lived Entra token in
    the password field, but the token is acquired per connection and is never
    persisted by ETS.
    """

    def __init__(
        self,
        *,
        host: str,
        database: str,
        user: str,
        credential: _TokenCredential | None = None,
        port: int = 5432,
        connect_timeout_seconds: int = 10,
    ) -> None:
        if not host.strip() or not database.strip() or not user.strip():
            raise ValueError("Fleet PostgreSQL host, database, and Entra user are required")
        if port < 1 or port > 65535:
            raise ValueError("invalid Fleet PostgreSQL port")
        if connect_timeout_seconds < 1 or connect_timeout_seconds > 60:
            raise ValueError("invalid Fleet PostgreSQL connect timeout")
        if credential is None:
            from azure.identity import DefaultAzureCredential

            credential = cast(_TokenCredential, DefaultAzureCredential())
        self._host = host.strip()
        self._database = database.strip()
        self._user = user.strip()
        self._credential = credential
        self._port = port
        self._connect_timeout_seconds = connect_timeout_seconds

    def __call__(self) -> PostgresConnection:
        import psycopg
        from psycopg.rows import dict_row

        access_token = self._credential.get_token(_POSTGRES_TOKEN_SCOPE).token
        if not access_token:
            raise RuntimeError("managed identity returned an empty PostgreSQL access token")
        connection = psycopg.connect(
            host=self._host,
            dbname=self._database,
            user=self._user,
            password=access_token,
            port=self._port,
            connect_timeout=self._connect_timeout_seconds,
            sslmode="verify-full",
            application_name="ets-fleet-c3b",
            row_factory=dict_row,
        )
        return cast(PostgresConnection, connection)


class _PostgresTransactionManager:
    def __init__(self, factory: PostgresConnectionFactory) -> None:
        self._factory = factory
        self._current: ContextVar[PostgresConnection | None] = ContextVar(
            f"ets_fleet_postgres_connection_{id(self)}",
            default=None,
        )

    @contextmanager
    def transaction(self) -> Iterator[None]:
        existing = self._current.get()
        if existing is not None:
            yield
            return

        connection = self._factory()
        token = self._current.set(connection)
        try:
            connection.execute("BEGIN ISOLATION LEVEL SERIALIZABLE")
            yield
            connection.commit()
        except Exception as exc:
            try:
                connection.rollback()
            finally:
                if _is_concurrency_conflict(exc):
                    raise FleetStoreConflict(
                        "concurrent Fleet state changed; retry from fresh authoritative state"
                    ) from exc
            raise
        finally:
            self._current.reset(token)
            connection.close()

    def connection(self) -> PostgresConnection:
        connection = self._current.get()
        if connection is None:
            raise RuntimeError("Fleet PostgreSQL access requires an active transaction")
        return connection


class PostgresEnrollmentStore:
    """Shared SERIALIZABLE PostgreSQL implementation of ``EnrollmentStore``."""

    provider_name = "postgresql"

    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._transactions = _PostgresTransactionManager(connection_factory)

    def transaction(self) -> Iterator[None]:
        return self._transactions.transaction()

    def get_enrollment(self, enrollment_id: str) -> DeviceEnrollmentRecord | None:
        with self.transaction():
            row = self._transactions.connection().execute(
                "SELECT record_json FROM fleet_enrollments WHERE enrollment_id = %s",
                (enrollment_id,),
            ).fetchone()
            if row is None:
                return None
            return _validated_json_model(
                row.get("record_json"),
                DeviceEnrollmentRecord,
                "Fleet enrollment",
            )

    def put_enrollment(self, record: DeviceEnrollmentRecord) -> None:
        with self.transaction():
            connection = self._transactions.connection()
            existing = connection.execute(
                "SELECT record_version FROM fleet_enrollments WHERE enrollment_id = %s",
                (record.enrollment_id,),
            ).fetchone()
            payload = record.model_dump_json()
            updated_at = normalize_time(record.updated_at_utc or record.created_at_utc)
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO fleet_enrollments (
                        enrollment_id, device_id, public_key_fingerprint_sha256,
                        registration_state, tenant_id, workspace_id, record_version,
                        record_json, created_at_utc, updated_at_utc
                    ) VALUES (%s, %s, %s, %s, %s, %s, 1, %s::jsonb, %s, %s)
                    """,
                    (
                        record.enrollment_id,
                        record.device_id,
                        record.public_key_fingerprint_sha256,
                        record.registration_state.value,
                        record.scope_binding.tenant_id,
                        record.scope_binding.workspace_id,
                        payload,
                        normalize_time(record.created_at_utc),
                        updated_at,
                    ),
                )
                return
            connection.execute(
                """
                UPDATE fleet_enrollments
                SET device_id = %s,
                    public_key_fingerprint_sha256 = %s,
                    registration_state = %s,
                    tenant_id = %s,
                    workspace_id = %s,
                    record_version = record_version + 1,
                    record_json = %s::jsonb,
                    updated_at_utc = %s
                WHERE enrollment_id = %s
                """,
                (
                    record.device_id,
                    record.public_key_fingerprint_sha256,
                    record.registration_state.value,
                    record.scope_binding.tenant_id,
                    record.scope_binding.workspace_id,
                    payload,
                    updated_at,
                    record.enrollment_id,
                ),
            )

    def get_current_enrollment_id(self, device_id: str) -> str | None:
        with self.transaction():
            row = self._transactions.connection().execute(
                "SELECT enrollment_id FROM fleet_current_enrollments WHERE device_id = %s",
                (device_id,),
            ).fetchone()
            return None if row is None else str(row["enrollment_id"])

    def set_current_enrollment_id(self, device_id: str, enrollment_id: str) -> None:
        with self.transaction():
            self._transactions.connection().execute(
                """
                INSERT INTO fleet_current_enrollments (
                    device_id, enrollment_id, pointer_version, updated_at_utc
                ) VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (device_id) DO UPDATE
                SET enrollment_id = EXCLUDED.enrollment_id,
                    pointer_version = fleet_current_enrollments.pointer_version + 1,
                    updated_at_utc = CURRENT_TIMESTAMP
                """,
                (device_id, enrollment_id),
            )

    def list_current_enrollments(self) -> list[DeviceEnrollmentRecord]:
        with self.transaction():
            rows = self._transactions.connection().execute(
                """
                SELECT e.record_json
                FROM fleet_current_enrollments c
                JOIN fleet_enrollments e ON e.enrollment_id = c.enrollment_id
                ORDER BY e.device_id ASC
                """
            ).fetchall()
            return [
                _validated_json_model(
                    row.get("record_json"),
                    DeviceEnrollmentRecord,
                    "Fleet enrollment",
                )
                for row in rows
            ]

    def get_public_identity_owner(self, fingerprint: str) -> str | None:
        with self.transaction():
            row = self._transactions.connection().execute(
                """
                SELECT device_id
                FROM fleet_public_identity_owners
                WHERE public_key_fingerprint_sha256 = %s
                """,
                (fingerprint,),
            ).fetchone()
            return None if row is None else str(row["device_id"])

    def set_public_identity_owner(self, fingerprint: str, device_id: str) -> None:
        with self.transaction():
            cursor = self._transactions.connection().execute(
                """
                INSERT INTO fleet_public_identity_owners (
                    public_key_fingerprint_sha256, device_id
                ) VALUES (%s, %s)
                ON CONFLICT (public_key_fingerprint_sha256) DO UPDATE
                SET device_id = EXCLUDED.device_id
                WHERE fleet_public_identity_owners.device_id = EXCLUDED.device_id
                """,
                (fingerprint, device_id),
            )
            if cursor.rowcount != 1:
                raise FleetStoreConflict(
                    "public identity is already bound to another Fleet device"
                )

    def get_rotation(self, device_id: str) -> RotationWindow | None:
        with self.transaction():
            row = self._transactions.connection().execute(
                "SELECT rotation_json FROM fleet_rotations WHERE device_id = %s",
                (device_id,),
            ).fetchone()
            if row is None:
                return None
            return _validated_json_model(
                row.get("rotation_json"),
                RotationWindow,
                "Fleet rotation",
            )

    def set_rotation(self, rotation: RotationWindow) -> None:
        with self.transaction():
            self._transactions.connection().execute(
                """
                INSERT INTO fleet_rotations (
                    device_id, old_enrollment_id, new_enrollment_id,
                    overlap_expires_at_utc, rotation_version, rotation_json
                ) VALUES (%s, %s, %s, %s, 1, %s::jsonb)
                ON CONFLICT (device_id) DO UPDATE
                SET old_enrollment_id = EXCLUDED.old_enrollment_id,
                    new_enrollment_id = EXCLUDED.new_enrollment_id,
                    overlap_expires_at_utc = EXCLUDED.overlap_expires_at_utc,
                    rotation_version = fleet_rotations.rotation_version + 1,
                    rotation_json = EXCLUDED.rotation_json
                """,
                (
                    rotation.device_id,
                    rotation.old_enrollment_id,
                    rotation.new_enrollment_id,
                    normalize_time(rotation.overlap_expires_at_utc),
                    rotation.model_dump_json(),
                ),
            )

    def clear_rotation(self, device_id: str) -> None:
        with self.transaction():
            self._transactions.connection().execute(
                "DELETE FROM fleet_rotations WHERE device_id = %s",
                (device_id,),
            )

    def check_ready(self) -> bool:
        """Probe schema/database readiness only; this is not device health."""

        with self.transaction():
            row = self._transactions.connection().execute(
                "SELECT schema_version FROM ets_fleet_schema WHERE singleton = TRUE"
            ).fetchone()
            return row is not None and int(row["schema_version"]) == _POSTGRES_SCHEMA_VERSION


class PostgresFleetAdminMutationJournal:
    """Shared C3A reservation/commit semantics backed by PostgreSQL."""

    provider_name = "postgresql"

    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._transactions = _PostgresTransactionManager(connection_factory)

    def reserve(
        self,
        *,
        actor_subject: str,
        idempotency_key_sha256: str,
        request_fingerprint_sha256: str,
        now: datetime,
    ) -> FleetMutationResult | None:
        _require_sha256(idempotency_key_sha256, "idempotency key hash")
        _require_sha256(request_fingerprint_sha256, "request fingerprint")
        with self._transactions.transaction():
            connection = self._transactions.connection()
            inserted = connection.execute(
                """
                INSERT INTO fleet_admin_mutations (
                    actor_subject, idempotency_key_sha256,
                    request_fingerprint_sha256, status, result_json,
                    administrative_evidence_id, created_at_utc, committed_at_utc
                ) VALUES (%s, %s, %s, 'pending', NULL, NULL, %s, NULL)
                ON CONFLICT (actor_subject, idempotency_key_sha256) DO NOTHING
                """,
                (
                    actor_subject,
                    idempotency_key_sha256,
                    request_fingerprint_sha256,
                    normalize_time(now),
                ),
            )
            if inserted.rowcount == 1:
                return None
            row = connection.execute(
                """
                SELECT request_fingerprint_sha256, status, result_json
                FROM fleet_admin_mutations
                WHERE actor_subject = %s AND idempotency_key_sha256 = %s
                """,
                (actor_subject, idempotency_key_sha256),
            ).fetchone()
            if row is None:
                raise FleetAdminDurabilityError(
                    "Fleet mutation reservation disappeared during replay"
                )
            if str(row["request_fingerprint_sha256"]) != request_fingerprint_sha256:
                raise FleetAdminIdempotencyConflict(
                    "idempotency key was already used for another Fleet mutation"
                )
            status = str(row["status"])
            if status == "pending":
                raise FleetAdminMutationPending(
                    "prior Fleet mutation outcome is pending reconciliation"
                )
            if status != "committed":
                raise FleetAdminDurabilityError(
                    "stored Fleet mutation has an unsupported status"
                )
            return _validated_json_model(
                row.get("result_json"),
                FleetMutationResult,
                "Fleet mutation result",
                durability_error=True,
            )

    def commit(
        self,
        *,
        actor_subject: str,
        idempotency_key_sha256: str,
        request_fingerprint_sha256: str,
        result: FleetMutationResult,
        evidence: FleetAdministrativeEvidence,
        now: datetime,
    ) -> None:
        _validate_commit_binding(
            actor_subject=actor_subject,
            idempotency_key_sha256=idempotency_key_sha256,
            request_fingerprint_sha256=request_fingerprint_sha256,
            result=result,
            evidence=evidence,
        )
        with self._transactions.transaction():
            connection = self._transactions.connection()
            row = connection.execute(
                """
                SELECT request_fingerprint_sha256, status, result_json,
                       administrative_evidence_id
                FROM fleet_admin_mutations
                WHERE actor_subject = %s AND idempotency_key_sha256 = %s
                FOR UPDATE
                """,
                (actor_subject, idempotency_key_sha256),
            ).fetchone()
            if row is None:
                raise FleetAdminDurabilityError(
                    "Fleet mutation commit has no durable reservation"
                )
            if str(row["request_fingerprint_sha256"]) != request_fingerprint_sha256:
                raise FleetAdminIdempotencyConflict(
                    "idempotency reservation fingerprint changed before commit"
                )
            status = str(row["status"])
            if status == "committed":
                existing = _validated_json_model(
                    row.get("result_json"),
                    FleetMutationResult,
                    "Fleet mutation result",
                    durability_error=True,
                )
                evidence_id = str(row.get("administrative_evidence_id") or "")
                if existing != result or evidence_id != evidence.evidence_id:
                    raise FleetAdminDurabilityError(
                        "committed Fleet mutation does not match retry commit"
                    )
                return
            if status != "pending":
                raise FleetAdminDurabilityError(
                    "Fleet mutation reservation is not pending"
                )

            connection.execute(
                """
                INSERT INTO fleet_admin_evidence (
                    evidence_id, actor_subject, tenant_id, workspace_id,
                    occurred_at_utc, evidence_json
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    evidence.evidence_id,
                    evidence.actor_subject,
                    evidence.tenant_id,
                    evidence.workspace_id,
                    normalize_time(evidence.occurred_at_utc),
                    evidence.model_dump_json(),
                ),
            )
            updated = connection.execute(
                """
                UPDATE fleet_admin_mutations
                SET status = 'committed',
                    result_json = %s::jsonb,
                    administrative_evidence_id = %s,
                    committed_at_utc = %s
                WHERE actor_subject = %s
                  AND idempotency_key_sha256 = %s
                  AND status = 'pending'
                  AND request_fingerprint_sha256 = %s
                """,
                (
                    result.model_dump_json(),
                    evidence.evidence_id,
                    normalize_time(now),
                    actor_subject,
                    idempotency_key_sha256,
                    request_fingerprint_sha256,
                ),
            )
            if updated.rowcount != 1:
                raise FleetAdminDurabilityError(
                    "Fleet mutation reservation changed before durable commit"
                )

    def list_records(self) -> list[FleetAdministrativeEvidence]:
        with self._transactions.transaction():
            rows = self._transactions.connection().execute(
                """
                SELECT evidence_json
                FROM fleet_admin_evidence
                ORDER BY occurred_at_utc ASC, evidence_id ASC
                LIMIT 10000
                """
            ).fetchall()
            return [
                _validated_json_model(
                    row.get("evidence_json"),
                    FleetAdministrativeEvidence,
                    "Fleet administrative evidence",
                    durability_error=True,
                )
                for row in rows
            ]

    def count_pending(self) -> int:
        with self._transactions.transaction():
            row = self._transactions.connection().execute(
                """
                SELECT COUNT(*) AS item_count
                FROM fleet_admin_mutations
                WHERE status = 'pending'
                """
            ).fetchone()
            return 0 if row is None else int(row["item_count"])


_MIGRATION_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS ets_fleet_schema (
        singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
        schema_version INTEGER NOT NULL CHECK (schema_version > 0),
        applied_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT INTO ets_fleet_schema (singleton, schema_version)
    VALUES (TRUE, 1)
    ON CONFLICT (singleton) DO NOTHING
    """,
    """
    CREATE TABLE IF NOT EXISTS fleet_enrollments (
        enrollment_id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL,
        public_key_fingerprint_sha256 CHAR(64) NOT NULL,
        registration_state TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        record_version BIGINT NOT NULL CHECK (record_version > 0),
        record_json JSONB NOT NULL CHECK (jsonb_typeof(record_json) = 'object'),
        created_at_utc TIMESTAMPTZ NOT NULL,
        updated_at_utc TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fleet_enrollments_device_history
    ON fleet_enrollments(device_id, created_at_utc, enrollment_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fleet_enrollments_scope_state
    ON fleet_enrollments(tenant_id, workspace_id, registration_state, device_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS fleet_current_enrollments (
        device_id TEXT PRIMARY KEY,
        enrollment_id TEXT NOT NULL REFERENCES fleet_enrollments(enrollment_id),
        pointer_version BIGINT NOT NULL CHECK (pointer_version > 0),
        updated_at_utc TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fleet_public_identity_owners (
        public_key_fingerprint_sha256 CHAR(64) PRIMARY KEY,
        device_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fleet_rotations (
        device_id TEXT PRIMARY KEY,
        old_enrollment_id TEXT NOT NULL REFERENCES fleet_enrollments(enrollment_id),
        new_enrollment_id TEXT NOT NULL REFERENCES fleet_enrollments(enrollment_id),
        overlap_expires_at_utc TIMESTAMPTZ NOT NULL,
        rotation_version BIGINT NOT NULL CHECK (rotation_version > 0),
        rotation_json JSONB NOT NULL CHECK (jsonb_typeof(rotation_json) = 'object'),
        CHECK (old_enrollment_id <> new_enrollment_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fleet_admin_mutations (
        actor_subject TEXT NOT NULL,
        idempotency_key_sha256 CHAR(64) NOT NULL,
        request_fingerprint_sha256 CHAR(64) NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('pending', 'committed')),
        result_json JSONB NULL,
        administrative_evidence_id TEXT NULL,
        created_at_utc TIMESTAMPTZ NOT NULL,
        committed_at_utc TIMESTAMPTZ NULL,
        PRIMARY KEY (actor_subject, idempotency_key_sha256),
        CHECK (
            (status = 'pending' AND result_json IS NULL AND committed_at_utc IS NULL)
            OR
            (status = 'committed' AND result_json IS NOT NULL
             AND administrative_evidence_id IS NOT NULL
             AND committed_at_utc IS NOT NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fleet_admin_evidence (
        evidence_id TEXT PRIMARY KEY,
        actor_subject TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        occurred_at_utc TIMESTAMPTZ NOT NULL,
        evidence_json JSONB NOT NULL CHECK (jsonb_typeof(evidence_json) = 'object')
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fleet_admin_evidence_scope_time
    ON fleet_admin_evidence(tenant_id, workspace_id, occurred_at_utc, evidence_id)
    """,
)


def apply_fleet_postgres_migrations(
    connection_factory: PostgresConnectionFactory,
) -> None:
    """Apply the repeatable C3B schema and reject unknown schema versions."""

    transactions = _PostgresTransactionManager(connection_factory)
    with transactions.transaction():
        connection = transactions.connection()
        for statement in _MIGRATION_STATEMENTS:
            connection.execute(statement)
        row = connection.execute(
            "SELECT schema_version FROM ets_fleet_schema WHERE singleton = TRUE"
        ).fetchone()
        if row is None:
            raise FleetStoreSchemaError("Fleet PostgreSQL schema version row is missing")
        version = int(row["schema_version"])
        if version != _POSTGRES_SCHEMA_VERSION:
            raise FleetStoreSchemaError(
                f"unsupported Fleet PostgreSQL schema version: {version}"
            )


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _validated_json_model(
    raw: object,
    model: type[_ModelT],
    label: str,
    *,
    durability_error: bool = False,
) -> _ModelT:
    if raw is None:
        error_type: type[RuntimeError] = (
            FleetAdminDurabilityError if durability_error else FleetStoreSchemaError
        )
        raise error_type(f"stored {label} is missing")
    encoded = raw if isinstance(raw, str) else json.dumps(raw, separators=(",", ":"))
    try:
        return model.model_validate_json(encoded)
    except (ValidationError, ValueError, TypeError) as exc:
        error_type = FleetAdminDurabilityError if durability_error else FleetStoreSchemaError
        raise error_type(f"stored {label} failed validation") from exc


def _require_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"invalid {name}")


def _validate_commit_binding(
    *,
    actor_subject: str,
    idempotency_key_sha256: str,
    request_fingerprint_sha256: str,
    result: FleetMutationResult,
    evidence: FleetAdministrativeEvidence,
) -> None:
    if evidence.actor_subject != actor_subject:
        raise FleetAdminDurabilityError("Fleet evidence actor does not match reservation")
    if evidence.idempotency_key_sha256 != idempotency_key_sha256:
        raise FleetAdminDurabilityError(
            "Fleet evidence idempotency hash does not match reservation"
        )
    if evidence.request_fingerprint_sha256 != request_fingerprint_sha256:
        raise FleetAdminDurabilityError(
            "Fleet evidence request fingerprint does not match reservation"
        )
    if result.administrative_evidence_id != evidence.evidence_id:
        raise FleetAdminDurabilityError("Fleet result does not reference committed evidence")
    if (
        result.device_id != evidence.device_id
        or result.enrollment_id != evidence.enrollment_id
        or result.resulting_state is not evidence.resulting_state
        or result.action is not evidence.action
    ):
        raise FleetAdminDurabilityError(
            "Fleet result and administrative evidence describe different mutations"
        )


def _is_concurrency_conflict(exc: BaseException) -> bool:
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        sqlstate = getattr(current, "sqlstate", None)
        if isinstance(sqlstate, str) and sqlstate in _CONFLICT_SQLSTATES:
            return True
        current = current.__cause__ or current.__context__
    return False
