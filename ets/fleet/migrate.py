"""Controlled Entra-only schema migration entrypoint for Fleet C3B."""

from __future__ import annotations

import os

from ets.fleet.postgres import (
    AzureManagedIdentityPostgresFactory,
    apply_fleet_postgres_migrations,
)
from ets.fleet.postgres_auth import apply_fleet_postgres_authorization_migrations


def main() -> None:
    """Apply Fleet schema using the current Entra credential; no DB password fallback."""

    factory = AzureManagedIdentityPostgresFactory(
        host=_required_env("ETS_FLEET_POSTGRES_HOST"),
        database=_required_env("ETS_FLEET_POSTGRES_DATABASE"),
        user=_required_env("ETS_FLEET_POSTGRES_MIGRATION_USER"),
    )
    apply_fleet_postgres_migrations(factory)
    apply_fleet_postgres_authorization_migrations(factory)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required for Fleet PostgreSQL migration")
    return value.strip()


if __name__ == "__main__":
    main()
