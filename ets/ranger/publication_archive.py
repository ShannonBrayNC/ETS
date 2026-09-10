"""Separately keyed archive and retrieval audits for Ranger publication receipts.

The SQLite adapter enforces append-only writes and detects rollback relative to an expected
publication head supplied by the caller.  It is a software reference, not proof of physical
WORM storage, independent administration, continued availability, or hardware anti-rollback.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.external_publication import (
    RangerExternalPublicationChainVerification,
    RangerExternalPublicationReceipt,
    verify_external_publication_chain,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerPublicationArchiveError(RuntimeError):
    """Base error for publication archive validation or persistence."""


class RangerPublicationArchiveConflict(RangerPublicationArchiveError):
    """Raised when a write would duplicate, regress, or fork archived state."""


class RangerPublicationArchiveIntegrityError(RangerPublicationArchiveError):
    """Raised when archived data cannot be parsed or its indexes disagree."""


class RangerPublicationRetrievalAudit(StrictModel):
    """Custodian-signed evidence from one expected-head retrieval attempt."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/publication-retrieval-audit/v1"
        },
    )

    schema_version: Literal["ets.ranger.publication-retrieval-audit.v1"] = (
        "ets.ranger.publication-retrieval-audit.v1"
    )
    audit_id: str = Field(min_length=1, max_length=256)
    expected_publication_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_publication_head_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    archived_receipt_count: int = Field(ge=0, le=2**63 - 1)
    result: Literal["match", "head_mismatch", "archive_empty"]
    observed_at_utc: datetime
    custodian_id: str = Field(min_length=1, max_length=160)
    custodian_signing_key_id: str = Field(min_length=1, max_length=256)
    custodian_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    audit_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custodian_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    archive_chain_integrity_verified: bool
    freshness_relative_to_expected_head: bool
    logical_append_only_storage_enforced: Literal[True] = True
    separate_custodian_key_proven: Literal[True] = True
    physical_worm_storage_proven: Literal[False] = False
    organizational_independence_proven: Literal[False] = False
    hardware_rollback_resistance_proven: Literal[False] = False
    continued_availability_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "expected_head_relative_archive_audit_no_worm_independence_or_truth_claim"
    ] = "expected_head_relative_archive_audit_no_worm_independence_or_truth_claim"

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at_utc must be timezone-aware")
        return value.astimezone(UTC)


class RangerPublicationRetrievalAuditVerification(StrictModel):
    valid: bool
    result: Literal["match", "head_mismatch", "archive_empty"] | None = None
    archive_chain_integrity_verified: bool = False
    matches_expected_publication_head: bool = False
    freshness_relative_to_expected_head: bool = False
    separate_custodian_key_proven: bool = False
    physical_worm_storage_proven: Literal[False] = False
    organizational_independence_proven: Literal[False] = False
    hardware_rollback_resistance_proven: Literal[False] = False
    continued_availability_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


class SQLiteRangerPublicationArchiveStore:
    """Crash-consistent, logically append-only publication archive software reference."""

    provider_name = "sqlite"
    storage_profile = "sqlite-wal-full-logical-append-only-software-reference"
    physical_worm_storage_proven = False
    hardware_rollback_resistance_proven = False

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
            CREATE TABLE IF NOT EXISTS ranger_publication_archive (
                publication_sequence INTEGER PRIMARY KEY,
                publication_digest_sha256 TEXT NOT NULL UNIQUE,
                previous_publication_digest_sha256 TEXT NOT NULL,
                publication_id TEXT NOT NULL UNIQUE,
                publication_json TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ranger_publication_retrieval_audits (
                audit_id TEXT PRIMARY KEY,
                audit_digest_sha256 TEXT NOT NULL UNIQUE,
                expected_publication_head_digest_sha256 TEXT NOT NULL,
                result TEXT NOT NULL,
                audit_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def append_receipt(self, receipt: RangerExternalPublicationReceipt) -> None:
        receipt = RangerExternalPublicationReceipt.model_validate(receipt.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT publication_sequence, publication_digest_sha256
                    FROM ranger_publication_archive
                    ORDER BY publication_sequence DESC
                    LIMIT 1
                    """
                ).fetchone()
                expected_sequence = 1 if row is None else int(row["publication_sequence"]) + 1
                expected_previous = (
                    "0" * 64 if row is None else str(row["publication_digest_sha256"])
                )
                if receipt.publication_sequence != expected_sequence:
                    raise RangerPublicationArchiveConflict(
                        f"archive publication sequence must be {expected_sequence}"
                    )
                if receipt.previous_publication_digest_sha256 != expected_previous:
                    raise RangerPublicationArchiveConflict(
                        "publication receipt does not extend the archived head"
                    )
                self._connection.execute(
                    """
                    INSERT INTO ranger_publication_archive (
                        publication_sequence,
                        publication_digest_sha256,
                        previous_publication_digest_sha256,
                        publication_id,
                        publication_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.publication_sequence,
                        receipt.publication_digest_sha256,
                        receipt.previous_publication_digest_sha256,
                        receipt.publication_id,
                        receipt.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except RangerPublicationArchiveConflict:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerPublicationArchiveConflict(
                    "duplicate publication identity or digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_receipts(self) -> list[RangerExternalPublicationReceipt]:
        with self._lock:
            self._require_integrity()
            rows = self._connection.execute(
                """
                SELECT publication_sequence, publication_digest_sha256,
                       previous_publication_digest_sha256, publication_id, publication_json
                FROM ranger_publication_archive
                ORDER BY publication_sequence ASC
                """
            ).fetchall()
        try:
            receipts = [
                RangerExternalPublicationReceipt.model_validate_json(row["publication_json"])
                for row in rows
            ]
        except ValidationError as exc:
            raise RangerPublicationArchiveIntegrityError(
                "stored external publication receipt is invalid"
            ) from exc
        for row, receipt in zip(rows, receipts, strict=True):
            if (
                int(row["publication_sequence"]) != receipt.publication_sequence
                or str(row["publication_digest_sha256"]) != receipt.publication_digest_sha256
                or str(row["previous_publication_digest_sha256"])
                != receipt.previous_publication_digest_sha256
                or str(row["publication_id"]) != receipt.publication_id
            ):
                raise RangerPublicationArchiveIntegrityError(
                    "stored publication index metadata does not match signed receipt"
                )
        return receipts

    def append_audit(self, audit: RangerPublicationRetrievalAudit) -> None:
        audit = RangerPublicationRetrievalAudit.model_validate(audit.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """
                    INSERT INTO ranger_publication_retrieval_audits (
                        audit_id, audit_digest_sha256,
                        expected_publication_head_digest_sha256, result, audit_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        audit.audit_id,
                        audit.audit_digest_sha256,
                        audit.expected_publication_head_digest_sha256,
                        audit.result,
                        audit.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerPublicationArchiveConflict(
                    "duplicate retrieval audit identity or digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_audits(self) -> list[RangerPublicationRetrievalAudit]:
        with self._lock:
            self._require_integrity()
            rows = self._connection.execute(
                """
                SELECT audit_id, audit_digest_sha256,
                       expected_publication_head_digest_sha256, result, audit_json
                FROM ranger_publication_retrieval_audits
                ORDER BY rowid ASC
                """
            ).fetchall()
        try:
            audits = [
                RangerPublicationRetrievalAudit.model_validate_json(row["audit_json"])
                for row in rows
            ]
        except ValidationError as exc:
            raise RangerPublicationArchiveIntegrityError(
                "stored publication retrieval audit is invalid"
            ) from exc
        for row, audit in zip(rows, audits, strict=True):
            if (
                str(row["audit_id"]) != audit.audit_id
                or str(row["audit_digest_sha256"]) != audit.audit_digest_sha256
                or str(row["expected_publication_head_digest_sha256"])
                != audit.expected_publication_head_digest_sha256
                or str(row["result"]) != audit.result
            ):
                raise RangerPublicationArchiveIntegrityError(
                    "stored retrieval-audit index metadata does not match signed audit"
                )
        return audits

    def _require_integrity(self) -> None:
        integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise RangerPublicationArchiveIntegrityError("SQLite integrity_check failed")


class RangerPublicationArchive:
    """Verify, retain, and audit publication chains under a distinct custodian key."""

    def __init__(
        self,
        store: SQLiteRangerPublicationArchiveStore,
        *,
        publisher_public_key_hex: str,
        registry_public_key_hex: str,
        expected_publisher_id: str,
        expected_publisher_signing_key_id: str,
        expected_registry_id: str,
        expected_registry_signing_key_id: str,
        custodian_id: str,
        custodian_signing_key_id: str,
        custodian_private_key_hex: str,
        expected_retained_publication_head_digest_sha256: str | None = None,
    ) -> None:
        self.store = store
        self.publisher_public_key_hex = publisher_public_key_hex
        self.expected_publisher_id = expected_publisher_id
        self.expected_publisher_signing_key_id = expected_publisher_signing_key_id
        self.expected_registry_id = expected_registry_id
        self.expected_registry_signing_key_id = expected_registry_signing_key_id
        self.custodian_id = custodian_id
        self.custodian_signing_key_id = custodian_signing_key_id
        self._custodian_private_key = _private_key(custodian_private_key_hex)
        publisher_key = _public_key_bytes(publisher_public_key_hex)
        registry_key = _public_key_bytes(registry_public_key_hex)
        if publisher_key is None:
            raise RangerPublicationArchiveError(
                "publisher public key must be a 32-byte Ed25519 key"
            )
        if registry_key is None:
            raise RangerPublicationArchiveError("registry public key must be a 32-byte Ed25519 key")
        if publisher_key == registry_key:
            raise RangerPublicationArchiveError(
                "publisher and registry public keys must be distinct"
            )
        custodian_key = self._custodian_private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        for name, value, maximum in (
            ("expected_publisher_id", expected_publisher_id, 160),
            ("expected_publisher_signing_key_id", expected_publisher_signing_key_id, 256),
            ("expected_registry_id", expected_registry_id, 160),
            ("expected_registry_signing_key_id", expected_registry_signing_key_id, 256),
            ("custodian_id", custodian_id, 160),
            ("custodian_signing_key_id", custodian_signing_key_id, 256),
        ):
            if not value or len(value) > maximum:
                raise RangerPublicationArchiveError(f"{name} must contain 1-{maximum} characters")
        if (
            custodian_id in {expected_publisher_id, expected_registry_id}
            or custodian_signing_key_id
            in {expected_publisher_signing_key_id, expected_registry_signing_key_id}
            or custodian_key in {publisher_key, registry_key}
        ):
            raise RangerPublicationArchiveError(
                "custodian identity and key must be distinct from publisher and registry"
            )

        retained = self.store.list_receipts()
        if retained:
            verified = self._verify(retained, retained[-1].publication_digest_sha256)
            if not verified.valid:
                raise RangerPublicationArchiveIntegrityError(
                    f"retained publication archive is invalid: {verified.reason}"
                )
        if expected_retained_publication_head_digest_sha256 is not None:
            observed = retained[-1].publication_digest_sha256 if retained else None
            if observed != expected_retained_publication_head_digest_sha256:
                raise RangerPublicationArchiveIntegrityError(
                    "archive does not match the expected retained publication head"
                )
        self._receipts = retained

    @property
    def custodian_public_key_hex(self) -> str:
        return (
            self._custodian_private_key.public_key()
            .public_bytes(Encoding.Raw, PublicFormat.Raw)
            .hex()
        )

    @property
    def latest_publication_digest_sha256(self) -> str | None:
        return self._receipts[-1].publication_digest_sha256 if self._receipts else None

    def retain(self, receipts: Iterable[RangerExternalPublicationReceipt]) -> int:
        """Verify a complete chain and append only its exact new suffix."""

        presented = list(receipts)
        if not presented:
            raise RangerPublicationArchiveError("publication chain is empty")
        verified = self._verify(presented, presented[-1].publication_digest_sha256)
        if not verified.valid:
            raise RangerPublicationArchiveError(
                f"external publication chain is invalid: {verified.reason}"
            )
        if len(presented) < len(self._receipts):
            raise RangerPublicationArchiveConflict("presented publication chain is stale")
        for retained, candidate in zip(self._receipts, presented, strict=False):
            if retained.publication_digest_sha256 != candidate.publication_digest_sha256:
                raise RangerPublicationArchiveConflict("presented publication chain forks archive")
        appended = 0
        for receipt in presented[len(self._receipts) :]:
            self.store.append_receipt(receipt)
            self._receipts.append(receipt)
            appended += 1
        return appended

    def audit_retrieval(
        self,
        *,
        audit_id: str,
        expected_publication_head_digest_sha256: str,
        observed_at_utc: datetime,
    ) -> RangerPublicationRetrievalAudit:
        """Retrieve and verify the archive, then persist a signed audit result."""

        observed_at = _aware_utc(observed_at_utc)
        receipts = self.store.list_receipts()
        observed_head = receipts[-1].publication_digest_sha256 if receipts else None
        if not receipts:
            result: Literal["match", "head_mismatch", "archive_empty"] = "archive_empty"
            chain_valid = False
        else:
            verification = self._verify(receipts, receipts[-1].publication_digest_sha256)
            chain_valid = verification.valid
            if not chain_valid:
                raise RangerPublicationArchiveIntegrityError(
                    f"retrieved publication archive is invalid: {verification.reason}"
                )
            result = (
                "match"
                if observed_head == expected_publication_head_digest_sha256
                else "head_mismatch"
            )
        payload = _audit_payload(
            audit_id=audit_id,
            expected_publication_head_digest_sha256=(expected_publication_head_digest_sha256),
            observed_publication_head_digest_sha256=observed_head,
            archived_receipt_count=len(receipts),
            result=result,
            observed_at_utc=observed_at,
            custodian_id=self.custodian_id,
            custodian_signing_key_id=self.custodian_signing_key_id,
            custodian_public_key_fingerprint_sha256=hashlib.sha256(
                bytes.fromhex(self.custodian_public_key_hex)
            ).hexdigest(),
            archive_chain_integrity_verified=chain_valid,
        )
        digest = canonical_sha256(payload)
        try:
            audit = RangerPublicationRetrievalAudit.model_validate(
                {
                    **payload,
                    "observed_at_utc": observed_at,
                    "audit_digest_sha256": digest,
                    "custodian_signature_hex": self._custodian_private_key.sign(
                        canonicalize(payload)
                    ).hex(),
                }
            )
        except ValidationError as exc:
            raise RangerPublicationArchiveError("invalid retrieval audit fields") from exc
        self.store.append_audit(audit)
        return audit

    def _verify(
        self, receipts: list[RangerExternalPublicationReceipt], head: str
    ) -> RangerExternalPublicationChainVerification:
        return verify_external_publication_chain(
            receipts,
            publisher_public_key_hex=self.publisher_public_key_hex,
            expected_publisher_id=self.expected_publisher_id,
            expected_publisher_signing_key_id=self.expected_publisher_signing_key_id,
            expected_registry_id=self.expected_registry_id,
            expected_registry_signing_key_id=self.expected_registry_signing_key_id,
            expected_latest_publication_digest_sha256=head,
        )


def verify_publication_retrieval_audit(
    audit: RangerPublicationRetrievalAudit,
    *,
    custodian_public_key_hex: str,
    expected_custodian_id: str,
    expected_custodian_signing_key_id: str,
    expected_publication_head_digest_sha256: str,
) -> RangerPublicationRetrievalAuditVerification:
    """Verify one signed retrieval audit without upgrading its bounded claims."""

    key_bytes = _public_key_bytes(custodian_public_key_hex)
    if key_bytes is None:
        return _audit_failure("custodian public key is not 32-byte Ed25519")
    try:
        record = RangerPublicationRetrievalAudit.model_validate(audit.model_dump())
    except (AttributeError, ValidationError):
        return _audit_failure("retrieval audit schema validation failed")
    fingerprint = hashlib.sha256(key_bytes).hexdigest()
    if (
        record.custodian_id != expected_custodian_id
        or record.custodian_signing_key_id != expected_custodian_signing_key_id
        or record.custodian_public_key_fingerprint_sha256 != fingerprint
    ):
        return _audit_failure("retrieval audit custodian identity or key mismatch")
    if record.expected_publication_head_digest_sha256 != expected_publication_head_digest_sha256:
        return _audit_failure("retrieval audit expected publication head mismatch")
    payload = _audit_payload_from_record(record)
    if canonical_sha256(payload) != record.audit_digest_sha256:
        return _audit_failure("retrieval audit digest mismatch")
    try:
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(
            bytes.fromhex(record.custodian_signature_hex), canonicalize(payload)
        )
    except (InvalidSignature, ValueError):
        return _audit_failure("retrieval audit signature is invalid")
    matched = record.result == "match"
    if matched != (
        record.archive_chain_integrity_verified
        and record.observed_publication_head_digest_sha256
        == record.expected_publication_head_digest_sha256
        and record.freshness_relative_to_expected_head
    ):
        return _audit_failure("retrieval audit result flags are inconsistent")
    return RangerPublicationRetrievalAuditVerification(
        valid=True,
        result=record.result,
        archive_chain_integrity_verified=record.archive_chain_integrity_verified,
        matches_expected_publication_head=matched,
        freshness_relative_to_expected_head=record.freshness_relative_to_expected_head,
        separate_custodian_key_proven=True,
        reason=(
            "the configured custodian signed an integrity-checked retrieval matching the expected "
            "publication head"
            if matched
            else "the configured custodian signed a bounded retrieval failure observation"
        ),
    )


def _audit_payload(
    *,
    audit_id: str,
    expected_publication_head_digest_sha256: str,
    observed_publication_head_digest_sha256: str | None,
    archived_receipt_count: int,
    result: Literal["match", "head_mismatch", "archive_empty"],
    observed_at_utc: datetime,
    custodian_id: str,
    custodian_signing_key_id: str,
    custodian_public_key_fingerprint_sha256: str,
    archive_chain_integrity_verified: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "ets.ranger.publication-retrieval-audit.v1",
        "audit_id": audit_id,
        "expected_publication_head_digest_sha256": expected_publication_head_digest_sha256,
        "observed_publication_head_digest_sha256": observed_publication_head_digest_sha256,
        "archived_receipt_count": archived_receipt_count,
        "result": result,
        "observed_at_utc": observed_at_utc.isoformat().replace("+00:00", "Z"),
        "custodian_id": custodian_id,
        "custodian_signing_key_id": custodian_signing_key_id,
        "custodian_public_key_fingerprint_sha256": (custodian_public_key_fingerprint_sha256),
        "signing_algorithm": "ed25519",
        "archive_chain_integrity_verified": archive_chain_integrity_verified,
        "freshness_relative_to_expected_head": result == "match",
        "logical_append_only_storage_enforced": True,
        "separate_custodian_key_proven": True,
        "physical_worm_storage_proven": False,
        "organizational_independence_proven": False,
        "hardware_rollback_resistance_proven": False,
        "continued_availability_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "expected_head_relative_archive_audit_no_worm_independence_or_truth_claim"
        ),
    }


def _audit_payload_from_record(audit: RangerPublicationRetrievalAudit) -> dict[str, Any]:
    return _audit_payload(
        audit_id=audit.audit_id,
        expected_publication_head_digest_sha256=(audit.expected_publication_head_digest_sha256),
        observed_publication_head_digest_sha256=(audit.observed_publication_head_digest_sha256),
        archived_receipt_count=audit.archived_receipt_count,
        result=audit.result,
        observed_at_utc=audit.observed_at_utc,
        custodian_id=audit.custodian_id,
        custodian_signing_key_id=audit.custodian_signing_key_id,
        custodian_public_key_fingerprint_sha256=(audit.custodian_public_key_fingerprint_sha256),
        archive_chain_integrity_verified=audit.archive_chain_integrity_verified,
    )


def publication_retrieval_audit_signing_payload(
    audit: RangerPublicationRetrievalAudit,
) -> dict[str, Any]:
    """Return the canonical signed payload for one strict retrieval audit.

    Key-lifecycle verifiers use this helper to check an audit with the
    custodian key that stood at a named authority-history prefix. It does not
    make the archive backend immutable or continuously available.
    """

    validated = RangerPublicationRetrievalAudit.model_validate(audit.model_dump())
    return _audit_payload_from_record(validated)


def _private_key(value: str) -> Ed25519PrivateKey:
    try:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))
    except ValueError as exc:
        raise RangerPublicationArchiveError(
            "custodian private key must be a 32-byte Ed25519 key"
        ) from exc


def _public_key_bytes(value: str) -> bytes | None:
    try:
        key_bytes = bytes.fromhex(value)
        if len(key_bytes) != 32:
            return None
        Ed25519PublicKey.from_public_bytes(key_bytes)
        return key_bytes
    except ValueError:
        return None


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerPublicationArchiveError("audit observation time must be timezone-aware")
    return value.astimezone(UTC)


def _audit_failure(reason: str) -> RangerPublicationRetrievalAuditVerification:
    return RangerPublicationRetrievalAuditVerification(valid=False, reason=reason)
