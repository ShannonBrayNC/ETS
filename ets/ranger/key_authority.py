"""Authority-signed lifecycle evidence for Ranger custody signing keys.

The Ranger custody chain proves that records were signed by a particular key.  This module
adds a separate, append-only authority history that can establish whether that key was enrolled,
rotated, or revoked for a Ranger boot sequence.  It deliberately does not replace ETS Fleet
device authorization or prove trusted time, hardware custody, administrative independence,
semantic truth, or physical outcome.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
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
from ets.ranger.custody import RangerBootCheckpoint, RangerCustodyLedger, RangerCustodyRecord
from ets.ranger.mobility import ClockQuality

_ZERO_DIGEST = "0" * 64


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerKeyAuthorityError(RuntimeError):
    """Base error for Ranger signing-key authority validation or persistence."""


class RangerKeyAuthorityConflict(RangerKeyAuthorityError):
    """Raised when an authority event conflicts with retained key history."""


class RangerKeyAuthorityIntegrityError(RangerKeyAuthorityError):
    """Raised when retained authority history cannot be parsed or verified."""


class RangerKeyEventKind(StrEnum):
    ENROLL = "enroll"
    ROTATE = "rotate"
    REVOKE = "revoke"


class RangerKeyRevocationReason(StrEnum):
    COMPROMISE_SUSPECTED = "compromise_suspected"
    CUSTODY_LOST = "custody_lost"
    ADMINISTRATIVE = "administrative"
    RETIRED = "retired"


class RangerKeyAuthorizationReason(StrEnum):
    AUTHORIZED = "authorized"
    HISTORY_INVALID = "history_invalid"
    IDENTITY_SCOPE_MISMATCH = "identity_scope_mismatch"
    NOT_YET_ENROLLED = "not_yet_enrolled"
    CREDENTIAL_NOT_YET_ACTIVE = "credential_not_yet_active"
    CREDENTIAL_MISMATCH = "credential_mismatch"
    SUPERSEDED_CREDENTIAL = "superseded_credential"
    REVOKED = "revoked"


class RangerSigningKeyDescriptor(StrictModel):
    """Public, non-secret identity for one R0 software custody key."""

    signing_key_id: str = Field(min_length=1, max_length=256)
    public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    key_custody: Literal["software_demo"] = "software_demo"
    hardware_backed_key_proven: Literal[False] = False

    @model_validator(mode="after")
    def require_matching_ed25519_fingerprint(self) -> Self:
        try:
            public_key_bytes = bytes.fromhex(self.public_key_hex)
            Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except ValueError as exc:
            raise ValueError("public key must be a 32-byte Ed25519 key") from exc
        if hashlib.sha256(public_key_bytes).hexdigest() != self.public_key_fingerprint_sha256:
            raise ValueError("public key fingerprint does not match public key")
        return self


class RangerKeyBindingIntent(StrictModel):
    """Unsigned enrollment, rotation, or revocation intent."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/key-binding-intent/v1"
        },
    )

    schema_version: Literal["ets.ranger.key-binding-intent.v1"] = (
        "ets.ranger.key-binding-intent.v1"
    )
    request_id: str = Field(min_length=1, max_length=256)
    event_kind: RangerKeyEventKind
    vehicle_id: str = Field(min_length=12, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    effective_boot_sequence: int = Field(ge=1, le=2**63 - 1)
    subject_key: RangerSigningKeyDescriptor
    replacement_key: RangerSigningKeyDescriptor | None = None
    revocation_reason: RangerKeyRevocationReason | None = None
    recorded_at_utc: datetime
    clock_quality: ClockQuality
    clock_source: str = Field(min_length=1, max_length=128)
    clock_uncertainty_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    trusted_time_proven: Literal[False] = False

    @field_validator("vehicle_id")
    @classmethod
    def require_ranger_vehicle_id(cls, value: str) -> str:
        if not value.startswith("ets-ranger:"):
            raise ValueError("vehicle_id must use the ets-ranger: namespace")
        return value

    @field_validator("recorded_at_utc")
    @classmethod
    def normalize_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_kind_and_clock_fields(self) -> Self:
        if self.clock_quality is ClockQuality.UNKNOWN:
            if self.clock_uncertainty_ms is not None:
                raise ValueError("unknown clock quality cannot claim bounded uncertainty")
        elif self.clock_uncertainty_ms is None:
            raise ValueError("bounded clock quality requires clock_uncertainty_ms")

        if self.event_kind is RangerKeyEventKind.ENROLL:
            if self.replacement_key is not None or self.revocation_reason is not None:
                raise ValueError("enrollment cannot name a replacement or revocation reason")
        elif self.event_kind is RangerKeyEventKind.ROTATE:
            if self.replacement_key is None:
                raise ValueError("rotation requires a replacement key")
            if self.replacement_key == self.subject_key:
                raise ValueError("rotation requires a different replacement key")
            if self.revocation_reason is not None:
                raise ValueError("rotation cannot include a revocation reason")
        else:
            if self.replacement_key is not None:
                raise ValueError("revocation cannot name a replacement key")
            if self.revocation_reason is None:
                raise ValueError("revocation requires a bounded reason")
        return self


class RangerKeyBindingRequest(StrictModel):
    """A key intent plus the possession proofs required for that transition."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/key-binding-request/v1"
        },
    )

    schema_version: Literal["ets.ranger.key-binding-request.v1"] = (
        "ets.ranger.key-binding-request.v1"
    )
    intent: RangerKeyBindingIntent
    intent_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    subject_key_proof_signature_hex: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{128}$"
    )
    replacement_key_proof_signature_hex: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{128}$"
    )

    @model_validator(mode="after")
    def require_digest_and_proofs(self) -> Self:
        expected = canonical_sha256(self.intent.model_dump(mode="json"))
        if self.intent_digest_sha256 != expected:
            raise ValueError("intent digest does not match intent")
        if self.intent.event_kind is RangerKeyEventKind.ENROLL:
            if self.subject_key_proof_signature_hex is None:
                raise ValueError("enrollment requires subject-key proof")
            if self.replacement_key_proof_signature_hex is not None:
                raise ValueError("enrollment cannot include replacement-key proof")
        elif self.intent.event_kind is RangerKeyEventKind.ROTATE:
            if (
                self.subject_key_proof_signature_hex is None
                or self.replacement_key_proof_signature_hex is None
            ):
                raise ValueError("rotation requires old- and new-key possession proofs")
        elif (
            self.subject_key_proof_signature_hex is not None
            or self.replacement_key_proof_signature_hex is not None
        ):
            raise ValueError("authority revocation does not accept device-key proof fields")
        return self


class RangerKeyAuthorityEvent(StrictModel):
    """One authority-signed accepted key-lifecycle request."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/key-authority-event/v1"
        },
    )

    schema_version: Literal["ets.ranger.key-authority-event.v1"] = (
        "ets.ranger.key-authority-event.v1"
    )
    authority_sequence: int = Field(ge=1, le=2**63 - 1)
    previous_event_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: RangerKeyBindingRequest
    authority_id: str = Field(min_length=1, max_length=160)
    authority_signing_key_id: str = Field(min_length=1, max_length=256)
    authority_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    event_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    storage_profile: Literal["sqlite-wal-full-software-reference"] = (
        "sqlite-wal-full-software-reference"
    )
    operational_device_authorization_proven: Literal[False] = False
    authority_administrative_independence_proven: Literal[False] = False
    hardware_identity_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "authority_relative_key_standing_no_operational_or_global_currentness_claim"
    ] = "authority_relative_key_standing_no_operational_or_global_currentness_claim"

    @model_validator(mode="after")
    def require_predecessor_shape(self) -> Self:
        if self.authority_sequence == 1:
            if self.previous_event_digest_sha256 != _ZERO_DIGEST:
                raise ValueError("authority genesis must use the zero predecessor digest")
        elif self.previous_event_digest_sha256 == _ZERO_DIGEST:
            raise ValueError("non-genesis authority event requires a predecessor digest")
        return self


class RangerKeyAuthorityVerification(StrictModel):
    valid: bool
    event_count: int = Field(ge=0)
    head_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    latest_signing_key_id: str | None = None
    latest_effective_boot_sequence: int | None = Field(default=None, ge=1)
    latest_key_revoked: bool = False
    reason: str


class RangerKeyAuthorizationDecision(StrictModel):
    allowed: bool
    reason: RangerKeyAuthorizationReason
    vehicle_id: str
    tenant_id: str
    workspace_id: str
    boot_sequence: int = Field(ge=1)
    signing_key_id: str
    public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_hex: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    matched_authority_sequence: int | None = Field(default=None, ge=1)
    history_head_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authority_relative_key_standing: bool
    operational_device_authorization_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False


class RangerKeyContinuityVerification(StrictModel):
    valid: bool
    previous_boot_id: str | None = None
    current_boot_id: str | None = None
    previous_signing_key_id: str | None = None
    current_signing_key_id: str | None = None
    key_rotation_authorized: bool = False
    authority_relative_key_standing: bool = False
    operational_device_authorization_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    reason: str


def key_binding_intent_bytes(intent: RangerKeyBindingIntent) -> bytes:
    """Return the canonical bytes a Ranger key signs as proof of possession."""

    validated = RangerKeyBindingIntent.model_validate(intent.model_dump())
    return canonicalize(validated.model_dump(mode="json"))


def build_key_binding_request(
    intent: RangerKeyBindingIntent,
    *,
    subject_key_proof_signature_hex: str | None = None,
    replacement_key_proof_signature_hex: str | None = None,
) -> RangerKeyBindingRequest:
    """Construct a strict request after external key holders sign the intent bytes."""

    validated = RangerKeyBindingIntent.model_validate(intent.model_dump())
    return RangerKeyBindingRequest(
        intent=validated,
        intent_digest_sha256=canonical_sha256(validated.model_dump(mode="json")),
        subject_key_proof_signature_hex=subject_key_proof_signature_hex,
        replacement_key_proof_signature_hex=replacement_key_proof_signature_hex,
    )


class SQLiteRangerKeyAuthorityStore:
    """Crash-consistent append-only software reference for accepted key events."""

    provider_name = "sqlite"
    storage_profile = "sqlite-wal-full-software-reference"

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
            CREATE TABLE IF NOT EXISTS ranger_key_authority_events (
                authority_sequence INTEGER PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                event_digest_sha256 TEXT NOT NULL UNIQUE,
                vehicle_id TEXT NOT NULL,
                event_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def append(self, event: RangerKeyAuthorityEvent) -> None:
        event = RangerKeyAuthorityEvent.model_validate(event.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT authority_sequence, event_digest_sha256
                    FROM ranger_key_authority_events
                    ORDER BY authority_sequence DESC
                    LIMIT 1
                    """
                ).fetchone()
                expected_sequence = 1 if row is None else int(row["authority_sequence"]) + 1
                expected_previous = (
                    _ZERO_DIGEST if row is None else str(row["event_digest_sha256"])
                )
                if event.authority_sequence != expected_sequence:
                    raise RangerKeyAuthorityConflict(
                        f"authority sequence must be {expected_sequence}"
                    )
                if event.previous_event_digest_sha256 != expected_previous:
                    raise RangerKeyAuthorityConflict(
                        "event does not extend the retained key-authority head"
                    )
                self._connection.execute(
                    """
                    INSERT INTO ranger_key_authority_events (
                        authority_sequence,
                        request_id,
                        event_digest_sha256,
                        vehicle_id,
                        event_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.authority_sequence,
                        event.request.intent.request_id,
                        event.event_digest_sha256,
                        event.request.intent.vehicle_id,
                        event.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except RangerKeyAuthorityConflict:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerKeyAuthorityConflict(
                    "duplicate authority sequence, request identity, or event digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_events(self) -> list[RangerKeyAuthorityEvent]:
        with self._lock:
            integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise RangerKeyAuthorityIntegrityError("SQLite integrity_check failed")
            rows = self._connection.execute(
                """
                SELECT authority_sequence, request_id, event_digest_sha256, vehicle_id, event_json
                FROM ranger_key_authority_events
                ORDER BY authority_sequence ASC
                """
            ).fetchall()
        try:
            events = [
                RangerKeyAuthorityEvent.model_validate_json(row["event_json"]) for row in rows
            ]
        except ValidationError as exc:
            raise RangerKeyAuthorityIntegrityError(
                "stored Ranger key-authority event is invalid"
            ) from exc
        for row, event in zip(rows, events, strict=True):
            intent = event.request.intent
            if (
                int(row["authority_sequence"]) != event.authority_sequence
                or str(row["request_id"]) != intent.request_id
                or str(row["event_digest_sha256"]) != event.event_digest_sha256
                or str(row["vehicle_id"]) != intent.vehicle_id
            ):
                raise RangerKeyAuthorityIntegrityError(
                    "stored Ranger key-authority index does not match signed event"
                )
        return events


class RangerKeyAuthorityLedger:
    """Validate possession proofs, sign key events, and verify historical key standing."""

    def __init__(
        self,
        store: SQLiteRangerKeyAuthorityStore,
        *,
        vehicle_id: str,
        tenant_id: str,
        workspace_id: str,
        authority_id: str,
        authority_signing_key_id: str,
        authority_private_key_hex: str,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerKeyAuthorityError("vehicle_id must use the ets-ranger: namespace")
        for name, value, maximum in (
            ("tenant_id", tenant_id, 128),
            ("workspace_id", workspace_id, 128),
            ("authority_id", authority_id, 160),
            ("authority_signing_key_id", authority_signing_key_id, 256),
        ):
            if not value or len(value) > maximum:
                raise RangerKeyAuthorityError(f"{name} must contain 1-{maximum} characters")
        try:
            self._authority_private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(authority_private_key_hex)
            )
        except ValueError as exc:
            raise RangerKeyAuthorityError(
                "authority private key must be a 32-byte Ed25519 key"
            ) from exc

        self.store = store
        self.vehicle_id = vehicle_id
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self.authority_id = authority_id
        self.authority_signing_key_id = authority_signing_key_id
        retained = self.store.list_events()
        if retained:
            verification = self.verify_history(retained, self.authority_public_key_hex)
            if not verification.valid:
                raise RangerKeyAuthorityIntegrityError(
                    f"retained key-authority history is invalid: {verification.reason}"
                )
            for event in retained:
                intent = event.request.intent
                if (
                    intent.vehicle_id != vehicle_id
                    or intent.tenant_id != tenant_id
                    or intent.workspace_id != workspace_id
                    or event.authority_id != authority_id
                    or event.authority_signing_key_id != authority_signing_key_id
                    or event.authority_public_key_fingerprint_sha256
                    != self.authority_public_key_fingerprint_sha256
                ):
                    raise RangerKeyAuthorityIntegrityError(
                        "retained key-authority identity or scope mismatch"
                    )
        self._events = retained

    @property
    def authority_public_key_hex(self) -> str:
        return (
            self._authority_private_key.public_key()
            .public_bytes(Encoding.Raw, PublicFormat.Raw)
            .hex()
        )

    @property
    def authority_public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.authority_public_key_hex)).hexdigest()

    def append(self, request: RangerKeyBindingRequest) -> RangerKeyAuthorityEvent:
        """Validate a key-lifecycle request and atomically retain the authority decision."""

        retained = self.store.list_events()
        if retained != self._events:
            raise RangerKeyAuthorityConflict(
                "retained key-authority history changed; reopen the ledger before appending"
            )
        try:
            validated = RangerKeyBindingRequest.model_validate(request.model_dump())
        except (AttributeError, ValidationError) as exc:
            raise RangerKeyAuthorityError("invalid Ranger key-binding request") from exc
        intent = validated.intent
        if (
            intent.vehicle_id != self.vehicle_id
            or intent.tenant_id != self.tenant_id
            or intent.workspace_id != self.workspace_id
        ):
            raise RangerKeyAuthorityError("Ranger key-binding identity or scope mismatch")
        proof_error = _request_proof_error(validated)
        if proof_error is not None:
            raise RangerKeyAuthorityError(proof_error)
        transition_error = _request_transition_error(self._events, validated)
        if transition_error is not None:
            raise RangerKeyAuthorityConflict(transition_error)
        for descriptor in _request_descriptors(validated):
            if (
                descriptor.public_key_fingerprint_sha256
                == self.authority_public_key_fingerprint_sha256
            ):
                raise RangerKeyAuthorityError(
                    "Ranger custody key must differ from the authority signing key"
                )

        sequence = len(self._events) + 1
        previous = _ZERO_DIGEST if not self._events else self._events[-1].event_digest_sha256
        payload = _authority_event_payload(
            authority_sequence=sequence,
            previous_event_digest_sha256=previous,
            request=validated,
            authority_id=self.authority_id,
            authority_signing_key_id=self.authority_signing_key_id,
            authority_public_key_fingerprint_sha256=(
                self.authority_public_key_fingerprint_sha256
            ),
        )
        digest = canonical_sha256(payload)
        event = RangerKeyAuthorityEvent.model_validate(
            {
                **payload,
                "request": validated,
                "event_digest_sha256": digest,
                "authority_signature_hex": self._authority_private_key.sign(
                    canonicalize(payload)
                ).hex(),
            }
        )
        self.store.append(event)
        self._events.append(event)
        return event

    def list_events(self) -> list[RangerKeyAuthorityEvent]:
        return self.store.list_events()

    @staticmethod
    def verify_history(
        events: Iterable[RangerKeyAuthorityEvent],
        authority_public_key_hex: str,
    ) -> RangerKeyAuthorityVerification:
        """Verify a complete supplied authority history without trusting its store."""

        try:
            authority_key_bytes = bytes.fromhex(authority_public_key_hex)
            authority_key = Ed25519PublicKey.from_public_bytes(authority_key_bytes)
        except ValueError:
            return _history_failure(0, "authority public key is not 32-byte Ed25519")
        expected_authority_fingerprint = hashlib.sha256(authority_key_bytes).hexdigest()
        previous = _ZERO_DIGEST
        expected_sequence = 1
        verified: list[RangerKeyAuthorityEvent] = []
        request_ids: set[str] = set()
        identity: tuple[str, str, str, str, str] | None = None

        for unvalidated in events:
            count = len(verified) + 1
            try:
                event = RangerKeyAuthorityEvent.model_validate(unvalidated.model_dump())
            except (AttributeError, ValidationError):
                return _history_failure(count, "key-authority event schema validation failed")
            intent = event.request.intent
            if event.authority_sequence != expected_sequence:
                return _history_failure(
                    count, "missing, duplicate, or reordered authority sequence"
                )
            if event.previous_event_digest_sha256 != previous:
                return _history_failure(count, "previous key-authority event digest mismatch")
            if intent.request_id in request_ids:
                return _history_failure(count, "duplicate key-binding request identity")
            current_identity = (
                intent.vehicle_id,
                intent.tenant_id,
                intent.workspace_id,
                event.authority_id,
                event.authority_signing_key_id,
            )
            if identity is None:
                identity = current_identity
            elif current_identity != identity:
                return _history_failure(count, "key-authority identity or scope changed")
            if event.authority_public_key_fingerprint_sha256 != expected_authority_fingerprint:
                return _history_failure(count, "authority public key fingerprint mismatch")
            if any(
                descriptor.public_key_fingerprint_sha256 == expected_authority_fingerprint
                for descriptor in _request_descriptors(event.request)
            ):
                return _history_failure(count, "Ranger and authority signing keys are not distinct")
            proof_error = _request_proof_error(event.request)
            if proof_error is not None:
                return _history_failure(count, proof_error)
            transition_error = _request_transition_error(verified, event.request)
            if transition_error is not None:
                return _history_failure(count, transition_error)
            payload = _authority_event_payload_from_record(event)
            if canonical_sha256(payload) != event.event_digest_sha256:
                return _history_failure(count, "key-authority event digest mismatch")
            try:
                authority_key.verify(
                    bytes.fromhex(event.authority_signature_hex), canonicalize(payload)
                )
            except (InvalidSignature, ValueError):
                return _history_failure(count, "key-authority signature invalid")

            verified.append(event)
            request_ids.add(intent.request_id)
            previous = event.event_digest_sha256
            expected_sequence += 1

        if not verified:
            return _history_failure(0, "key-authority history is empty")
        latest = verified[-1].request.intent
        active = _resulting_descriptor(latest)
        return RangerKeyAuthorityVerification(
            valid=True,
            event_count=len(verified),
            head_digest_sha256=previous,
            latest_signing_key_id=None if active is None else active.signing_key_id,
            latest_effective_boot_sequence=latest.effective_boot_sequence,
            latest_key_revoked=latest.event_kind is RangerKeyEventKind.REVOKE,
            reason=(
                "authority signatures, possession proofs, identities, ordering, and key "
                "transitions are valid; operational authorization and global currentness are "
                "not proven"
            ),
        )

    @staticmethod
    def authorize_key(
        events: Iterable[RangerKeyAuthorityEvent],
        authority_public_key_hex: str,
        *,
        vehicle_id: str,
        tenant_id: str,
        workspace_id: str,
        boot_sequence: int,
        signing_key_id: str,
        public_key_fingerprint_sha256: str,
    ) -> RangerKeyAuthorizationDecision:
        """Evaluate authority-relative key standing for one Ranger boot sequence."""

        history = list(events)
        verification = RangerKeyAuthorityLedger.verify_history(
            history, authority_public_key_hex
        )
        if not verification.valid:
            return _authorization_decision(
                allowed=False,
                reason=RangerKeyAuthorizationReason.HISTORY_INVALID,
                vehicle_id=vehicle_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                boot_sequence=boot_sequence,
                signing_key_id=signing_key_id,
                fingerprint=public_key_fingerprint_sha256,
            )
        first = history[0]
        first_intent = first.request.intent
        if (
            first_intent.vehicle_id != vehicle_id
            or first_intent.tenant_id != tenant_id
            or first_intent.workspace_id != workspace_id
        ):
            return _authorization_decision(
                allowed=False,
                reason=RangerKeyAuthorizationReason.IDENTITY_SCOPE_MISMATCH,
                vehicle_id=vehicle_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                boot_sequence=boot_sequence,
                signing_key_id=signing_key_id,
                fingerprint=public_key_fingerprint_sha256,
                head=verification.head_digest_sha256,
            )
        if boot_sequence < 1:
            return _authorization_decision(
                allowed=False,
                reason=RangerKeyAuthorizationReason.NOT_YET_ENROLLED,
                vehicle_id=vehicle_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                boot_sequence=1,
                signing_key_id=signing_key_id,
                fingerprint=public_key_fingerprint_sha256,
                head=verification.head_digest_sha256,
            )

        applied = [
            event
            for event in history
            if event.request.intent.effective_boot_sequence <= boot_sequence
        ]
        if not applied:
            return _authorization_decision(
                allowed=False,
                reason=RangerKeyAuthorizationReason.NOT_YET_ENROLLED,
                vehicle_id=vehicle_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                boot_sequence=boot_sequence,
                signing_key_id=signing_key_id,
                fingerprint=public_key_fingerprint_sha256,
                head=verification.head_digest_sha256,
            )

        latest = applied[-1]
        active = _resulting_descriptor(latest.request.intent)
        requested = (signing_key_id, public_key_fingerprint_sha256)
        if active is not None and _descriptor_identity(active) == requested:
            return _authorization_decision(
                allowed=True,
                reason=RangerKeyAuthorizationReason.AUTHORIZED,
                vehicle_id=vehicle_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                boot_sequence=boot_sequence,
                signing_key_id=signing_key_id,
                fingerprint=public_key_fingerprint_sha256,
                public_key_hex=active.public_key_hex,
                matched_sequence=latest.authority_sequence,
                head=verification.head_digest_sha256,
            )

        descriptor_events = _descriptor_events(history, requested)
        if not descriptor_events:
            reason = RangerKeyAuthorizationReason.CREDENTIAL_MISMATCH
        else:
            first_seen = descriptor_events[0]
            if first_seen.request.intent.effective_boot_sequence > boot_sequence:
                reason = RangerKeyAuthorizationReason.CREDENTIAL_NOT_YET_ACTIVE
            elif (
                latest.request.intent.event_kind is RangerKeyEventKind.REVOKE
                and _descriptor_identity(latest.request.intent.subject_key) == requested
            ):
                reason = RangerKeyAuthorizationReason.REVOKED
            else:
                reason = RangerKeyAuthorizationReason.SUPERSEDED_CREDENTIAL
        return _authorization_decision(
            allowed=False,
            reason=reason,
            vehicle_id=vehicle_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            boot_sequence=boot_sequence,
            signing_key_id=signing_key_id,
            fingerprint=public_key_fingerprint_sha256,
            matched_sequence=(
                descriptor_events[-1].authority_sequence if descriptor_events else None
            ),
            head=verification.head_digest_sha256,
        )

    @staticmethod
    def verify_boot_continuity(
        previous_records: Iterable[RangerCustodyRecord],
        current_records: Iterable[RangerCustodyRecord],
        events: Iterable[RangerKeyAuthorityEvent],
        authority_public_key_hex: str,
        *,
        tenant_id: str,
        workspace_id: str,
    ) -> RangerKeyContinuityVerification:
        """Verify adjacent Ranger boots using authority-resolved historical custody keys."""

        previous = list(previous_records)
        current = list(current_records)
        history = list(events)
        if not previous or not current:
            return _continuity_failure("both Ranger custody chains are required")
        previous_checkpoint = _boot_checkpoint(previous)
        current_checkpoint = _boot_checkpoint(current)
        if previous_checkpoint is None or current_checkpoint is None:
            return _continuity_failure(
                "each Ranger custody chain must start with a boot checkpoint"
            )
        previous_first = previous[0]
        current_first = current[0]
        previous_auth = RangerKeyAuthorityLedger.authorize_key(
            history,
            authority_public_key_hex,
            vehicle_id=previous_first.vehicle_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            boot_sequence=previous_checkpoint.boot_sequence,
            signing_key_id=previous_first.signing_key_id,
            public_key_fingerprint_sha256=(
                previous_first.public_key_fingerprint_sha256
            ),
        )
        if not previous_auth.allowed or previous_auth.public_key_hex is None:
            return _continuity_failure(
                f"previous Ranger custody key lacks authority-relative standing: "
                f"{previous_auth.reason.value}",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        current_auth = RangerKeyAuthorityLedger.authorize_key(
            history,
            authority_public_key_hex,
            vehicle_id=current_first.vehicle_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            boot_sequence=current_checkpoint.boot_sequence,
            signing_key_id=current_first.signing_key_id,
            public_key_fingerprint_sha256=current_first.public_key_fingerprint_sha256,
        )
        if not current_auth.allowed or current_auth.public_key_hex is None:
            return _continuity_failure(
                f"current Ranger custody key lacks authority-relative standing: "
                f"{current_auth.reason.value}",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        previous_verification = RangerCustodyLedger.verify_chain(
            previous, previous_auth.public_key_hex
        )
        if not previous_verification.valid:
            return _continuity_failure(
                f"previous Ranger custody chain is invalid: {previous_verification.reason}",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        current_verification = RangerCustodyLedger.verify_chain(
            current, current_auth.public_key_hex
        )
        if not current_verification.valid:
            return _continuity_failure(
                f"current Ranger custody chain is invalid: {current_verification.reason}",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        if (
            previous_checkpoint.vehicle_id != current_checkpoint.vehicle_id
            or previous_checkpoint.mission_id != current_checkpoint.mission_id
        ):
            return _continuity_failure(
                "vehicle or mission identity changed across boots",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        if current_checkpoint.previous_boot_id != previous_checkpoint.boot_id:
            return _continuity_failure(
                "previous boot identity does not match",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        if (
            current_checkpoint.previous_custody_head_digest_sha256
            != previous_verification.head_digest_sha256
        ):
            return _continuity_failure(
                "previous custody head digest does not match",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        if current_checkpoint.boot_sequence != previous_checkpoint.boot_sequence + 1:
            return _continuity_failure(
                "boot sequence is missing, duplicate, or reordered",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        if current_checkpoint.started_at_utc <= previous_checkpoint.started_at_utc:
            return _continuity_failure(
                "recorded boot timestamp did not advance",
                previous=previous_first.signing_key_id,
                current=current_first.signing_key_id,
            )
        rotated = previous_first.signing_key_id != current_first.signing_key_id
        return RangerKeyContinuityVerification(
            valid=True,
            previous_boot_id=previous_checkpoint.boot_id,
            current_boot_id=current_checkpoint.boot_id,
            previous_signing_key_id=previous_first.signing_key_id,
            current_signing_key_id=current_first.signing_key_id,
            key_rotation_authorized=rotated,
            authority_relative_key_standing=True,
            reason=(
                "custody signatures, adjacent boot linkage, and authority-relative historical "
                "key standing are valid; operational authorization, global key-history "
                "currentness, trusted time, completeness, and physical outcome are not proven"
            ),
        )


def _request_proof_error(request: RangerKeyBindingRequest) -> str | None:
    payload = key_binding_intent_bytes(request.intent)
    proofs: list[tuple[RangerSigningKeyDescriptor, str | None, str]] = [
        (
            request.intent.subject_key,
            request.subject_key_proof_signature_hex,
            "subject-key possession proof",
        )
    ]
    if request.intent.replacement_key is not None:
        proofs.append(
            (
                request.intent.replacement_key,
                request.replacement_key_proof_signature_hex,
                "replacement-key possession proof",
            )
        )
    if request.intent.event_kind is RangerKeyEventKind.REVOKE:
        return None
    for descriptor, signature_hex, label in proofs:
        if signature_hex is None:
            return f"{label} is missing"
        try:
            public_key = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(descriptor.public_key_hex)
            )
            public_key.verify(bytes.fromhex(signature_hex), payload)
        except (InvalidSignature, ValueError):
            return f"{label} is invalid"
    return None


def _request_transition_error(
    events: list[RangerKeyAuthorityEvent],
    request: RangerKeyBindingRequest,
) -> str | None:
    intent = request.intent
    if not events:
        if intent.event_kind is not RangerKeyEventKind.ENROLL:
            return "key-authority history must begin with enrollment"
        return None
    if intent.event_kind is RangerKeyEventKind.ENROLL:
        return "key-authority history can contain only one enrollment genesis"
    previous_intent = events[-1].request.intent
    current = _resulting_descriptor(previous_intent)
    if current is None:
        return "revoked Ranger key history cannot accept another transition"
    if intent.subject_key != current:
        return "key transition subject does not match the current enrolled key"
    if intent.effective_boot_sequence < previous_intent.effective_boot_sequence:
        return "key transition effective boot sequence regressed"
    if (
        intent.event_kind is RangerKeyEventKind.ROTATE
        and intent.effective_boot_sequence == previous_intent.effective_boot_sequence
    ):
        return "rotation must advance the effective boot sequence"
    if intent.replacement_key is not None:
        used_key_ids = {
            descriptor.signing_key_id
            for event in events
            for descriptor in _request_descriptors(event.request)
        }
        used_fingerprints = {
            descriptor.public_key_fingerprint_sha256
            for event in events
            for descriptor in _request_descriptors(event.request)
        }
        if intent.replacement_key.signing_key_id in used_key_ids:
            return "rotation cannot reuse a previously enrolled key identifier"
        if intent.replacement_key.public_key_fingerprint_sha256 in used_fingerprints:
            return "rotation cannot reuse a previously enrolled public key"
    return None


def _request_descriptors(
    request: RangerKeyBindingRequest,
) -> tuple[RangerSigningKeyDescriptor, ...]:
    replacement = request.intent.replacement_key
    return (
        (request.intent.subject_key,)
        if replacement is None
        else (request.intent.subject_key, replacement)
    )


def _resulting_descriptor(
    intent: RangerKeyBindingIntent,
) -> RangerSigningKeyDescriptor | None:
    if intent.event_kind is RangerKeyEventKind.REVOKE:
        return None
    return intent.subject_key if intent.replacement_key is None else intent.replacement_key


def _descriptor_identity(descriptor: RangerSigningKeyDescriptor) -> tuple[str, str]:
    return descriptor.signing_key_id, descriptor.public_key_fingerprint_sha256


def _descriptor_events(
    events: list[RangerKeyAuthorityEvent],
    requested: tuple[str, str],
) -> list[RangerKeyAuthorityEvent]:
    return [
        event
        for event in events
        if any(
            _descriptor_identity(descriptor) == requested
            for descriptor in _request_descriptors(event.request)
        )
    ]


def _authority_event_payload_from_record(
    event: RangerKeyAuthorityEvent,
) -> dict[str, object]:
    return _authority_event_payload(
        authority_sequence=event.authority_sequence,
        previous_event_digest_sha256=event.previous_event_digest_sha256,
        request=event.request,
        authority_id=event.authority_id,
        authority_signing_key_id=event.authority_signing_key_id,
        authority_public_key_fingerprint_sha256=(
            event.authority_public_key_fingerprint_sha256
        ),
    )


def _authority_event_payload(
    *,
    authority_sequence: int,
    previous_event_digest_sha256: str,
    request: RangerKeyBindingRequest,
    authority_id: str,
    authority_signing_key_id: str,
    authority_public_key_fingerprint_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": "ets.ranger.key-authority-event.v1",
        "authority_sequence": authority_sequence,
        "previous_event_digest_sha256": previous_event_digest_sha256,
        "request": request.model_dump(mode="json"),
        "authority_id": authority_id,
        "authority_signing_key_id": authority_signing_key_id,
        "authority_public_key_fingerprint_sha256": (
            authority_public_key_fingerprint_sha256
        ),
        "signing_algorithm": "ed25519",
        "storage_profile": "sqlite-wal-full-software-reference",
        "operational_device_authorization_proven": False,
        "authority_administrative_independence_proven": False,
        "hardware_identity_proven": False,
        "globally_current_history_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "authority_relative_key_standing_no_operational_or_global_currentness_claim"
        ),
    }


def _history_failure(count: int, reason: str) -> RangerKeyAuthorityVerification:
    return RangerKeyAuthorityVerification(valid=False, event_count=count, reason=reason)


def _authorization_decision(
    *,
    allowed: bool,
    reason: RangerKeyAuthorizationReason,
    vehicle_id: str,
    tenant_id: str,
    workspace_id: str,
    boot_sequence: int,
    signing_key_id: str,
    fingerprint: str,
    public_key_hex: str | None = None,
    matched_sequence: int | None = None,
    head: str | None = None,
) -> RangerKeyAuthorizationDecision:
    return RangerKeyAuthorizationDecision(
        allowed=allowed,
        reason=reason,
        vehicle_id=vehicle_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        boot_sequence=boot_sequence,
        signing_key_id=signing_key_id,
        public_key_fingerprint_sha256=fingerprint,
        public_key_hex=public_key_hex,
        matched_authority_sequence=matched_sequence,
        history_head_digest_sha256=head,
        authority_relative_key_standing=allowed,
    )


def _continuity_failure(
    reason: str,
    *,
    previous: str | None = None,
    current: str | None = None,
) -> RangerKeyContinuityVerification:
    return RangerKeyContinuityVerification(
        valid=False,
        previous_signing_key_id=previous,
        current_signing_key_id=current,
        reason=reason,
    )


def _boot_checkpoint(records: list[RangerCustodyRecord]) -> RangerBootCheckpoint | None:
    if records[0].custody_sequence != 1:
        return None
    source = records[0].source_event
    return source if isinstance(source, RangerBootCheckpoint) else None
