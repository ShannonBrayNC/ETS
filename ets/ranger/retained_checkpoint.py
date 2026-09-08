"""Verifier-side retained checkpoints for Ranger custody freshness.

This software reference accepts complete Ranger custody chains, verifies them under an
out-of-band Ranger key, and signs an append-only statement of the latest accepted boot,
record count, and custody head under a separate registry key.  Comparison with that retained
state detects rollback and stale-but-valid replay.  It does not prove global freshness,
complete capture, trusted time, semantic truth, or physical outcome.
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
from ets.ranger.custody import (
    RangerBootCheckpoint,
    RangerCustodyLedger,
    RangerCustodyRecord,
)

_ZERO_DIGEST = "0" * 64


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerCheckpointError(RuntimeError):
    """Base error for retained-checkpoint validation or persistence failures."""


class RangerCheckpointConflict(RangerCheckpointError):
    """Raised when a checkpoint would regress or fork retained state."""


class RangerCheckpointIntegrityError(RangerCheckpointError):
    """Raised when retained checkpoint data cannot be parsed or verified."""


class RangerRetainedCheckpoint(StrictModel):
    """Registry-signed statement of one verified Ranger custody head."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/retained-checkpoint/v1"
        },
    )

    schema_version: Literal["ets.ranger.retained-checkpoint.v1"] = (
        "ets.ranger.retained-checkpoint.v1"
    )
    registry_sequence: int = Field(ge=1, le=2**63 - 1)
    previous_checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vehicle_id: str = Field(min_length=12, max_length=160)
    mission_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    boot_sequence: int = Field(ge=1, le=2**63 - 1)
    custody_record_count: int = Field(ge=1, le=2**63 - 1)
    custody_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ranger_signing_key_id: str = Field(min_length=1, max_length=256)
    ranger_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_boot_id: str | None = Field(default=None, min_length=1, max_length=128)
    previous_custody_head_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    received_at_utc: datetime
    registry_id: str = Field(min_length=1, max_length=160)
    registry_signing_key_id: str = Field(min_length=1, max_length=256)
    registry_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ranger_chain_integrity_verified: Literal[True] = True
    retained_state_advanced: bool
    freshness_scope: Literal["registry_baseline", "newer_than_retained_checkpoint"]
    signing_algorithm: Literal["ed25519"] = "ed25519"
    checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    storage_profile: Literal["sqlite-wal-full-software-reference"] = (
        "sqlite-wal-full-software-reference"
    )
    independent_external_custody_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "registry_relative_freshness_no_global_time_completeness_truth_or_outcome_claim"
    ] = "registry_relative_freshness_no_global_time_completeness_truth_or_outcome_claim"

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
                raise ValueError("registry baseline must use the zero predecessor digest")
            if self.retained_state_advanced:
                raise ValueError("registry baseline cannot claim retained-state advancement")
            if self.freshness_scope != "registry_baseline":
                raise ValueError("registry baseline must use registry_baseline freshness scope")
        else:
            if self.previous_checkpoint_digest_sha256 == _ZERO_DIGEST:
                raise ValueError("advanced checkpoint requires a nonzero predecessor digest")
            if not self.retained_state_advanced:
                raise ValueError("advanced checkpoint must claim retained-state advancement")
            if self.freshness_scope != "newer_than_retained_checkpoint":
                raise ValueError(
                    "advanced checkpoint must use newer_than_retained_checkpoint freshness scope"
                )
        predecessor = (self.previous_boot_id, self.previous_custody_head_digest_sha256)
        if self.boot_sequence == 1:
            if predecessor != (None, None):
                raise ValueError("genesis boot cannot identify a previous custody chain")
        elif None in predecessor:
            raise ValueError("non-genesis boot requires the previous boot and custody head")
        return self


class RangerCheckpointChainVerification(StrictModel):
    valid: bool
    checkpoint_count: int = Field(ge=0)
    latest_checkpoint_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    latest_boot_sequence: int | None = Field(default=None, ge=1)
    latest_custody_head_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    freshness_relative_to_retained_state: bool
    reason: str


class RangerCheckpointPresentationVerification(StrictModel):
    valid: bool
    stale: bool
    presented_boot_sequence: int | None = Field(default=None, ge=1)
    retained_boot_sequence: int = Field(ge=1)
    retained_checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str


class SQLiteRangerCheckpointStore:
    """Crash-consistent append-only store intended for a verifier-side boundary."""

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
            CREATE TABLE IF NOT EXISTS ranger_retained_checkpoints (
                registry_sequence INTEGER PRIMARY KEY,
                checkpoint_digest_sha256 TEXT NOT NULL UNIQUE,
                vehicle_id TEXT NOT NULL,
                mission_id TEXT NOT NULL,
                boot_sequence INTEGER NOT NULL,
                custody_head_digest_sha256 TEXT NOT NULL,
                checkpoint_json TEXT NOT NULL,
                UNIQUE(vehicle_id, mission_id, boot_sequence, custody_head_digest_sha256)
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def append(self, checkpoint: RangerRetainedCheckpoint) -> None:
        checkpoint = RangerRetainedCheckpoint.model_validate(checkpoint.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT registry_sequence, checkpoint_digest_sha256
                    FROM ranger_retained_checkpoints
                    ORDER BY registry_sequence DESC
                    LIMIT 1
                    """
                ).fetchone()
                expected_sequence = 1 if row is None else int(row["registry_sequence"]) + 1
                expected_previous = (
                    _ZERO_DIGEST if row is None else str(row["checkpoint_digest_sha256"])
                )
                if checkpoint.registry_sequence != expected_sequence:
                    raise RangerCheckpointConflict(f"registry sequence must be {expected_sequence}")
                if checkpoint.previous_checkpoint_digest_sha256 != expected_previous:
                    raise RangerCheckpointConflict(
                        "checkpoint does not extend the retained registry head"
                    )
                self._connection.execute(
                    """
                    INSERT INTO ranger_retained_checkpoints (
                        registry_sequence,
                        checkpoint_digest_sha256,
                        vehicle_id,
                        mission_id,
                        boot_sequence,
                        custody_head_digest_sha256,
                        checkpoint_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        checkpoint.registry_sequence,
                        checkpoint.checkpoint_digest_sha256,
                        checkpoint.vehicle_id,
                        checkpoint.mission_id,
                        checkpoint.boot_sequence,
                        checkpoint.custody_head_digest_sha256,
                        checkpoint.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except RangerCheckpointConflict:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerCheckpointConflict(
                    "duplicate retained checkpoint identity or digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_checkpoints(self) -> list[RangerRetainedCheckpoint]:
        with self._lock:
            integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise RangerCheckpointIntegrityError("SQLite integrity_check failed")
            rows = self._connection.execute(
                """
                SELECT
                    registry_sequence,
                    checkpoint_digest_sha256,
                    vehicle_id,
                    mission_id,
                    boot_sequence,
                    custody_head_digest_sha256,
                    checkpoint_json
                FROM ranger_retained_checkpoints
                ORDER BY registry_sequence ASC
                """
            ).fetchall()
        try:
            checkpoints = [
                RangerRetainedCheckpoint.model_validate_json(row["checkpoint_json"]) for row in rows
            ]
        except ValidationError as exc:
            raise RangerCheckpointIntegrityError(
                "stored Ranger retained checkpoint is invalid"
            ) from exc
        for row, checkpoint in zip(rows, checkpoints, strict=True):
            if (
                int(row["registry_sequence"]) != checkpoint.registry_sequence
                or str(row["checkpoint_digest_sha256"]) != checkpoint.checkpoint_digest_sha256
                or str(row["vehicle_id"]) != checkpoint.vehicle_id
                or str(row["mission_id"]) != checkpoint.mission_id
                or int(row["boot_sequence"]) != checkpoint.boot_sequence
                or str(row["custody_head_digest_sha256"]) != checkpoint.custody_head_digest_sha256
            ):
                raise RangerCheckpointIntegrityError(
                    "stored Ranger checkpoint index metadata does not match signed record"
                )
        return checkpoints


class RangerCheckpointRegistry:
    """Verify Ranger custody and retain a separately signed latest-state history."""

    def __init__(
        self,
        store: SQLiteRangerCheckpointStore,
        *,
        vehicle_id: str,
        mission_id: str,
        ranger_signing_key_id: str,
        ranger_public_key_hex: str,
        registry_id: str,
        registry_signing_key_id: str,
        registry_private_key_hex: str,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerCheckpointError("vehicle_id must use the ets-ranger: namespace")
        for name, value, maximum in (
            ("mission_id", mission_id, 128),
            ("ranger_signing_key_id", ranger_signing_key_id, 256),
            ("registry_id", registry_id, 160),
            ("registry_signing_key_id", registry_signing_key_id, 256),
        ):
            if not value or len(value) > maximum:
                raise RangerCheckpointError(f"{name} must contain 1-{maximum} characters")
        try:
            ranger_public_key_bytes = bytes.fromhex(ranger_public_key_hex)
            Ed25519PublicKey.from_public_bytes(ranger_public_key_bytes)
        except ValueError as exc:
            raise RangerCheckpointError("Ranger public key must be a 32-byte Ed25519 key") from exc
        try:
            self._registry_private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(registry_private_key_hex)
            )
        except ValueError as exc:
            raise RangerCheckpointError(
                "registry private key must be a 32-byte Ed25519 key"
            ) from exc
        registry_public_key_bytes = self._registry_private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        if registry_public_key_bytes == ranger_public_key_bytes:
            raise RangerCheckpointError("registry and Ranger signing keys must be distinct")

        self.store = store
        self.vehicle_id = vehicle_id
        self.mission_id = mission_id
        self.ranger_signing_key_id = ranger_signing_key_id
        self.ranger_public_key_hex = ranger_public_key_hex
        self.ranger_public_key_fingerprint_sha256 = hashlib.sha256(
            ranger_public_key_bytes
        ).hexdigest()
        self.registry_id = registry_id
        self.registry_signing_key_id = registry_signing_key_id

        retained = self.store.list_checkpoints()
        if retained:
            verification = self.verify_checkpoint_chain(retained, self.registry_public_key_hex)
            if not verification.valid:
                raise RangerCheckpointIntegrityError(
                    f"retained checkpoint chain is invalid: {verification.reason}"
                )
            for checkpoint in retained:
                if (
                    checkpoint.vehicle_id != vehicle_id
                    or checkpoint.mission_id != mission_id
                    or checkpoint.ranger_signing_key_id != ranger_signing_key_id
                    or checkpoint.ranger_public_key_fingerprint_sha256
                    != self.ranger_public_key_fingerprint_sha256
                    or checkpoint.registry_id != registry_id
                    or checkpoint.registry_signing_key_id != registry_signing_key_id
                    or checkpoint.registry_public_key_fingerprint_sha256
                    != self.registry_public_key_fingerprint_sha256
                ):
                    raise RangerCheckpointIntegrityError(
                        "retained checkpoint identity or signing key mismatch"
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
        records: Iterable[RangerCustodyRecord],
        *,
        received_at_utc: datetime,
    ) -> RangerRetainedCheckpoint:
        """Verify and atomically retain a newer Ranger custody head."""

        received_at = _require_aware_utc(received_at_utc)
        chain = list(records)
        verification = RangerCustodyLedger.verify_chain(chain, self.ranger_public_key_hex)
        if not verification.valid or verification.head_digest_sha256 is None:
            raise RangerCheckpointError(f"Ranger custody chain is invalid: {verification.reason}")
        if not chain or not isinstance(chain[0].source_event, RangerBootCheckpoint):
            raise RangerCheckpointError("Ranger custody chain must start with a boot checkpoint")
        boot_checkpoint = chain[0].source_event
        first_record = chain[0]
        if (
            first_record.vehicle_id != self.vehicle_id
            or first_record.mission_id != self.mission_id
            or first_record.signing_key_id != self.ranger_signing_key_id
            or first_record.public_key_fingerprint_sha256
            != self.ranger_public_key_fingerprint_sha256
        ):
            raise RangerCheckpointError("Ranger custody identity or signing key mismatch")

        latest = self._checkpoints[-1] if self._checkpoints else None
        if latest is not None:
            if (
                boot_checkpoint.boot_sequence == latest.boot_sequence
                and len(chain) == latest.custody_record_count
                and verification.head_digest_sha256 == latest.custody_head_digest_sha256
            ):
                return latest
            if received_at <= latest.received_at_utc:
                raise RangerCheckpointConflict("registry receipt time must advance")
            self._require_extension(
                latest=latest,
                chain=chain,
                boot_checkpoint=boot_checkpoint,
                head_digest_sha256=verification.head_digest_sha256,
            )

        registry_sequence = len(self._checkpoints) + 1
        previous_checkpoint_digest = (
            _ZERO_DIGEST if latest is None else latest.checkpoint_digest_sha256
        )
        payload = _checkpoint_payload(
            registry_sequence=registry_sequence,
            previous_checkpoint_digest_sha256=previous_checkpoint_digest,
            vehicle_id=self.vehicle_id,
            mission_id=self.mission_id,
            boot_id=boot_checkpoint.boot_id,
            boot_sequence=boot_checkpoint.boot_sequence,
            custody_record_count=len(chain),
            custody_head_digest_sha256=verification.head_digest_sha256,
            ranger_signing_key_id=self.ranger_signing_key_id,
            ranger_public_key_fingerprint_sha256=self.ranger_public_key_fingerprint_sha256,
            previous_boot_id=boot_checkpoint.previous_boot_id,
            previous_custody_head_digest_sha256=(
                boot_checkpoint.previous_custody_head_digest_sha256
            ),
            received_at_utc=received_at,
            registry_id=self.registry_id,
            registry_signing_key_id=self.registry_signing_key_id,
            registry_public_key_fingerprint_sha256=(self.registry_public_key_fingerprint_sha256),
            retained_state_advanced=latest is not None,
            freshness_scope=(
                "registry_baseline" if latest is None else "newer_than_retained_checkpoint"
            ),
        )
        digest = canonical_sha256(payload)
        checkpoint_data = {
            **payload,
            "received_at_utc": received_at,
            "checkpoint_digest_sha256": digest,
            "signature_hex": self._registry_private_key.sign(canonicalize(payload)).hex(),
        }
        checkpoint = RangerRetainedCheckpoint.model_validate(checkpoint_data)
        self.store.append(checkpoint)
        self._checkpoints.append(checkpoint)
        return checkpoint

    def _require_extension(
        self,
        *,
        latest: RangerRetainedCheckpoint,
        chain: list[RangerCustodyRecord],
        boot_checkpoint: RangerBootCheckpoint,
        head_digest_sha256: str,
    ) -> None:
        if boot_checkpoint.boot_sequence < latest.boot_sequence:
            raise RangerCheckpointConflict(
                "presented Ranger chain is stale relative to retained boot sequence"
            )
        if boot_checkpoint.boot_sequence == latest.boot_sequence:
            if boot_checkpoint.boot_id != latest.boot_id:
                raise RangerCheckpointConflict("boot identity fork at retained sequence")
            if len(chain) < latest.custody_record_count:
                raise RangerCheckpointConflict(
                    "presented Ranger chain is truncated relative to retained state"
                )
            if len(chain) == latest.custody_record_count:
                raise RangerCheckpointConflict("custody head fork at retained record count")
            retained_record = chain[latest.custody_record_count - 1]
            if retained_record.record_digest_sha256 != latest.custody_head_digest_sha256:
                raise RangerCheckpointConflict(
                    "presented Ranger chain does not extend the retained custody head"
                )
            return
        if boot_checkpoint.boot_sequence != latest.boot_sequence + 1:
            raise RangerCheckpointConflict(
                "boot sequence must advance exactly once from retained state"
            )
        if boot_checkpoint.previous_boot_id != latest.boot_id:
            raise RangerCheckpointConflict("new boot does not identify retained boot")
        if boot_checkpoint.previous_custody_head_digest_sha256 != latest.custody_head_digest_sha256:
            raise RangerCheckpointConflict("new boot does not extend retained custody head")
        if head_digest_sha256 == latest.custody_head_digest_sha256:
            raise RangerCheckpointConflict("new boot cannot reuse retained custody head")

    @staticmethod
    def verify_checkpoint_chain(
        checkpoints: Iterable[RangerRetainedCheckpoint],
        registry_public_key_hex: str,
    ) -> RangerCheckpointChainVerification:
        """Verify signatures and order for a complete retained-checkpoint history."""

        try:
            public_key_bytes = bytes.fromhex(registry_public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except ValueError:
            return _checkpoint_chain_failure(0, "registry public key is not 32-byte Ed25519")
        expected_fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
        expected_sequence = 1
        previous_digest = _ZERO_DIGEST
        previous_checkpoint: RangerRetainedCheckpoint | None = None
        identities: tuple[str, str, str, str, str, str] | None = None
        count = 0
        for unvalidated in checkpoints:
            count += 1
            try:
                checkpoint = RangerRetainedCheckpoint.model_validate(unvalidated.model_dump())
            except ValidationError:
                return _checkpoint_chain_failure(
                    count, "retained checkpoint schema validation failed"
                )
            if checkpoint.registry_sequence != expected_sequence:
                return _checkpoint_chain_failure(
                    count, "missing, duplicate, or reordered registry sequence"
                )
            if checkpoint.previous_checkpoint_digest_sha256 != previous_digest:
                return _checkpoint_chain_failure(
                    count, "previous retained checkpoint digest mismatch"
                )
            if checkpoint.registry_public_key_fingerprint_sha256 != expected_fingerprint:
                return _checkpoint_chain_failure(count, "registry public key fingerprint mismatch")
            identity = (
                checkpoint.vehicle_id,
                checkpoint.mission_id,
                checkpoint.ranger_signing_key_id,
                checkpoint.ranger_public_key_fingerprint_sha256,
                checkpoint.registry_id,
                checkpoint.registry_signing_key_id,
            )
            if identities is None:
                identities = identity
            elif identity != identities:
                return _checkpoint_chain_failure(
                    count, "Ranger mission, key, or registry identity changed"
                )
            payload = _checkpoint_payload_from_record(checkpoint)
            if canonical_sha256(payload) != checkpoint.checkpoint_digest_sha256:
                return _checkpoint_chain_failure(count, "checkpoint digest mismatch")
            try:
                public_key.verify(bytes.fromhex(checkpoint.signature_hex), canonicalize(payload))
            except (InvalidSignature, ValueError):
                return _checkpoint_chain_failure(count, "checkpoint signature invalid")
            if previous_checkpoint is not None:
                reason = _checkpoint_transition_error(previous_checkpoint, checkpoint)
                if reason is not None:
                    return _checkpoint_chain_failure(count, reason)
            previous_checkpoint = checkpoint
            previous_digest = checkpoint.checkpoint_digest_sha256
            expected_sequence += 1
        if previous_checkpoint is None:
            return _checkpoint_chain_failure(0, "retained checkpoint chain is empty")
        return RangerCheckpointChainVerification(
            valid=True,
            checkpoint_count=count,
            latest_checkpoint_digest_sha256=previous_checkpoint.checkpoint_digest_sha256,
            latest_boot_sequence=previous_checkpoint.boot_sequence,
            latest_custody_head_digest_sha256=(previous_checkpoint.custody_head_digest_sha256),
            freshness_relative_to_retained_state=count > 1,
            reason=(
                "registry signatures and retained progression are valid; freshness is only "
                "relative to this supplied registry history"
            ),
        )

    @staticmethod
    def verify_presented_chain(
        records: Iterable[RangerCustodyRecord],
        latest_checkpoint: RangerRetainedCheckpoint,
        *,
        ranger_public_key_hex: str,
        registry_public_key_hex: str,
    ) -> RangerCheckpointPresentationVerification:
        """Compare a complete Ranger chain with an out-of-band retained latest checkpoint."""

        retained_boot_sequence = latest_checkpoint.boot_sequence
        retained_digest = latest_checkpoint.checkpoint_digest_sha256
        checkpoint_error = _standalone_checkpoint_error(latest_checkpoint, registry_public_key_hex)
        if checkpoint_error is not None:
            return RangerCheckpointPresentationVerification(
                valid=False,
                stale=False,
                retained_boot_sequence=retained_boot_sequence,
                retained_checkpoint_digest_sha256=retained_digest,
                reason=checkpoint_error,
            )
        chain = list(records)
        verification = RangerCustodyLedger.verify_chain(chain, ranger_public_key_hex)
        if not verification.valid or verification.head_digest_sha256 is None:
            return RangerCheckpointPresentationVerification(
                valid=False,
                stale=False,
                retained_boot_sequence=retained_boot_sequence,
                retained_checkpoint_digest_sha256=retained_digest,
                reason=f"presented Ranger custody chain is invalid: {verification.reason}",
            )
        if not chain or not isinstance(chain[0].source_event, RangerBootCheckpoint):
            return RangerCheckpointPresentationVerification(
                valid=False,
                stale=False,
                retained_boot_sequence=retained_boot_sequence,
                retained_checkpoint_digest_sha256=retained_digest,
                reason="presented Ranger chain does not start with a boot checkpoint",
            )
        boot_checkpoint = chain[0].source_event
        presented_sequence = boot_checkpoint.boot_sequence
        mapping_matches = (
            chain[0].vehicle_id == latest_checkpoint.vehicle_id
            and chain[0].mission_id == latest_checkpoint.mission_id
            and chain[0].signing_key_id == latest_checkpoint.ranger_signing_key_id
            and chain[0].public_key_fingerprint_sha256
            == latest_checkpoint.ranger_public_key_fingerprint_sha256
        )
        if not mapping_matches:
            return RangerCheckpointPresentationVerification(
                valid=False,
                stale=False,
                presented_boot_sequence=presented_sequence,
                retained_boot_sequence=retained_boot_sequence,
                retained_checkpoint_digest_sha256=retained_digest,
                reason="presented Ranger identity or key does not match retained checkpoint",
            )
        if presented_sequence < retained_boot_sequence or (
            presented_sequence == retained_boot_sequence
            and boot_checkpoint.boot_id == latest_checkpoint.boot_id
            and len(chain) < latest_checkpoint.custody_record_count
        ):
            return RangerCheckpointPresentationVerification(
                valid=False,
                stale=True,
                presented_boot_sequence=presented_sequence,
                retained_boot_sequence=retained_boot_sequence,
                retained_checkpoint_digest_sha256=retained_digest,
                reason="presented Ranger chain is stale relative to retained checkpoint",
            )
        exact_match = (
            presented_sequence == retained_boot_sequence
            and boot_checkpoint.boot_id == latest_checkpoint.boot_id
            and len(chain) == latest_checkpoint.custody_record_count
            and verification.head_digest_sha256 == latest_checkpoint.custody_head_digest_sha256
        )
        if not exact_match:
            return RangerCheckpointPresentationVerification(
                valid=False,
                stale=False,
                presented_boot_sequence=presented_sequence,
                retained_boot_sequence=retained_boot_sequence,
                retained_checkpoint_digest_sha256=retained_digest,
                reason="presented Ranger chain does not match retained latest state",
            )
        return RangerCheckpointPresentationVerification(
            valid=True,
            stale=False,
            presented_boot_sequence=presented_sequence,
            retained_boot_sequence=retained_boot_sequence,
            retained_checkpoint_digest_sha256=retained_digest,
            reason=(
                "Ranger signatures and exact retained head match; global freshness, complete "
                "capture, trusted time, semantic truth, and physical outcome are not proven"
            ),
        )

    def list_checkpoints(self) -> list[RangerRetainedCheckpoint]:
        return self.store.list_checkpoints()


def _checkpoint_payload_from_record(
    checkpoint: RangerRetainedCheckpoint,
) -> dict[str, object]:
    return _checkpoint_payload(
        registry_sequence=checkpoint.registry_sequence,
        previous_checkpoint_digest_sha256=(checkpoint.previous_checkpoint_digest_sha256),
        vehicle_id=checkpoint.vehicle_id,
        mission_id=checkpoint.mission_id,
        boot_id=checkpoint.boot_id,
        boot_sequence=checkpoint.boot_sequence,
        custody_record_count=checkpoint.custody_record_count,
        custody_head_digest_sha256=checkpoint.custody_head_digest_sha256,
        ranger_signing_key_id=checkpoint.ranger_signing_key_id,
        ranger_public_key_fingerprint_sha256=(checkpoint.ranger_public_key_fingerprint_sha256),
        previous_boot_id=checkpoint.previous_boot_id,
        previous_custody_head_digest_sha256=(checkpoint.previous_custody_head_digest_sha256),
        received_at_utc=checkpoint.received_at_utc,
        registry_id=checkpoint.registry_id,
        registry_signing_key_id=checkpoint.registry_signing_key_id,
        registry_public_key_fingerprint_sha256=(checkpoint.registry_public_key_fingerprint_sha256),
        retained_state_advanced=checkpoint.retained_state_advanced,
        freshness_scope=checkpoint.freshness_scope,
    )


def _checkpoint_payload(
    *,
    registry_sequence: int,
    previous_checkpoint_digest_sha256: str,
    vehicle_id: str,
    mission_id: str,
    boot_id: str,
    boot_sequence: int,
    custody_record_count: int,
    custody_head_digest_sha256: str,
    ranger_signing_key_id: str,
    ranger_public_key_fingerprint_sha256: str,
    previous_boot_id: str | None,
    previous_custody_head_digest_sha256: str | None,
    received_at_utc: datetime,
    registry_id: str,
    registry_signing_key_id: str,
    registry_public_key_fingerprint_sha256: str,
    retained_state_advanced: bool,
    freshness_scope: str,
) -> dict[str, object]:
    return {
        "schema_version": "ets.ranger.retained-checkpoint.v1",
        "registry_sequence": registry_sequence,
        "previous_checkpoint_digest_sha256": previous_checkpoint_digest_sha256,
        "vehicle_id": vehicle_id,
        "mission_id": mission_id,
        "boot_id": boot_id,
        "boot_sequence": boot_sequence,
        "custody_record_count": custody_record_count,
        "custody_head_digest_sha256": custody_head_digest_sha256,
        "ranger_signing_key_id": ranger_signing_key_id,
        "ranger_public_key_fingerprint_sha256": ranger_public_key_fingerprint_sha256,
        "previous_boot_id": previous_boot_id,
        "previous_custody_head_digest_sha256": previous_custody_head_digest_sha256,
        "received_at_utc": received_at_utc.astimezone(UTC).isoformat(),
        "registry_id": registry_id,
        "registry_signing_key_id": registry_signing_key_id,
        "registry_public_key_fingerprint_sha256": (registry_public_key_fingerprint_sha256),
        "ranger_chain_integrity_verified": True,
        "retained_state_advanced": retained_state_advanced,
        "freshness_scope": freshness_scope,
        "signing_algorithm": "ed25519",
        "storage_profile": "sqlite-wal-full-software-reference",
        "independent_external_custody_proven": False,
        "globally_current_state_proven": False,
        "trusted_time_proven": False,
        "complete_capture_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "registry_relative_freshness_no_global_time_completeness_truth_or_outcome_claim"
        ),
    }


def _checkpoint_transition_error(
    previous: RangerRetainedCheckpoint,
    current: RangerRetainedCheckpoint,
) -> str | None:
    if current.received_at_utc <= previous.received_at_utc:
        return "registry receipt time did not advance"
    if current.boot_sequence == previous.boot_sequence:
        if current.boot_id != previous.boot_id:
            return "boot identity fork at retained sequence"
        if (
            current.previous_boot_id != previous.previous_boot_id
            or current.previous_custody_head_digest_sha256
            != previous.previous_custody_head_digest_sha256
        ):
            return "same-boot predecessor claim changed"
        if current.custody_record_count <= previous.custody_record_count:
            return "same-boot retained record count did not advance"
        if current.custody_head_digest_sha256 == previous.custody_head_digest_sha256:
            return "same-boot custody head did not advance"
    elif current.boot_sequence == previous.boot_sequence + 1:
        if current.previous_boot_id != previous.boot_id:
            return "new boot does not identify retained boot"
        if current.previous_custody_head_digest_sha256 != previous.custody_head_digest_sha256:
            return "new boot does not extend retained custody head"
    else:
        return "retained boot sequence is missing, duplicate, or reordered"
    return None


def _standalone_checkpoint_error(
    checkpoint: RangerRetainedCheckpoint,
    registry_public_key_hex: str,
) -> str | None:
    try:
        validated = RangerRetainedCheckpoint.model_validate(checkpoint.model_dump())
        public_key_bytes = bytes.fromhex(registry_public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    except (ValidationError, ValueError):
        return "retained checkpoint or registry public key is invalid"
    if (
        hashlib.sha256(public_key_bytes).hexdigest()
        != validated.registry_public_key_fingerprint_sha256
    ):
        return "registry public key fingerprint mismatch"
    payload = _checkpoint_payload_from_record(validated)
    if canonical_sha256(payload) != validated.checkpoint_digest_sha256:
        return "retained checkpoint digest mismatch"
    try:
        public_key.verify(bytes.fromhex(validated.signature_hex), canonicalize(payload))
    except (InvalidSignature, ValueError):
        return "retained checkpoint signature invalid"
    return None


def _checkpoint_chain_failure(count: int, reason: str) -> RangerCheckpointChainVerification:
    return RangerCheckpointChainVerification(
        valid=False,
        checkpoint_count=count,
        freshness_relative_to_retained_state=False,
        reason=reason,
    )


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerCheckpointError("received_at_utc must be timezone-aware")
    return value.astimezone(UTC)
