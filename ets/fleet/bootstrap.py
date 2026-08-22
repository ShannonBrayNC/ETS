"""Private Entra-only PostgreSQL bootstrap for the live Fleet C3D substrate."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from typing import Any, cast

from ets.fleet.postgres import (
    AzureManagedIdentityPostgresFactory,
    PostgresConnection,
    PostgresEnrollmentStore,
    apply_fleet_postgres_migrations,
)
from ets.fleet.postgres_auth import (
    PostgresFleetAuthorizationState,
    apply_fleet_postgres_authorization_migrations,
)

_ROLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DATABASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class FleetBootstrapError(RuntimeError):
    """The live Fleet PostgreSQL bootstrap failed a security invariant."""


def main() -> None:
    """Create/verify the runtime Entra principal, migrate, grant, and self-test."""

    host = _required_env("ETS_FLEET_POSTGRES_HOST")
    database = _validated_database(_required_env("ETS_FLEET_POSTGRES_DATABASE"))
    migration_user = _validated_role(
        _required_env("ETS_FLEET_POSTGRES_MIGRATION_USER")
    )
    runtime_role = _validated_role(_required_env("ETS_FLEET_RUNTIME_POSTGRES_ROLE"))
    runtime_object_id = _validated_guid(
        _required_env("ETS_FLEET_RUNTIME_PRINCIPAL_ID")
    )
    runtime_client_id = _validated_guid(_required_env("ETS_FLEET_RUNTIME_CLIENT_ID"))

    admin_factory = AzureManagedIdentityPostgresFactory(
        host=host,
        database="postgres",
        user=migration_user,
    )
    _ensure_runtime_principal(
        admin_factory(),
        role_name=runtime_role,
        object_id=runtime_object_id,
    )

    migration_factory = AzureManagedIdentityPostgresFactory(
        host=host,
        database=database,
        user=migration_user,
    )
    apply_fleet_postgres_migrations(migration_factory)
    apply_fleet_postgres_authorization_migrations(migration_factory)
    _grant_runtime_data_plane(
        migration_factory(),
        database=database,
        role_name=runtime_role,
    )

    from azure.identity import ManagedIdentityCredential

    runtime_credential = ManagedIdentityCredential(client_id=runtime_client_id)
    runtime_factory = AzureManagedIdentityPostgresFactory(
        host=host,
        database=database,
        user=runtime_role,
        credential=cast(Any, runtime_credential),
    )
    enrollment_ready = PostgresEnrollmentStore(runtime_factory).check_ready()
    authorization_ready = PostgresFleetAuthorizationState(runtime_factory).check_ready()
    if not enrollment_ready or not authorization_ready:
        raise FleetBootstrapError(
            "Fleet runtime identity cannot read the qualified shared schema"
        )

    print(
        json.dumps(
            {
                "schema_version": "ets.fleet.c3d.bootstrap.v1",
                "runtime_role": runtime_role,
                "runtime_principal_object_id": runtime_object_id.lower(),
                "runtime_admin": False,
                "runtime_createrole": False,
                "runtime_createdb": False,
                "runtime_superuser": False,
                "schema_ready": True,
                "authorization_schema_ready": True,
                "database_password_used": False,
            },
            sort_keys=True,
        )
    )


def _ensure_runtime_principal(
    connection: PostgresConnection,
    *,
    role_name: str,
    object_id: str,
) -> None:
    try:
        connection.execute("BEGIN")
        principals = connection.execute(
            "SELECT * FROM pg_catalog.pgaadauth_list_principals(false)"
        ).fetchall()
        matches = [
            row
            for row in principals
            if str(_row_value(row, "rolename", "roleName") or "") == role_name
        ]
        if len(matches) > 1:
            raise FleetBootstrapError("duplicate Microsoft Entra role mapping detected")
        if not matches:
            connection.execute(
                """
                SELECT pg_catalog.pgaadauth_create_principal_with_oid(
                    %s, %s, 'service', false, false
                )
                """,
                (role_name, object_id),
            ).fetchone()
            principals = connection.execute(
                "SELECT * FROM pg_catalog.pgaadauth_list_principals(false)"
            ).fetchall()
            matches = [
                row
                for row in principals
                if str(_row_value(row, "rolename", "roleName") or "") == role_name
            ]
        if len(matches) != 1:
            raise FleetBootstrapError("runtime Microsoft Entra role mapping is missing")

        principal = matches[0]
        mapped_oid = str(_row_value(principal, "objectId", "objectid") or "")
        principal_type = str(
            _row_value(principal, "principalType", "principaltype") or ""
        ).lower()
        is_admin = _as_zero_one(_row_value(principal, "isAdmin", "isadmin"))
        if mapped_oid.lower() != object_id.lower():
            raise FleetBootstrapError(
                "runtime PostgreSQL role is mapped to a different Entra object ID"
            )
        if principal_type != "service":
            raise FleetBootstrapError(
                "runtime PostgreSQL role is not mapped to an Entra service principal"
            )
        if is_admin != 0:
            raise FleetBootstrapError("runtime PostgreSQL role unexpectedly has admin standing")

        role = connection.execute(
            """
            SELECT rolcreaterole, rolcreatedb, rolsuper, rolcanlogin
            FROM pg_catalog.pg_roles
            WHERE rolname = %s
            """,
            (role_name,),
        ).fetchone()
        if role is None:
            raise FleetBootstrapError("runtime PostgreSQL role disappeared during bootstrap")
        if _required_bool(role, "rolcreaterole"):
            raise FleetBootstrapError("runtime PostgreSQL role may not have CREATEROLE")
        if _required_bool(role, "rolcreatedb"):
            raise FleetBootstrapError("runtime PostgreSQL role may not have CREATEDB")
        if _required_bool(role, "rolsuper"):
            raise FleetBootstrapError("runtime PostgreSQL role may not be superuser")
        if not _required_bool(role, "rolcanlogin"):
            raise FleetBootstrapError("runtime PostgreSQL role must be login-capable")

        membership = connection.execute(
            "SELECT pg_has_role(%s, 'azure_pg_admin', 'member') AS is_admin_member",
            (role_name,),
        ).fetchone()
        if membership is None or _required_bool(membership, "is_admin_member"):
            raise FleetBootstrapError(
                "runtime PostgreSQL role may not be a member of azure_pg_admin"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _grant_runtime_data_plane(
    connection: PostgresConnection,
    *,
    database: str,
    role_name: str,
) -> None:
    quoted_database = _quote_identifier(database)
    quoted_role = _quote_identifier(role_name)
    statements = (
        f"GRANT CONNECT ON DATABASE {quoted_database} TO {quoted_role}",
        f"GRANT USAGE ON SCHEMA public TO {quoted_role}",
        (
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
            f"TO {quoted_role}"
        ),
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES "
            f"TO {quoted_role}"
        ),
    )
    try:
        connection.execute("BEGIN")
        for statement in statements:
            connection.execute(statement)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _row_value(row: Mapping[str, object], *names: str) -> object | None:
    for name in names:
        if name in row:
            return row[name]
    return None


def _required_bool(row: Mapping[str, object], name: str) -> bool:
    value = row.get(name)
    if not isinstance(value, bool):
        raise FleetBootstrapError(f"PostgreSQL {name} flag is invalid")
    return value


def _as_zero_one(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in {0, 1}:
        return value
    raise FleetBootstrapError("Microsoft Entra admin flag is invalid")


def _validated_role(value: str) -> str:
    if _ROLE_RE.fullmatch(value) is None:
        raise FleetBootstrapError("Fleet PostgreSQL role name is invalid")
    return value


def _validated_database(value: str) -> str:
    if _DATABASE_RE.fullmatch(value) is None:
        raise FleetBootstrapError("Fleet PostgreSQL database name is invalid")
    return value


def _validated_guid(value: str) -> str:
    if _GUID_RE.fullmatch(value) is None:
        raise FleetBootstrapError("Fleet managed identity identifier is invalid")
    return value


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise FleetBootstrapError(f"{name} is required for Fleet live bootstrap")
    return value.strip()


if __name__ == "__main__":
    main()
