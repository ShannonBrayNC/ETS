"""Deterministic Agent 365 inventory reconciliation and derived change history for A365-Q0."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.connectors.enterprise.microsoft_agent365_custody import (
    MicrosoftAgent365SnapshotCheckpointV1,
)

Agent365ChangeKind = Literal["ADDED", "CHANGED", "REMOVED", "UNCHANGED"]


class MicrosoftAgent365ReconciliationError(RuntimeError):
    """Base error for Agent 365 reconciliation and derived history."""


class MicrosoftAgent365ReconciliationConflict(MicrosoftAgent365ReconciliationError):
    """Raised when derived history would fork, overlap, or detach from custody."""


class StrictAgent365ReconciliationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftAgent365PackageChangeV1(StrictAgent365ReconciliationModel):
    """One package-state comparison between two adjacent retained snapshots."""

    schema_version: Literal["ets.connector.microsoft.agent365.package_change.v1"] = (
        "ets.connector.microsoft.agent365.package_change.v1"
    )
    package_id: str = Field(min_length=1, max_length=1024)
    change_kind: Agent365ChangeKind
    previous_configuration_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    current_configuration_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def validate_change_shape(self) -> Self:
        previous = self.previous_configuration_sha256
        current = self.current_configuration_sha256
        if self.change_kind == "ADDED" and not (previous is None and current is not None):
            raise ValueError("ADDED requires only a current configuration commitment")
        if self.change_kind == "REMOVED" and not (previous is not None and current is None):
            raise ValueError("REMOVED requires only a previous configuration commitment")
        if self.change_kind == "CHANGED" and not (
            previous is not None and current is not None and previous != current
        ):
            raise ValueError("CHANGED requires distinct previous and current commitments")
        if self.change_kind == "UNCHANGED" and not (
            previous is not None and current is not None and previous == current
        ):
            raise ValueError("UNCHANGED requires matching previous and current commitments")
        return self


class MicrosoftAgent365InventoryReconciliationV1(StrictAgent365ReconciliationModel):
    """Derived comparison of two adjacent Agent 365 custody checkpoints."""

    schema_version: Literal["ets.connector.microsoft.agent365.inventory_reconciliation.v1"] = (
        "ets.connector.microsoft.agent365.inventory_reconciliation.v1"
    )
    tenant_id: str = Field(min_length=36, max_length=36)
    previous_snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_checkpoint_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_checkpoint_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_inventory_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_inventory_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at_utc: datetime
    changes: tuple[MicrosoftAgent365PackageChangeV1, ...]
    added_count: int = Field(ge=0)
    changed_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    unchanged_count: int = Field(ge=0)
    previous_reconciliation_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    reconciliation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reconciliation time must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_counts_and_order(self) -> Self:
        package_ids = tuple(change.package_id for change in self.changes)
        if package_ids != tuple(sorted(package_ids)):
            raise ValueError("reconciliation changes must use canonical package-id order")
        if len(package_ids) != len(set(package_ids)):
            raise ValueError("reconciliation cannot contain duplicate package ids")
        expected = {
            "ADDED": sum(change.change_kind == "ADDED" for change in self.changes),
            "CHANGED": sum(change.change_kind == "CHANGED" for change in self.changes),
            "REMOVED": sum(change.change_kind == "REMOVED" for change in self.changes),
            "UNCHANGED": sum(change.change_kind == "UNCHANGED" for change in self.changes),
        }
        if self.added_count != expected["ADDED"]:
            raise ValueError("added_count does not match reconciliation changes")
        if self.changed_count != expected["CHANGED"]:
            raise ValueError("changed_count does not match reconciliation changes")
        if self.removed_count != expected["REMOVED"]:
            raise ValueError("removed_count does not match reconciliation changes")
        if self.unchanged_count != expected["UNCHANGED"]:
            raise ValueError("unchanged_count does not match reconciliation changes")
        return self


class MicrosoftAgent365ConfigurationChangeProjectionV1(StrictAgent365ReconciliationModel):
    """Evidence-model projection without claiming independent verification."""

    schema_version: Literal[
        "ets.connector.microsoft.agent365.configuration_change_projection.v1"
    ] = "ets.connector.microsoft.agent365.configuration_change_projection.v1"
    object_class: Literal["A365_AGENT_CONFIGURATION"] = "A365_AGENT_CONFIGURATION"
    observation_semantics: Literal["microsoft_attributable_reconciliation"] = (
        "microsoft_attributable_reconciliation"
    )
    tenant_id: str = Field(min_length=36, max_length=36)
    package_id: str = Field(min_length=1, max_length=1024)
    change_kind: Agent365ChangeKind
    previous_configuration_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    current_configuration_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    previous_checkpoint_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_checkpoint_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reconciliation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class MicrosoftAgent365ReconciliationHistoryStore:
    """Crash-consistent history for derived reconciliation records.

    Snapshot custody remains authoritative. This store retains deterministic comparisons of
    adjacent custody checkpoints; it does not convert Microsoft observations into an independent
    verification verdict.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def reconcile_and_commit(
        self,
        *,
        previous_checkpoint: MicrosoftAgent365SnapshotCheckpointV1,
        current_checkpoint: MicrosoftAgent365SnapshotCheckpointV1,
        previous_state: Mapping[str, str],
        current_state: Mapping[str, str],
        include_unchanged: bool = True,
    ) -> MicrosoftAgent365InventoryReconciliationV1:
        latest = self.get_latest(current_checkpoint.tenant_id)
        previous_reconciliation_hash = None if latest is None else latest.reconciliation_hash
        record = reconcile_agent365_inventory(
            previous_checkpoint=previous_checkpoint,
            current_checkpoint=current_checkpoint,
            previous_state=previous_state,
            current_state=current_state,
            include_unchanged=include_unchanged,
            previous_reconciliation_hash=previous_reconciliation_hash,
        )
        self.commit(record)
        return record

    def commit(self, record: MicrosoftAgent365InventoryReconciliationV1) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT reconciliation_hash
                FROM agent365_reconciliations
                WHERE tenant_id = ? AND current_checkpoint_hash = ?
                """,
                (record.tenant_id, record.current_checkpoint_hash),
            ).fetchone()
            if existing is not None:
                if str(existing[0]) == record.reconciliation_hash:
                    return
                raise MicrosoftAgent365ReconciliationConflict(
                    "current Agent 365 checkpoint already has a different reconciliation"
                )

            latest = connection.execute(
                """
                SELECT current_checkpoint_hash, reconciliation_hash
                FROM agent365_reconciliations
                WHERE tenant_id = ?
                ORDER BY reconciliation_id DESC
                LIMIT 1
                """,
                (record.tenant_id,),
            ).fetchone()
            if latest is None:
                if record.previous_reconciliation_hash is not None:
                    raise MicrosoftAgent365ReconciliationConflict(
                        "first reconciliation cannot claim a predecessor reconciliation"
                    )
            else:
                if record.previous_checkpoint_hash != str(latest[0]):
                    raise MicrosoftAgent365ReconciliationConflict(
                        "reconciliation does not extend the prior current checkpoint"
                    )
                if record.previous_reconciliation_hash != str(latest[1]):
                    raise MicrosoftAgent365ReconciliationConflict(
                        "reconciliation hash chain does not extend durable history"
                    )

            try:
                connection.execute(
                    """
                    INSERT INTO agent365_reconciliations(
                        tenant_id,
                        previous_checkpoint_hash,
                        current_checkpoint_hash,
                        reconciliation_hash,
                        reconciliation_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.tenant_id,
                        record.previous_checkpoint_hash,
                        record.current_checkpoint_hash,
                        record.reconciliation_hash,
                        record.model_dump_json(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise MicrosoftAgent365ReconciliationConflict(
                    "Agent 365 reconciliation overlaps durable history"
                ) from exc

    def get_latest(self, tenant_id: str) -> MicrosoftAgent365InventoryReconciliationV1 | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT reconciliation_json
                FROM agent365_reconciliations
                WHERE tenant_id = ?
                ORDER BY reconciliation_id DESC
                LIMIT 1
                """,
                (tenant_id.lower(),),
            ).fetchone()
        if row is None:
            return None
        return MicrosoftAgent365InventoryReconciliationV1.model_validate_json(str(row[0]))

    def list_history(
        self,
        tenant_id: str,
    ) -> tuple[MicrosoftAgent365InventoryReconciliationV1, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT reconciliation_json
                FROM agent365_reconciliations
                WHERE tenant_id = ?
                ORDER BY reconciliation_id
                """,
                (tenant_id.lower(),),
            ).fetchall()
        return tuple(
            MicrosoftAgent365InventoryReconciliationV1.model_validate_json(str(row[0]))
            for row in rows
        )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent365_reconciliations(
                    reconciliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    previous_checkpoint_hash TEXT NOT NULL,
                    current_checkpoint_hash TEXT NOT NULL,
                    reconciliation_hash TEXT NOT NULL UNIQUE,
                    reconciliation_json TEXT NOT NULL,
                    UNIQUE(tenant_id, current_checkpoint_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_agent365_reconciliation_tenant
                    ON agent365_reconciliations(tenant_id, reconciliation_id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection


def reconcile_agent365_inventory(
    *,
    previous_checkpoint: MicrosoftAgent365SnapshotCheckpointV1,
    current_checkpoint: MicrosoftAgent365SnapshotCheckpointV1,
    previous_state: Mapping[str, str],
    current_state: Mapping[str, str],
    include_unchanged: bool = True,
    previous_reconciliation_hash: str | None = None,
) -> MicrosoftAgent365InventoryReconciliationV1:
    """Compare adjacent retained inventory states without inferring Microsoft-side causation."""

    if previous_checkpoint.tenant_id != current_checkpoint.tenant_id:
        raise MicrosoftAgent365ReconciliationConflict(
            "Agent 365 reconciliation cannot cross tenant boundaries"
        )
    if current_checkpoint.previous_checkpoint_hash != previous_checkpoint.checkpoint_hash:
        raise MicrosoftAgent365ReconciliationConflict(
            "Agent 365 checkpoints are not adjacent in durable custody"
        )
    _validate_inventory_state(previous_state)
    _validate_inventory_state(current_state)
    if _state_sha256(previous_state) != previous_checkpoint.inventory_state_sha256:
        raise MicrosoftAgent365ReconciliationConflict(
            "previous inventory state does not match its custody checkpoint"
        )
    if _state_sha256(current_state) != current_checkpoint.inventory_state_sha256:
        raise MicrosoftAgent365ReconciliationConflict(
            "current inventory state does not match its custody checkpoint"
        )

    changes: list[MicrosoftAgent365PackageChangeV1] = []
    for package_id in sorted(set(previous_state) | set(current_state)):
        previous = previous_state.get(package_id)
        current = current_state.get(package_id)
        if previous is None:
            change_kind: Agent365ChangeKind = "ADDED"
        elif current is None:
            change_kind = "REMOVED"
        elif previous != current:
            change_kind = "CHANGED"
        else:
            change_kind = "UNCHANGED"
        if change_kind == "UNCHANGED" and not include_unchanged:
            continue
        changes.append(
            MicrosoftAgent365PackageChangeV1(
                package_id=package_id,
                change_kind=change_kind,
                previous_configuration_sha256=previous,
                current_configuration_sha256=current,
            )
        )

    changes_tuple = tuple(changes)
    counts = {
        "ADDED": sum(change.change_kind == "ADDED" for change in changes_tuple),
        "CHANGED": sum(change.change_kind == "CHANGED" for change in changes_tuple),
        "REMOVED": sum(change.change_kind == "REMOVED" for change in changes_tuple),
        "UNCHANGED": sum(change.change_kind == "UNCHANGED" for change in changes_tuple),
    }
    observed_at = current_checkpoint.completed_at_utc.astimezone(UTC)
    material = {
        "tenant_id": current_checkpoint.tenant_id,
        "previous_snapshot_id": previous_checkpoint.snapshot_id,
        "current_snapshot_id": current_checkpoint.snapshot_id,
        "previous_checkpoint_hash": previous_checkpoint.checkpoint_hash,
        "current_checkpoint_hash": current_checkpoint.checkpoint_hash,
        "previous_inventory_state_sha256": previous_checkpoint.inventory_state_sha256,
        "current_inventory_state_sha256": current_checkpoint.inventory_state_sha256,
        "observed_at_utc": observed_at.isoformat(),
        "changes": [change.model_dump(mode="json") for change in changes_tuple],
        "added_count": counts["ADDED"],
        "changed_count": counts["CHANGED"],
        "removed_count": counts["REMOVED"],
        "unchanged_count": counts["UNCHANGED"],
        "previous_reconciliation_hash": previous_reconciliation_hash,
    }
    reconciliation_hash = _sha256_json(material)
    return MicrosoftAgent365InventoryReconciliationV1(
        tenant_id=current_checkpoint.tenant_id,
        previous_snapshot_id=previous_checkpoint.snapshot_id,
        current_snapshot_id=current_checkpoint.snapshot_id,
        previous_checkpoint_hash=previous_checkpoint.checkpoint_hash,
        current_checkpoint_hash=current_checkpoint.checkpoint_hash,
        previous_inventory_state_sha256=previous_checkpoint.inventory_state_sha256,
        current_inventory_state_sha256=current_checkpoint.inventory_state_sha256,
        observed_at_utc=observed_at,
        changes=changes_tuple,
        added_count=counts["ADDED"],
        changed_count=counts["CHANGED"],
        removed_count=counts["REMOVED"],
        unchanged_count=counts["UNCHANGED"],
        previous_reconciliation_hash=previous_reconciliation_hash,
        reconciliation_hash=reconciliation_hash,
    )


def project_agent365_reconciliation(
    record: MicrosoftAgent365InventoryReconciliationV1,
    *,
    include_unchanged: bool = False,
) -> tuple[MicrosoftAgent365ConfigurationChangeProjectionV1, ...]:
    """Project reconciliation records toward the Evidence Object model without a verdict claim."""

    projected: list[MicrosoftAgent365ConfigurationChangeProjectionV1] = []
    for change in record.changes:
        if change.change_kind == "UNCHANGED" and not include_unchanged:
            continue
        projected.append(
            MicrosoftAgent365ConfigurationChangeProjectionV1(
                tenant_id=record.tenant_id,
                package_id=change.package_id,
                change_kind=change.change_kind,
                previous_configuration_sha256=change.previous_configuration_sha256,
                current_configuration_sha256=change.current_configuration_sha256,
                previous_checkpoint_hash=record.previous_checkpoint_hash,
                current_checkpoint_hash=record.current_checkpoint_hash,
                reconciliation_hash=record.reconciliation_hash,
            )
        )
    return tuple(projected)


def _validate_inventory_state(state: Mapping[str, str]) -> None:
    for package_id, digest in state.items():
        if not package_id:
            raise ValueError("Agent 365 inventory state contains an empty package id")
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("Agent 365 inventory state contains an invalid configuration digest")


def _state_sha256(state: Mapping[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(
            dict(state),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
