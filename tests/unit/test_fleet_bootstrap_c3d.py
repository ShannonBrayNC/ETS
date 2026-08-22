from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from ets.fleet.bootstrap import (
    FleetBootstrapError,
    _ensure_runtime_principal,
    _grant_runtime_data_plane,
    _validated_database,
    _validated_guid,
    _validated_role,
)

_RUNTIME_ROLE = "ets-fleet-runtime"
_RUNTIME_OID = "11111111-2222-3333-4444-555555555555"


class _Cursor:
    def __init__(
        self,
        *,
        row: Mapping[str, object] | None = None,
        rows: list[Mapping[str, object]] | None = None,
    ) -> None:
        self._row = row
        self._rows = rows or []
        self.rowcount = 1

    def fetchone(self) -> Mapping[str, object] | None:
        return self._row

    def fetchall(self) -> list[Mapping[str, object]]:
        return self._rows


class _BootstrapConnection:
    def __init__(self, *, mapped_oid: str = _RUNTIME_OID, is_admin: int = 0) -> None:
        self.mapped_oid = mapped_oid
        self.is_admin = is_admin
        self.created = False
        self.queries: list[tuple[str, Sequence[object] | None]] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(
        self,
        query: str,
        params: Sequence[object] | None = None,
    ) -> _Cursor:
        self.queries.append((query, params))
        if "pgaadauth_list_principals" in query:
            if not self.created and self.mapped_oid == "":
                return _Cursor(rows=[])
            return _Cursor(
                rows=[
                    {
                        "rolename": _RUNTIME_ROLE,
                        "principalType": "service",
                        "objectId": self.mapped_oid or _RUNTIME_OID,
                        "isAdmin": self.is_admin,
                    }
                ]
            )
        if "pgaadauth_create_principal_with_oid" in query:
            self.created = True
            self.mapped_oid = _RUNTIME_OID
            return _Cursor(row={"created": True})
        if "FROM pg_catalog.pg_roles" in query:
            return _Cursor(
                row={
                    "rolcreaterole": False,
                    "rolcreatedb": False,
                    "rolsuper": False,
                    "rolcanlogin": True,
                }
            )
        if "pg_has_role" in query:
            return _Cursor(row={"is_admin_member": False})
        return _Cursor()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_runtime_principal_is_bound_to_exact_entra_object_and_non_admin() -> None:
    connection = _BootstrapConnection()
    _ensure_runtime_principal(
        connection,
        role_name=_RUNTIME_ROLE,
        object_id=_RUNTIME_OID,
    )
    assert connection.committed is True
    assert connection.closed is True
    assert any("pgaadauth_list_principals" in query for query, _ in connection.queries)
    assert any("pg_has_role" in query for query, _ in connection.queries)


def test_missing_runtime_principal_is_created_by_oid_not_name_lookup() -> None:
    connection = _BootstrapConnection(mapped_oid="")
    _ensure_runtime_principal(
        connection,
        role_name=_RUNTIME_ROLE,
        object_id=_RUNTIME_OID,
    )
    create_calls = [
        (query, params)
        for query, params in connection.queries
        if "pgaadauth_create_principal_with_oid" in query
    ]
    assert len(create_calls) == 1
    assert create_calls[0][1] == (_RUNTIME_ROLE, _RUNTIME_OID)


def test_wrong_entra_object_mapping_fails_closed_and_rolls_back() -> None:
    connection = _BootstrapConnection(
        mapped_oid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    with pytest.raises(FleetBootstrapError, match="different Entra object ID"):
        _ensure_runtime_principal(
            connection,
            role_name=_RUNTIME_ROLE,
            object_id=_RUNTIME_OID,
        )
    assert connection.rolled_back is True
    assert connection.closed is True


def test_admin_runtime_mapping_fails_closed() -> None:
    connection = _BootstrapConnection(is_admin=1)
    with pytest.raises(FleetBootstrapError, match="admin standing"):
        _ensure_runtime_principal(
            connection,
            role_name=_RUNTIME_ROLE,
            object_id=_RUNTIME_OID,
        )
    assert connection.rolled_back is True


def test_runtime_grants_are_data_plane_only() -> None:
    connection = _BootstrapConnection()
    _grant_runtime_data_plane(
        connection,
        database="fleet",
        role_name=_RUNTIME_ROLE,
    )
    statements = "\n".join(query for query, _ in connection.queries)
    assert "GRANT CONNECT ON DATABASE" in statements
    assert "GRANT USAGE ON SCHEMA public" in statements
    assert "GRANT SELECT, INSERT, UPDATE, DELETE" in statements
    assert "ALTER DEFAULT PRIVILEGES" in statements
    assert "CREATEROLE" not in statements
    assert "CREATEDB" not in statements
    assert "SUPERUSER" not in statements
    assert "azure_pg_admin" not in statements


def test_bootstrap_identifiers_are_bounded() -> None:
    assert _validated_role("ets-fleet-runtime") == "ets-fleet-runtime"
    assert _validated_database("fleet") == "fleet"
    assert _validated_guid(_RUNTIME_OID) == _RUNTIME_OID
    with pytest.raises(FleetBootstrapError):
        _validated_role('runtime";DROP ROLE x;--')
    with pytest.raises(FleetBootstrapError):
        _validated_database("fleet;drop")
    with pytest.raises(FleetBootstrapError):
        _validated_guid("not-a-guid")
