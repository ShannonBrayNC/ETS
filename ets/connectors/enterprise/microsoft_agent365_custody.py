"""Durable Agent 365 source custody and Gateway credential binding for A365-Q0."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
)
from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease, CredentialProvider
from ets.connectors.enterprise.microsoft_agent365 import MicrosoftSourceEnvelopeV1
from ets.connectors.enterprise.microsoft_agent365_http import (
    MicrosoftAgent365HttpClient,
    MicrosoftAgent365InventorySnapshot,
    MicrosoftAgent365LiveCollector,
)


class MicrosoftAgent365CustodyError(RuntimeError):
    """Base error for durable Agent 365 source custody."""


class MicrosoftAgent365CustodyConflict(MicrosoftAgent365CustodyError):
    """Raised when durable source history would regress, fork, or overlap."""


class StrictAgent365CustodyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftAgent365SnapshotCheckpointV1(StrictAgent365CustodyModel):
    """Durable snapshot boundary; this is collector state, not an ETS verification verdict."""

    schema_version: Literal["ets.connector.microsoft.agent365.snapshot_checkpoint.v1"] = (
        "ets.connector.microsoft.agent365.snapshot_checkpoint.v1"
    )
    tenant_id: str = Field(min_length=36, max_length=36)
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_at_utc: datetime
    envelope_count: int = Field(ge=1)
    package_count: int = Field(ge=0)
    first_acquisition_sequence: int = Field(ge=0)
    last_acquisition_sequence: int = Field(ge=0)
    last_envelope_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    inventory_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_checkpoint_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    checkpoint_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("completed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checkpoint time must be timezone-aware")
        return value.astimezone(UTC)


class MicrosoftAgent365CustodyStore:
    """Crash-consistent SQLite reference store for Agent 365 source envelopes."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def commit_snapshot(
        self,
        snapshot: MicrosoftAgent365InventorySnapshot,
        *,
        completed_at_utc: datetime,
    ) -> MicrosoftAgent365SnapshotCheckpointV1:
        envelopes = tuple(item.envelope for item in snapshot.inventory_pages) + tuple(
            item.envelope for item in snapshot.package_details
        )
        if not envelopes:
            raise ValueError("Agent 365 snapshot must contain at least one acquisition")

        tenant_id = envelopes[0].tenant_id
        if any(item.tenant_id != tenant_id for item in envelopes):
            raise MicrosoftAgent365CustodyConflict("snapshot contains more than one tenant")

        package_state: dict[str, str] = {}
        for page in snapshot.inventory_pages:
            for package in page.page.packages:
                existing = package_state.get(package.package_id)
                current = package.normalized_configuration_sha256
                if existing is not None and existing != current:
                    raise MicrosoftAgent365CustodyConflict(
                        "snapshot contains conflicting configurations for one package"
                    )
                package_state[package.package_id] = current

        normalized_time = _utc(completed_at_utc)
        state_json = _canonical_json(package_state)
        state_digest = hashlib.sha256(state_json.encode("utf-8")).hexdigest()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous_envelope = connection.execute(
                """
                SELECT acquisition_sequence, envelope_hash
                FROM agent365_envelopes
                WHERE tenant_id = ?
                ORDER BY acquisition_sequence DESC
                LIMIT 1
                """,
                (tenant_id,),
            ).fetchone()
            expected_sequence = 0 if previous_envelope is None else int(previous_envelope[0]) + 1
            expected_previous_hash = (
                None if previous_envelope is None else str(previous_envelope[1])
            )

            for envelope in envelopes:
                if envelope.acquisition_sequence != expected_sequence:
                    raise MicrosoftAgent365CustodyConflict(
                        "Agent 365 envelope acquisition sequence is not contiguous"
                    )
                if envelope.previous_envelope_hash != expected_previous_hash:
                    raise MicrosoftAgent365CustodyConflict(
                        "Agent 365 envelope chain does not extend durable custody"
                    )
                try:
                    connection.execute(
                        """
                        INSERT INTO agent365_envelopes(
                            tenant_id, acquisition_sequence, envelope_hash,
                            source_type, raw_payload_sha256, envelope_json
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            envelope.tenant_id,
                            envelope.acquisition_sequence,
                            envelope.envelope_hash,
                            envelope.source_type,
                            envelope.raw_payload_sha256,
                            envelope.model_dump_json(),
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise MicrosoftAgent365CustodyConflict(
                        "Agent 365 envelope already exists or overlaps durable history"
                    ) from exc
                expected_sequence += 1
                expected_previous_hash = envelope.envelope_hash

            previous_checkpoint_row = connection.execute(
                """
                SELECT checkpoint_hash
                FROM agent365_snapshot_checkpoints
                WHERE tenant_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT 1
                """,
                (tenant_id,),
            ).fetchone()
            previous_checkpoint_hash = (
                None if previous_checkpoint_row is None else str(previous_checkpoint_row[0])
            )

            snapshot_material = {
                "tenant_id": tenant_id,
                "completed_at_utc": normalized_time.isoformat(),
                "first_acquisition_sequence": envelopes[0].acquisition_sequence,
                "last_acquisition_sequence": envelopes[-1].acquisition_sequence,
                "last_envelope_hash": envelopes[-1].envelope_hash,
                "inventory_state_sha256": state_digest,
                "previous_checkpoint_hash": previous_checkpoint_hash,
            }
            snapshot_id = _sha256_json({**snapshot_material, "kind": "snapshot-id"})
            checkpoint_hash = _sha256_json(
                {
                    **snapshot_material,
                    "snapshot_id": snapshot_id,
                    "envelope_count": len(envelopes),
                    "package_count": len(package_state),
                }
            )
            checkpoint = MicrosoftAgent365SnapshotCheckpointV1(
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                completed_at_utc=normalized_time,
                envelope_count=len(envelopes),
                package_count=len(package_state),
                first_acquisition_sequence=envelopes[0].acquisition_sequence,
                last_acquisition_sequence=envelopes[-1].acquisition_sequence,
                last_envelope_hash=envelopes[-1].envelope_hash,
                inventory_state_sha256=state_digest,
                previous_checkpoint_hash=previous_checkpoint_hash,
                checkpoint_hash=checkpoint_hash,
            )
            connection.execute(
                """
                INSERT INTO agent365_snapshot_checkpoints(
                    tenant_id, snapshot_id, checkpoint_hash, checkpoint_json, inventory_state_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    snapshot_id,
                    checkpoint_hash,
                    checkpoint.model_dump_json(),
                    state_json,
                ),
            )
        return checkpoint

    def get_latest_checkpoint(
        self,
        tenant_id: str,
    ) -> MicrosoftAgent365SnapshotCheckpointV1 | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT checkpoint_json
                FROM agent365_snapshot_checkpoints
                WHERE tenant_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT 1
                """,
                (tenant_id.lower(),),
            ).fetchone()
        if row is None:
            return None
        return MicrosoftAgent365SnapshotCheckpointV1.model_validate_json(str(row[0]))

    def list_envelopes(self, tenant_id: str) -> tuple[MicrosoftSourceEnvelopeV1, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT envelope_json
                FROM agent365_envelopes
                WHERE tenant_id = ?
                ORDER BY acquisition_sequence
                """,
                (tenant_id.lower(),),
            ).fetchall()
        return tuple(MicrosoftSourceEnvelopeV1.model_validate_json(str(row[0])) for row in rows)

    def get_latest_inventory_state(self, tenant_id: str) -> dict[str, str]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT inventory_state_json
                FROM agent365_snapshot_checkpoints
                WHERE tenant_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT 1
                """,
                (tenant_id.lower(),),
            ).fetchone()
        if row is None:
            return {}
        decoded = json.loads(str(row[0]))
        if not isinstance(decoded, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in decoded.items()
        ):
            raise MicrosoftAgent365CustodyError("durable Agent 365 inventory state is invalid")
        return dict(decoded)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent365_envelopes(
                    tenant_id TEXT NOT NULL,
                    acquisition_sequence INTEGER NOT NULL,
                    envelope_hash TEXT NOT NULL UNIQUE,
                    source_type TEXT NOT NULL,
                    raw_payload_sha256 TEXT NOT NULL,
                    envelope_json TEXT NOT NULL,
                    PRIMARY KEY(tenant_id, acquisition_sequence)
                );
                CREATE TABLE IF NOT EXISTS agent365_snapshot_checkpoints(
                    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL UNIQUE,
                    checkpoint_hash TEXT NOT NULL UNIQUE,
                    checkpoint_json TEXT NOT NULL,
                    inventory_state_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent365_checkpoint_tenant
                    ON agent365_snapshot_checkpoints(tenant_id, checkpoint_id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection


class MicrosoftAgent365CredentialSession:
    """Bind the Agent 365 collector to the existing short-lived Graph credential broker."""

    def __init__(
        self,
        provider: CredentialProvider,
        reference: CredentialReferenceV1,
    ) -> None:
        if reference.ref != MICROSOFT_GRAPH_CREDENTIAL_REFERENCE:
            raise ValueError("Agent 365 requires the server-owned Microsoft Graph credential route")
        self._lease: CredentialLease = provider.resolve(reference)
        try:
            self.client = MicrosoftAgent365HttpClient(self._lease.reveal())
        except Exception:
            self._lease.close()
            raise
        self._closed = False

    def collector(
        self,
        *,
        tenant_id: str,
        collector_identity: str,
        collector_version: str,
    ) -> MicrosoftAgent365LiveCollector:
        if self._closed:
            raise RuntimeError("Agent 365 credential session is closed")
        return MicrosoftAgent365LiveCollector(
            self.client,
            tenant_id=tenant_id,
            collector_identity=collector_identity,
            collector_version=collector_version,
        )

    def close(self) -> None:
        if self._closed:
            return
        self.client.close()
        self._lease.close()
        self._closed = True

    def __enter__(self) -> MicrosoftAgent365CredentialSession:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Agent 365 custody timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _canonical_json(value: Mapping[str, str]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
