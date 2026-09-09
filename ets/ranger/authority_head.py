"""Verifier-retained heads for Ranger custody-key authority history.

The key-authority ledger proves an authority-signed sequence when the complete history is
supplied.  This module adds separately retained, registry-signed heads so a valid but stale
authority-history prefix cannot be replayed as the latest known history.  Freshness remains
relative to the configured registry; global currentness, Fleet authorization, trusted time,
hardware custody, semantic truth, and physical outcome are not proven.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Literal, Self

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.key_authority import RangerKeyAuthorityEvent, RangerKeyAuthorityLedger

_ZERO_DIGEST = "0" * 64


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerAuthorityHeadError(RuntimeError):
    """Base error for retained authority-head verification or persistence."""


class RangerAuthorityHeadConflict(RangerAuthorityHeadError):
    """Raised when a supplied history regresses or forks retained authority state."""


class RangerAuthorityHeadIntegrityError(RangerAuthorityHeadError):
    """Raised when durable retained authority-head state is invalid."""


class RangerRetainedAuthorityHead(StrictModel):
    """Registry-signed statement of a verified Ranger key-authority history head."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": ("https://lanternprotocol.org/schemas/ets/ranger/retained-key-authority-head/v1")
        },
    )

    schema_version: Literal["ets.ranger.retained-key-authority-head.v1"] = (
        "ets.ranger.retained-key-authority-head.v1"
    )
    registry_sequence: int = Field(ge=1, le=2**63 - 1)
    previous_checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vehicle_id: str = Field(min_length=12, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    authority_event_count: int = Field(ge=1, le=2**63 - 1)
    authority_history_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_id: str = Field(min_length=1, max_length=160)
    authority_signing_key_id: str = Field(min_length=1, max_length=256)
    authority_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    received_at_utc: datetime
    registry_id: str = Field(min_length=1, max_length=160)
    registry_signing_key_id: str = Field(min_length=1, max_length=256)
    registry_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_history_integrity_verified: Literal[True] = True
    retained_state_advanced: bool
    freshness_scope: Literal["registry_baseline", "newer_than_retained_authority_head"]
    signing_algorithm: Literal["ed25519"] = "ed25519"
    checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    storage_profile: Literal["sqlite-wal-full-software-reference"] = (
        "sqlite-wal-full-software-reference"
    )
    independent_external_custody_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    operational_device_authorization_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "registry_relative_authority_freshness_no_global_operational_time_truth_or_outcome_claim"
    ] = "registry_relative_authority_freshness_no_global_operational_time_truth_or_outcome_claim"

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("received_at_utc")
    @classmethod
    def normalize_received_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("received_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_sequence_claims(self) -> Self:
        if self.registry_sequence == 1:
            if self.previous_checkpoint_digest_sha256 != _ZERO_DIGEST:
                raise ValueError("authority-head baseline must use the zero predecessor digest")
            if self.retained_state_advanced:
                raise ValueError("authority-head baseline cannot claim retained-state advancement")
            if self.freshness_scope != "registry_baseline":
                raise ValueError("authority-head baseline must use registry_baseline scope")
        else:
            if self.previous_checkpoint_digest_sha256 == _ZERO_DIGEST:
                raise ValueError("advanced authority head requires a predecessor digest")
            if not self.retained_state_advanced:
                raise ValueError("advanced authority head must claim retained-state advancement")
            if self.freshness_scope != "newer_than_retained_authority_head":
                raise ValueError("advanced authority head must use retained-relative scope")
        return self


class RangerAuthorityHeadChainVerification(StrictModel):
    valid: bool
    checkpoint_count: int = Field(ge=0)
    latest_checkpoint_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    latest_authority_event_count: int | None = Field(default=None, ge=1)
    latest_authority_history_head_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    freshness_relative_to_retained_state: bool
    reason: str


class RangerAuthorityHistoryPresentationVerification(StrictModel):
    valid: bool
    stale: bool
    presented_authority_event_count: int = Field(ge=0)
    retained_authority_event_count: int = Field(ge=1)
    retained_checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str


class SQLiteRangerAuthorityHeadStore:
    """Crash-consistent append-only store for verifier-retained authority heads."""

    provider_name = "sqlite"
    storage_profile = "sqlite-wal-full-software-reference"
    independent_external_custody_proven = False

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ranger_retained_authority_heads (
                registry_sequence INTEGER PRIMARY KEY,
                checkpoint_digest_sha256 TEXT NOT NULL UNIQUE,
                vehicle_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                authority_event_count INTEGER NOT NULL,
                authority_history_head_digest_sha256 TEXT NOT NULL UNIQUE,
                checkpoint_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def append(self, checkpoint: RangerRetainedAuthorityHead) -> None:
        checkpoint = RangerRetainedAuthorityHead.model_validate(checkpoint.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT registry_sequence, checkpoint_digest_sha256
                    FROM ranger_retained_authority_heads
                    ORDER BY registry_sequence DESC
                    LIMIT 1
                    """
                ).fetchone()
                expected_sequence = 1 if row is None else int(row["registry_sequence"]) + 1
                expected_previous = (
                    _ZERO_DIGEST if row is None else str(row["checkpoint_digest_sha256"])
                )
                if checkpoint.registry_sequence != expected_sequence:
                    raise RangerAuthorityHeadConflict(
                        f"authority-head registry sequence must be {expected_sequence}"
                    )
                if checkpoint.previous_checkpoint_digest_sha256 != expected_previous:
                    raise RangerAuthorityHeadConflict(
                        "authority-head checkpoint does not extend the retained registry head"
                    )
                self._connection.execute(
                    """
                    INSERT INTO ranger_retained_authority_heads (
                        registry_sequence,
                        checkpoint_digest_sha256,
                        vehicle_id,
                        tenant_id,
                        workspace_id,
                        authority_event_count,
                        authority_history_head_digest_sha256,
                        checkpoint_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        checkpoint.registry_sequence,
                        checkpoint.checkpoint_digest_sha256,
                        checkpoint.vehicle_id,
                        checkpoint.tenant_id,
                        checkpoint.workspace_id,
                        checkpoint.authority_event_count,
                        checkpoint.authority_history_head_digest_sha256,
                        checkpoint.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except RangerAuthorityHeadConflict:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerAuthorityHeadConflict(
                    "duplicate retained authority-head identity or digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_checkpoints(self) -> list[RangerRetainedAuthorityHead]:
        with self._lock:
            integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise RangerAuthorityHeadIntegrityError("SQLite integrity_check failed")
            rows = self._connection.execute(
                """
                SELECT
                    registry_sequence,
                    checkpoint_digest_sha256,
                    vehicle_id,
                    tenant_id,
                    workspace_id,
                    authority_event_count,
                    authority_history_head_digest_sha256,
                    checkpoint_json
                FROM ranger_retained_authority_heads
                ORDER BY registry_sequence ASC
                """
            ).fetchall()
        try:
            checkpoints = [
                RangerRetainedAuthorityHead.model_validate_json(row["checkpoint_json"])
                for row in rows
            ]
        except ValidationError as exc:
            raise RangerAuthorityHeadIntegrityError(
                "stored Ranger authority-head checkpoint is invalid"
            ) from exc
        for row, checkpoint in zip(rows, checkpoints, strict=True):
            if (
                int(row["registry_sequence"]) != checkpoint.registry_sequence
                or str(row["checkpoint_digest_sha256"]) != checkpoint.checkpoint_digest_sha256
                or str(row["vehicle_id"]) != checkpoint.vehicle_id
                or str(row["tenant_id"]) != checkpoint.tenant_id
                or str(row["workspace_id"]) != checkpoint.workspace_id
                or int(row["authority_event_count"]) != checkpoint.authority_event_count
                or str(row["authority_history_head_digest_sha256"])
                != checkpoint.authority_history_head_digest_sha256
            ):
                raise RangerAuthorityHeadIntegrityError(
                    "stored authority-head index metadata does not match signed record"
                )
        return checkpoints


class RangerAuthorityHeadRegistry:
    """Retain the latest verified key-authority history under a registry signer."""

    def __init__(
        self,
        store: SQLiteRangerAuthorityHeadStore,
        *,
        vehicle_id: str,
        tenant_id: str,
        workspace_id: str,
        authority_id: str,
        authority_signing_key_id: str,
        authority_public_key_hex: str,
        registry_id: str,
        registry_signing_key_id: str,
        registry_private_key_hex: str,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerAuthorityHeadError("vehicle_id must use the ets-ranger: namespace")
        for name, value, maximum in (
            ("tenant_id", tenant_id, 128),
            ("workspace_id", workspace_id, 128),
            ("authority_id", authority_id, 160),
            ("authority_signing_key_id", authority_signing_key_id, 256),
            ("registry_id", registry_id, 160),
            ("registry_signing_key_id", registry_signing_key_id, 256),
        ):
            if not value or len(value) > maximum:
                raise RangerAuthorityHeadError(f"{name} must contain 1-{maximum} characters")
        try:
            authority_key_bytes = bytes.fromhex(authority_public_key_hex)
            Ed25519PublicKey.from_public_bytes(authority_key_bytes)
        except ValueError as exc:
            raise RangerAuthorityHeadError(
                "authority public key must be a 32-byte Ed25519 key"
            ) from exc
        try:
            self._registry_private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(registry_private_key_hex)
            )
        except ValueError as exc:
            raise RangerAuthorityHeadError(
                "registry private key must be a 32-byte Ed25519 key"
            ) from exc
        registry_key_bytes = self._registry_private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        if registry_key_bytes == authority_key_bytes:
            raise RangerAuthorityHeadError("registry and authority signing keys must be distinct")

        self.store = store
        self.vehicle_id = vehicle_id
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self.authority_id = authority_id
        self.authority_signing_key_id = authority_signing_key_id
        self.authority_public_key_hex = authority_public_key_hex
        self.authority_public_key_fingerprint_sha256 = hashlib.sha256(
            authority_key_bytes
        ).hexdigest()
        self.registry_id = registry_id
        self.registry_signing_key_id = registry_signing_key_id

        retained = self.store.list_checkpoints()
        if retained:
            verification = self.verify_checkpoint_chain(retained, self.registry_public_key_hex)
            if not verification.valid:
                raise RangerAuthorityHeadIntegrityError(
                    f"retained authority-head chain is invalid: {verification.reason}"
                )
            for checkpoint in retained:
                if not self._matches_configuration(checkpoint):
                    raise RangerAuthorityHeadIntegrityError(
                        "retained authority-head identity, scope, or signing key mismatch"
                    )
        self._checkpoints = retained

    @property
    def registry_public_key_hex(self) -> str:
        return (
            self._registry_private_key.public_key()
            .public_bytes(Encoding.Raw, PublicFormat.Raw)
            .hex()
        )

    @property
    def registry_public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.registry_public_key_hex)).hexdigest()

    def retain(
        self,
        events: Iterable[RangerKeyAuthorityEvent],
        *,
        received_at_utc: datetime,
    ) -> RangerRetainedAuthorityHead:
        """Verify and retain a full authority history, rejecting rollback and forks."""

        retained = self.store.list_checkpoints()
        if retained != self._checkpoints:
            raise RangerAuthorityHeadConflict(
                "retained authority-head history changed; reopen the registry before appending"
            )
        received_at = _require_aware_utc(received_at_utc)
        history = list(events)
        verification = RangerKeyAuthorityLedger.verify_history(
            history, self.authority_public_key_hex
        )
        if not verification.valid or verification.head_digest_sha256 is None:
            raise RangerAuthorityHeadError(
                f"Ranger key-authority history is invalid: {verification.reason}"
            )
        if not history or not self._matches_history(history):
            raise RangerAuthorityHeadError(
                "Ranger key-authority identity, scope, or signing key mismatch"
            )
        latest = self._checkpoints[-1] if self._checkpoints else None
        if latest is not None:
            if (
                len(history) == latest.authority_event_count
                and verification.head_digest_sha256 == latest.authority_history_head_digest_sha256
            ):
                return latest
            if received_at <= latest.received_at_utc:
                raise RangerAuthorityHeadConflict("registry receipt time must advance")
            if len(history) < latest.authority_event_count:
                raise RangerAuthorityHeadConflict(
                    "presented authority history is stale relative to retained event count"
                )
            if len(history) == latest.authority_event_count:
                raise RangerAuthorityHeadConflict("authority history fork at retained event count")
            retained_event = history[latest.authority_event_count - 1]
            if retained_event.event_digest_sha256 != latest.authority_history_head_digest_sha256:
                raise RangerAuthorityHeadConflict(
                    "presented authority history does not extend the retained authority head"
                )

        sequence = len(self._checkpoints) + 1
        payload = _authority_head_payload(
            registry_sequence=sequence,
            previous_checkpoint_digest_sha256=(
                _ZERO_DIGEST if latest is None else latest.checkpoint_digest_sha256
            ),
            vehicle_id=self.vehicle_id,
            tenant_id=self.tenant_id,
            workspace_id=self.workspace_id,
            authority_event_count=len(history),
            authority_history_head_digest_sha256=verification.head_digest_sha256,
            authority_id=self.authority_id,
            authority_signing_key_id=self.authority_signing_key_id,
            authority_public_key_fingerprint_sha256=(self.authority_public_key_fingerprint_sha256),
            received_at_utc=received_at,
            registry_id=self.registry_id,
            registry_signing_key_id=self.registry_signing_key_id,
            registry_public_key_fingerprint_sha256=(self.registry_public_key_fingerprint_sha256),
            retained_state_advanced=latest is not None,
            freshness_scope=(
                "registry_baseline" if latest is None else "newer_than_retained_authority_head"
            ),
        )
        digest = canonical_sha256(payload)
        checkpoint = RangerRetainedAuthorityHead.model_validate(
            {
                **payload,
                "received_at_utc": received_at,
                "checkpoint_digest_sha256": digest,
                "signature_hex": self._registry_private_key.sign(canonicalize(payload)).hex(),
            }
        )
        self.store.append(checkpoint)
        self._checkpoints.append(checkpoint)
        return checkpoint

    def _matches_configuration(self, checkpoint: RangerRetainedAuthorityHead) -> bool:
        return (
            checkpoint.vehicle_id == self.vehicle_id
            and checkpoint.tenant_id == self.tenant_id
            and checkpoint.workspace_id == self.workspace_id
            and checkpoint.authority_id == self.authority_id
            and checkpoint.authority_signing_key_id == self.authority_signing_key_id
            and checkpoint.authority_public_key_fingerprint_sha256
            == self.authority_public_key_fingerprint_sha256
            and checkpoint.registry_id == self.registry_id
            and checkpoint.registry_signing_key_id == self.registry_signing_key_id
            and checkpoint.registry_public_key_fingerprint_sha256
            == self.registry_public_key_fingerprint_sha256
        )

    def _matches_history(self, history: list[RangerKeyAuthorityEvent]) -> bool:
        first = history[0]
        intent = first.request.intent
        return (
            intent.vehicle_id == self.vehicle_id
            and intent.tenant_id == self.tenant_id
            and intent.workspace_id == self.workspace_id
            and first.authority_id == self.authority_id
            and first.authority_signing_key_id == self.authority_signing_key_id
            and first.authority_public_key_fingerprint_sha256
            == self.authority_public_key_fingerprint_sha256
        )

    @staticmethod
    def verify_checkpoint_chain(
        checkpoints: Iterable[RangerRetainedAuthorityHead],
        registry_public_key_hex: str,
    ) -> RangerAuthorityHeadChainVerification:
        """Verify registry signatures and progression for retained authority heads."""

        try:
            public_key_bytes = bytes.fromhex(registry_public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except ValueError:
            return _head_chain_failure(0, "registry public key is not 32-byte Ed25519")
        expected_fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
        expected_sequence = 1
        previous_digest = _ZERO_DIGEST
        previous: RangerRetainedAuthorityHead | None = None
        identity: tuple[str, ...] | None = None
        count = 0
        for unvalidated in checkpoints:
            count += 1
            try:
                checkpoint = RangerRetainedAuthorityHead.model_validate(unvalidated.model_dump())
            except (AttributeError, ValidationError):
                return _head_chain_failure(count, "authority-head schema validation failed")
            if checkpoint.registry_sequence != expected_sequence:
                return _head_chain_failure(
                    count, "missing, duplicate, or reordered authority-head registry sequence"
                )
            if checkpoint.previous_checkpoint_digest_sha256 != previous_digest:
                return _head_chain_failure(
                    count, "previous retained authority-head digest mismatch"
                )
            if checkpoint.registry_public_key_fingerprint_sha256 != expected_fingerprint:
                return _head_chain_failure(count, "registry public key fingerprint mismatch")
            current_identity = (
                checkpoint.vehicle_id,
                checkpoint.tenant_id,
                checkpoint.workspace_id,
                checkpoint.authority_id,
                checkpoint.authority_signing_key_id,
                checkpoint.authority_public_key_fingerprint_sha256,
                checkpoint.registry_id,
                checkpoint.registry_signing_key_id,
            )
            if identity is None:
                identity = current_identity
            elif current_identity != identity:
                return _head_chain_failure(
                    count, "authority, Ranger scope, or registry identity changed"
                )
            payload = _authority_head_payload_from_record(checkpoint)
            if canonical_sha256(payload) != checkpoint.checkpoint_digest_sha256:
                return _head_chain_failure(count, "authority-head checkpoint digest mismatch")
            try:
                public_key.verify(bytes.fromhex(checkpoint.signature_hex), canonicalize(payload))
            except (InvalidSignature, ValueError):
                return _head_chain_failure(count, "authority-head checkpoint signature invalid")
            if previous is not None:
                if checkpoint.received_at_utc <= previous.received_at_utc:
                    return _head_chain_failure(count, "registry receipt time did not advance")
                if checkpoint.authority_event_count <= previous.authority_event_count:
                    return _head_chain_failure(
                        count, "retained authority event count did not advance"
                    )
                if (
                    checkpoint.authority_history_head_digest_sha256
                    == previous.authority_history_head_digest_sha256
                ):
                    return _head_chain_failure(count, "retained authority head did not advance")
            previous = checkpoint
            previous_digest = checkpoint.checkpoint_digest_sha256
            expected_sequence += 1
        if previous is None:
            return _head_chain_failure(0, "retained authority-head chain is empty")
        return RangerAuthorityHeadChainVerification(
            valid=True,
            checkpoint_count=count,
            latest_checkpoint_digest_sha256=previous.checkpoint_digest_sha256,
            latest_authority_event_count=previous.authority_event_count,
            latest_authority_history_head_digest_sha256=(
                previous.authority_history_head_digest_sha256
            ),
            freshness_relative_to_retained_state=count > 1,
            reason=(
                "registry signatures and authority-head progression are valid; freshness is "
                "relative to this supplied registry history"
            ),
        )

    @staticmethod
    def verify_presented_history(
        events: Iterable[RangerKeyAuthorityEvent],
        latest_checkpoint: RangerRetainedAuthorityHead,
        *,
        authority_public_key_hex: str,
        registry_public_key_hex: str,
    ) -> RangerAuthorityHistoryPresentationVerification:
        """Compare a supplied authority history with an out-of-band retained head."""

        retained_count = latest_checkpoint.authority_event_count
        retained_digest = latest_checkpoint.checkpoint_digest_sha256
        error = _standalone_head_error(latest_checkpoint, registry_public_key_hex)
        if error is not None:
            return _history_presentation_failure(retained_count, retained_digest, error)
        history = list(events)
        verification = RangerKeyAuthorityLedger.verify_history(history, authority_public_key_hex)
        if not verification.valid or verification.head_digest_sha256 is None:
            return _history_presentation_failure(
                retained_count,
                retained_digest,
                f"presented authority history is invalid: {verification.reason}",
                presented_count=len(history),
            )
        if history:
            first = history[0]
            intent = first.request.intent
            expected_authority_fingerprint = hashlib.sha256(
                bytes.fromhex(authority_public_key_hex)
            ).hexdigest()
            if (
                intent.vehicle_id != latest_checkpoint.vehicle_id
                or intent.tenant_id != latest_checkpoint.tenant_id
                or intent.workspace_id != latest_checkpoint.workspace_id
                or first.authority_id != latest_checkpoint.authority_id
                or first.authority_signing_key_id != latest_checkpoint.authority_signing_key_id
                or expected_authority_fingerprint
                != latest_checkpoint.authority_public_key_fingerprint_sha256
            ):
                return _history_presentation_failure(
                    retained_count,
                    retained_digest,
                    "presented authority identity or scope does not match retained head",
                    presented_count=len(history),
                )
        if len(history) < retained_count:
            return _history_presentation_failure(
                retained_count,
                retained_digest,
                "presented authority history is stale relative to retained head",
                stale=True,
                presented_count=len(history),
            )
        if len(history) > retained_count:
            return _history_presentation_failure(
                retained_count,
                retained_digest,
                "presented authority history is ahead of retained registry state",
                presented_count=len(history),
            )
        if (
            verification.head_digest_sha256
            != latest_checkpoint.authority_history_head_digest_sha256
        ):
            return _history_presentation_failure(
                retained_count,
                retained_digest,
                "presented authority history forks the retained head",
                presented_count=len(history),
            )
        return RangerAuthorityHistoryPresentationVerification(
            valid=True,
            stale=False,
            presented_authority_event_count=len(history),
            retained_authority_event_count=retained_count,
            retained_checkpoint_digest_sha256=retained_digest,
            reason=(
                "authority history exactly matches the separately retained registry head; "
                "global currentness and operational authorization are not proven"
            ),
        )

    def list_checkpoints(self) -> list[RangerRetainedAuthorityHead]:
        return self.store.list_checkpoints()


def _authority_head_payload_from_record(
    checkpoint: RangerRetainedAuthorityHead,
) -> dict[str, object]:
    return _authority_head_payload(
        registry_sequence=checkpoint.registry_sequence,
        previous_checkpoint_digest_sha256=checkpoint.previous_checkpoint_digest_sha256,
        vehicle_id=checkpoint.vehicle_id,
        tenant_id=checkpoint.tenant_id,
        workspace_id=checkpoint.workspace_id,
        authority_event_count=checkpoint.authority_event_count,
        authority_history_head_digest_sha256=(checkpoint.authority_history_head_digest_sha256),
        authority_id=checkpoint.authority_id,
        authority_signing_key_id=checkpoint.authority_signing_key_id,
        authority_public_key_fingerprint_sha256=(
            checkpoint.authority_public_key_fingerprint_sha256
        ),
        received_at_utc=checkpoint.received_at_utc,
        registry_id=checkpoint.registry_id,
        registry_signing_key_id=checkpoint.registry_signing_key_id,
        registry_public_key_fingerprint_sha256=(checkpoint.registry_public_key_fingerprint_sha256),
        retained_state_advanced=checkpoint.retained_state_advanced,
        freshness_scope=checkpoint.freshness_scope,
    )


def _authority_head_payload(
    *,
    registry_sequence: int,
    previous_checkpoint_digest_sha256: str,
    vehicle_id: str,
    tenant_id: str,
    workspace_id: str,
    authority_event_count: int,
    authority_history_head_digest_sha256: str,
    authority_id: str,
    authority_signing_key_id: str,
    authority_public_key_fingerprint_sha256: str,
    received_at_utc: datetime,
    registry_id: str,
    registry_signing_key_id: str,
    registry_public_key_fingerprint_sha256: str,
    retained_state_advanced: bool,
    freshness_scope: str,
) -> dict[str, object]:
    return {
        "schema_version": "ets.ranger.retained-key-authority-head.v1",
        "registry_sequence": registry_sequence,
        "previous_checkpoint_digest_sha256": previous_checkpoint_digest_sha256,
        "vehicle_id": vehicle_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "authority_event_count": authority_event_count,
        "authority_history_head_digest_sha256": authority_history_head_digest_sha256,
        "authority_id": authority_id,
        "authority_signing_key_id": authority_signing_key_id,
        "authority_public_key_fingerprint_sha256": (authority_public_key_fingerprint_sha256),
        "received_at_utc": received_at_utc.astimezone(UTC).isoformat(),
        "registry_id": registry_id,
        "registry_signing_key_id": registry_signing_key_id,
        "registry_public_key_fingerprint_sha256": (registry_public_key_fingerprint_sha256),
        "authority_history_integrity_verified": True,
        "retained_state_advanced": retained_state_advanced,
        "freshness_scope": freshness_scope,
        "signing_algorithm": "ed25519",
        "storage_profile": "sqlite-wal-full-software-reference",
        "independent_external_custody_proven": False,
        "globally_current_history_proven": False,
        "operational_device_authorization_proven": False,
        "trusted_time_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "registry_relative_authority_freshness_no_global_operational_time_truth_or_"
            "outcome_claim"
        ),
    }


def _standalone_head_error(
    checkpoint: RangerRetainedAuthorityHead,
    registry_public_key_hex: str,
) -> str | None:
    try:
        validated = RangerRetainedAuthorityHead.model_validate(checkpoint.model_dump())
        public_key_bytes = bytes.fromhex(registry_public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    except (AttributeError, ValidationError, ValueError):
        return "retained authority head or registry public key is invalid"
    if (
        hashlib.sha256(public_key_bytes).hexdigest()
        != validated.registry_public_key_fingerprint_sha256
    ):
        return "registry public key fingerprint mismatch"
    payload = _authority_head_payload_from_record(validated)
    if canonical_sha256(payload) != validated.checkpoint_digest_sha256:
        return "retained authority-head checkpoint digest mismatch"
    try:
        public_key.verify(bytes.fromhex(validated.signature_hex), canonicalize(payload))
    except (InvalidSignature, ValueError):
        return "retained authority-head checkpoint signature invalid"
    return None


def _head_chain_failure(count: int, reason: str) -> RangerAuthorityHeadChainVerification:
    return RangerAuthorityHeadChainVerification(
        valid=False,
        checkpoint_count=count,
        freshness_relative_to_retained_state=False,
        reason=reason,
    )


def _history_presentation_failure(
    retained_count: int,
    retained_digest: str,
    reason: str,
    *,
    stale: bool = False,
    presented_count: int = 0,
) -> RangerAuthorityHistoryPresentationVerification:
    return RangerAuthorityHistoryPresentationVerification(
        valid=False,
        stale=stale,
        presented_authority_event_count=presented_count,
        retained_authority_event_count=retained_count,
        retained_checkpoint_digest_sha256=retained_digest,
        reason=reason,
    )


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerAuthorityHeadError("received_at_utc must be timezone-aware")
    return value.astimezone(UTC)
