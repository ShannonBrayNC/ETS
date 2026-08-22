"""Shared PostgreSQL authorization state for ETS Fleet C3B.

This store contains server-owned scope and session standing only. It does not
persist access tokens, refresh tokens, cookies, CSRF tokens, credentials, or raw
browser session identifiers.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from pydantic import ValidationError

from ets.fleet.entra_session import FleetSessionStanding
from ets.fleet.models import ScopeBinding, normalize_time
from ets.fleet.portal import FleetRole
from ets.fleet.postgres import PostgresConnection, PostgresConnectionFactory


class FleetAuthorizationStoreError(RuntimeError):
    """Shared authorization state is malformed or unavailable."""


class PostgresFleetAuthorizationState:
    """Server-owned ETS scope, role, revocation, and session-generation state."""

    def __init__(self, connection_factory: PostgresConnectionFactory) -> None:
        self._factory = connection_factory

    def resolve_scopes(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
    ) -> tuple[ScopeBinding, ...]:
        with self._transaction() as connection:
            rows = connection.execute(
                """
                SELECT tenant_id, workspace_id
                FROM fleet_principal_scopes
                WHERE entra_tenant_id = %s
                  AND subject = %s
                  AND active = TRUE
                ORDER BY tenant_id ASC, workspace_id ASC
                LIMIT 128
                """,
                (entra_tenant_id, subject),
            ).fetchall()
        try:
            return tuple(
                ScopeBinding(
                    tenant_id=str(row["tenant_id"]),
                    workspace_id=str(row["workspace_id"]),
                )
                for row in rows
            )
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise FleetAuthorizationStoreError(
                "stored Fleet scope mapping failed validation"
            ) from exc

    def resolve_standing(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
        session_id: str,
    ) -> FleetSessionStanding | None:
        session_hash = _sha256(session_id)
        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT active, generation, roles_json, not_before_utc,
                       step_up_not_before_utc
                FROM fleet_session_standing
                WHERE entra_tenant_id = %s
                  AND subject = %s
                  AND session_id_sha256 = %s
                """,
                (entra_tenant_id, subject, session_hash),
            ).fetchone()
        if row is None:
            return None
        try:
            raw_roles = row["roles_json"]
            decoded = raw_roles if isinstance(raw_roles, list) else json.loads(str(raw_roles))
            if not isinstance(decoded, list):
                raise ValueError("roles_json is not an array")
            roles = tuple(FleetRole(str(item)) for item in decoded)
            if not roles or len(set(roles)) != len(roles):
                raise ValueError("stored Fleet roles are empty or duplicated")
            not_before = row["not_before_utc"]
            if not isinstance(not_before, datetime):
                raise ValueError("stored Fleet not-before timestamp is invalid")
            raw_step_up = row.get("step_up_not_before_utc")
            if raw_step_up is not None and not isinstance(raw_step_up, datetime):
                raise ValueError("stored Fleet step-up timestamp is invalid")
            return FleetSessionStanding(
                active=bool(row["active"]),
                generation=int(row["generation"]),
                roles=roles,
                not_before_utc=not_before,
                step_up_not_before_utc=raw_step_up,
            )
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise FleetAuthorizationStoreError(
                "stored Fleet session standing failed validation"
            ) from exc

    def grant_scope(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
        scope: ScopeBinding,
        now: datetime,
    ) -> None:
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO fleet_principal_scopes (
                    entra_tenant_id, subject, tenant_id, workspace_id,
                    active, updated_at_utc
                ) VALUES (%s, %s, %s, %s, TRUE, %s)
                ON CONFLICT (entra_tenant_id, subject, tenant_id, workspace_id)
                DO UPDATE SET active = TRUE, updated_at_utc = EXCLUDED.updated_at_utc
                """,
                (
                    entra_tenant_id,
                    subject,
                    scope.tenant_id,
                    scope.workspace_id,
                    normalize_time(now),
                ),
            )

    def revoke_scope(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
        scope: ScopeBinding,
        now: datetime,
    ) -> None:
        with self._transaction() as connection:
            connection.execute(
                """
                UPDATE fleet_principal_scopes
                SET active = FALSE, updated_at_utc = %s
                WHERE entra_tenant_id = %s
                  AND subject = %s
                  AND tenant_id = %s
                  AND workspace_id = %s
                """,
                (
                    normalize_time(now),
                    entra_tenant_id,
                    subject,
                    scope.tenant_id,
                    scope.workspace_id,
                ),
            )

    def upsert_session_standing(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
        session_id: str,
        standing: FleetSessionStanding,
        now: datetime,
    ) -> None:
        canonical_roles = sorted({role.value for role in standing.roles})
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO fleet_session_standing (
                    entra_tenant_id, subject, session_id_sha256,
                    active, generation, roles_json, not_before_utc,
                    step_up_not_before_utc, updated_at_utc
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                ON CONFLICT (entra_tenant_id, subject, session_id_sha256)
                DO UPDATE SET
                    active = EXCLUDED.active,
                    generation = EXCLUDED.generation,
                    roles_json = EXCLUDED.roles_json,
                    not_before_utc = EXCLUDED.not_before_utc,
                    step_up_not_before_utc = EXCLUDED.step_up_not_before_utc,
                    updated_at_utc = EXCLUDED.updated_at_utc
                """,
                (
                    entra_tenant_id,
                    subject,
                    _sha256(session_id),
                    standing.active,
                    standing.generation,
                    json.dumps(canonical_roles, separators=(",", ":")),
                    normalize_time(standing.not_before_utc),
                    (
                        None
                        if standing.step_up_not_before_utc is None
                        else normalize_time(standing.step_up_not_before_utc)
                    ),
                    normalize_time(now),
                ),
            )

    def revoke_session(
        self,
        *,
        subject: str,
        entra_tenant_id: str,
        session_id: str,
        new_generation: int,
        now: datetime,
    ) -> None:
        if new_generation < 1:
            raise ValueError("Fleet session generation must be positive")
        with self._transaction() as connection:
            connection.execute(
                """
                UPDATE fleet_session_standing
                SET active = FALSE,
                    generation = %s,
                    not_before_utc = %s,
                    step_up_not_before_utc = %s,
                    updated_at_utc = %s
                WHERE entra_tenant_id = %s
                  AND subject = %s
                  AND session_id_sha256 = %s
                """,
                (
                    new_generation,
                    normalize_time(now),
                    normalize_time(now),
                    normalize_time(now),
                    entra_tenant_id,
                    subject,
                    _sha256(session_id),
                ),
            )

    @contextmanager
    def _transaction(self) -> Iterator[PostgresConnection]:
        connection = self._factory()
        try:
            connection.execute("BEGIN ISOLATION LEVEL SERIALIZABLE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def apply_fleet_postgres_authorization_migrations(
    connection_factory: PostgresConnectionFactory,
) -> None:
    """Create the server-owned C3B scope/session standing tables."""

    store = PostgresFleetAuthorizationState(connection_factory)
    with store._transaction() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fleet_principal_scopes (
                entra_tenant_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                active BOOLEAN NOT NULL,
                updated_at_utc TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (entra_tenant_id, subject, tenant_id, workspace_id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fleet_principal_scopes_active
            ON fleet_principal_scopes(entra_tenant_id, subject, active)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fleet_session_standing (
                entra_tenant_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                session_id_sha256 CHAR(64) NOT NULL,
                active BOOLEAN NOT NULL,
                generation BIGINT NOT NULL CHECK (generation > 0),
                roles_json JSONB NOT NULL CHECK (jsonb_typeof(roles_json) = 'array'),
                not_before_utc TIMESTAMPTZ NOT NULL,
                step_up_not_before_utc TIMESTAMPTZ NULL,
                updated_at_utc TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (entra_tenant_id, subject, session_id_sha256)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fleet_session_standing_active
            ON fleet_session_standing(entra_tenant_id, subject, active, updated_at_utc)
            """
        )


def _sha256(value: str) -> str:
    if not value:
        raise ValueError("Fleet session identifier is required")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
