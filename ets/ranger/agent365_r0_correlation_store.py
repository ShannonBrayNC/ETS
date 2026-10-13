"""Durable mission-scoped storage for sanitized Agent 365 correlation bundles.

The verified Ranger R0 Evidence Object v2 bundle remains authoritative for the physical chain.
This store retains a separate Microsoft observation/correlation proposition keyed by the same
``mission_id``. The stored model contains only source references, hashes, identifiers, and
correlation metadata; raw Agent 365 / OTLP payload bodies are not part of this schema.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, cast

from pydantic import ValidationError

from ets.demos.agent365_r0_correlation import Agent365R0CorrelationBundleV1

_STORE_SCHEMA_VERSION = 1


class Agent365R0CorrelationStoreError(ValueError):
    """Raised when retained Agent 365 correlation state cannot be trusted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SQLiteAgent365R0CorrelationStore:
    """Retry-safe store for one sanitized Agent 365 correlation bundle per mission."""

    provider_name = "sqlite"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def save(self, bundle: Agent365R0CorrelationBundleV1) -> None:
        """Persist one bundle; identical replay is idempotent and conflict fails closed."""

        bundle_json = _canonical_json(bundle.model_dump(mode="json"))
        bundle_sha256 = _sha256_text(bundle_json)
        with self._lock:
            existing = self._connection.execute(
                """
                SELECT bundle_sha256
                FROM agent365_r0_correlation_bundles
                WHERE mission_id = ?
                """,
                (bundle.mission_id,),
            ).fetchone()
            if existing is not None:
                if str(existing["bundle_sha256"]) == bundle_sha256:
                    return
                raise Agent365R0CorrelationStoreError(
                    "duplicate_mission_conflict",
                    "mission_id already has different retained Agent 365 correlation evidence",
                )

            self._connection.execute(
                """
                INSERT INTO agent365_r0_correlation_bundles (
                    mission_id, bundle_json, bundle_sha256
                )
                VALUES (?, ?, ?)
                """,
                (bundle.mission_id, bundle_json, bundle_sha256),
            )
            self._connection.commit()

    def load(self, mission_id: str) -> Agent365R0CorrelationBundleV1:
        """Load one digest-verified sanitized correlation bundle."""

        if not mission_id:
            raise Agent365R0CorrelationStoreError(
                "empty_mission_id",
                "mission_id must be a non-empty string",
            )
        with self._lock:
            row = self._connection.execute(
                """
                SELECT bundle_json, bundle_sha256
                FROM agent365_r0_correlation_bundles
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()
        if row is None:
            raise Agent365R0CorrelationStoreError(
                "mission_not_found",
                "no Agent 365 correlation bundle exists for mission_id",
            )

        bundle_json = str(row["bundle_json"])
        stored_sha256 = str(row["bundle_sha256"])
        if _sha256_text(bundle_json) != stored_sha256:
            raise Agent365R0CorrelationStoreError(
                "stored_bundle_hash_mismatch",
                "stored Agent 365 correlation no longer matches its SHA-256 commitment",
            )
        try:
            bundle = Agent365R0CorrelationBundleV1.model_validate_json(bundle_json)
        except ValidationError as exc:
            raise Agent365R0CorrelationStoreError(
                "stored_bundle_invalid",
                "stored Agent 365 correlation failed schema validation",
            ) from exc
        if bundle.mission_id != mission_id:
            raise Agent365R0CorrelationStoreError(
                "stored_mission_mismatch",
                "stored Agent 365 correlation belongs to another mission_id",
            )
        return bundle

    def contains(self, mission_id: str) -> bool:
        if not mission_id:
            return False
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1
                FROM agent365_r0_correlation_bundles
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()
        return row is not None

    def mission_ids(self) -> tuple[str, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT mission_id
                FROM agent365_r0_correlation_bundles
                ORDER BY mission_id ASC
                """
            ).fetchall()
        return tuple(str(row["mission_id"]) for row in rows)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=FULL")
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent365_r0_correlation_store_schema (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent365_r0_correlation_bundles (
                    mission_id TEXT PRIMARY KEY,
                    bundle_json TEXT NOT NULL,
                    bundle_sha256 TEXT NOT NULL
                );
                """
            )
            row = self._connection.execute(
                "SELECT version FROM agent365_r0_correlation_store_schema WHERE id = 1"
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO agent365_r0_correlation_store_schema (id, version) VALUES (1, ?)",
                    (_STORE_SCHEMA_VERSION,),
                )
            elif int(row["version"]) != _STORE_SCHEMA_VERSION:
                raise Agent365R0CorrelationStoreError(
                    "unsupported_store_schema",
                    "Agent 365 correlation store schema version is not supported",
                )
            self._connection.commit()


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _decode_json_object(value: str) -> dict[str, Any]:
    """Reserved helper for schema migrations; validates object shape without coercion."""

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise Agent365R0CorrelationStoreError(
            "stored_bundle_invalid_json",
            "stored Agent 365 correlation is not valid JSON",
        ) from exc
    if not isinstance(decoded, dict):
        raise Agent365R0CorrelationStoreError(
            "stored_bundle_invalid_shape",
            "stored Agent 365 correlation must be a JSON object",
        )
    return cast(dict[str, Any], decoded)


__all__ = [
    "Agent365R0CorrelationStoreError",
    "SQLiteAgent365R0CorrelationStore",
]
