"""Authority-history-aware retained checkpoints for Ranger custody chains.

This profile composes Ranger custody verification with the separately retained key-authority
head.  It permits authorized boot-boundary key rotation, rejects revoked or substituted keys,
and binds each accepted custody head to the exact authority view used by the verifier.  The
registry remains outside Ranger's real-time safety loop and makes no global-currentness,
operational-authorization, completeness, semantic-truth, or physical-outcome claim.
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
from ets.ranger.authority_head import (
    RangerAuthorityHeadRegistry,
    RangerRetainedAuthorityHead,
)
from ets.ranger.custody import RangerBootCheckpoint, RangerCustodyLedger, RangerCustodyRecord
from ets.ranger.key_authority import RangerKeyAuthorityEvent, RangerKeyAuthorityLedger

_ZERO_DIGEST = "0" * 64


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerAuthorityCheckpointError(RuntimeError):
    """Base error for authority-bound checkpoint verification or persistence."""


class RangerAuthorityCheckpointConflict(RangerAuthorityCheckpointError):
    """Raised when presented Ranger or authority state regresses or forks."""


class RangerAuthorityCheckpointIntegrityError(RangerAuthorityCheckpointError):
    """Raised when durable authority-bound checkpoint state is invalid."""


class RangerAuthorityBoundCheckpoint(StrictModel):
    """Registry-signed Ranger custody head bound to a retained authority-history head."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "authority-bound-retained-checkpoint/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.authority-bound-retained-checkpoint.v1"] = (
        "ets.ranger.authority-bound-retained-checkpoint.v1"
    )
    registry_sequence: int = Field(ge=1, le=2**63 - 1)
    previous_checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vehicle_id: str = Field(min_length=12, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    mission_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    boot_sequence: int = Field(ge=1, le=2**63 - 1)
    custody_record_count: int = Field(ge=1, le=2**63 - 1)
    custody_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ranger_signing_key_id: str = Field(min_length=1, max_length=256)
    ranger_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_boot_id: str | None = Field(default=None, min_length=1, max_length=128)
    previous_custody_head_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authority_head_registry_sequence: int = Field(ge=1, le=2**63 - 1)
    authority_head_checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_event_count: int = Field(ge=1, le=2**63 - 1)
    authority_history_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_id: str = Field(min_length=1, max_length=160)
    authority_signing_key_id: str = Field(min_length=1, max_length=256)
    authority_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    received_at_utc: datetime
    registry_id: str = Field(min_length=1, max_length=160)
    registry_signing_key_id: str = Field(min_length=1, max_length=256)
    registry_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ranger_chain_integrity_verified: Literal[True] = True
    authority_history_integrity_verified: Literal[True] = True
    authority_relative_key_standing_verified: Literal[True] = True
    authority_history_current_relative_to_registry: Literal[True] = True
    ranger_state_advanced: bool
    authority_state_advanced: bool
    freshness_scope: Literal[
        "registry_baseline",
        "ranger_state_advanced",
        "authority_state_advanced",
        "ranger_and_authority_state_advanced",
    ]
    signing_algorithm: Literal["ed25519"] = "ed25519"
    checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    storage_profile: Literal["sqlite-wal-full-software-reference"] = (
        "sqlite-wal-full-software-reference"
    )
    independent_external_custody_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    operational_device_authorization_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "authority_bound_registry_freshness_no_global_operational_time_completeness_truth_or_outcome_claim"
    ] = (
        "authority_bound_registry_freshness_no_global_operational_time_completeness_truth_or_"
        "outcome_claim"
    )

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
            if self.ranger_state_advanced or self.authority_state_advanced:
                raise ValueError("registry baseline cannot claim retained-state advancement")
            if self.freshness_scope != "registry_baseline":
                raise ValueError("registry baseline must use registry_baseline scope")
        else:
            if self.previous_checkpoint_digest_sha256 == _ZERO_DIGEST:
                raise ValueError("advanced checkpoint requires a predecessor digest")
            expected_scope = _freshness_scope(
                ranger_advanced=self.ranger_state_advanced,
                authority_advanced=self.authority_state_advanced,
            )
            if expected_scope == "registry_baseline":
                raise ValueError("advanced checkpoint must advance Ranger or authority state")
            if self.freshness_scope != expected_scope:
                raise ValueError("freshness scope does not match retained-state advancement")
        predecessor = (self.previous_boot_id, self.previous_custody_head_digest_sha256)
        if self.boot_sequence == 1:
            if predecessor != (None, None):
                raise ValueError("genesis boot cannot identify a previous custody chain")
        elif None in predecessor:
            raise ValueError("non-genesis boot requires the previous boot and custody head")
        return self


class RangerAuthorityCheckpointChainVerification(StrictModel):
    valid: bool
    checkpoint_count: int = Field(ge=0)
    latest_checkpoint_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    latest_boot_sequence: int | None = Field(default=None, ge=1)
    latest_authority_history_head_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    authority_bindings_verified: bool
    freshness_relative_to_retained_state: bool
    reason: str


class RangerAuthorityCheckpointPresentationVerification(StrictModel):
    valid: bool
    stale: bool
    presented_boot_sequence: int | None = Field(default=None, ge=1)
    retained_boot_sequence: int = Field(ge=1)
    retained_checkpoint_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_history_current_relative_to_registry: bool
    authority_relative_key_standing: bool
    operational_device_authorization_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    reason: str


class SQLiteRangerAuthorityCheckpointStore:
    """Crash-consistent append-only store for authority-bound Ranger checkpoints."""

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
            CREATE TABLE IF NOT EXISTS ranger_authority_bound_checkpoints (
                registry_sequence INTEGER PRIMARY KEY,
                checkpoint_digest_sha256 TEXT NOT NULL UNIQUE,
                vehicle_id TEXT NOT NULL,
                mission_id TEXT NOT NULL,
                boot_sequence INTEGER NOT NULL,
                custody_head_digest_sha256 TEXT NOT NULL,
                authority_head_checkpoint_digest_sha256 TEXT NOT NULL,
                checkpoint_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def append(self, checkpoint: RangerAuthorityBoundCheckpoint) -> None:
        checkpoint = RangerAuthorityBoundCheckpoint.model_validate(checkpoint.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT registry_sequence, checkpoint_digest_sha256
                    FROM ranger_authority_bound_checkpoints
                    ORDER BY registry_sequence DESC
                    LIMIT 1
                    """
                ).fetchone()
                expected_sequence = 1 if row is None else int(row["registry_sequence"]) + 1
                expected_previous = (
                    _ZERO_DIGEST if row is None else str(row["checkpoint_digest_sha256"])
                )
                if checkpoint.registry_sequence != expected_sequence:
                    raise RangerAuthorityCheckpointConflict(
                        f"checkpoint registry sequence must be {expected_sequence}"
                    )
                if checkpoint.previous_checkpoint_digest_sha256 != expected_previous:
                    raise RangerAuthorityCheckpointConflict(
                        "checkpoint does not extend the retained registry head"
                    )
                self._connection.execute(
                    """
                    INSERT INTO ranger_authority_bound_checkpoints (
                        registry_sequence,
                        checkpoint_digest_sha256,
                        vehicle_id,
                        mission_id,
                        boot_sequence,
                        custody_head_digest_sha256,
                        authority_head_checkpoint_digest_sha256,
                        checkpoint_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        checkpoint.registry_sequence,
                        checkpoint.checkpoint_digest_sha256,
                        checkpoint.vehicle_id,
                        checkpoint.mission_id,
                        checkpoint.boot_sequence,
                        checkpoint.custody_head_digest_sha256,
                        checkpoint.authority_head_checkpoint_digest_sha256,
                        checkpoint.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except RangerAuthorityCheckpointConflict:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerAuthorityCheckpointConflict(
                    "duplicate authority-bound checkpoint identity or digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_checkpoints(self) -> list[RangerAuthorityBoundCheckpoint]:
        with self._lock:
            integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise RangerAuthorityCheckpointIntegrityError("SQLite integrity_check failed")
            rows = self._connection.execute(
                """
                SELECT
                    registry_sequence,
                    checkpoint_digest_sha256,
                    vehicle_id,
                    mission_id,
                    boot_sequence,
                    custody_head_digest_sha256,
                    authority_head_checkpoint_digest_sha256,
                    checkpoint_json
                FROM ranger_authority_bound_checkpoints
                ORDER BY registry_sequence ASC
                """
            ).fetchall()
        try:
            checkpoints = [
                RangerAuthorityBoundCheckpoint.model_validate_json(row["checkpoint_json"])
                for row in rows
            ]
        except ValidationError as exc:
            raise RangerAuthorityCheckpointIntegrityError(
                "stored Ranger authority-bound checkpoint is invalid"
            ) from exc
        for row, checkpoint in zip(rows, checkpoints, strict=True):
            if (
                int(row["registry_sequence"]) != checkpoint.registry_sequence
                or str(row["checkpoint_digest_sha256"]) != checkpoint.checkpoint_digest_sha256
                or str(row["vehicle_id"]) != checkpoint.vehicle_id
                or str(row["mission_id"]) != checkpoint.mission_id
                or int(row["boot_sequence"]) != checkpoint.boot_sequence
                or str(row["custody_head_digest_sha256"]) != checkpoint.custody_head_digest_sha256
                or str(row["authority_head_checkpoint_digest_sha256"])
                != checkpoint.authority_head_checkpoint_digest_sha256
            ):
                raise RangerAuthorityCheckpointIntegrityError(
                    "stored authority-bound checkpoint index metadata does not match signed record"
                )
        return checkpoints


class RangerAuthorityCheckpointRegistry:
    """Retain Ranger custody heads under keys resolved by retained authority history."""

    def __init__(
        self,
        store: SQLiteRangerAuthorityCheckpointStore,
        *,
        authority_head_registry: RangerAuthorityHeadRegistry,
        vehicle_id: str,
        tenant_id: str,
        workspace_id: str,
        mission_id: str,
        registry_id: str,
        registry_signing_key_id: str,
        registry_private_key_hex: str,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerAuthorityCheckpointError("vehicle_id must use the ets-ranger: namespace")
        for name, value, maximum in (
            ("tenant_id", tenant_id, 128),
            ("workspace_id", workspace_id, 128),
            ("mission_id", mission_id, 128),
            ("registry_id", registry_id, 160),
            ("registry_signing_key_id", registry_signing_key_id, 256),
        ):
            if not value or len(value) > maximum:
                raise RangerAuthorityCheckpointError(f"{name} must contain 1-{maximum} characters")
        try:
            self._registry_private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(registry_private_key_hex)
            )
        except ValueError as exc:
            raise RangerAuthorityCheckpointError(
                "registry private key must be a 32-byte Ed25519 key"
            ) from exc

        self.store = store
        self.authority_head_registry = authority_head_registry
        self.vehicle_id = vehicle_id
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self.mission_id = mission_id
        self.registry_id = registry_id
        self.registry_signing_key_id = registry_signing_key_id
        if (
            authority_head_registry.vehicle_id != vehicle_id
            or authority_head_registry.tenant_id != tenant_id
            or authority_head_registry.workspace_id != workspace_id
            or authority_head_registry.registry_id != registry_id
            or authority_head_registry.registry_signing_key_id != registry_signing_key_id
            or authority_head_registry.registry_public_key_hex != self.registry_public_key_hex
        ):
            raise RangerAuthorityCheckpointError(
                "authority-head registry identity, scope, or signer does not match"
            )

        retained = self.store.list_checkpoints()
        if retained:
            verification = self.verify_checkpoint_chain(retained, self.registry_public_key_hex)
            if not verification.valid:
                raise RangerAuthorityCheckpointIntegrityError(
                    f"retained authority-bound chain is invalid: {verification.reason}"
                )
            retained_authority_heads = authority_head_registry.list_checkpoints()
            authority_verification = RangerAuthorityHeadRegistry.verify_checkpoint_chain(
                retained_authority_heads, self.registry_public_key_hex
            )
            if not authority_verification.valid:
                raise RangerAuthorityCheckpointIntegrityError(
                    f"retained authority-head chain is invalid: {authority_verification.reason}"
                )
            authority_heads = {
                item.checkpoint_digest_sha256: item for item in retained_authority_heads
            }
            for checkpoint in retained:
                if not self._matches_configuration(checkpoint):
                    raise RangerAuthorityCheckpointIntegrityError(
                        "retained checkpoint identity, scope, or signing key mismatch"
                    )
                head = authority_heads.get(checkpoint.authority_head_checkpoint_digest_sha256)
                if head is None or not _checkpoint_matches_authority_head(checkpoint, head):
                    raise RangerAuthorityCheckpointIntegrityError(
                        "retained checkpoint authority-head binding is unavailable or mismatched"
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
        authority_events: Iterable[RangerKeyAuthorityEvent],
        *,
        received_at_utc: datetime,
    ) -> RangerAuthorityBoundCheckpoint:
        """Retain authority state first, then accept custody only under its resolved key."""

        retained = self.store.list_checkpoints()
        if retained != self._checkpoints:
            raise RangerAuthorityCheckpointConflict(
                "retained checkpoint history changed; reopen the registry before appending"
            )
        received_at = _require_aware_utc(received_at_utc)
        history = list(authority_events)
        authority_head = self.authority_head_registry.retain(history, received_at_utc=received_at)
        chain = list(records)
        boot_checkpoint = _first_boot_checkpoint(chain)
        if boot_checkpoint is None:
            raise RangerAuthorityCheckpointError(
                "Ranger custody chain must start with a boot checkpoint"
            )
        first_record = chain[0]
        if first_record.vehicle_id != self.vehicle_id or first_record.mission_id != self.mission_id:
            raise RangerAuthorityCheckpointError("Ranger custody identity mismatch")
        decision = RangerKeyAuthorityLedger.authorize_key(
            history,
            self.authority_head_registry.authority_public_key_hex,
            vehicle_id=self.vehicle_id,
            tenant_id=self.tenant_id,
            workspace_id=self.workspace_id,
            boot_sequence=boot_checkpoint.boot_sequence,
            signing_key_id=first_record.signing_key_id,
            public_key_fingerprint_sha256=(first_record.public_key_fingerprint_sha256),
        )
        if not decision.allowed or decision.public_key_hex is None:
            raise RangerAuthorityCheckpointError(
                f"Ranger custody key lacks authority-relative standing: {decision.reason.value}"
            )
        if decision.public_key_hex == self.registry_public_key_hex:
            raise RangerAuthorityCheckpointError(
                "registry and Ranger custody signing keys must be distinct"
            )
        verification = RangerCustodyLedger.verify_chain(chain, decision.public_key_hex)
        if not verification.valid or verification.head_digest_sha256 is None:
            raise RangerAuthorityCheckpointError(
                f"Ranger custody chain is invalid: {verification.reason}"
            )

        latest = self._checkpoints[-1] if self._checkpoints else None
        ranger_same = latest is not None and _matches_ranger_state(
            latest, chain, boot_checkpoint, verification.head_digest_sha256
        )
        authority_same = latest is not None and _matches_authority_state(latest, authority_head)
        if latest is not None and ranger_same and authority_same:
            return latest
        if received_at < authority_head.received_at_utc:
            raise RangerAuthorityCheckpointConflict(
                "checkpoint receipt time predates the bound retained authority head"
            )
        if latest is not None:
            if received_at <= latest.received_at_utc:
                raise RangerAuthorityCheckpointConflict("registry receipt time must advance")
            if not ranger_same:
                _require_ranger_extension(
                    latest=latest,
                    chain=chain,
                    boot_checkpoint=boot_checkpoint,
                    head_digest_sha256=verification.head_digest_sha256,
                )
            if not authority_same and (
                authority_head.registry_sequence <= latest.authority_head_registry_sequence
            ):
                raise RangerAuthorityCheckpointConflict(
                    "authority-head registry sequence did not advance"
                )

        ranger_advanced = latest is not None and not ranger_same
        authority_advanced = latest is not None and not authority_same
        payload = _checkpoint_payload(
            registry_sequence=len(self._checkpoints) + 1,
            previous_checkpoint_digest_sha256=(
                _ZERO_DIGEST if latest is None else latest.checkpoint_digest_sha256
            ),
            vehicle_id=self.vehicle_id,
            tenant_id=self.tenant_id,
            workspace_id=self.workspace_id,
            mission_id=self.mission_id,
            boot_id=boot_checkpoint.boot_id,
            boot_sequence=boot_checkpoint.boot_sequence,
            custody_record_count=len(chain),
            custody_head_digest_sha256=verification.head_digest_sha256,
            ranger_signing_key_id=first_record.signing_key_id,
            ranger_public_key_fingerprint_sha256=(first_record.public_key_fingerprint_sha256),
            previous_boot_id=boot_checkpoint.previous_boot_id,
            previous_custody_head_digest_sha256=(
                boot_checkpoint.previous_custody_head_digest_sha256
            ),
            authority_head_registry_sequence=authority_head.registry_sequence,
            authority_head_checkpoint_digest_sha256=(authority_head.checkpoint_digest_sha256),
            authority_event_count=authority_head.authority_event_count,
            authority_history_head_digest_sha256=(
                authority_head.authority_history_head_digest_sha256
            ),
            authority_id=authority_head.authority_id,
            authority_signing_key_id=authority_head.authority_signing_key_id,
            authority_public_key_fingerprint_sha256=(
                authority_head.authority_public_key_fingerprint_sha256
            ),
            received_at_utc=received_at,
            registry_id=self.registry_id,
            registry_signing_key_id=self.registry_signing_key_id,
            registry_public_key_fingerprint_sha256=(self.registry_public_key_fingerprint_sha256),
            ranger_state_advanced=ranger_advanced,
            authority_state_advanced=authority_advanced,
            freshness_scope=_freshness_scope(
                ranger_advanced=ranger_advanced,
                authority_advanced=authority_advanced,
            ),
        )
        digest = canonical_sha256(payload)
        checkpoint = RangerAuthorityBoundCheckpoint.model_validate(
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

    def _matches_configuration(self, checkpoint: RangerAuthorityBoundCheckpoint) -> bool:
        authority = self.authority_head_registry
        return (
            checkpoint.vehicle_id == self.vehicle_id
            and checkpoint.tenant_id == self.tenant_id
            and checkpoint.workspace_id == self.workspace_id
            and checkpoint.mission_id == self.mission_id
            and checkpoint.authority_id == authority.authority_id
            and checkpoint.authority_signing_key_id == authority.authority_signing_key_id
            and checkpoint.authority_public_key_fingerprint_sha256
            == authority.authority_public_key_fingerprint_sha256
            and checkpoint.registry_id == self.registry_id
            and checkpoint.registry_signing_key_id == self.registry_signing_key_id
            and checkpoint.registry_public_key_fingerprint_sha256
            == self.registry_public_key_fingerprint_sha256
        )

    @staticmethod
    def verify_checkpoint_chain(
        checkpoints: Iterable[RangerAuthorityBoundCheckpoint],
        registry_public_key_hex: str,
    ) -> RangerAuthorityCheckpointChainVerification:
        """Verify signed structural progression without reconstructing source custody."""

        try:
            public_key_bytes = bytes.fromhex(registry_public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except ValueError:
            return _chain_failure(0, "registry public key is not 32-byte Ed25519")
        expected_fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
        expected_sequence = 1
        previous_digest = _ZERO_DIGEST
        previous: RangerAuthorityBoundCheckpoint | None = None
        identity: tuple[str, ...] | None = None
        count = 0
        for unvalidated in checkpoints:
            count += 1
            try:
                checkpoint = RangerAuthorityBoundCheckpoint.model_validate(unvalidated.model_dump())
            except (AttributeError, ValidationError):
                return _chain_failure(count, "authority-bound checkpoint schema invalid")
            if checkpoint.registry_sequence != expected_sequence:
                return _chain_failure(
                    count, "missing, duplicate, or reordered checkpoint registry sequence"
                )
            if checkpoint.previous_checkpoint_digest_sha256 != previous_digest:
                return _chain_failure(count, "previous checkpoint digest mismatch")
            if checkpoint.registry_public_key_fingerprint_sha256 != expected_fingerprint:
                return _chain_failure(count, "registry public key fingerprint mismatch")
            current_identity = (
                checkpoint.vehicle_id,
                checkpoint.tenant_id,
                checkpoint.workspace_id,
                checkpoint.mission_id,
                checkpoint.authority_id,
                checkpoint.authority_signing_key_id,
                checkpoint.authority_public_key_fingerprint_sha256,
                checkpoint.registry_id,
                checkpoint.registry_signing_key_id,
            )
            if identity is None:
                identity = current_identity
            elif current_identity != identity:
                return _chain_failure(
                    count, "Ranger scope, mission, authority, or registry identity changed"
                )
            payload = _checkpoint_payload_from_record(checkpoint)
            if canonical_sha256(payload) != checkpoint.checkpoint_digest_sha256:
                return _chain_failure(count, "checkpoint digest mismatch")
            try:
                public_key.verify(bytes.fromhex(checkpoint.signature_hex), canonicalize(payload))
            except (InvalidSignature, ValueError):
                return _chain_failure(count, "checkpoint signature invalid")
            if previous is not None:
                error = _checkpoint_transition_error(previous, checkpoint)
                if error is not None:
                    return _chain_failure(count, error)
            previous = checkpoint
            previous_digest = checkpoint.checkpoint_digest_sha256
            expected_sequence += 1
        if previous is None:
            return _chain_failure(0, "authority-bound checkpoint chain is empty")
        return RangerAuthorityCheckpointChainVerification(
            valid=True,
            checkpoint_count=count,
            latest_checkpoint_digest_sha256=previous.checkpoint_digest_sha256,
            latest_boot_sequence=previous.boot_sequence,
            latest_authority_history_head_digest_sha256=(
                previous.authority_history_head_digest_sha256
            ),
            authority_bindings_verified=False,
            freshness_relative_to_retained_state=count > 1,
            reason=(
                "registry signatures and structural progression are valid; authority bindings "
                "require the referenced retained heads and authority history"
            ),
        )

    @staticmethod
    def verify_bound_checkpoint_chain(
        checkpoints: Iterable[RangerAuthorityBoundCheckpoint],
        authority_heads: Iterable[RangerRetainedAuthorityHead],
        authority_events: Iterable[RangerKeyAuthorityEvent],
        *,
        registry_public_key_hex: str,
        authority_public_key_hex: str,
    ) -> RangerAuthorityCheckpointChainVerification:
        """Verify checkpoint signatures plus every retained authority-prefix binding."""

        retained = list(checkpoints)
        heads = list(authority_heads)
        history = list(authority_events)
        structural = RangerAuthorityCheckpointRegistry.verify_checkpoint_chain(
            retained, registry_public_key_hex
        )
        if not structural.valid:
            return structural
        head_chain = RangerAuthorityHeadRegistry.verify_checkpoint_chain(
            heads, registry_public_key_hex
        )
        if not head_chain.valid:
            return _chain_failure(
                len(retained), f"retained authority-head chain is invalid: {head_chain.reason}"
            )
        if not heads:
            return _chain_failure(len(retained), "retained authority-head chain is empty")
        current_history = RangerAuthorityHeadRegistry.verify_presented_history(
            history,
            heads[-1],
            authority_public_key_hex=authority_public_key_hex,
            registry_public_key_hex=registry_public_key_hex,
        )
        if not current_history.valid:
            return _chain_failure(
                len(retained),
                f"authority history does not match retained latest head: {current_history.reason}",
            )
        head_by_digest = {head.checkpoint_digest_sha256: head for head in heads}
        for index, checkpoint in enumerate(retained, start=1):
            head = head_by_digest.get(checkpoint.authority_head_checkpoint_digest_sha256)
            if head is None or not _checkpoint_matches_authority_head(checkpoint, head):
                return _chain_failure(index, "checkpoint authority-head binding mismatch")
            prefix = history[: head.authority_event_count]
            prefix_verification = RangerKeyAuthorityLedger.verify_history(
                prefix, authority_public_key_hex
            )
            if (
                not prefix_verification.valid
                or prefix_verification.head_digest_sha256
                != head.authority_history_head_digest_sha256
            ):
                return _chain_failure(index, "checkpoint authority-history prefix is invalid")
            decision = RangerKeyAuthorityLedger.authorize_key(
                prefix,
                authority_public_key_hex,
                vehicle_id=checkpoint.vehicle_id,
                tenant_id=checkpoint.tenant_id,
                workspace_id=checkpoint.workspace_id,
                boot_sequence=checkpoint.boot_sequence,
                signing_key_id=checkpoint.ranger_signing_key_id,
                public_key_fingerprint_sha256=(checkpoint.ranger_public_key_fingerprint_sha256),
            )
            if not decision.allowed:
                return _chain_failure(
                    index,
                    "checkpoint Ranger key lacks standing in its bound authority prefix: "
                    f"{decision.reason.value}",
                )
        latest = retained[-1]
        return RangerAuthorityCheckpointChainVerification(
            valid=True,
            checkpoint_count=len(retained),
            latest_checkpoint_digest_sha256=latest.checkpoint_digest_sha256,
            latest_boot_sequence=latest.boot_sequence,
            latest_authority_history_head_digest_sha256=(
                heads[-1].authority_history_head_digest_sha256
            ),
            authority_bindings_verified=True,
            freshness_relative_to_retained_state=len(retained) > 1,
            reason=(
                "registry signatures, retained authority heads, authority-history prefixes, "
                "and authority-relative Ranger key standing are valid; source custody, global "
                "currentness, and operational authorization are not proven by checkpoints alone"
            ),
        )

    @staticmethod
    def verify_presented_chain(
        records: Iterable[RangerCustodyRecord],
        latest_checkpoint: RangerAuthorityBoundCheckpoint,
        authority_heads: Iterable[RangerRetainedAuthorityHead],
        authority_events: Iterable[RangerKeyAuthorityEvent],
        *,
        registry_public_key_hex: str,
        authority_public_key_hex: str,
    ) -> RangerAuthorityCheckpointPresentationVerification:
        """Verify current authority standing and exact Ranger state against retained views."""

        retained_sequence = latest_checkpoint.boot_sequence
        retained_digest = latest_checkpoint.checkpoint_digest_sha256
        error = _standalone_checkpoint_error(latest_checkpoint, registry_public_key_hex)
        if error is not None:
            return _presentation_failure(retained_sequence, retained_digest, error)
        heads = list(authority_heads)
        head_verification = RangerAuthorityHeadRegistry.verify_checkpoint_chain(
            heads, registry_public_key_hex
        )
        if not head_verification.valid:
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                f"retained authority-head chain is invalid: {head_verification.reason}",
            )
        latest_authority_head = heads[-1]
        history = list(authority_events)
        history_result = RangerAuthorityHeadRegistry.verify_presented_history(
            history,
            latest_authority_head,
            authority_public_key_hex=authority_public_key_hex,
            registry_public_key_hex=registry_public_key_hex,
        )
        if not history_result.valid:
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                f"authority history is not current relative to registry: {history_result.reason}",
                stale=history_result.stale,
            )
        bound_head = next(
            (
                head
                for head in heads
                if head.checkpoint_digest_sha256
                == latest_checkpoint.authority_head_checkpoint_digest_sha256
            ),
            None,
        )
        if bound_head is None or not _checkpoint_matches_authority_head(
            latest_checkpoint, bound_head
        ):
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                "Ranger checkpoint authority-head binding is unavailable or mismatched",
            )
        bound_prefix = history[: bound_head.authority_event_count]
        if (
            not bound_prefix
            or bound_prefix[-1].event_digest_sha256
            != latest_checkpoint.authority_history_head_digest_sha256
        ):
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                "Ranger checkpoint authority-history prefix does not match current history",
            )

        chain = list(records)
        boot = _first_boot_checkpoint(chain)
        if boot is None:
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                "presented Ranger chain does not start with a boot checkpoint",
            )
        first = chain[0]
        decision = RangerKeyAuthorityLedger.authorize_key(
            history,
            authority_public_key_hex,
            vehicle_id=first.vehicle_id,
            tenant_id=latest_checkpoint.tenant_id,
            workspace_id=latest_checkpoint.workspace_id,
            boot_sequence=boot.boot_sequence,
            signing_key_id=first.signing_key_id,
            public_key_fingerprint_sha256=first.public_key_fingerprint_sha256,
        )
        if not decision.allowed or decision.public_key_hex is None:
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                "presented Ranger key lacks current authority-relative standing: "
                f"{decision.reason.value}",
                presented_sequence=boot.boot_sequence,
                authority_current=True,
            )
        verification = RangerCustodyLedger.verify_chain(chain, decision.public_key_hex)
        if not verification.valid or verification.head_digest_sha256 is None:
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                f"presented Ranger custody chain is invalid: {verification.reason}",
                presented_sequence=boot.boot_sequence,
                authority_current=True,
            )
        if (
            first.vehicle_id != latest_checkpoint.vehicle_id
            or first.mission_id != latest_checkpoint.mission_id
        ):
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                "presented Ranger identity or mission does not match retained checkpoint",
                presented_sequence=boot.boot_sequence,
                authority_current=True,
                authority_standing=True,
            )
        if boot.boot_sequence < retained_sequence or (
            boot.boot_sequence == retained_sequence
            and boot.boot_id == latest_checkpoint.boot_id
            and len(chain) < latest_checkpoint.custody_record_count
        ):
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                "presented Ranger chain is stale relative to retained checkpoint",
                stale=True,
                presented_sequence=boot.boot_sequence,
                authority_current=True,
                authority_standing=True,
            )
        exact = (
            boot.boot_sequence == retained_sequence
            and boot.boot_id == latest_checkpoint.boot_id
            and len(chain) == latest_checkpoint.custody_record_count
            and verification.head_digest_sha256 == latest_checkpoint.custody_head_digest_sha256
            and first.signing_key_id == latest_checkpoint.ranger_signing_key_id
            and first.public_key_fingerprint_sha256
            == latest_checkpoint.ranger_public_key_fingerprint_sha256
        )
        if not exact:
            return _presentation_failure(
                retained_sequence,
                retained_digest,
                "presented Ranger chain does not match retained latest state",
                presented_sequence=boot.boot_sequence,
                authority_current=True,
                authority_standing=True,
            )
        return RangerAuthorityCheckpointPresentationVerification(
            valid=True,
            stale=False,
            presented_boot_sequence=boot.boot_sequence,
            retained_boot_sequence=retained_sequence,
            retained_checkpoint_digest_sha256=retained_digest,
            authority_history_current_relative_to_registry=True,
            authority_relative_key_standing=True,
            reason=(
                "Ranger signatures, current authority-relative key standing, and exact retained "
                "heads match; global currentness, operational authorization, completeness, "
                "trusted time, semantic truth, and physical outcome are not proven"
            ),
        )

    def list_checkpoints(self) -> list[RangerAuthorityBoundCheckpoint]:
        return self.store.list_checkpoints()


def _matches_ranger_state(
    checkpoint: RangerAuthorityBoundCheckpoint,
    chain: list[RangerCustodyRecord],
    boot: RangerBootCheckpoint,
    head_digest_sha256: str,
) -> bool:
    first = chain[0]
    return (
        boot.boot_id == checkpoint.boot_id
        and boot.boot_sequence == checkpoint.boot_sequence
        and len(chain) == checkpoint.custody_record_count
        and head_digest_sha256 == checkpoint.custody_head_digest_sha256
        and first.signing_key_id == checkpoint.ranger_signing_key_id
        and first.public_key_fingerprint_sha256 == checkpoint.ranger_public_key_fingerprint_sha256
    )


def _first_boot_checkpoint(
    records: list[RangerCustodyRecord],
) -> RangerBootCheckpoint | None:
    if not records or records[0].custody_sequence != 1:
        return None
    source = records[0].source_event
    return source if isinstance(source, RangerBootCheckpoint) else None


def _matches_authority_state(
    checkpoint: RangerAuthorityBoundCheckpoint,
    head: RangerRetainedAuthorityHead,
) -> bool:
    return (
        checkpoint.authority_head_registry_sequence == head.registry_sequence
        and checkpoint.authority_head_checkpoint_digest_sha256 == head.checkpoint_digest_sha256
        and checkpoint.authority_event_count == head.authority_event_count
        and checkpoint.authority_history_head_digest_sha256
        == head.authority_history_head_digest_sha256
    )


def _checkpoint_matches_authority_head(
    checkpoint: RangerAuthorityBoundCheckpoint,
    head: RangerRetainedAuthorityHead,
) -> bool:
    return (
        _matches_authority_state(checkpoint, head)
        and checkpoint.vehicle_id == head.vehicle_id
        and checkpoint.tenant_id == head.tenant_id
        and checkpoint.workspace_id == head.workspace_id
        and checkpoint.authority_id == head.authority_id
        and checkpoint.authority_signing_key_id == head.authority_signing_key_id
        and checkpoint.authority_public_key_fingerprint_sha256
        == head.authority_public_key_fingerprint_sha256
        and checkpoint.registry_id == head.registry_id
        and checkpoint.registry_signing_key_id == head.registry_signing_key_id
        and checkpoint.registry_public_key_fingerprint_sha256
        == head.registry_public_key_fingerprint_sha256
        and checkpoint.received_at_utc >= head.received_at_utc
    )


def _require_ranger_extension(
    *,
    latest: RangerAuthorityBoundCheckpoint,
    chain: list[RangerCustodyRecord],
    boot_checkpoint: RangerBootCheckpoint,
    head_digest_sha256: str,
) -> None:
    if boot_checkpoint.boot_sequence < latest.boot_sequence:
        raise RangerAuthorityCheckpointConflict(
            "presented Ranger chain is stale relative to retained boot sequence"
        )
    first = chain[0]
    if boot_checkpoint.boot_sequence == latest.boot_sequence:
        if boot_checkpoint.boot_id != latest.boot_id:
            raise RangerAuthorityCheckpointConflict("boot identity fork at retained sequence")
        if (
            first.signing_key_id != latest.ranger_signing_key_id
            or first.public_key_fingerprint_sha256 != latest.ranger_public_key_fingerprint_sha256
        ):
            raise RangerAuthorityCheckpointConflict("Ranger custody key changed within one boot")
        if len(chain) < latest.custody_record_count:
            raise RangerAuthorityCheckpointConflict(
                "presented Ranger chain is truncated relative to retained state"
            )
        if len(chain) == latest.custody_record_count:
            raise RangerAuthorityCheckpointConflict("custody head fork at retained record count")
        if (
            chain[latest.custody_record_count - 1].record_digest_sha256
            != latest.custody_head_digest_sha256
        ):
            raise RangerAuthorityCheckpointConflict(
                "presented Ranger chain does not extend the retained custody head"
            )
        return
    if boot_checkpoint.boot_sequence != latest.boot_sequence + 1:
        raise RangerAuthorityCheckpointConflict(
            "boot sequence must advance exactly once from retained state"
        )
    if boot_checkpoint.previous_boot_id != latest.boot_id:
        raise RangerAuthorityCheckpointConflict("new boot does not identify retained boot")
    if boot_checkpoint.previous_custody_head_digest_sha256 != latest.custody_head_digest_sha256:
        raise RangerAuthorityCheckpointConflict("new boot does not extend retained custody head")
    if head_digest_sha256 == latest.custody_head_digest_sha256:
        raise RangerAuthorityCheckpointConflict("new boot cannot reuse retained custody head")


def _checkpoint_transition_error(
    previous: RangerAuthorityBoundCheckpoint,
    current: RangerAuthorityBoundCheckpoint,
) -> str | None:
    if current.received_at_utc <= previous.received_at_utc:
        return "registry receipt time did not advance"
    ranger_same = _checkpoint_ranger_state(previous) == _checkpoint_ranger_state(current)
    authority_same = _checkpoint_authority_state(previous) == _checkpoint_authority_state(current)
    if current.ranger_state_advanced == ranger_same:
        return "Ranger advancement claim does not match retained state"
    if current.authority_state_advanced == authority_same:
        return "authority advancement claim does not match retained state"
    expected_scope = _freshness_scope(
        ranger_advanced=not ranger_same,
        authority_advanced=not authority_same,
    )
    if current.freshness_scope != expected_scope:
        return "freshness scope does not match retained-state transition"
    if not ranger_same:
        if current.boot_sequence == previous.boot_sequence:
            if current.boot_id != previous.boot_id:
                return "boot identity fork at retained sequence"
            if (
                current.ranger_signing_key_id != previous.ranger_signing_key_id
                or current.ranger_public_key_fingerprint_sha256
                != previous.ranger_public_key_fingerprint_sha256
            ):
                return "Ranger custody key changed within one boot"
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
    if not authority_same:
        if current.authority_head_registry_sequence <= previous.authority_head_registry_sequence:
            return "authority-head registry sequence did not advance"
        if current.authority_event_count <= previous.authority_event_count:
            return "retained authority event count did not advance"
        if (
            current.authority_history_head_digest_sha256
            == previous.authority_history_head_digest_sha256
            or current.authority_head_checkpoint_digest_sha256
            == previous.authority_head_checkpoint_digest_sha256
        ):
            return "retained authority head did not advance"
    return None


def _checkpoint_ranger_state(
    checkpoint: RangerAuthorityBoundCheckpoint,
) -> tuple[object, ...]:
    return (
        checkpoint.boot_id,
        checkpoint.boot_sequence,
        checkpoint.custody_record_count,
        checkpoint.custody_head_digest_sha256,
        checkpoint.ranger_signing_key_id,
        checkpoint.ranger_public_key_fingerprint_sha256,
        checkpoint.previous_boot_id,
        checkpoint.previous_custody_head_digest_sha256,
    )


def _checkpoint_authority_state(
    checkpoint: RangerAuthorityBoundCheckpoint,
) -> tuple[object, ...]:
    return (
        checkpoint.authority_head_registry_sequence,
        checkpoint.authority_head_checkpoint_digest_sha256,
        checkpoint.authority_event_count,
        checkpoint.authority_history_head_digest_sha256,
    )


def _checkpoint_payload_from_record(
    checkpoint: RangerAuthorityBoundCheckpoint,
) -> dict[str, object]:
    return _checkpoint_payload(
        registry_sequence=checkpoint.registry_sequence,
        previous_checkpoint_digest_sha256=checkpoint.previous_checkpoint_digest_sha256,
        vehicle_id=checkpoint.vehicle_id,
        tenant_id=checkpoint.tenant_id,
        workspace_id=checkpoint.workspace_id,
        mission_id=checkpoint.mission_id,
        boot_id=checkpoint.boot_id,
        boot_sequence=checkpoint.boot_sequence,
        custody_record_count=checkpoint.custody_record_count,
        custody_head_digest_sha256=checkpoint.custody_head_digest_sha256,
        ranger_signing_key_id=checkpoint.ranger_signing_key_id,
        ranger_public_key_fingerprint_sha256=(checkpoint.ranger_public_key_fingerprint_sha256),
        previous_boot_id=checkpoint.previous_boot_id,
        previous_custody_head_digest_sha256=(checkpoint.previous_custody_head_digest_sha256),
        authority_head_registry_sequence=checkpoint.authority_head_registry_sequence,
        authority_head_checkpoint_digest_sha256=(
            checkpoint.authority_head_checkpoint_digest_sha256
        ),
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
        ranger_state_advanced=checkpoint.ranger_state_advanced,
        authority_state_advanced=checkpoint.authority_state_advanced,
        freshness_scope=checkpoint.freshness_scope,
    )


def _checkpoint_payload(
    *,
    registry_sequence: int,
    previous_checkpoint_digest_sha256: str,
    vehicle_id: str,
    tenant_id: str,
    workspace_id: str,
    mission_id: str,
    boot_id: str,
    boot_sequence: int,
    custody_record_count: int,
    custody_head_digest_sha256: str,
    ranger_signing_key_id: str,
    ranger_public_key_fingerprint_sha256: str,
    previous_boot_id: str | None,
    previous_custody_head_digest_sha256: str | None,
    authority_head_registry_sequence: int,
    authority_head_checkpoint_digest_sha256: str,
    authority_event_count: int,
    authority_history_head_digest_sha256: str,
    authority_id: str,
    authority_signing_key_id: str,
    authority_public_key_fingerprint_sha256: str,
    received_at_utc: datetime,
    registry_id: str,
    registry_signing_key_id: str,
    registry_public_key_fingerprint_sha256: str,
    ranger_state_advanced: bool,
    authority_state_advanced: bool,
    freshness_scope: str,
) -> dict[str, object]:
    return {
        "schema_version": "ets.ranger.authority-bound-retained-checkpoint.v1",
        "registry_sequence": registry_sequence,
        "previous_checkpoint_digest_sha256": previous_checkpoint_digest_sha256,
        "vehicle_id": vehicle_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "mission_id": mission_id,
        "boot_id": boot_id,
        "boot_sequence": boot_sequence,
        "custody_record_count": custody_record_count,
        "custody_head_digest_sha256": custody_head_digest_sha256,
        "ranger_signing_key_id": ranger_signing_key_id,
        "ranger_public_key_fingerprint_sha256": ranger_public_key_fingerprint_sha256,
        "previous_boot_id": previous_boot_id,
        "previous_custody_head_digest_sha256": previous_custody_head_digest_sha256,
        "authority_head_registry_sequence": authority_head_registry_sequence,
        "authority_head_checkpoint_digest_sha256": (authority_head_checkpoint_digest_sha256),
        "authority_event_count": authority_event_count,
        "authority_history_head_digest_sha256": authority_history_head_digest_sha256,
        "authority_id": authority_id,
        "authority_signing_key_id": authority_signing_key_id,
        "authority_public_key_fingerprint_sha256": (authority_public_key_fingerprint_sha256),
        "received_at_utc": received_at_utc.astimezone(UTC).isoformat(),
        "registry_id": registry_id,
        "registry_signing_key_id": registry_signing_key_id,
        "registry_public_key_fingerprint_sha256": (registry_public_key_fingerprint_sha256),
        "ranger_chain_integrity_verified": True,
        "authority_history_integrity_verified": True,
        "authority_relative_key_standing_verified": True,
        "authority_history_current_relative_to_registry": True,
        "ranger_state_advanced": ranger_state_advanced,
        "authority_state_advanced": authority_state_advanced,
        "freshness_scope": freshness_scope,
        "signing_algorithm": "ed25519",
        "storage_profile": "sqlite-wal-full-software-reference",
        "independent_external_custody_proven": False,
        "globally_current_state_proven": False,
        "operational_device_authorization_proven": False,
        "trusted_time_proven": False,
        "complete_capture_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "authority_bound_registry_freshness_no_global_operational_time_completeness_"
            "truth_or_outcome_claim"
        ),
    }


def _standalone_checkpoint_error(
    checkpoint: RangerAuthorityBoundCheckpoint,
    registry_public_key_hex: str,
) -> str | None:
    try:
        validated = RangerAuthorityBoundCheckpoint.model_validate(checkpoint.model_dump())
        public_key_bytes = bytes.fromhex(registry_public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    except (AttributeError, ValidationError, ValueError):
        return "authority-bound checkpoint or registry public key is invalid"
    if (
        hashlib.sha256(public_key_bytes).hexdigest()
        != validated.registry_public_key_fingerprint_sha256
    ):
        return "registry public key fingerprint mismatch"
    payload = _checkpoint_payload_from_record(validated)
    if canonical_sha256(payload) != validated.checkpoint_digest_sha256:
        return "authority-bound checkpoint digest mismatch"
    try:
        public_key.verify(bytes.fromhex(validated.signature_hex), canonicalize(payload))
    except (InvalidSignature, ValueError):
        return "authority-bound checkpoint signature invalid"
    return None


def _freshness_scope(*, ranger_advanced: bool, authority_advanced: bool) -> str:
    if ranger_advanced and authority_advanced:
        return "ranger_and_authority_state_advanced"
    if ranger_advanced:
        return "ranger_state_advanced"
    if authority_advanced:
        return "authority_state_advanced"
    return "registry_baseline"


def _chain_failure(count: int, reason: str) -> RangerAuthorityCheckpointChainVerification:
    return RangerAuthorityCheckpointChainVerification(
        valid=False,
        checkpoint_count=count,
        authority_bindings_verified=False,
        freshness_relative_to_retained_state=False,
        reason=reason,
    )


def _presentation_failure(
    retained_sequence: int,
    retained_digest: str,
    reason: str,
    *,
    stale: bool = False,
    presented_sequence: int | None = None,
    authority_current: bool = False,
    authority_standing: bool = False,
) -> RangerAuthorityCheckpointPresentationVerification:
    return RangerAuthorityCheckpointPresentationVerification(
        valid=False,
        stale=stale,
        presented_boot_sequence=presented_sequence,
        retained_boot_sequence=retained_sequence,
        retained_checkpoint_digest_sha256=retained_digest,
        authority_history_current_relative_to_registry=authority_current,
        authority_relative_key_standing=authority_standing,
        reason=reason,
    )


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerAuthorityCheckpointError("received_at_utc must be timezone-aware")
    return value.astimezone(UTC)
