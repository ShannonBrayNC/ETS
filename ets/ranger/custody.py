"""Signed, append-only local custody for Ranger source evidence records.

This software reference boundary preserves the exact versioned source structures emitted by
Ranger controllers and simulators.  It proves signature validity, append order, and retained
bytes; it does not prove semantic truth, physical state, complete capture, or hardware key
custody.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal, Self

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.lifecycle import RangerLifecycleEvent
from ets.ranger.mobility import RangerMobilityEvent
from ets.ranger.simulation import RangerActuatorResponse, RangerSimulatedResult

_ZERO_DIGEST = "0" * 64
_MAX_SOURCE_RECORD_BYTES = 256 * 1024

RangerSourceEvent = Annotated[
    RangerMobilityEvent
    | RangerLifecycleEvent
    | RangerActuatorResponse
    | RangerSimulatedResult,
    Field(discriminator="schema_version"),
]
_SOURCE_EVENT_ADAPTER: TypeAdapter[RangerSourceEvent] = TypeAdapter(RangerSourceEvent)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerCustodyError(RuntimeError):
    """Base error for Ranger custody validation or persistence failures."""


class RangerCustodyConflict(RangerCustodyError):
    """Raised when an append would violate durable sequence or uniqueness."""


class RangerCustodyIntegrityError(RangerCustodyError):
    """Raised when retained custody data cannot be parsed or verified."""


class RangerCustodyRecord(StrictModel):
    """One signed source record in the Ranger local custody chain."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/custody-record/v1"
        },
    )

    schema_version: Literal["ets.ranger.custody-record.v1"] = (
        "ets.ranger.custody-record.v1"
    )
    custody_sequence: int = Field(ge=1, le=2**63 - 1)
    previous_record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_schema_version: Literal[
        "ets.ranger.mobility-event.v1",
        "ets.ranger.lifecycle-event.v1",
        "ets.ranger.actuator-response.v1",
        "ets.ranger.simulated-result.v1",
    ]
    source_event_id: str = Field(min_length=1, max_length=256)
    source_record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_event: RangerSourceEvent
    vehicle_id: str = Field(min_length=12, max_length=160)
    mission_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    signing_algorithm: Literal["ed25519"] = "ed25519"
    signing_key_id: str = Field(min_length=1, max_length=256)
    public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    storage_profile: Literal["sqlite-wal-full-software-reference"] = (
        "sqlite-wal-full-software-reference"
    )
    hardware_backed_key: Literal[False] = False
    encrypted_at_rest: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "signed_ordered_source_custody_no_truth_completeness_or_physical_claim"
    ] = "signed_ordered_source_custody_no_truth_completeness_or_physical_claim"

    @model_validator(mode="after")
    def require_source_identity_and_digest(self) -> Self:
        source = self.source_event
        if self.source_schema_version != source.schema_version:
            raise ValueError("source_schema_version does not match source_event")
        if self.source_event_id != _source_event_id(source):
            raise ValueError("source_event_id does not match source_event")
        if self.vehicle_id != source.vehicle_id:
            raise ValueError("vehicle_id does not match source_event")
        if self.mission_id != source.mission_id:
            raise ValueError("mission_id does not match source_event")
        if self.boot_id != source.boot_id:
            raise ValueError("boot_id does not match source_event")
        source_digest = canonical_sha256(source.model_dump(mode="json"))
        if self.source_record_digest_sha256 != source_digest:
            raise ValueError("source record digest mismatch")
        return self


class RangerCustodyVerification(StrictModel):
    valid: bool
    record_count: int = Field(ge=0)
    head_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason: str


class SQLiteRangerCustodyStore:
    """Crash-consistent software reference store for complete signed Ranger records."""

    provider_name = "sqlite"
    storage_profile = "sqlite-wal-full-software-reference"
    hardware_backed_key = False
    encrypted_at_rest = False

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ranger_custody_records (
                custody_sequence INTEGER PRIMARY KEY,
                source_schema_version TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                record_digest_sha256 TEXT NOT NULL UNIQUE,
                record_json TEXT NOT NULL,
                UNIQUE(source_schema_version, source_event_id)
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def append(self, record: RangerCustodyRecord) -> None:
        """Atomically append only if sequence and predecessor extend the durable head."""

        record = RangerCustodyRecord.model_validate(record.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT custody_sequence, record_digest_sha256
                    FROM ranger_custody_records
                    ORDER BY custody_sequence DESC
                    LIMIT 1
                    """
                ).fetchone()
                expected_sequence = 1 if row is None else int(row["custody_sequence"]) + 1
                expected_previous = (
                    _ZERO_DIGEST if row is None else str(row["record_digest_sha256"])
                )
                if record.custody_sequence != expected_sequence:
                    raise RangerCustodyConflict(
                        f"custody sequence must be {expected_sequence}"
                    )
                if record.previous_record_digest_sha256 != expected_previous:
                    raise RangerCustodyConflict("record does not extend durable custody head")
                self._connection.execute(
                    """
                    INSERT INTO ranger_custody_records (
                        custody_sequence,
                        source_schema_version,
                        source_event_id,
                        record_digest_sha256,
                        record_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.custody_sequence,
                        record.source_schema_version,
                        record.source_event_id,
                        record.record_digest_sha256,
                        record.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except RangerCustodyConflict:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerCustodyConflict(
                    "duplicate Ranger source identity, sequence, or record digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_records(self) -> list[RangerCustodyRecord]:
        with self._lock:
            integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise RangerCustodyIntegrityError("SQLite integrity_check failed")
            rows = self._connection.execute(
                """
                SELECT
                    custody_sequence,
                    source_schema_version,
                    source_event_id,
                    record_digest_sha256,
                    record_json
                FROM ranger_custody_records
                ORDER BY custody_sequence ASC
                """
            ).fetchall()
        try:
            records = [
                RangerCustodyRecord.model_validate_json(row["record_json"])
                for row in rows
            ]
        except ValidationError as exc:
            raise RangerCustodyIntegrityError("stored Ranger custody record is invalid") from exc
        for row, record in zip(rows, records, strict=True):
            if (
                int(row["custody_sequence"]) != record.custody_sequence
                or str(row["source_schema_version"]) != record.source_schema_version
                or str(row["source_event_id"]) != record.source_event_id
                or str(row["record_digest_sha256"]) != record.record_digest_sha256
            ):
                raise RangerCustodyIntegrityError(
                    "stored Ranger custody index metadata does not match signed record"
                )
        return records


class RangerCustodyLedger:
    """Sign, persist, recover, and independently verify Ranger source evidence."""

    def __init__(
        self,
        store: SQLiteRangerCustodyStore,
        *,
        vehicle_id: str,
        mission_id: str,
        boot_id: str,
        signing_key_id: str,
        private_key_hex: str,
    ) -> None:
        if not vehicle_id.startswith("ets-ranger:") or len(vehicle_id) > 160:
            raise RangerCustodyError("vehicle_id must use the ets-ranger: namespace")
        for name, value, maximum in (
            ("mission_id", mission_id, 128),
            ("boot_id", boot_id, 128),
            ("signing_key_id", signing_key_id, 256),
        ):
            if not value or len(value) > maximum:
                raise RangerCustodyError(f"{name} must contain 1-{maximum} characters")
        try:
            self._private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(private_key_hex)
            )
        except ValueError as exc:
            raise RangerCustodyError("private key must be a 32-byte Ed25519 key") from exc

        self.store = store
        self.vehicle_id = vehicle_id
        self.mission_id = mission_id
        self.boot_id = boot_id
        self.signing_key_id = signing_key_id
        retained = self.store.list_records()
        if retained:
            verification = self.verify_chain(retained, self.public_key_hex)
            if not verification.valid:
                raise RangerCustodyIntegrityError(
                    f"retained Ranger custody chain is invalid: {verification.reason}"
                )
            for record in retained:
                if (
                    record.vehicle_id != vehicle_id
                    or record.mission_id != mission_id
                    or record.boot_id != boot_id
                    or record.signing_key_id != signing_key_id
                    or record.public_key_fingerprint_sha256
                    != self.public_key_fingerprint_sha256
                ):
                    raise RangerCustodyIntegrityError(
                        "retained Ranger custody identity or signing key mismatch"
                    )
        self._records = retained

    @property
    def public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    @property
    def public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.public_key_hex)).hexdigest()

    def append(self, source_event: RangerSourceEvent) -> RangerCustodyRecord:
        source = _validate_source_event(source_event)
        if len(canonicalize(source.model_dump(mode="json"))) > _MAX_SOURCE_RECORD_BYTES:
            raise RangerCustodyError("Ranger source record exceeds 256 KiB")
        if (
            source.vehicle_id != self.vehicle_id
            or source.mission_id != self.mission_id
            or source.boot_id != self.boot_id
        ):
            raise RangerCustodyError("Ranger source record identity mismatch")

        source_identity = (source.schema_version, _source_event_id(source))
        if any(
            (record.source_schema_version, record.source_event_id) == source_identity
            for record in self._records
        ):
            raise RangerCustodyConflict("duplicate Ranger source event identity")

        sequence = len(self._records) + 1
        previous = (
            _ZERO_DIGEST
            if not self._records
            else self._records[-1].record_digest_sha256
        )
        source_payload = source.model_dump(mode="json")
        source_digest = canonical_sha256(source_payload)
        payload = _record_payload(
            custody_sequence=sequence,
            previous_record_digest_sha256=previous,
            source_schema_version=source.schema_version,
            source_event_id=_source_event_id(source),
            source_record_digest_sha256=source_digest,
            source_event=source_payload,
            vehicle_id=self.vehicle_id,
            mission_id=self.mission_id,
            boot_id=self.boot_id,
            signing_key_id=self.signing_key_id,
            public_key_fingerprint_sha256=self.public_key_fingerprint_sha256,
        )
        record_digest = canonical_sha256(payload)
        record = RangerCustodyRecord(
            custody_sequence=sequence,
            previous_record_digest_sha256=previous,
            source_schema_version=source.schema_version,
            source_event_id=_source_event_id(source),
            source_record_digest_sha256=source_digest,
            source_event=source,
            vehicle_id=self.vehicle_id,
            mission_id=self.mission_id,
            boot_id=self.boot_id,
            signing_key_id=self.signing_key_id,
            public_key_fingerprint_sha256=self.public_key_fingerprint_sha256,
            record_digest_sha256=record_digest,
            signature_hex=self._private_key.sign(canonicalize(payload)).hex(),
        )
        self.store.append(record)
        self._records.append(record)
        return record

    @staticmethod
    def verify_chain(
        records: Iterable[RangerCustodyRecord],
        public_key_hex: str,
    ) -> RangerCustodyVerification:
        try:
            public_key_bytes = bytes.fromhex(public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except ValueError:
            return RangerCustodyVerification(
                valid=False, record_count=0, reason="public key is not 32-byte Ed25519"
            )
        expected_fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
        previous = _ZERO_DIGEST
        expected_sequence = 1
        seen_sources: set[tuple[str, str]] = set()
        count = 0
        identities: tuple[str, str, str, str] | None = None
        for unvalidated in records:
            count += 1
            try:
                record = RangerCustodyRecord.model_validate(unvalidated.model_dump())
            except ValidationError:
                return RangerCustodyVerification(
                    valid=False, record_count=count, reason="record schema validation failed"
                )
            if record.custody_sequence != expected_sequence:
                return _verification_failure(count, "missing, duplicate, or reordered sequence")
            if record.previous_record_digest_sha256 != previous:
                return _verification_failure(count, "previous record digest mismatch")
            source_identity = (record.source_schema_version, record.source_event_id)
            if source_identity in seen_sources:
                return _verification_failure(count, "duplicate source event identity")
            if record.public_key_fingerprint_sha256 != expected_fingerprint:
                return _verification_failure(count, "public key fingerprint mismatch")
            record_identity = (
                record.vehicle_id,
                record.mission_id,
                record.boot_id,
                record.signing_key_id,
            )
            if identities is None:
                identities = record_identity
            elif record_identity != identities:
                return _verification_failure(count, "custody identity changed within chain")
            payload = _record_payload_from_record(record)
            if canonical_sha256(payload) != record.record_digest_sha256:
                return _verification_failure(count, "record digest mismatch")
            try:
                public_key.verify(bytes.fromhex(record.signature_hex), canonicalize(payload))
            except (InvalidSignature, ValueError):
                return _verification_failure(count, "record signature invalid")
            seen_sources.add(source_identity)
            previous = record.record_digest_sha256
            expected_sequence += 1
        if count == 0:
            return RangerCustodyVerification(
                valid=False, record_count=0, reason="custody chain is empty"
            )
        return RangerCustodyVerification(
            valid=True,
            record_count=count,
            head_digest_sha256=previous,
            reason="signatures, source digests, identities, and append linkage are valid",
        )

    def list_records(self) -> list[RangerCustodyRecord]:
        return self.store.list_records()


def _validate_source_event(source_event: RangerSourceEvent) -> RangerSourceEvent:
    try:
        return _SOURCE_EVENT_ADAPTER.validate_python(source_event.model_dump())
    except (AttributeError, ValidationError) as exc:
        raise RangerCustodyError("unsupported or invalid Ranger source record") from exc


def _source_event_id(source: RangerSourceEvent) -> str:
    if isinstance(source, (RangerMobilityEvent, RangerLifecycleEvent)):
        return source.event_id
    if isinstance(source, RangerActuatorResponse):
        return source.response_id
    return source.result_id


def _record_payload_from_record(record: RangerCustodyRecord) -> dict[str, object]:
    return _record_payload(
        custody_sequence=record.custody_sequence,
        previous_record_digest_sha256=record.previous_record_digest_sha256,
        source_schema_version=record.source_schema_version,
        source_event_id=record.source_event_id,
        source_record_digest_sha256=record.source_record_digest_sha256,
        source_event=record.source_event.model_dump(mode="json"),
        vehicle_id=record.vehicle_id,
        mission_id=record.mission_id,
        boot_id=record.boot_id,
        signing_key_id=record.signing_key_id,
        public_key_fingerprint_sha256=record.public_key_fingerprint_sha256,
    )


def _record_payload(
    *,
    custody_sequence: int,
    previous_record_digest_sha256: str,
    source_schema_version: str,
    source_event_id: str,
    source_record_digest_sha256: str,
    source_event: dict[str, object],
    vehicle_id: str,
    mission_id: str,
    boot_id: str,
    signing_key_id: str,
    public_key_fingerprint_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": "ets.ranger.custody-record-payload.v1",
        "custody_sequence": custody_sequence,
        "previous_record_digest_sha256": previous_record_digest_sha256,
        "source_schema_version": source_schema_version,
        "source_event_id": source_event_id,
        "source_record_digest_sha256": source_record_digest_sha256,
        "source_event": source_event,
        "vehicle_id": vehicle_id,
        "mission_id": mission_id,
        "boot_id": boot_id,
        "signing_algorithm": "ed25519",
        "signing_key_id": signing_key_id,
        "public_key_fingerprint_sha256": public_key_fingerprint_sha256,
        "storage_profile": "sqlite-wal-full-software-reference",
        "hardware_backed_key": False,
        "encrypted_at_rest": False,
        "complete_capture_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "signed_ordered_source_custody_no_truth_completeness_or_physical_claim"
        ),
    }


def _verification_failure(count: int, reason: str) -> RangerCustodyVerification:
    return RangerCustodyVerification(valid=False, record_count=count, reason=reason)
