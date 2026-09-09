"""External publication receipts for Ranger retained latest-head evidence.

The software reference models a separately configured publisher that signs an append-only
receipt chain over exact trusted-time-attested Ranger receipt digests.  A verifier must compare
the presented chain with an externally observed publication head.  The result proves only the
configured publisher signature and head match; continued retention, organizational independence,
global currentness, semantic truth, and physical outcome remain separate claims.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Literal, Self

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.authority_checkpoint import RangerAuthorityBoundCheckpoint
from ets.ranger.authority_head import RangerRetainedAuthorityHead
from ets.ranger.governance import RangerGovernanceSubjectKind, RangerTrustedTimeAttestation
from ets.ranger.timed_retained_receipts import (
    RangerTimeAttestedReceiptVerification,
    verify_time_attested_authority_checkpoint,
    verify_time_attested_authority_head,
)

_ZERO_DIGEST = "0" * 64
_SUPPORTED_SUBJECTS = {
    RangerGovernanceSubjectKind.RETAINED_AUTHORITY_HEAD,
    RangerGovernanceSubjectKind.AUTHORITY_BOUND_CHECKPOINT,
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerExternalPublicationError(RuntimeError):
    """Raised when a publication receipt cannot be built safely."""


class RangerExternalPublicationReceipt(StrictModel):
    """Publisher-signed binding to one exact time-attested retained receipt."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": "https://lanternprotocol.org/schemas/ets/ranger/external-publication-receipt/v1"
        },
    )

    schema_version: Literal["ets.ranger.external-publication-receipt.v1"] = (
        "ets.ranger.external-publication-receipt.v1"
    )
    publication_id: str = Field(min_length=1, max_length=256)
    publication_sequence: int = Field(ge=1, le=2**63 - 1)
    previous_publication_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    subject_kind: RangerGovernanceSubjectKind
    subject_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    time_attestation_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    registry_id: str = Field(min_length=1, max_length=160)
    registry_signing_key_id: str = Field(min_length=1, max_length=256)
    published_at_utc: datetime
    publisher_id: str = Field(min_length=1, max_length=160)
    publisher_signing_key_id: str = Field(min_length=1, max_length=256)
    publisher_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    publication_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    publisher_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    configured_external_publisher_receipt: Literal[True] = True
    continued_external_custody_proven: Literal[False] = False
    publisher_organizational_independence_proven: Literal[False] = False
    publisher_clock_trusted: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_external_publisher_receipt_no_continued_custody_independence_or_truth_claim"
    ] = "configured_external_publisher_receipt_no_continued_custody_independence_or_truth_claim"

    @field_validator("subject_kind")
    @classmethod
    def require_retained_subject(
        cls, value: RangerGovernanceSubjectKind
    ) -> RangerGovernanceSubjectKind:
        if value not in _SUPPORTED_SUBJECTS:
            raise ValueError("external publication subject must be a retained Ranger receipt")
        return value

    @field_validator("published_at_utc")
    @classmethod
    def normalize_published_at(cls, value: datetime) -> datetime:
        return _require_aware_utc(value)

    @model_validator(mode="after")
    def require_predecessor(self) -> Self:
        if self.publication_sequence == 1:
            if self.previous_publication_digest_sha256 != _ZERO_DIGEST:
                raise ValueError("publication genesis must use the zero predecessor digest")
        elif self.previous_publication_digest_sha256 == _ZERO_DIGEST:
            raise ValueError("non-genesis publication requires a predecessor digest")
        return self


class RangerExternalPublicationChainVerification(StrictModel):
    valid: bool
    receipt_count: int = Field(ge=0)
    latest_publication_sequence: int | None = Field(default=None, ge=1)
    latest_publication_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    latest_subject_kind: RangerGovernanceSubjectKind | None = None
    latest_subject_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    configured_external_publisher_receipts_proven: bool = False
    matches_expected_publication_head: bool = False
    freshness_relative_to_expected_head: bool = False
    reason: str


class RangerExternallyPublishedReceiptVerification(StrictModel):
    valid: bool
    subject_kind: RangerGovernanceSubjectKind | None = None
    subject_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    time_attestation_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    publication_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    publication_sequence: int | None = Field(default=None, ge=1)
    publisher_id: str | None = None
    publisher_signing_key_id: str | None = None
    time_attested_retained_receipt_proven: bool = False
    configured_external_publisher_receipt_proven: bool = False
    publisher_key_distinct_from_registry_proven: bool = False
    matches_expected_publication_head: bool = False
    freshness_relative_to_expected_head: bool = False
    continued_external_custody_proven: Literal[False] = False
    publisher_organizational_independence_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    operational_device_authorization_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


class RangerExternalPublisher:
    """In-memory software reference for an externally hosted publication adapter."""

    provider_name = "software-reference-external-publisher"
    continued_external_custody_proven = False
    publisher_organizational_independence_proven = False

    def __init__(
        self,
        *,
        publisher_id: str,
        publisher_signing_key_id: str,
        publisher_private_key_hex: str,
        expected_registry_id: str,
        expected_registry_signing_key_id: str,
    ) -> None:
        self.publisher_id = publisher_id
        self.publisher_signing_key_id = publisher_signing_key_id
        self.expected_registry_id = expected_registry_id
        self.expected_registry_signing_key_id = expected_registry_signing_key_id
        self._private_key = _private_key(publisher_private_key_hex)
        self._receipts: list[RangerExternalPublicationReceipt] = []

    @property
    def publisher_public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    @property
    def latest_publication_digest_sha256(self) -> str | None:
        return self._receipts[-1].publication_digest_sha256 if self._receipts else None

    def publish(
        self,
        *,
        publication_id: str,
        subject_kind: RangerGovernanceSubjectKind,
        subject_digest_sha256: str,
        time_attestation_digest_sha256: str,
        registry_id: str,
        registry_signing_key_id: str,
        published_at_utc: datetime,
    ) -> RangerExternalPublicationReceipt:
        """Append a separately signed receipt for exact retained and time-attestation digests."""

        if (
            registry_id != self.expected_registry_id
            or registry_signing_key_id != self.expected_registry_signing_key_id
        ):
            raise RangerExternalPublicationError(
                "publication registry identity does not match publisher configuration"
            )
        if subject_kind not in _SUPPORTED_SUBJECTS:
            raise RangerExternalPublicationError(
                "external publication subject must be a retained Ranger receipt"
            )
        if any(item.publication_id == publication_id for item in self._receipts):
            raise RangerExternalPublicationError("publication_id has already been used")
        binding = (subject_kind, subject_digest_sha256, time_attestation_digest_sha256)
        if any(
            (item.subject_kind, item.subject_digest_sha256, item.time_attestation_digest_sha256)
            == binding
            for item in self._receipts
        ):
            raise RangerExternalPublicationError(
                "retained receipt binding has already been published"
            )

        published_at = _require_aware_utc(published_at_utc)
        latest = self._receipts[-1] if self._receipts else None
        if latest is not None and published_at <= latest.published_at_utc:
            raise RangerExternalPublicationError("publisher receipt time must advance")
        public_bytes = self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        payload = _publication_payload(
            publication_id=publication_id,
            publication_sequence=len(self._receipts) + 1,
            previous_publication_digest_sha256=(
                _ZERO_DIGEST if latest is None else latest.publication_digest_sha256
            ),
            subject_kind=subject_kind,
            subject_digest_sha256=subject_digest_sha256,
            time_attestation_digest_sha256=time_attestation_digest_sha256,
            registry_id=registry_id,
            registry_signing_key_id=registry_signing_key_id,
            published_at_utc=published_at,
            publisher_id=self.publisher_id,
            publisher_signing_key_id=self.publisher_signing_key_id,
            publisher_public_key_fingerprint_sha256=hashlib.sha256(public_bytes).hexdigest(),
        )
        digest = canonical_sha256(payload)
        try:
            receipt = RangerExternalPublicationReceipt.model_validate(
                {
                    **payload,
                    "subject_kind": subject_kind,
                    "published_at_utc": published_at,
                    "publication_digest_sha256": digest,
                    "publisher_signature_hex": self._private_key.sign(canonicalize(payload)).hex(),
                }
            )
        except ValidationError as exc:
            raise RangerExternalPublicationError("invalid external publication fields") from exc
        self._receipts.append(receipt)
        return receipt

    def list_receipts(self) -> list[RangerExternalPublicationReceipt]:
        return list(self._receipts)


def verify_external_publication_chain(
    receipts: Iterable[RangerExternalPublicationReceipt],
    *,
    publisher_public_key_hex: str,
    expected_publisher_id: str,
    expected_publisher_signing_key_id: str,
    expected_registry_id: str,
    expected_registry_signing_key_id: str,
    expected_latest_publication_digest_sha256: str,
) -> RangerExternalPublicationChainVerification:
    """Verify the complete presented publication chain against an externally observed head."""

    chain = list(receipts)
    if not chain:
        return _chain_failure(0, "external publication receipt chain is empty")
    public_key, fingerprint = _public_key(publisher_public_key_hex)
    if public_key is None or fingerprint is None:
        return _chain_failure(len(chain), "publisher public key is not 32-byte Ed25519")

    seen_ids: set[str] = set()
    seen_bindings: set[tuple[RangerGovernanceSubjectKind, str, str]] = set()
    previous: RangerExternalPublicationReceipt | None = None
    for index, unvalidated in enumerate(chain, start=1):
        try:
            receipt = RangerExternalPublicationReceipt.model_validate(unvalidated.model_dump())
        except (AttributeError, ValidationError):
            return _chain_failure(index - 1, "external publication schema validation failed")
        expected_previous = _ZERO_DIGEST if previous is None else previous.publication_digest_sha256
        if receipt.publication_sequence != index:
            return _chain_failure(index - 1, "external publication sequence is not contiguous")
        if receipt.previous_publication_digest_sha256 != expected_previous:
            return _chain_failure(index - 1, "external publication predecessor digest mismatch")
        if (
            receipt.publisher_id != expected_publisher_id
            or receipt.publisher_signing_key_id != expected_publisher_signing_key_id
        ):
            return _chain_failure(
                index - 1,
                "external publisher identity does not match configuration",
            )
        if (
            receipt.registry_id != expected_registry_id
            or receipt.registry_signing_key_id != expected_registry_signing_key_id
        ):
            return _chain_failure(
                index - 1,
                "published registry identity does not match configuration",
            )
        if receipt.publisher_public_key_fingerprint_sha256 != fingerprint:
            return _chain_failure(index - 1, "publisher public key fingerprint mismatch")
        if receipt.publication_id in seen_ids:
            return _chain_failure(index - 1, "duplicate external publication_id")
        binding = (
            receipt.subject_kind,
            receipt.subject_digest_sha256,
            receipt.time_attestation_digest_sha256,
        )
        if binding in seen_bindings:
            return _chain_failure(index - 1, "duplicate external publication binding")
        if previous is not None and receipt.published_at_utc <= previous.published_at_utc:
            return _chain_failure(index - 1, "external publication receipt time did not advance")
        payload = _publication_payload_from_record(receipt)
        if canonical_sha256(payload) != receipt.publication_digest_sha256:
            return _chain_failure(index - 1, "external publication digest mismatch")
        try:
            public_key.verify(bytes.fromhex(receipt.publisher_signature_hex), canonicalize(payload))
        except (InvalidSignature, ValueError):
            return _chain_failure(index - 1, "external publisher signature invalid")
        seen_ids.add(receipt.publication_id)
        seen_bindings.add(binding)
        previous = receipt

    latest = chain[-1]
    if latest.publication_digest_sha256 != expected_latest_publication_digest_sha256:
        return _chain_failure(
            len(chain),
            "presented publication chain does not match expected head",
        )
    return RangerExternalPublicationChainVerification(
        valid=True,
        receipt_count=len(chain),
        latest_publication_sequence=latest.publication_sequence,
        latest_publication_digest_sha256=latest.publication_digest_sha256,
        latest_subject_kind=latest.subject_kind,
        latest_subject_digest_sha256=latest.subject_digest_sha256,
        configured_external_publisher_receipts_proven=True,
        matches_expected_publication_head=True,
        freshness_relative_to_expected_head=True,
        reason=(
            "configured external-publisher signatures and append-only linkage verify through the "
            "expected publication head; continued custody, organizational independence, and "
            "global latest-state currentness are not proven"
        ),
    )


def verify_externally_published_authority_head(
    checkpoints: Iterable[RangerRetainedAuthorityHead],
    time_attestation: RangerTrustedTimeAttestation,
    publication_receipts: Iterable[RangerExternalPublicationReceipt],
    *,
    registry_public_key_hex: str,
    expected_registry_id: str,
    expected_registry_signing_key_id: str,
    time_public_key_hex: str,
    expected_time_source_id: str,
    expected_time_signing_key_id: str,
    publisher_public_key_hex: str,
    expected_publisher_id: str,
    expected_publisher_signing_key_id: str,
    expected_latest_publication_digest_sha256: str,
) -> RangerExternallyPublishedReceiptVerification:
    """Compose authority-head, trusted-time, and external-publication verification."""

    retained = list(checkpoints)
    timed = verify_time_attested_authority_head(
        retained,
        time_attestation,
        registry_public_key_hex=registry_public_key_hex,
        expected_registry_id=expected_registry_id,
        expected_registry_signing_key_id=expected_registry_signing_key_id,
        time_public_key_hex=time_public_key_hex,
        expected_time_source_id=expected_time_source_id,
        expected_time_signing_key_id=expected_time_signing_key_id,
    )
    return _verify_composed_publication(
        timed,
        publication_receipts,
        registry_public_key_hex=registry_public_key_hex,
        expected_registry_id=expected_registry_id,
        expected_registry_signing_key_id=expected_registry_signing_key_id,
        publisher_public_key_hex=publisher_public_key_hex,
        expected_publisher_id=expected_publisher_id,
        expected_publisher_signing_key_id=expected_publisher_signing_key_id,
        expected_latest_publication_digest_sha256=expected_latest_publication_digest_sha256,
    )


def verify_externally_published_authority_checkpoint(
    checkpoints: Iterable[RangerAuthorityBoundCheckpoint],
    time_attestation: RangerTrustedTimeAttestation,
    publication_receipts: Iterable[RangerExternalPublicationReceipt],
    *,
    registry_public_key_hex: str,
    expected_registry_id: str,
    expected_registry_signing_key_id: str,
    time_public_key_hex: str,
    expected_time_source_id: str,
    expected_time_signing_key_id: str,
    publisher_public_key_hex: str,
    expected_publisher_id: str,
    expected_publisher_signing_key_id: str,
    expected_latest_publication_digest_sha256: str,
) -> RangerExternallyPublishedReceiptVerification:
    """Compose authority-bound custody, trusted-time, and publication verification."""

    retained = list(checkpoints)
    timed = verify_time_attested_authority_checkpoint(
        retained,
        time_attestation,
        registry_public_key_hex=registry_public_key_hex,
        expected_registry_id=expected_registry_id,
        expected_registry_signing_key_id=expected_registry_signing_key_id,
        time_public_key_hex=time_public_key_hex,
        expected_time_source_id=expected_time_source_id,
        expected_time_signing_key_id=expected_time_signing_key_id,
    )
    return _verify_composed_publication(
        timed,
        publication_receipts,
        registry_public_key_hex=registry_public_key_hex,
        expected_registry_id=expected_registry_id,
        expected_registry_signing_key_id=expected_registry_signing_key_id,
        publisher_public_key_hex=publisher_public_key_hex,
        expected_publisher_id=expected_publisher_id,
        expected_publisher_signing_key_id=expected_publisher_signing_key_id,
        expected_latest_publication_digest_sha256=expected_latest_publication_digest_sha256,
    )


def _verify_composed_publication(
    timed: RangerTimeAttestedReceiptVerification,
    publication_receipts: Iterable[RangerExternalPublicationReceipt],
    *,
    registry_public_key_hex: str,
    expected_registry_id: str,
    expected_registry_signing_key_id: str,
    publisher_public_key_hex: str,
    expected_publisher_id: str,
    expected_publisher_signing_key_id: str,
    expected_latest_publication_digest_sha256: str,
) -> RangerExternallyPublishedReceiptVerification:
    if not timed.valid:
        return _publication_failure(f"time-attested retained receipt is invalid: {timed.reason}")
    if (
        timed.receipt_kind is None
        or timed.receipt_digest_sha256 is None
        or timed.time_attestation_digest_sha256 is None
    ):
        return _publication_failure("time-attested verification omitted required receipt bindings")

    registry_key_bytes = _raw_public_key_bytes(registry_public_key_hex)
    publisher_key_bytes = _raw_public_key_bytes(publisher_public_key_hex)
    if registry_key_bytes is None or publisher_key_bytes is None:
        return _publication_failure("registry or publisher public key is not 32-byte Ed25519")
    if (
        expected_publisher_id == expected_registry_id
        or expected_publisher_signing_key_id == expected_registry_signing_key_id
        or publisher_key_bytes == registry_key_bytes
    ):
        return _publication_failure(
            "external publisher identity and key must be distinct from the receipt registry"
        )

    chain = list(publication_receipts)
    chain_verification = verify_external_publication_chain(
        chain,
        publisher_public_key_hex=publisher_public_key_hex,
        expected_publisher_id=expected_publisher_id,
        expected_publisher_signing_key_id=expected_publisher_signing_key_id,
        expected_registry_id=expected_registry_id,
        expected_registry_signing_key_id=expected_registry_signing_key_id,
        expected_latest_publication_digest_sha256=expected_latest_publication_digest_sha256,
    )
    if not chain_verification.valid:
        return _publication_failure(chain_verification.reason)
    latest = chain[-1]
    if (
        latest.subject_kind != timed.receipt_kind
        or latest.subject_digest_sha256 != timed.receipt_digest_sha256
        or latest.time_attestation_digest_sha256 != timed.time_attestation_digest_sha256
    ):
        return _publication_failure(
            "latest external publication does not bind the verified retained receipt "
            "and time evidence"
        )

    return RangerExternallyPublishedReceiptVerification(
        valid=True,
        subject_kind=timed.receipt_kind,
        subject_digest_sha256=timed.receipt_digest_sha256,
        time_attestation_digest_sha256=timed.time_attestation_digest_sha256,
        publication_digest_sha256=latest.publication_digest_sha256,
        publication_sequence=latest.publication_sequence,
        publisher_id=latest.publisher_id,
        publisher_signing_key_id=latest.publisher_signing_key_id,
        time_attested_retained_receipt_proven=True,
        configured_external_publisher_receipt_proven=True,
        publisher_key_distinct_from_registry_proven=True,
        matches_expected_publication_head=True,
        freshness_relative_to_expected_head=True,
        reason=(
            "the configured external publisher signed the exact trusted-time-attested retained "
            "receipt and the append-only chain matches the expected publication head; continued "
            "custody, organizational independence, global currentness, truth, and outcome remain "
            "unproven"
        ),
    )


def _publication_payload(
    *,
    publication_id: str,
    publication_sequence: int,
    previous_publication_digest_sha256: str,
    subject_kind: RangerGovernanceSubjectKind,
    subject_digest_sha256: str,
    time_attestation_digest_sha256: str,
    registry_id: str,
    registry_signing_key_id: str,
    published_at_utc: datetime,
    publisher_id: str,
    publisher_signing_key_id: str,
    publisher_public_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "ets.ranger.external-publication-receipt.v1",
        "publication_id": publication_id,
        "publication_sequence": publication_sequence,
        "previous_publication_digest_sha256": previous_publication_digest_sha256,
        "subject_kind": subject_kind.value,
        "subject_digest_sha256": subject_digest_sha256,
        "time_attestation_digest_sha256": time_attestation_digest_sha256,
        "registry_id": registry_id,
        "registry_signing_key_id": registry_signing_key_id,
        "published_at_utc": published_at_utc.isoformat().replace("+00:00", "Z"),
        "publisher_id": publisher_id,
        "publisher_signing_key_id": publisher_signing_key_id,
        "publisher_public_key_fingerprint_sha256": publisher_public_key_fingerprint_sha256,
        "signing_algorithm": "ed25519",
        "configured_external_publisher_receipt": True,
        "continued_external_custody_proven": False,
        "publisher_organizational_independence_proven": False,
        "publisher_clock_trusted": False,
        "globally_current_state_proven": False,
        "complete_capture_proven": False,
        "semantic_truth_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "configured_external_publisher_receipt_no_continued_custody_independence_or_truth_claim"
        ),
    }


def _publication_payload_from_record(receipt: RangerExternalPublicationReceipt) -> dict[str, Any]:
    return _publication_payload(
        publication_id=receipt.publication_id,
        publication_sequence=receipt.publication_sequence,
        previous_publication_digest_sha256=receipt.previous_publication_digest_sha256,
        subject_kind=receipt.subject_kind,
        subject_digest_sha256=receipt.subject_digest_sha256,
        time_attestation_digest_sha256=receipt.time_attestation_digest_sha256,
        registry_id=receipt.registry_id,
        registry_signing_key_id=receipt.registry_signing_key_id,
        published_at_utc=receipt.published_at_utc,
        publisher_id=receipt.publisher_id,
        publisher_signing_key_id=receipt.publisher_signing_key_id,
        publisher_public_key_fingerprint_sha256=(receipt.publisher_public_key_fingerprint_sha256),
    )


def _private_key(value: str) -> Ed25519PrivateKey:
    try:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))
    except ValueError as exc:
        raise RangerExternalPublicationError(
            "publisher private key must be a 32-byte Ed25519 key"
        ) from exc


def _raw_public_key_bytes(value: str) -> bytes | None:
    try:
        key_bytes = bytes.fromhex(value)
        if len(key_bytes) != 32:
            return None
        Ed25519PublicKey.from_public_bytes(key_bytes)
        return key_bytes
    except ValueError:
        return None


def _public_key(value: str) -> tuple[Ed25519PublicKey | None, str | None]:
    key_bytes = _raw_public_key_bytes(value)
    if key_bytes is None:
        return None, None
    return Ed25519PublicKey.from_public_bytes(key_bytes), hashlib.sha256(key_bytes).hexdigest()


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerExternalPublicationError("publisher receipt time must be timezone-aware")
    return value.astimezone(UTC)


def _chain_failure(count: int, reason: str) -> RangerExternalPublicationChainVerification:
    return RangerExternalPublicationChainVerification(
        valid=False,
        receipt_count=count,
        reason=reason,
    )


def _publication_failure(reason: str) -> RangerExternallyPublishedReceiptVerification:
    return RangerExternallyPublishedReceiptVerification(valid=False, reason=reason)
