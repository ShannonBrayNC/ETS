"""Authority-relative lifecycle evidence for Ranger publication and archive keys.

External-publication receipts and publication-retrieval audits identify the key that signed a
record, but a signature alone cannot say whether that key stood under the configured publisher or
custodian authority.  This additive profile retains an authority-signed, append-only lifecycle
for those two roles and lets a verifier check a source record against the exact authority-history
prefix named by its signed standing record.

An old key can therefore retain *historical* standing after rotation or revocation without being
treated as currently authorized.  The profile has no trusted-time binding, so it does not prove
when a source record was signed relative to lifecycle events.  It also does not establish WORM
storage, organizational independence, operational authorization, semantic truth, or physical
outcome.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Any, Literal, Self

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.external_publication import (
    RangerExternalPublicationReceipt,
    external_publication_receipt_signing_payload,
)
from ets.ranger.publication_archive import (
    RangerPublicationRetrievalAudit,
    publication_retrieval_audit_signing_payload,
    verify_publication_retrieval_audit,
)

_ZERO_DIGEST = "0" * 64


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerPublicationKeyLifecycleError(RuntimeError):
    """Base error for publication-key lifecycle validation or persistence."""


class RangerPublicationKeyLifecycleConflict(RangerPublicationKeyLifecycleError):
    """Raised when an authority event conflicts with retained lifecycle history."""


class RangerPublicationKeyLifecycleIntegrityError(RangerPublicationKeyLifecycleError):
    """Raised when stored lifecycle history is malformed or internally inconsistent."""


class RangerPublicationKeyRole(StrEnum):
    """The independently keyed authority roles covered by this profile."""

    PUBLISHER = "publisher"
    CUSTODIAN = "custodian"


class RangerPublicationKeyEventKind(StrEnum):
    ENROLL = "enroll"
    ROTATE = "rotate"
    REVOKE = "revoke"


class RangerPublicationKeyRevocationReason(StrEnum):
    COMPROMISE_SUSPECTED = "compromise_suspected"
    CUSTODY_LOST = "custody_lost"
    ADMINISTRATIVE = "administrative"
    RETIRED = "retired"


class RangerPublicationKeySourceKind(StrEnum):
    EXTERNAL_PUBLICATION_RECEIPT = "external_publication_receipt"
    PUBLICATION_RETRIEVAL_AUDIT = "publication_retrieval_audit"


class RangerPublicationSigningKeyDescriptor(StrictModel):
    """Public, non-secret identity for one software-reference signing key."""

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


class RangerPublicationKeyBindingIntent(StrictModel):
    """Unsigned publisher/custodian lifecycle intent requiring possession proofs."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/publication-key-binding-intent/v1"
        },
    )

    schema_version: Literal["ets.ranger.publication-key-binding-intent.v1"] = (
        "ets.ranger.publication-key-binding-intent.v1"
    )
    request_id: str = Field(min_length=1, max_length=256)
    key_role: RangerPublicationKeyRole
    event_kind: RangerPublicationKeyEventKind
    publication_scope_id: str = Field(min_length=24, max_length=192)
    principal_id: str = Field(min_length=1, max_length=160)
    subject_key: RangerPublicationSigningKeyDescriptor
    replacement_key: RangerPublicationSigningKeyDescriptor | None = None
    revocation_reason: RangerPublicationKeyRevocationReason | None = None
    recorded_at_utc: datetime
    clock_trusted: Literal[False] = False

    @field_validator("publication_scope_id")
    @classmethod
    def require_publication_scope(cls, value: str) -> str:
        if not value.startswith("ets-ranger-publication:"):
            raise ValueError("publication_scope_id must use the ets-ranger-publication: namespace")
        return value

    @field_validator("recorded_at_utc")
    @classmethod
    def normalize_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_transition_fields(self) -> Self:
        if self.event_kind is RangerPublicationKeyEventKind.ENROLL:
            if self.replacement_key is not None or self.revocation_reason is not None:
                raise ValueError("enrollment cannot name a replacement or revocation reason")
        elif self.event_kind is RangerPublicationKeyEventKind.ROTATE:
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


class RangerPublicationKeyBindingRequest(StrictModel):
    """A strict lifecycle intent plus the possession proofs needed for it."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/publication-key-binding-request/v1"
        },
    )

    schema_version: Literal["ets.ranger.publication-key-binding-request.v1"] = (
        "ets.ranger.publication-key-binding-request.v1"
    )
    intent: RangerPublicationKeyBindingIntent
    intent_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    subject_key_proof_signature_hex: str | None = Field(default=None, pattern=r"^[0-9a-f]{128}$")
    replacement_key_proof_signature_hex: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{128}$"
    )

    @model_validator(mode="after")
    def require_digest_and_proofs(self) -> Self:
        expected = canonical_sha256(self.intent.model_dump(mode="json"))
        if self.intent_digest_sha256 != expected:
            raise ValueError("intent digest does not match intent")
        if self.intent.event_kind is RangerPublicationKeyEventKind.ENROLL:
            if self.subject_key_proof_signature_hex is None:
                raise ValueError("enrollment requires subject-key proof")
            if self.replacement_key_proof_signature_hex is not None:
                raise ValueError("enrollment cannot include replacement-key proof")
        elif self.intent.event_kind is RangerPublicationKeyEventKind.ROTATE:
            if (
                self.subject_key_proof_signature_hex is None
                or self.replacement_key_proof_signature_hex is None
            ):
                raise ValueError("rotation requires old- and new-key possession proofs")
        elif (
            self.subject_key_proof_signature_hex is not None
            or self.replacement_key_proof_signature_hex is not None
        ):
            raise ValueError("authority revocation does not accept key proof fields")
        return self


class RangerPublicationKeyAuthorityEvent(StrictModel):
    """One authority-signed accepted publisher/custodian lifecycle event."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/publication-key-authority-event/v1"
        },
    )

    schema_version: Literal["ets.ranger.publication-key-authority-event.v1"] = (
        "ets.ranger.publication-key-authority-event.v1"
    )
    authority_sequence: int = Field(ge=1, le=2**63 - 1)
    previous_event_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: RangerPublicationKeyBindingRequest
    authority_id: str = Field(min_length=1, max_length=160)
    authority_signing_key_id: str = Field(min_length=1, max_length=256)
    authority_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    event_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    storage_profile: Literal["sqlite-wal-full-software-reference"] = (
        "sqlite-wal-full-software-reference"
    )
    operational_authorization_proven: Literal[False] = False
    authority_administrative_independence_proven: Literal[False] = False
    hardware_identity_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "authority_relative_publication_key_standing_no_global_time_or_operational_claim"
    ] = "authority_relative_publication_key_standing_no_global_time_or_operational_claim"

    @model_validator(mode="after")
    def require_predecessor_shape(self) -> Self:
        if self.authority_sequence == 1:
            if self.previous_event_digest_sha256 != _ZERO_DIGEST:
                raise ValueError("authority genesis must use the zero predecessor digest")
        elif self.previous_event_digest_sha256 == _ZERO_DIGEST:
            raise ValueError("non-genesis authority event requires a predecessor digest")
        return self


class RangerPublicationKeyAuthorityVerification(StrictModel):
    valid: bool
    event_count: int = Field(ge=0)
    head_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    publisher_key_currently_active: bool = False
    custodian_key_currently_active: bool = False
    reason: str


class RangerPublicationSourceKeyStanding(StrictModel):
    """Authority-signed key standing for one receipt or retrieval-audit digest."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/publication-source-key-standing/v1"
        },
    )

    schema_version: Literal["ets.ranger.publication-source-key-standing.v1"] = (
        "ets.ranger.publication-source-key-standing.v1"
    )
    standing_id: str = Field(min_length=1, max_length=256)
    source_kind: RangerPublicationKeySourceKind
    source_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    key_role: RangerPublicationKeyRole
    publication_scope_id: str = Field(min_length=24, max_length=192)
    principal_id: str = Field(min_length=1, max_length=160)
    signing_key_id: str = Field(min_length=1, max_length=256)
    public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_event_count: int = Field(ge=1, le=2**63 - 1)
    authority_history_head_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    matched_authority_sequence: int = Field(ge=1, le=2**63 - 1)
    authority_id: str = Field(min_length=1, max_length=160)
    authority_signing_key_id: str = Field(min_length=1, max_length=256)
    authority_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    standing_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    historical_key_standing_at_named_history_prefix: Literal[True] = True
    source_signature_time_proven: Literal[False] = False
    currently_authorized_proven: Literal[False] = False
    operational_authorization_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "historical_publication_key_standing_no_source_time_global_currentness_or_truth_claim"
    ] = "historical_publication_key_standing_no_source_time_global_currentness_or_truth_claim"

    @field_validator("publication_scope_id")
    @classmethod
    def require_publication_scope(cls, value: str) -> str:
        if not value.startswith("ets-ranger-publication:"):
            raise ValueError("publication_scope_id must use the ets-ranger-publication: namespace")
        return value

    @model_validator(mode="after")
    def require_source_role_pair(self) -> Self:
        if _source_role(self.source_kind) is not self.key_role:
            raise ValueError("source kind must use its matching publisher or custodian role")
        return self


class RangerPublicationSourceKeyStandingVerification(StrictModel):
    valid: bool
    source_kind: RangerPublicationKeySourceKind | None = None
    source_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    historical_authority_relative_key_standing: bool = False
    source_signature_valid: bool = False
    currently_authorized_relative_to_presented_history: bool = False
    matched_authority_sequence: int | None = Field(default=None, ge=1)
    named_authority_history_head_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    source_signature_time_proven: Literal[False] = False
    operational_authorization_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


class RangerPublicationLifecycleChainVerification(StrictModel):
    valid: bool
    receipt_count: int = Field(ge=0)
    latest_publication_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    historical_publisher_key_standing_proven: bool = False
    all_publisher_keys_currently_authorized_relative_to_presented_history: bool = False
    matches_expected_publication_head: bool = False
    source_signature_time_proven: Literal[False] = False
    physical_worm_storage_proven: Literal[False] = False
    organizational_independence_proven: Literal[False] = False
    globally_current_history_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


def publication_key_binding_intent_bytes(intent: RangerPublicationKeyBindingIntent) -> bytes:
    """Return canonical possession-proof bytes for a publisher/custodian intent."""

    validated = RangerPublicationKeyBindingIntent.model_validate(intent.model_dump())
    return canonicalize(validated.model_dump(mode="json"))


def build_publication_key_binding_request(
    intent: RangerPublicationKeyBindingIntent,
    *,
    subject_key_proof_signature_hex: str | None = None,
    replacement_key_proof_signature_hex: str | None = None,
) -> RangerPublicationKeyBindingRequest:
    """Construct a strict request after the relevant key holders prove possession."""

    validated = RangerPublicationKeyBindingIntent.model_validate(intent.model_dump())
    return RangerPublicationKeyBindingRequest(
        intent=validated,
        intent_digest_sha256=canonical_sha256(validated.model_dump(mode="json")),
        subject_key_proof_signature_hex=subject_key_proof_signature_hex,
        replacement_key_proof_signature_hex=replacement_key_proof_signature_hex,
    )


class SQLiteRangerPublicationKeyAuthorityStore:
    """Crash-consistent append-only software reference for publication-key events."""

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
            CREATE TABLE IF NOT EXISTS ranger_publication_key_authority_events (
                authority_sequence INTEGER PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                event_digest_sha256 TEXT NOT NULL UNIQUE,
                key_role TEXT NOT NULL,
                publication_scope_id TEXT NOT NULL,
                event_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def append(self, event: RangerPublicationKeyAuthorityEvent) -> None:
        validated = RangerPublicationKeyAuthorityEvent.model_validate(event.model_dump())
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT authority_sequence, event_digest_sha256
                    FROM ranger_publication_key_authority_events
                    ORDER BY authority_sequence DESC
                    LIMIT 1
                    """
                ).fetchone()
                expected_sequence = 1 if row is None else int(row["authority_sequence"]) + 1
                expected_previous = _ZERO_DIGEST if row is None else str(row["event_digest_sha256"])
                if validated.authority_sequence != expected_sequence:
                    raise RangerPublicationKeyLifecycleConflict(
                        f"authority sequence must be {expected_sequence}"
                    )
                if validated.previous_event_digest_sha256 != expected_previous:
                    raise RangerPublicationKeyLifecycleConflict(
                        "event does not extend the retained publication-key authority head"
                    )
                intent = validated.request.intent
                self._connection.execute(
                    """
                    INSERT INTO ranger_publication_key_authority_events (
                        authority_sequence, request_id, event_digest_sha256, key_role,
                        publication_scope_id, event_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        validated.authority_sequence,
                        intent.request_id,
                        validated.event_digest_sha256,
                        intent.key_role.value,
                        intent.publication_scope_id,
                        validated.model_dump_json(),
                    ),
                )
                self._connection.commit()
            except RangerPublicationKeyLifecycleConflict:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                self._connection.rollback()
                raise RangerPublicationKeyLifecycleConflict(
                    "duplicate authority sequence, request identity, or event digest"
                ) from exc
            except Exception:
                self._connection.rollback()
                raise

    def list_events(self) -> list[RangerPublicationKeyAuthorityEvent]:
        with self._lock:
            integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise RangerPublicationKeyLifecycleIntegrityError("SQLite integrity_check failed")
            rows = self._connection.execute(
                """
                SELECT authority_sequence, request_id, event_digest_sha256, key_role,
                       publication_scope_id, event_json
                FROM ranger_publication_key_authority_events
                ORDER BY authority_sequence ASC
                """
            ).fetchall()
        try:
            events = [
                RangerPublicationKeyAuthorityEvent.model_validate_json(row["event_json"])
                for row in rows
            ]
        except ValidationError as exc:
            raise RangerPublicationKeyLifecycleIntegrityError(
                "stored publication-key authority event is invalid"
            ) from exc
        for row, event in zip(rows, events, strict=True):
            intent = event.request.intent
            if (
                int(row["authority_sequence"]) != event.authority_sequence
                or str(row["request_id"]) != intent.request_id
                or str(row["event_digest_sha256"]) != event.event_digest_sha256
                or str(row["key_role"]) != intent.key_role.value
                or str(row["publication_scope_id"]) != intent.publication_scope_id
            ):
                raise RangerPublicationKeyLifecycleIntegrityError(
                    "stored publication-key index metadata does not match signed event"
                )
        return events


class RangerPublicationKeyAuthorityLedger:
    """Validate lifecycle proofs, retain authority events, and attest historic key standing."""

    def __init__(
        self,
        store: SQLiteRangerPublicationKeyAuthorityStore,
        *,
        publication_scope_id: str,
        publisher_id: str,
        custodian_id: str,
        authority_id: str,
        authority_signing_key_id: str,
        authority_private_key_hex: str,
    ) -> None:
        if (
            not publication_scope_id.startswith("ets-ranger-publication:")
            or len(publication_scope_id) > 192
        ):
            raise RangerPublicationKeyLifecycleError(
                "publication_scope_id must use the ets-ranger-publication: namespace"
            )
        for name, value, maximum in (
            ("publisher_id", publisher_id, 160),
            ("custodian_id", custodian_id, 160),
            ("authority_id", authority_id, 160),
            ("authority_signing_key_id", authority_signing_key_id, 256),
        ):
            if not value or len(value) > maximum:
                raise RangerPublicationKeyLifecycleError(
                    f"{name} must contain 1-{maximum} characters"
                )
        if len({publisher_id, custodian_id, authority_id}) != 3:
            raise RangerPublicationKeyLifecycleError(
                "publisher, custodian, and authority identities must be distinct"
            )
        try:
            self._authority_private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(authority_private_key_hex)
            )
        except ValueError as exc:
            raise RangerPublicationKeyLifecycleError(
                "authority private key must be a 32-byte Ed25519 key"
            ) from exc

        self.store = store
        self.publication_scope_id = publication_scope_id
        self.publisher_id = publisher_id
        self.custodian_id = custodian_id
        self.authority_id = authority_id
        self.authority_signing_key_id = authority_signing_key_id
        retained = self.store.list_events()
        if retained:
            verification = self.verify_history(retained, self.authority_public_key_hex)
            if not verification.valid:
                raise RangerPublicationKeyLifecycleIntegrityError(
                    f"retained publication-key history is invalid: {verification.reason}"
                )
            configuration_error = _configured_history_error(
                retained,
                publication_scope_id=publication_scope_id,
                publisher_id=publisher_id,
                custodian_id=custodian_id,
                authority_id=authority_id,
                authority_signing_key_id=authority_signing_key_id,
                authority_fingerprint=self.authority_public_key_fingerprint_sha256,
            )
            if configuration_error is not None:
                raise RangerPublicationKeyLifecycleIntegrityError(configuration_error)
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

    def append(
        self, request: RangerPublicationKeyBindingRequest
    ) -> RangerPublicationKeyAuthorityEvent:
        """Validate, sign, and atomically retain one publisher/custodian transition."""

        retained = self.store.list_events()
        if retained != self._events:
            raise RangerPublicationKeyLifecycleConflict(
                "retained publication-key history changed; reopen the ledger before appending"
            )
        try:
            validated = RangerPublicationKeyBindingRequest.model_validate(request.model_dump())
        except (AttributeError, ValidationError) as exc:
            raise RangerPublicationKeyLifecycleError(
                "invalid publication-key binding request"
            ) from exc
        intent = validated.intent
        if intent.publication_scope_id != self.publication_scope_id:
            raise RangerPublicationKeyLifecycleError("publication-key scope does not match ledger")
        if intent.principal_id != self._principal_for_role(intent.key_role):
            raise RangerPublicationKeyLifecycleError(
                "publication-key principal does not match the configured role"
            )
        proof_error = _request_proof_error(validated)
        if proof_error is not None:
            raise RangerPublicationKeyLifecycleError(proof_error)
        transition_error = _request_transition_error(self._events, validated)
        if transition_error is not None:
            raise RangerPublicationKeyLifecycleConflict(transition_error)
        reuse_error = _new_key_reuse_error(self._events, validated)
        if reuse_error is not None:
            raise RangerPublicationKeyLifecycleConflict(reuse_error)
        for descriptor in _request_descriptors(validated):
            if (
                descriptor.public_key_fingerprint_sha256
                == self.authority_public_key_fingerprint_sha256
            ):
                raise RangerPublicationKeyLifecycleError(
                    "publisher or custodian key must differ from the authority signing key"
                )

        sequence = len(self._events) + 1
        previous = _ZERO_DIGEST if not self._events else self._events[-1].event_digest_sha256
        payload = _authority_event_payload(
            authority_sequence=sequence,
            previous_event_digest_sha256=previous,
            request=validated,
            authority_id=self.authority_id,
            authority_signing_key_id=self.authority_signing_key_id,
            authority_public_key_fingerprint_sha256=self.authority_public_key_fingerprint_sha256,
        )
        digest = canonical_sha256(payload)
        event = RangerPublicationKeyAuthorityEvent.model_validate(
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

    def list_events(self) -> list[RangerPublicationKeyAuthorityEvent]:
        return self.store.list_events()

    def attest_source_key_standing(
        self,
        *,
        standing_id: str,
        source_kind: RangerPublicationKeySourceKind,
        source_digest_sha256: str,
        principal_id: str,
        signing_key_id: str,
        public_key_fingerprint_sha256: str,
        authority_event_count: int | None = None,
    ) -> RangerPublicationSourceKeyStanding:
        """Sign an authority-relative source-key standing at an exact history prefix.

        The caller must separately preserve and verify the source record. This method attests the
        lifecycle mapping only; the untrusted source timestamp is not evidence that the record was
        signed before a later rotation or revocation.
        """

        if len(standing_id) == 0 or len(standing_id) > 256:
            raise RangerPublicationKeyLifecycleError("standing_id must contain 1-256 characters")
        if len(source_digest_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in source_digest_sha256
        ):
            raise RangerPublicationKeyLifecycleError("source digest must be lowercase SHA-256")
        if len(public_key_fingerprint_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in public_key_fingerprint_sha256
        ):
            raise RangerPublicationKeyLifecycleError(
                "public-key fingerprint must be lowercase SHA-256"
            )
        if any(event.request.intent.request_id == standing_id for event in self._events):
            raise RangerPublicationKeyLifecycleError(
                "standing_id collides with an authority request"
            )
        count = len(self._events) if authority_event_count is None else authority_event_count
        if count < 1 or count > len(self._events):
            raise RangerPublicationKeyLifecycleError(
                "authority_event_count must name a retained non-empty history prefix"
            )
        prefix = self._events[:count]
        verification = self.verify_history(prefix, self.authority_public_key_hex)
        if not verification.valid:
            raise RangerPublicationKeyLifecycleIntegrityError(
                f"retained publication-key history is invalid: {verification.reason}"
            )
        key_role = _source_role(source_kind)
        if principal_id != self._principal_for_role(key_role):
            raise RangerPublicationKeyLifecycleError(
                "source principal does not match the configured publisher or custodian"
            )
        descriptor, event = _active_descriptor(prefix, key_role)
        if descriptor is None or event is None:
            raise RangerPublicationKeyLifecycleConflict(
                "source key has no active authority-relative standing at the named history prefix"
            )
        if _descriptor_identity(descriptor) != (signing_key_id, public_key_fingerprint_sha256):
            raise RangerPublicationKeyLifecycleConflict(
                "source key does not match the active key at the named history prefix"
            )
        payload = _source_key_standing_payload(
            standing_id=standing_id,
            source_kind=source_kind,
            source_digest_sha256=source_digest_sha256,
            key_role=key_role,
            publication_scope_id=self.publication_scope_id,
            principal_id=principal_id,
            signing_key_id=signing_key_id,
            public_key_fingerprint_sha256=public_key_fingerprint_sha256,
            authority_event_count=count,
            authority_history_head_digest_sha256=prefix[-1].event_digest_sha256,
            matched_authority_sequence=event.authority_sequence,
            authority_id=self.authority_id,
            authority_signing_key_id=self.authority_signing_key_id,
            authority_public_key_fingerprint_sha256=self.authority_public_key_fingerprint_sha256,
        )
        digest = canonical_sha256(payload)
        return RangerPublicationSourceKeyStanding.model_validate(
            {
                **payload,
                "source_kind": source_kind,
                "key_role": key_role,
                "standing_digest_sha256": digest,
                "authority_signature_hex": self._authority_private_key.sign(
                    canonicalize(payload)
                ).hex(),
            }
        )

    def _principal_for_role(self, role: RangerPublicationKeyRole) -> str:
        return (
            self.publisher_id if role is RangerPublicationKeyRole.PUBLISHER else self.custodian_id
        )

    @staticmethod
    def verify_history(
        events: Iterable[RangerPublicationKeyAuthorityEvent],
        authority_public_key_hex: str,
    ) -> RangerPublicationKeyAuthorityVerification:
        """Verify the complete supplied lifecycle history without trusting its store."""

        try:
            authority_key_bytes = bytes.fromhex(authority_public_key_hex)
            authority_key = Ed25519PublicKey.from_public_bytes(authority_key_bytes)
        except ValueError:
            return _history_failure(0, "authority public key is not 32-byte Ed25519")
        expected_fingerprint = hashlib.sha256(authority_key_bytes).hexdigest()
        previous = _ZERO_DIGEST
        expected_sequence = 1
        verified: list[RangerPublicationKeyAuthorityEvent] = []
        request_ids: set[str] = set()
        identity: tuple[str, str, str] | None = None
        principal_by_role: dict[RangerPublicationKeyRole, str] = {}

        for unvalidated in events:
            count = len(verified) + 1
            try:
                event = RangerPublicationKeyAuthorityEvent.model_validate(unvalidated.model_dump())
            except (AttributeError, ValidationError):
                return _history_failure(
                    count, "publication-key authority event schema validation failed"
                )
            intent = event.request.intent
            if event.authority_sequence != expected_sequence:
                return _history_failure(
                    count, "missing, duplicate, or reordered authority sequence"
                )
            if event.previous_event_digest_sha256 != previous:
                return _history_failure(count, "previous publication-key authority digest mismatch")
            if intent.request_id in request_ids:
                return _history_failure(count, "duplicate publication-key request identity")
            current_identity = (
                intent.publication_scope_id,
                event.authority_id,
                event.authority_signing_key_id,
            )
            if identity is None:
                identity = current_identity
            elif current_identity != identity:
                return _history_failure(
                    count, "publication-key scope or authority identity changed"
                )
            prior_principal = principal_by_role.get(intent.key_role)
            if prior_principal is None:
                principal_by_role[intent.key_role] = intent.principal_id
            elif prior_principal != intent.principal_id:
                return _history_failure(count, "publication-key principal changed within one role")
            if event.authority_public_key_fingerprint_sha256 != expected_fingerprint:
                return _history_failure(count, "authority public key fingerprint mismatch")
            if any(
                descriptor.public_key_fingerprint_sha256 == expected_fingerprint
                for descriptor in _request_descriptors(event.request)
            ):
                return _history_failure(count, "source and authority signing keys are not distinct")
            proof_error = _request_proof_error(event.request)
            if proof_error is not None:
                return _history_failure(count, proof_error)
            transition_error = _request_transition_error(verified, event.request)
            if transition_error is not None:
                return _history_failure(count, transition_error)
            reuse_error = _new_key_reuse_error(verified, event.request)
            if reuse_error is not None:
                return _history_failure(count, reuse_error)
            payload = _authority_event_payload_from_record(event)
            if canonical_sha256(payload) != event.event_digest_sha256:
                return _history_failure(count, "publication-key authority event digest mismatch")
            try:
                authority_key.verify(
                    bytes.fromhex(event.authority_signature_hex), canonicalize(payload)
                )
            except (InvalidSignature, ValueError):
                return _history_failure(count, "publication-key authority signature invalid")
            verified.append(event)
            request_ids.add(intent.request_id)
            previous = event.event_digest_sha256
            expected_sequence += 1

        if not verified:
            return _history_failure(0, "publication-key authority history is empty")
        publisher_active, _ = _active_descriptor(verified, RangerPublicationKeyRole.PUBLISHER)
        custodian_active, _ = _active_descriptor(verified, RangerPublicationKeyRole.CUSTODIAN)
        return RangerPublicationKeyAuthorityVerification(
            valid=True,
            event_count=len(verified),
            head_digest_sha256=previous,
            publisher_key_currently_active=publisher_active is not None,
            custodian_key_currently_active=custodian_active is not None,
            reason=(
                "authority signatures, possession proofs, role-scoped transitions, and ordering "
                "verify; operational authorization, trusted time, and global currentness are "
                "not proven"
            ),
        )


def verify_publication_source_key_standing(
    standing: RangerPublicationSourceKeyStanding,
    source: RangerExternalPublicationReceipt | RangerPublicationRetrievalAudit,
    authority_events: Iterable[RangerPublicationKeyAuthorityEvent],
    *,
    authority_public_key_hex: str,
    expected_publication_scope_id: str,
    expected_publisher_id: str,
    expected_custodian_id: str,
    expected_authority_id: str,
    expected_authority_signing_key_id: str,
) -> RangerPublicationSourceKeyStandingVerification:
    """Verify source signature plus its exact historic publisher/custodian key standing.

    A valid historical standing means only that the named source key was active in the exact
    authority-history prefix. It deliberately does not prove the source signature occurred at
    that time, nor that the key remains currently authorized in the full presented history.
    """

    history = list(authority_events)
    history_verification = RangerPublicationKeyAuthorityLedger.verify_history(
        history, authority_public_key_hex
    )
    if not history_verification.valid:
        return _standing_failure(
            f"publication-key authority history is invalid: {history_verification.reason}"
        )
    authority_key, authority_fingerprint = _public_key(authority_public_key_hex)
    if authority_key is None or authority_fingerprint is None:
        return _standing_failure("authority public key is not 32-byte Ed25519")
    configuration_error = _configured_history_error(
        history,
        publication_scope_id=expected_publication_scope_id,
        publisher_id=expected_publisher_id,
        custodian_id=expected_custodian_id,
        authority_id=expected_authority_id,
        authority_signing_key_id=expected_authority_signing_key_id,
        authority_fingerprint=authority_fingerprint,
    )
    if configuration_error is not None:
        return _standing_failure(configuration_error)
    try:
        record = RangerPublicationSourceKeyStanding.model_validate(standing.model_dump())
    except (AttributeError, ValidationError):
        return _standing_failure("publication source-key standing schema validation failed")
    if (
        record.publication_scope_id != expected_publication_scope_id
        or record.authority_id != expected_authority_id
        or record.authority_signing_key_id != expected_authority_signing_key_id
        or record.authority_public_key_fingerprint_sha256 != authority_fingerprint
    ):
        return _standing_failure("source-key standing scope or authority identity mismatch")
    if record.authority_event_count > len(history):
        return _standing_failure(
            "source-key standing names an unavailable authority-history prefix"
        )
    prefix = history[: record.authority_event_count]
    if not prefix or prefix[-1].event_digest_sha256 != record.authority_history_head_digest_sha256:
        return _standing_failure("source-key standing authority-history head mismatch")
    payload = _source_key_standing_payload_from_record(record)
    if canonical_sha256(payload) != record.standing_digest_sha256:
        return _standing_failure("source-key standing digest mismatch")
    try:
        authority_key.verify(bytes.fromhex(record.authority_signature_hex), canonicalize(payload))
    except (InvalidSignature, ValueError):
        return _standing_failure("source-key standing authority signature invalid")

    source_error = _source_binding_error(record, source)
    if source_error is not None:
        return _standing_failure(source_error)
    descriptor, matched_event = _active_descriptor(prefix, record.key_role)
    if descriptor is None or matched_event is None:
        return _standing_failure("source key was not active at the named authority-history prefix")
    if _descriptor_identity(descriptor) != (
        record.signing_key_id,
        record.public_key_fingerprint_sha256,
    ):
        return _standing_failure(
            "source key does not match the named historical authority standing"
        )
    if matched_event.authority_sequence != record.matched_authority_sequence:
        return _standing_failure("source-key standing matched authority sequence mismatch")
    signature_error = _source_signature_error(source, descriptor)
    if signature_error is not None:
        return _standing_failure(signature_error)
    current_descriptor, _ = _active_descriptor(history, record.key_role)
    currently_authorized = current_descriptor is not None and _descriptor_identity(
        current_descriptor
    ) == (record.signing_key_id, record.public_key_fingerprint_sha256)
    return RangerPublicationSourceKeyStandingVerification(
        valid=True,
        source_kind=record.source_kind,
        source_digest_sha256=record.source_digest_sha256,
        historical_authority_relative_key_standing=True,
        source_signature_valid=True,
        currently_authorized_relative_to_presented_history=currently_authorized,
        matched_authority_sequence=record.matched_authority_sequence,
        named_authority_history_head_digest_sha256=record.authority_history_head_digest_sha256,
        reason=(
            "the source signature and authority-relative key standing verify at the named history "
            "prefix; source-signature time, operational authorization, and global currentness "
            "are not proven"
            if currently_authorized
            else "the source signature and historical authority-relative key standing verify "
            "at the "
            "named history prefix, but the key is not currently authorized relative to the full "
            "presented history; source-signature time and operational authorization are not proven"
        ),
    )


def verify_publication_lifecycle_chain(
    receipts: Iterable[RangerExternalPublicationReceipt],
    standings: Iterable[RangerPublicationSourceKeyStanding],
    authority_events: Iterable[RangerPublicationKeyAuthorityEvent],
    *,
    authority_public_key_hex: str,
    expected_publication_scope_id: str,
    expected_publisher_id: str,
    expected_custodian_id: str,
    expected_authority_id: str,
    expected_authority_signing_key_id: str,
    expected_registry_id: str,
    expected_registry_signing_key_id: str,
    expected_latest_publication_digest_sha256: str,
) -> RangerPublicationLifecycleChainVerification:
    """Verify a publication chain whose publisher key may have changed over time."""

    chain = list(receipts)
    standing_records = list(standings)
    if not chain:
        return _chain_failure(0, "publication receipt chain is empty")
    if len(chain) != len(standing_records):
        return _chain_failure(
            0, "each publication receipt requires exactly one source-key standing"
        )
    history = list(authority_events)
    seen_ids: set[str] = set()
    seen_bindings: set[tuple[str, str, str]] = set()
    previous: RangerExternalPublicationReceipt | None = None
    all_current = True
    for index, (unvalidated, standing) in enumerate(
        zip(chain, standing_records, strict=True), start=1
    ):
        try:
            receipt = RangerExternalPublicationReceipt.model_validate(unvalidated.model_dump())
        except (AttributeError, ValidationError):
            return _chain_failure(
                index - 1, "external publication receipt schema validation failed"
            )
        expected_previous = _ZERO_DIGEST if previous is None else previous.publication_digest_sha256
        if receipt.publication_sequence != index:
            return _chain_failure(index - 1, "external publication sequence is not contiguous")
        if receipt.previous_publication_digest_sha256 != expected_previous:
            return _chain_failure(index - 1, "external publication predecessor digest mismatch")
        if receipt.publisher_id != expected_publisher_id:
            return _chain_failure(
                index - 1, "external publisher identity does not match configuration"
            )
        if (
            receipt.registry_id != expected_registry_id
            or receipt.registry_signing_key_id != expected_registry_signing_key_id
        ):
            return _chain_failure(
                index - 1, "published registry identity does not match configuration"
            )
        if receipt.publication_id in seen_ids:
            return _chain_failure(index - 1, "duplicate external publication_id")
        binding = (
            receipt.subject_kind.value,
            receipt.subject_digest_sha256,
            receipt.time_attestation_digest_sha256,
        )
        if binding in seen_bindings:
            return _chain_failure(index - 1, "duplicate external publication binding")
        if previous is not None and receipt.published_at_utc <= previous.published_at_utc:
            return _chain_failure(index - 1, "external publication receipt time did not advance")
        source_verification = verify_publication_source_key_standing(
            standing,
            receipt,
            history,
            authority_public_key_hex=authority_public_key_hex,
            expected_publication_scope_id=expected_publication_scope_id,
            expected_publisher_id=expected_publisher_id,
            expected_custodian_id=expected_custodian_id,
            expected_authority_id=expected_authority_id,
            expected_authority_signing_key_id=expected_authority_signing_key_id,
        )
        if not source_verification.valid:
            return _chain_failure(
                index - 1,
                f"publication receipt source-key standing is invalid: {source_verification.reason}",
            )
        if (
            source_verification.source_kind
            is not RangerPublicationKeySourceKind.EXTERNAL_PUBLICATION_RECEIPT
        ):
            return _chain_failure(
                index - 1, "publication receipt standing has the wrong source kind"
            )
        all_current = (
            all_current and source_verification.currently_authorized_relative_to_presented_history
        )
        seen_ids.add(receipt.publication_id)
        seen_bindings.add(binding)
        previous = receipt
    latest = chain[-1]
    if latest.publication_digest_sha256 != expected_latest_publication_digest_sha256:
        return _chain_failure(
            len(chain), "presented publication chain does not match expected head"
        )
    return RangerPublicationLifecycleChainVerification(
        valid=True,
        receipt_count=len(chain),
        latest_publication_digest_sha256=latest.publication_digest_sha256,
        historical_publisher_key_standing_proven=True,
        all_publisher_keys_currently_authorized_relative_to_presented_history=all_current,
        matches_expected_publication_head=True,
        reason=(
            "publication signatures, append-only linkage, and authority-relative historical "
            "publisher-key standings verify through the expected head; one or more historical keys "
            "may no longer be currently authorized, and source-signature time, WORM custody, "
            "organizational independence, global currentness, truth, and outcome are not proven"
        ),
    )


def _source_role(source_kind: RangerPublicationKeySourceKind) -> RangerPublicationKeyRole:
    return (
        RangerPublicationKeyRole.PUBLISHER
        if source_kind is RangerPublicationKeySourceKind.EXTERNAL_PUBLICATION_RECEIPT
        else RangerPublicationKeyRole.CUSTODIAN
    )


def _request_proof_error(request: RangerPublicationKeyBindingRequest) -> str | None:
    if request.intent.event_kind is RangerPublicationKeyEventKind.REVOKE:
        return None
    payload = publication_key_binding_intent_bytes(request.intent)
    proofs: list[tuple[RangerPublicationSigningKeyDescriptor, str | None, str]] = [
        (request.intent.subject_key, request.subject_key_proof_signature_hex, "subject-key proof")
    ]
    if request.intent.replacement_key is not None:
        proofs.append(
            (
                request.intent.replacement_key,
                request.replacement_key_proof_signature_hex,
                "replacement-key proof",
            )
        )
    for descriptor, signature_hex, label in proofs:
        if signature_hex is None:
            return f"{label} is missing"
        try:
            key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(descriptor.public_key_hex))
            key.verify(bytes.fromhex(signature_hex), payload)
        except (InvalidSignature, ValueError):
            return f"{label} is invalid"
    return None


def _request_transition_error(
    events: list[RangerPublicationKeyAuthorityEvent],
    request: RangerPublicationKeyBindingRequest,
) -> str | None:
    intent = request.intent
    role_events = [event for event in events if event.request.intent.key_role is intent.key_role]
    if not role_events:
        if intent.event_kind is not RangerPublicationKeyEventKind.ENROLL:
            return "each publication-key role history must begin with enrollment"
        return None
    if intent.event_kind is RangerPublicationKeyEventKind.ENROLL:
        return "publication-key role history can contain only one enrollment"
    current, _ = _active_descriptor(role_events, intent.key_role)
    if current is None:
        return "revoked publication-key role cannot accept another transition"
    if intent.subject_key != current:
        return "publication-key transition subject does not match the current active key"
    return None


def _new_key_reuse_error(
    events: list[RangerPublicationKeyAuthorityEvent],
    request: RangerPublicationKeyBindingRequest,
) -> str | None:
    incoming = _new_descriptor(request.intent)
    if incoming is None:
        return None
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
    if incoming.signing_key_id in used_key_ids:
        return "publication-key lifecycle cannot reuse a previously enrolled key identifier"
    if incoming.public_key_fingerprint_sha256 in used_fingerprints:
        return "publication-key lifecycle cannot reuse a previously enrolled public key"
    return None


def _request_descriptors(
    request: RangerPublicationKeyBindingRequest,
) -> tuple[RangerPublicationSigningKeyDescriptor, ...]:
    replacement = request.intent.replacement_key
    return (
        (request.intent.subject_key,)
        if replacement is None
        else (request.intent.subject_key, replacement)
    )


def _new_descriptor(
    intent: RangerPublicationKeyBindingIntent,
) -> RangerPublicationSigningKeyDescriptor | None:
    if intent.event_kind is RangerPublicationKeyEventKind.ENROLL:
        return intent.subject_key
    if intent.event_kind is RangerPublicationKeyEventKind.ROTATE:
        return intent.replacement_key
    return None


def _active_descriptor(
    events: list[RangerPublicationKeyAuthorityEvent],
    role: RangerPublicationKeyRole,
) -> tuple[RangerPublicationSigningKeyDescriptor | None, RangerPublicationKeyAuthorityEvent | None]:
    role_events = [event for event in events if event.request.intent.key_role is role]
    if not role_events:
        return None, None
    latest = role_events[-1]
    intent = latest.request.intent
    if intent.event_kind is RangerPublicationKeyEventKind.REVOKE:
        return None, latest
    return (
        intent.subject_key if intent.replacement_key is None else intent.replacement_key
    ), latest


def _descriptor_identity(
    descriptor: RangerPublicationSigningKeyDescriptor,
) -> tuple[str, str]:
    return descriptor.signing_key_id, descriptor.public_key_fingerprint_sha256


def _authority_event_payload_from_record(
    event: RangerPublicationKeyAuthorityEvent,
) -> dict[str, Any]:
    return _authority_event_payload(
        authority_sequence=event.authority_sequence,
        previous_event_digest_sha256=event.previous_event_digest_sha256,
        request=event.request,
        authority_id=event.authority_id,
        authority_signing_key_id=event.authority_signing_key_id,
        authority_public_key_fingerprint_sha256=event.authority_public_key_fingerprint_sha256,
    )


def _authority_event_payload(
    *,
    authority_sequence: int,
    previous_event_digest_sha256: str,
    request: RangerPublicationKeyBindingRequest,
    authority_id: str,
    authority_signing_key_id: str,
    authority_public_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "ets.ranger.publication-key-authority-event.v1",
        "authority_sequence": authority_sequence,
        "previous_event_digest_sha256": previous_event_digest_sha256,
        "request": request.model_dump(mode="json"),
        "authority_id": authority_id,
        "authority_signing_key_id": authority_signing_key_id,
        "authority_public_key_fingerprint_sha256": authority_public_key_fingerprint_sha256,
        "signing_algorithm": "ed25519",
        "storage_profile": "sqlite-wal-full-software-reference",
        "operational_authorization_proven": False,
        "authority_administrative_independence_proven": False,
        "hardware_identity_proven": False,
        "trusted_time_proven": False,
        "globally_current_history_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "authority_relative_publication_key_standing_no_global_time_or_operational_claim"
        ),
    }


def _source_key_standing_payload_from_record(
    standing: RangerPublicationSourceKeyStanding,
) -> dict[str, Any]:
    return _source_key_standing_payload(
        standing_id=standing.standing_id,
        source_kind=standing.source_kind,
        source_digest_sha256=standing.source_digest_sha256,
        key_role=standing.key_role,
        publication_scope_id=standing.publication_scope_id,
        principal_id=standing.principal_id,
        signing_key_id=standing.signing_key_id,
        public_key_fingerprint_sha256=standing.public_key_fingerprint_sha256,
        authority_event_count=standing.authority_event_count,
        authority_history_head_digest_sha256=standing.authority_history_head_digest_sha256,
        matched_authority_sequence=standing.matched_authority_sequence,
        authority_id=standing.authority_id,
        authority_signing_key_id=standing.authority_signing_key_id,
        authority_public_key_fingerprint_sha256=standing.authority_public_key_fingerprint_sha256,
    )


def _source_key_standing_payload(
    *,
    standing_id: str,
    source_kind: RangerPublicationKeySourceKind,
    source_digest_sha256: str,
    key_role: RangerPublicationKeyRole,
    publication_scope_id: str,
    principal_id: str,
    signing_key_id: str,
    public_key_fingerprint_sha256: str,
    authority_event_count: int,
    authority_history_head_digest_sha256: str,
    matched_authority_sequence: int,
    authority_id: str,
    authority_signing_key_id: str,
    authority_public_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "ets.ranger.publication-source-key-standing.v1",
        "standing_id": standing_id,
        "source_kind": source_kind.value,
        "source_digest_sha256": source_digest_sha256,
        "key_role": key_role.value,
        "publication_scope_id": publication_scope_id,
        "principal_id": principal_id,
        "signing_key_id": signing_key_id,
        "public_key_fingerprint_sha256": public_key_fingerprint_sha256,
        "authority_event_count": authority_event_count,
        "authority_history_head_digest_sha256": authority_history_head_digest_sha256,
        "matched_authority_sequence": matched_authority_sequence,
        "authority_id": authority_id,
        "authority_signing_key_id": authority_signing_key_id,
        "authority_public_key_fingerprint_sha256": authority_public_key_fingerprint_sha256,
        "signing_algorithm": "ed25519",
        "historical_key_standing_at_named_history_prefix": True,
        "source_signature_time_proven": False,
        "currently_authorized_proven": False,
        "operational_authorization_proven": False,
        "globally_current_history_proven": False,
        "trusted_time_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "historical_publication_key_standing_no_source_time_global_currentness_or_truth_claim"
        ),
    }


def _configured_history_error(
    history: list[RangerPublicationKeyAuthorityEvent],
    *,
    publication_scope_id: str,
    publisher_id: str,
    custodian_id: str,
    authority_id: str,
    authority_signing_key_id: str,
    authority_fingerprint: str,
) -> str | None:
    if len({publisher_id, custodian_id, authority_id}) != 3:
        return "configured publisher, custodian, and authority identities are not distinct"
    expected_principal = {
        RangerPublicationKeyRole.PUBLISHER: publisher_id,
        RangerPublicationKeyRole.CUSTODIAN: custodian_id,
    }
    for event in history:
        intent = event.request.intent
        if (
            intent.publication_scope_id != publication_scope_id
            or intent.principal_id != expected_principal[intent.key_role]
            or event.authority_id != authority_id
            or event.authority_signing_key_id != authority_signing_key_id
            or event.authority_public_key_fingerprint_sha256 != authority_fingerprint
        ):
            return "publication-key authority history configuration mismatch"
    return None


def _source_binding_error(
    standing: RangerPublicationSourceKeyStanding,
    source: RangerExternalPublicationReceipt | RangerPublicationRetrievalAudit,
) -> str | None:
    if isinstance(source, RangerExternalPublicationReceipt):
        source_kind = RangerPublicationKeySourceKind.EXTERNAL_PUBLICATION_RECEIPT
        source_digest = source.publication_digest_sha256
        principal_id = source.publisher_id
        signing_key_id = source.publisher_signing_key_id
        fingerprint = source.publisher_public_key_fingerprint_sha256
    elif isinstance(source, RangerPublicationRetrievalAudit):
        source_kind = RangerPublicationKeySourceKind.PUBLICATION_RETRIEVAL_AUDIT
        source_digest = source.audit_digest_sha256
        principal_id = source.custodian_id
        signing_key_id = source.custodian_signing_key_id
        fingerprint = source.custodian_public_key_fingerprint_sha256
    else:
        return "source record is not a supported strict publication record"
    if (
        standing.source_kind is not source_kind
        or standing.source_digest_sha256 != source_digest
        or standing.key_role is not _source_role(source_kind)
        or standing.principal_id != principal_id
        or standing.signing_key_id != signing_key_id
        or standing.public_key_fingerprint_sha256 != fingerprint
    ):
        return "source record does not match its signed key-standing binding"
    return None


def _source_signature_error(
    source: RangerExternalPublicationReceipt | RangerPublicationRetrievalAudit,
    descriptor: RangerPublicationSigningKeyDescriptor,
) -> str | None:
    if isinstance(source, RangerExternalPublicationReceipt):
        payload = external_publication_receipt_signing_payload(source)
        if canonical_sha256(payload) != source.publication_digest_sha256:
            return "external publication digest mismatch"
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(descriptor.public_key_hex)).verify(
                bytes.fromhex(source.publisher_signature_hex), canonicalize(payload)
            )
        except (InvalidSignature, ValueError):
            return "external publication signature is invalid"
        return None
    audit_verification = verify_publication_retrieval_audit(
        source,
        custodian_public_key_hex=descriptor.public_key_hex,
        expected_custodian_id=source.custodian_id,
        expected_custodian_signing_key_id=source.custodian_signing_key_id,
        expected_publication_head_digest_sha256=source.expected_publication_head_digest_sha256,
    )
    if not audit_verification.valid:
        return f"publication retrieval audit is invalid: {audit_verification.reason}"
    payload = publication_retrieval_audit_signing_payload(source)
    if canonical_sha256(payload) != source.audit_digest_sha256:
        return "publication retrieval audit digest mismatch"
    return None


def _public_key(value: str) -> tuple[Ed25519PublicKey | None, str | None]:
    try:
        key_bytes = bytes.fromhex(value)
        if len(key_bytes) != 32:
            return None, None
        return Ed25519PublicKey.from_public_bytes(key_bytes), hashlib.sha256(key_bytes).hexdigest()
    except ValueError:
        return None, None


def _history_failure(count: int, reason: str) -> RangerPublicationKeyAuthorityVerification:
    return RangerPublicationKeyAuthorityVerification(valid=False, event_count=count, reason=reason)


def _standing_failure(reason: str) -> RangerPublicationSourceKeyStandingVerification:
    return RangerPublicationSourceKeyStandingVerification(valid=False, reason=reason)


def _chain_failure(count: int, reason: str) -> RangerPublicationLifecycleChainVerification:
    return RangerPublicationLifecycleChainVerification(
        valid=False, receipt_count=count, reason=reason
    )
