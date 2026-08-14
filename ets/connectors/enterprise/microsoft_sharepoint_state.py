"""Operational SharePoint/OneDrive metadata state for G2E-DQ.

This state is deliberately outside ETS canonical evidence. It supports derived transition
classification from successive minimized metadata observations and is advanced only by
an explicit caller after the corresponding evidence observations have been committed.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from pydantic import JsonValue

SharePointMetadataTransitionKind = Literal[
    "baseline_observation",
    "observed_deleted",
    "created",
    "updated",
    "renamed",
    "moved",
    "deleted",
    "restored",
    "unchanged",
]

SHAREPOINT_STATE_MAXIMUM_MAPPING_BYTES = 16 * 1024
SHAREPOINT_STATE_MAXIMUM_ITEMS = 250_000
SHAREPOINT_STATE_MAXIMUM_SOURCE_KEY_CHARACTERS = 500
SHAREPOINT_STATE_MAXIMUM_OBJECT_ID_CHARACTERS = 500

_VOLATILE_UPDATE_KEYS = frozenset(
    {
        "created_at_utc",
        "modified_at_utc",
        "etag",
        "ctag",
    }
)
_TRANSITION_KEYS = frozenset({"name", "parent", "deleted"})


class MicrosoftSharePointStateError(ValueError):
    """Raised when operational metadata state violates the bounded profile."""


@dataclass(frozen=True, slots=True)
class SharePointMetadataSnapshotV1:
    """One minimized operational object snapshot, not canonical ETS evidence."""

    object_id: str
    scope: Literal["drive", "list"]
    deleted: bool
    name: str | None
    parent_signature: str | None
    metadata_sha256: str
    metadata: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SharePointMetadataTransitionV1:
    """Derived transition supported by a prior and current qualified observation."""

    object_id: str
    scope: Literal["drive", "list"]
    kinds: tuple[SharePointMetadataTransitionKind, ...]
    prior_sha256: str | None
    current_sha256: str


class SharePointMetadataStateStore:
    """SQLite-backed bounded operational snapshot store with explicit baseline state."""

    def __init__(
        self,
        path: str | Path,
        *,
        max_items: int = SHAREPOINT_STATE_MAXIMUM_ITEMS,
    ) -> None:
        if not 1 <= max_items <= SHAREPOINT_STATE_MAXIMUM_ITEMS:
            raise ValueError("SharePoint state max_items exceeds the qualified bound")
        self.path = Path(path)
        self.max_items = max_items
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def baseline_complete(self, source_key: str) -> bool:
        source_key = _source_key(source_key)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT baseline_complete FROM sharepoint_state_meta WHERE source_key = ?",
                (source_key,),
            ).fetchone()
        return row is not None and bool(row[0])

    def get(
        self,
        source_key: str,
        scope: Literal["drive", "list"],
        object_id: str,
    ) -> SharePointMetadataSnapshotV1 | None:
        source_key = _source_key(source_key)
        object_id = _object_id(object_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json FROM sharepoint_state
                WHERE source_key = ? AND scope = ? AND object_id = ?
                """,
                (source_key, scope, object_id),
            ).fetchone()
        if row is None:
            return None
        return _snapshot_from_json(str(row[0]))

    def classify(
        self,
        source_key: str,
        current: SharePointMetadataSnapshotV1,
    ) -> SharePointMetadataTransitionV1:
        prior = self.get(source_key, current.scope, current.object_id)
        return classify_sharepoint_metadata_transition(
            prior,
            current,
            baseline_complete=self.baseline_complete(source_key),
        )

    def apply(
        self,
        source_key: str,
        snapshots: Iterable[SharePointMetadataSnapshotV1],
        *,
        mark_baseline_complete: bool = False,
    ) -> None:
        """Advance operational state only when the caller explicitly authorizes release."""

        source_key = _source_key(source_key)
        materialized = tuple(snapshots)
        unique: dict[tuple[str, str], SharePointMetadataSnapshotV1] = {}
        for snapshot in materialized:
            key = (snapshot.scope, snapshot.object_id)
            existing = unique.get(key)
            if existing is not None and existing != snapshot:
                raise MicrosoftSharePointStateError(
                    "SharePoint state proposal repeats one object with conflicting snapshots"
                )
            unique[key] = snapshot

        with self._connect() as connection:
            existing_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM sharepoint_state WHERE source_key = ?",
                    (source_key,),
                ).fetchone()[0]
            )
            new_keys = 0
            for scope, object_id in unique:
                row = connection.execute(
                    """
                    SELECT 1 FROM sharepoint_state
                    WHERE source_key = ? AND scope = ? AND object_id = ?
                    """,
                    (source_key, scope, object_id),
                ).fetchone()
                if row is None:
                    new_keys += 1
            if existing_count + new_keys > self.max_items:
                raise MicrosoftSharePointStateError(
                    "SharePoint operational state item capacity would be exceeded"
                )

            for snapshot in unique.values():
                connection.execute(
                    """
                    INSERT INTO sharepoint_state(
                        source_key, scope, object_id, snapshot_json, metadata_sha256
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(source_key, scope, object_id) DO UPDATE SET
                        snapshot_json = excluded.snapshot_json,
                        metadata_sha256 = excluded.metadata_sha256
                    """,
                    (
                        source_key,
                        snapshot.scope,
                        snapshot.object_id,
                        _snapshot_json(snapshot),
                        snapshot.metadata_sha256,
                    ),
                )
            connection.execute(
                """
                INSERT INTO sharepoint_state_meta(source_key, baseline_complete)
                VALUES (?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    baseline_complete = CASE
                        WHEN sharepoint_state_meta.baseline_complete = 1 THEN 1
                        ELSE excluded.baseline_complete
                    END
                """,
                (source_key, int(mark_baseline_complete)),
            )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sharepoint_state (
                    source_key TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    metadata_sha256 TEXT NOT NULL,
                    PRIMARY KEY(source_key, scope, object_id)
                );
                CREATE TABLE IF NOT EXISTS sharepoint_state_meta (
                    source_key TEXT PRIMARY KEY,
                    baseline_complete INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection


def snapshot_sharepoint_metadata_record(
    record: Mapping[str, JsonValue],
) -> SharePointMetadataSnapshotV1:
    """Create a bounded snapshot from the qualified G2E-D intermediate record."""

    object_id = _object_id(_required_string(record, "object_id"))
    scope_raw = _required_string(record, "scope")
    if scope_raw not in {"drive", "list"}:
        raise MicrosoftSharePointStateError("SharePoint state scope must be drive or list")
    scope = cast(Literal["drive", "list"], scope_raw)
    deleted = record.get("deleted")
    if not isinstance(deleted, bool):
        raise MicrosoftSharePointStateError("SharePoint state deleted flag must be boolean")
    metadata_raw = record.get("metadata")
    if not isinstance(metadata_raw, dict):
        raise MicrosoftSharePointStateError("SharePoint state metadata must be an object")
    metadata = metadata_raw
    encoded = _canonical_json(metadata)
    if len(encoded) > SHAREPOINT_STATE_MAXIMUM_MAPPING_BYTES:
        raise MicrosoftSharePointStateError(
            "SharePoint operational metadata exceeds the qualified byte bound"
        )
    name_value = metadata.get("name")
    if name_value is not None and not isinstance(name_value, str):
        raise MicrosoftSharePointStateError("SharePoint metadata name must be a string")
    parent_signature = _parent_signature(metadata.get("parent"))
    return SharePointMetadataSnapshotV1(
        object_id=object_id,
        scope=scope,
        deleted=deleted,
        name=name_value,
        parent_signature=parent_signature,
        metadata_sha256=hashlib.sha256(encoded).hexdigest(),
        metadata=metadata,
    )


def classify_sharepoint_metadata_transition(
    prior: SharePointMetadataSnapshotV1 | None,
    current: SharePointMetadataSnapshotV1,
    *,
    baseline_complete: bool,
) -> SharePointMetadataTransitionV1:
    """Classify only transitions supported by successive minimized observations."""

    if prior is not None and (
        prior.object_id != current.object_id or prior.scope != current.scope
    ):
        raise MicrosoftSharePointStateError(
            "SharePoint transition snapshots refer to different source objects"
        )

    kinds: tuple[SharePointMetadataTransitionKind, ...]
    if prior is None:
        if current.deleted:
            kinds = ("observed_deleted",)
        elif baseline_complete:
            kinds = ("created",)
        else:
            kinds = ("baseline_observation",)
    elif prior.deleted and current.deleted:
        kinds = ("unchanged",)
    elif prior.deleted and not current.deleted:
        kinds = ("restored",)
    elif not prior.deleted and current.deleted:
        kinds = ("deleted",)
    else:
        changes: list[SharePointMetadataTransitionKind] = []
        if prior.name != current.name:
            changes.append("renamed")
        if prior.parent_signature != current.parent_signature:
            changes.append("moved")
        if _material_metadata(prior.metadata) != _material_metadata(current.metadata):
            changes.append("updated")
        elif not changes and _volatile_update_state(prior.metadata) != _volatile_update_state(
            current.metadata
        ):
            changes.append("updated")
        kinds = tuple(changes) if changes else ("unchanged",)

    return SharePointMetadataTransitionV1(
        object_id=current.object_id,
        scope=current.scope,
        kinds=kinds,
        prior_sha256=None if prior is None else prior.metadata_sha256,
        current_sha256=current.metadata_sha256,
    )


def _material_metadata(value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {
        key: item
        for key, item in value.items()
        if key not in _TRANSITION_KEYS and key not in _VOLATILE_UPDATE_KEYS
    }


def _volatile_update_state(value: Mapping[str, JsonValue]) -> tuple[JsonValue | None, ...]:
    return tuple(value.get(key) for key in sorted(_VOLATILE_UPDATE_KEYS))


def _parent_signature(value: JsonValue | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MicrosoftSharePointStateError("SharePoint metadata parent must be an object")
    selected = {
        key: value.get(key)
        for key in ("id", "drive_id", "site_id", "list_id", "path")
        if value.get(key) is not None
    }
    return hashlib.sha256(_canonical_json(selected)).hexdigest()


def _required_string(value: Mapping[str, JsonValue], key: str) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate:
        raise MicrosoftSharePointStateError(f"SharePoint state {key} is invalid")
    return candidate


def _source_key(value: str) -> str:
    if not 1 <= len(value) <= SHAREPOINT_STATE_MAXIMUM_SOURCE_KEY_CHARACTERS:
        raise MicrosoftSharePointStateError("SharePoint state source key is outside bounds")
    return value


def _object_id(value: str) -> str:
    if not 1 <= len(value) <= SHAREPOINT_STATE_MAXIMUM_OBJECT_ID_CHARACTERS:
        raise MicrosoftSharePointStateError("SharePoint state object id is outside bounds")
    return value


def _snapshot_json(snapshot: SharePointMetadataSnapshotV1) -> str:
    return _canonical_json(
        {
            "object_id": snapshot.object_id,
            "scope": snapshot.scope,
            "deleted": snapshot.deleted,
            "name": snapshot.name,
            "parent_signature": snapshot.parent_signature,
            "metadata_sha256": snapshot.metadata_sha256,
            "metadata": snapshot.metadata,
        }
    ).decode("utf-8")


def _snapshot_from_json(value: str) -> SharePointMetadataSnapshotV1:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise MicrosoftSharePointStateError("stored SharePoint state is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise MicrosoftSharePointStateError("stored SharePoint state must be an object")
    scope = decoded.get("scope")
    if scope not in {"drive", "list"}:
        raise MicrosoftSharePointStateError("stored SharePoint state scope is invalid")
    metadata = decoded.get("metadata")
    if not isinstance(metadata, dict):
        raise MicrosoftSharePointStateError("stored SharePoint state metadata is invalid")
    return SharePointMetadataSnapshotV1(
        object_id=_object_id(str(decoded.get("object_id", ""))),
        scope=cast(Literal["drive", "list"], scope),
        deleted=bool(decoded.get("deleted")),
        name=None if decoded.get("name") is None else str(decoded.get("name")),
        parent_signature=(
            None
            if decoded.get("parent_signature") is None
            else str(decoded.get("parent_signature"))
        ),
        metadata_sha256=str(decoded.get("metadata_sha256", "")),
        metadata=cast(dict[str, JsonValue], metadata),
    )


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MicrosoftSharePointStateError(
            "SharePoint operational state must contain JSON-native values"
        ) from exc
