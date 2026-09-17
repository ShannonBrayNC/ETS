"""Durable retained-bundle storage for the frozen Agent 365 + Ranger R0 demo.

The mission API introduced in PR #843 consumes an in-memory ``RangerR0MissionIndex``.
This module closes the next P0 boundary by persisting the complete verified Evidence
Object v2 bundle, including the exact Step 4 source bytes, in a retry-safe SQLite store.
Every load verifies the stored envelope hash and re-runs the Evidence Object v2 verifier
before a bundle is admitted to the query index.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, cast

from pydantic import ValidationError

from ets.evidence_object import EvidenceObject, EvidenceObjectV2
from ets.ranger.agent365_r0_evidence import RangerR0ConsequenceClosureBundle
from ets.ranger.agent365_r0_evidence_v2 import (
    RangerR0EvidenceV2Bundle,
    verify_agent365_r0_evidence_v2,
)
from ets.ranger.agent365_r0_mission_query import (
    RangerR0MissionIndex,
    build_agent365_r0_mission_index,
)

_STORE_SCHEMA_VERSION = 1
_BUNDLE_SCHEMA_VERSION = "ets.demo.agent365-r0.durable-bundle.v1"


class RangerR0MissionStoreError(ValueError):
    """Raised when durable mission state cannot be trusted or reconstructed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SQLiteRangerR0MissionBundleStore:
    """Retry-safe durable store for verified Agent 365 + Ranger R0 mission bundles."""

    provider_name = "sqlite"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def save(self, bundle: RangerR0EvidenceV2Bundle) -> None:
        """Persist one verified bundle.

        Replaying the exact same bundle is idempotent. Reusing a ``mission_id`` with
        different retained evidence fails closed instead of replacing history.
        """

        verification = verify_agent365_r0_evidence_v2(bundle)
        if not verification.valid or verification.mission_id != bundle.mission_id:
            raise RangerR0MissionStoreError(
                "bundle_not_verified",
                "durable mission storage accepts only a verified bundle for its mission_id",
            )

        bundle_json = _serialize_bundle(bundle)
        bundle_sha256 = _sha256_text(bundle_json)
        created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        with self._lock:
            existing = self._connection.execute(
                """
                SELECT bundle_sha256
                FROM agent365_r0_mission_bundles
                WHERE mission_id = ?
                """,
                (bundle.mission_id,),
            ).fetchone()
            if existing is not None:
                if str(existing["bundle_sha256"]) == bundle_sha256:
                    return
                raise RangerR0MissionStoreError(
                    "duplicate_mission_conflict",
                    "mission_id already has different retained evidence",
                )

            self._connection.execute(
                """
                INSERT INTO agent365_r0_mission_bundles (
                    mission_id, bundle_json, bundle_sha256, created_at_utc
                )
                VALUES (?, ?, ?, ?)
                """,
                (bundle.mission_id, bundle_json, bundle_sha256, created_at),
            )
            self._connection.commit()

    def load(self, mission_id: str) -> RangerR0EvidenceV2Bundle:
        """Load and re-verify one retained bundle by exact mission identifier."""

        if not mission_id:
            raise RangerR0MissionStoreError(
                "empty_mission_id",
                "mission_id must be a non-empty string",
            )
        with self._lock:
            row = self._connection.execute(
                """
                SELECT bundle_json, bundle_sha256
                FROM agent365_r0_mission_bundles
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()
        if row is None:
            raise RangerR0MissionStoreError(
                "mission_not_found",
                "no durable Agent 365 R0 bundle exists for mission_id",
            )

        bundle_json = str(row["bundle_json"])
        stored_sha256 = str(row["bundle_sha256"])
        if _sha256_text(bundle_json) != stored_sha256:
            raise RangerR0MissionStoreError(
                "stored_bundle_hash_mismatch",
                "stored mission bundle no longer matches its retained SHA-256 commitment",
            )

        bundle = _deserialize_bundle(bundle_json)
        if bundle.mission_id != mission_id:
            raise RangerR0MissionStoreError(
                "stored_mission_mismatch",
                "stored bundle mission_id differs from the requested row key",
            )
        return bundle

    def list_bundles(self) -> tuple[RangerR0EvidenceV2Bundle, ...]:
        """Return every retained mission bundle in deterministic mission order."""

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT mission_id
                FROM agent365_r0_mission_bundles
                ORDER BY mission_id ASC
                """
            ).fetchall()
        return tuple(self.load(str(row["mission_id"])) for row in rows)

    def build_index(self) -> RangerR0MissionIndex:
        """Build the API's verified in-memory query index from durable retained state."""

        return build_agent365_r0_mission_index(self.list_bundles())

    def mission_ids(self) -> tuple[str, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT mission_id
                FROM agent365_r0_mission_bundles
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
                CREATE TABLE IF NOT EXISTS agent365_r0_store_schema (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent365_r0_mission_bundles (
                    mission_id TEXT PRIMARY KEY,
                    bundle_json TEXT NOT NULL,
                    bundle_sha256 TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                );
                """
            )
            row = self._connection.execute(
                "SELECT version FROM agent365_r0_store_schema WHERE id = 1"
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO agent365_r0_store_schema (id, version) VALUES (1, ?)",
                    (_STORE_SCHEMA_VERSION,),
                )
            elif int(row["version"]) != _STORE_SCHEMA_VERSION:
                raise RangerR0MissionStoreError(
                    "unsupported_store_schema",
                    "durable Agent 365 R0 store schema version is not supported",
                )
            self._connection.commit()


def _serialize_bundle(bundle: RangerR0EvidenceV2Bundle) -> str:
    closure = bundle.source_closure
    payload: dict[str, Any] = {
        "schema_version": _BUNDLE_SCHEMA_VERSION,
        "mission_id": bundle.mission_id,
        "evidence_object_v2": bundle.evidence_object.model_dump(mode="json"),
        "evidence_object_v2_identity_hash": bundle.evidence_object_identity_hash,
        "source_closure": {
            "mission_id": closure.mission_id,
            "decision_event": closure.decision_event,
            "evidence_object_v1": closure.evidence_object.model_dump(mode="json"),
            "evidence_object_v1_hash": closure.evidence_object_hash,
            "evidence_bundle_ref": closure.evidence_bundle_ref,
            "source_artifacts_base64": {
                artifact_id: base64.b64encode(raw).decode("ascii")
                for artifact_id, raw in sorted(closure.source_artifacts.items())
            },
        },
    }
    return _canonical_json(payload)


def _deserialize_bundle(bundle_json: str) -> RangerR0EvidenceV2Bundle:
    try:
        decoded = json.loads(bundle_json)
    except json.JSONDecodeError as exc:
        raise RangerR0MissionStoreError(
            "stored_bundle_invalid_json",
            "stored mission bundle is not valid JSON",
        ) from exc
    if not isinstance(decoded, dict):
        raise RangerR0MissionStoreError(
            "stored_bundle_invalid_shape",
            "stored mission bundle must be a JSON object",
        )
    payload = cast(dict[str, Any], decoded)
    if payload.get("schema_version") != _BUNDLE_SCHEMA_VERSION:
        raise RangerR0MissionStoreError(
            "unsupported_bundle_schema",
            "stored mission bundle schema version is not supported",
        )

    mission_id = _required_string(payload, "mission_id")
    closure_payload = _required_mapping(payload, "source_closure")
    closure_mission_id = _required_string(closure_payload, "mission_id")
    if closure_mission_id != mission_id:
        raise RangerR0MissionStoreError(
            "closure_mission_mismatch",
            "stored Step 4 closure belongs to another mission_id",
        )

    decision_event = dict(_required_mapping(closure_payload, "decision_event"))
    source_artifacts_encoded = _required_mapping(
        closure_payload,
        "source_artifacts_base64",
    )
    source_artifacts: dict[str, bytes] = {}
    for artifact_id, encoded in source_artifacts_encoded.items():
        if not isinstance(artifact_id, str) or not artifact_id:
            raise RangerR0MissionStoreError(
                "invalid_source_artifact_id",
                "retained source artifact identifiers must be non-empty strings",
            )
        if not isinstance(encoded, str):
            raise RangerR0MissionStoreError(
                "invalid_source_artifact_encoding",
                "retained source artifact bytes must be base64 strings",
            )
        try:
            source_artifacts[artifact_id] = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RangerR0MissionStoreError(
                "invalid_source_artifact_encoding",
                f"retained source artifact is not valid base64: {artifact_id}",
            ) from exc

    evidence_v1_payload = _required_mapping(closure_payload, "evidence_object_v1")
    evidence_v2_payload = _required_mapping(payload, "evidence_object_v2")
    try:
        evidence_v1 = EvidenceObject.model_validate_json(_canonical_json(evidence_v1_payload))
        evidence_v2 = EvidenceObjectV2.model_validate_json(_canonical_json(evidence_v2_payload))
    except ValidationError as exc:
        raise RangerR0MissionStoreError(
            "stored_evidence_object_invalid",
            "stored Evidence Object failed schema validation",
        ) from exc

    closure = RangerR0ConsequenceClosureBundle(
        mission_id=closure_mission_id,
        decision_event=decision_event,
        evidence_object=evidence_v1,
        evidence_object_hash=_required_string(closure_payload, "evidence_object_v1_hash"),
        evidence_bundle_ref=_required_string(closure_payload, "evidence_bundle_ref"),
        source_artifacts=source_artifacts,
    )
    bundle = RangerR0EvidenceV2Bundle(
        mission_id=mission_id,
        evidence_object=evidence_v2,
        evidence_object_identity_hash=_required_string(
            payload,
            "evidence_object_v2_identity_hash",
        ),
        source_closure=closure,
    )

    verification = verify_agent365_r0_evidence_v2(bundle)
    if not verification.valid or verification.mission_id != mission_id:
        raise RangerR0MissionStoreError(
            "stored_bundle_not_verified",
            "stored mission bundle no longer satisfies Evidence Object v2 verification",
        )
    return bundle


def _required_mapping(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    result = value.get(field)
    if not isinstance(result, dict):
        raise RangerR0MissionStoreError(
            "stored_bundle_missing_mapping",
            f"stored mission bundle field is not an object: {field}",
        )
    return cast(dict[str, Any], result)


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise RangerR0MissionStoreError(
            "stored_bundle_missing_string",
            f"stored mission bundle field is not a non-empty string: {field}",
        )
    return result


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "RangerR0MissionStoreError",
    "SQLiteRangerR0MissionBundleStore",
]
