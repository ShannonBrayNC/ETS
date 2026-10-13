"""Signed custody acceptance for a Ranger AWS qualification evidence manifest.

The receipt authenticates one configured custodian's acceptance of an exact manifest and
verification finding for a declared retention target. It does not prove that bytes were stored,
that retention continues, that the custodian is independent, or that a clock or physical WORM
control is trustworthy.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.aws_qualification_evidence_manifest import (
    RangerAwsQualificationEvidenceManifest,
    RangerAwsQualificationEvidenceManifestVerification,
)
from ets.ranger.aws_s3_object_lock import StrictModel


class RangerAwsQualificationManifestCustodyError(RuntimeError):
    """Raised when a manifest custody receipt cannot be issued safely."""


class RangerAwsQualificationManifestCustodyReceipt(StrictModel):
    """Custodian-signed acceptance of one exact manifest for a declared target."""

    schema_version: Literal[
        "ets.ranger.aws-qualification-manifest-custody-receipt.v1"
    ] = "ets.ranger.aws-qualification-manifest-custody-receipt.v1"
    receipt_id: str = Field(min_length=1, max_length=256)
    package_id: str = Field(min_length=1, max_length=256)
    qualification_id: str = Field(min_length=1, max_length=256)
    manifest_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_verification_record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_target_id: str = Field(min_length=1, max_length=256)
    retention_requested_until_utc: datetime
    accepted_at_utc: datetime
    custodian_id: str = Field(min_length=1, max_length=160)
    custodian_signing_key_id: str = Field(min_length=1, max_length=256)
    custodian_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    receipt_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custodian_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    configured_manifest_verification_present: Literal[True] = True
    configured_custodian_acceptance_proven: Literal[True] = True
    storage_write_proven: Literal[False] = False
    continued_retention_proven: Literal[False] = False
    custodian_independence_proven: Literal[False] = False
    custodian_clock_trusted: Literal[False] = False
    physical_worm_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_custodian_acceptance_no_storage_retention_independence_clock_worm_"
        "provider_execution_or_physical_outcome_proof"
    ] = (
        "configured_custodian_acceptance_no_storage_retention_independence_clock_worm_"
        "provider_execution_or_physical_outcome_proof"
    )

    @field_validator("retention_requested_until_utc", "accepted_at_utc")
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("manifest custody receipt times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_future_retention_target(self) -> RangerAwsQualificationManifestCustodyReceipt:
        if self.retention_requested_until_utc <= self.accepted_at_utc:
            raise ValueError("retention target must extend beyond custody acceptance")
        return self


class RangerAwsQualificationManifestCustodyPolicy(StrictModel):
    """Verifier-controlled identity, target, time, and retention expectations."""

    expected_receipt_id: str = Field(min_length=1, max_length=256)
    expected_custodian_id: str = Field(min_length=1, max_length=160)
    expected_custodian_signing_key_id: str = Field(min_length=1, max_length=256)
    custodian_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_custody_target_id: str = Field(min_length=1, max_length=256)
    acceptance_window_start_utc: datetime
    acceptance_window_end_utc: datetime
    minimum_retention_until_utc: datetime

    @field_validator(
        "acceptance_window_start_utc",
        "acceptance_window_end_utc",
        "minimum_retention_until_utc",
    )
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("manifest custody policy times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_valid_window(self) -> RangerAwsQualificationManifestCustodyPolicy:
        if self.acceptance_window_start_utc > self.acceptance_window_end_utc:
            raise ValueError("custody acceptance window is inverted")
        if self.minimum_retention_until_utc <= self.acceptance_window_end_utc:
            raise ValueError("minimum retention must extend beyond the acceptance window")
        return self


class RangerAwsQualificationManifestCustodyVerification(StrictModel):
    """Offline result for a configured manifest custody acceptance."""

    valid: bool
    receipt_id: str | None = None
    manifest_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    receipt_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    manifest_self_digest_verified: bool = False
    configured_manifest_verification_present: bool = False
    exact_manifest_and_finding_bound: bool = False
    configured_custodian_signature_proven: bool = False
    configured_target_and_retention_accepted: bool = False
    storage_write_proven: Literal[False] = False
    continued_retention_proven: Literal[False] = False
    custodian_independence_proven: Literal[False] = False
    custodian_clock_trusted: Literal[False] = False
    physical_worm_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


def build_aws_qualification_manifest_custody_receipt(
    manifest: RangerAwsQualificationEvidenceManifest,
    manifest_verification: RangerAwsQualificationEvidenceManifestVerification,
    *,
    receipt_id: str,
    custody_target_id: str,
    retention_requested_until_utc: datetime,
    accepted_at_utc: datetime,
    custodian_id: str,
    custodian_signing_key_id: str,
    custodian_private_key_hex: str,
) -> RangerAwsQualificationManifestCustodyReceipt:
    """Issue a receipt only for a self-consistent manifest with a successful finding."""

    record, finding = _validated_inputs(manifest, manifest_verification)
    accepted_at = _aware_utc(accepted_at_utc)
    retention_until = _aware_utc(retention_requested_until_utc)
    if retention_until <= accepted_at:
        raise RangerAwsQualificationManifestCustodyError(
            "retention target must extend beyond custody acceptance"
        )
    private_key = _private_key(custodian_private_key_hex)
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    unsigned: dict[str, Any] = {
        "schema_version": "ets.ranger.aws-qualification-manifest-custody-receipt.v1",
        "receipt_id": receipt_id,
        "package_id": record.package_id,
        "qualification_id": record.qualification_id,
        "manifest_digest_sha256": record.manifest_digest_sha256,
        "manifest_record_digest_sha256": _record_digest(record),
        "manifest_verification_record_digest_sha256": _record_digest(finding),
        "custody_target_id": custody_target_id,
        "retention_requested_until_utc": retention_until,
        "accepted_at_utc": accepted_at,
        "custodian_id": custodian_id,
        "custodian_signing_key_id": custodian_signing_key_id,
        "custodian_public_key_fingerprint_sha256": hashlib.sha256(public_bytes).hexdigest(),
        "signing_algorithm": "ed25519",
        "configured_manifest_verification_present": True,
        "configured_custodian_acceptance_proven": True,
        "storage_write_proven": False,
        "continued_retention_proven": False,
        "custodian_independence_proven": False,
        "custodian_clock_trusted": False,
        "physical_worm_proven": False,
        "provider_execution_independently_proven": False,
        "physical_outcome_proven": False,
        "claim_boundary": (
            "configured_custodian_acceptance_no_storage_retention_independence_clock_worm_"
            "provider_execution_or_physical_outcome_proof"
        ),
    }
    try:
        candidate = RangerAwsQualificationManifestCustodyReceipt.model_validate(
            {
                **unsigned,
                "receipt_digest_sha256": "0" * 64,
                "custodian_signature_hex": "0" * 128,
            }
        )
        payload = _receipt_payload(candidate)
        return RangerAwsQualificationManifestCustodyReceipt.model_validate(
            candidate.model_copy(
                update={
                    "receipt_digest_sha256": canonical_sha256(payload),
                    "custodian_signature_hex": private_key.sign(canonicalize(payload)).hex(),
                }
            ).model_dump()
        )
    except ValidationError as exc:
        raise RangerAwsQualificationManifestCustodyError(
            "invalid manifest custody receipt fields"
        ) from exc


def verify_aws_qualification_manifest_custody_receipt(
    receipt: RangerAwsQualificationManifestCustodyReceipt,
    manifest: RangerAwsQualificationEvidenceManifest,
    manifest_verification: RangerAwsQualificationEvidenceManifestVerification,
    *,
    policy: RangerAwsQualificationManifestCustodyPolicy,
) -> RangerAwsQualificationManifestCustodyVerification:
    """Verify exact manifest/finding binding and configured custodian acceptance."""

    try:
        record = RangerAwsQualificationManifestCustodyReceipt.model_validate(
            receipt.model_dump()
        )
        evidence, finding = _validated_inputs(manifest, manifest_verification)
        configured = RangerAwsQualificationManifestCustodyPolicy.model_validate(
            policy.model_dump()
        )
    except (AttributeError, ValidationError, RangerAwsQualificationManifestCustodyError):
        return _failure("manifest custody receipt inputs are invalid")
    if (
        record.receipt_id != configured.expected_receipt_id
        or record.custodian_id != configured.expected_custodian_id
        or record.custodian_signing_key_id
        != configured.expected_custodian_signing_key_id
    ):
        return _failure("manifest custody policy identity mismatch", manifest=True)
    if record.custody_target_id != configured.expected_custody_target_id:
        return _failure("manifest custody target mismatch", manifest=True)
    if not (
        configured.acceptance_window_start_utc
        <= record.accepted_at_utc
        <= configured.acceptance_window_end_utc
    ):
        return _failure("manifest custody acceptance is outside the policy window", manifest=True)
    if record.retention_requested_until_utc < configured.minimum_retention_until_utc:
        return _failure("manifest custody retention target is shorter than policy", manifest=True)
    if (
        record.package_id != evidence.package_id
        or record.qualification_id != evidence.qualification_id
        or record.manifest_digest_sha256 != evidence.manifest_digest_sha256
        or record.manifest_record_digest_sha256 != _record_digest(evidence)
        or record.manifest_verification_record_digest_sha256 != _record_digest(finding)
    ):
        return _failure("manifest custody receipt evidence binding mismatch", manifest=True)
    public_key, fingerprint = _public_key(configured.custodian_public_key_hex)
    if public_key is None or fingerprint is None:
        return _failure("custodian public key is not 32-byte Ed25519", manifest=True, bound=True)
    if record.custodian_public_key_fingerprint_sha256 != fingerprint:
        return _failure(
            "manifest custody custodian key fingerprint mismatch",
            manifest=True,
            bound=True,
        )
    payload = _receipt_payload(record)
    if canonical_sha256(payload) != record.receipt_digest_sha256:
        return _failure("manifest custody receipt digest mismatch", manifest=True, bound=True)
    try:
        public_key.verify(bytes.fromhex(record.custodian_signature_hex), canonicalize(payload))
    except (InvalidSignature, ValueError):
        return _failure("manifest custody receipt signature invalid", manifest=True, bound=True)
    return RangerAwsQualificationManifestCustodyVerification(
        valid=True,
        receipt_id=record.receipt_id,
        manifest_digest_sha256=record.manifest_digest_sha256,
        receipt_digest_sha256=record.receipt_digest_sha256,
        manifest_self_digest_verified=True,
        configured_manifest_verification_present=True,
        exact_manifest_and_finding_bound=True,
        configured_custodian_signature_proven=True,
        configured_target_and_retention_accepted=True,
        reason=(
            "configured custodian signature accepts the exact verified manifest for the declared "
            "target and retention request; storage, continued retention, independence, clock "
            "trust, physical WORM, provider execution, and physical outcome are not proven"
        ),
    )


def _validated_inputs(
    manifest: RangerAwsQualificationEvidenceManifest,
    verification: RangerAwsQualificationEvidenceManifestVerification,
) -> tuple[
    RangerAwsQualificationEvidenceManifest,
    RangerAwsQualificationEvidenceManifestVerification,
]:
    try:
        record = RangerAwsQualificationEvidenceManifest.model_validate(manifest.model_dump())
        finding = RangerAwsQualificationEvidenceManifestVerification.model_validate(
            verification.model_dump()
        )
    except (AttributeError, ValidationError) as exc:
        raise RangerAwsQualificationManifestCustodyError(
            "manifest or verification schema is invalid"
        ) from exc
    expected_digest = canonical_sha256(
        record.model_dump(mode="json", exclude={"manifest_digest_sha256"})
    )
    if expected_digest != record.manifest_digest_sha256:
        raise RangerAwsQualificationManifestCustodyError("manifest self-digest mismatch")
    if not (
        finding.valid
        and finding.manifest_digest_verified
        and finding.complete_inventory_verified
        and finding.qualification_run_replayed
        and finding.exact_artifact_digests_verified
    ):
        raise RangerAwsQualificationManifestCustodyError(
            "successful complete manifest verification is required"
        )
    return record, finding


def _record_digest(record: StrictModel) -> str:
    return canonical_sha256(record.model_dump(mode="json"))


def _receipt_payload(receipt: RangerAwsQualificationManifestCustodyReceipt) -> dict[str, Any]:
    return receipt.model_dump(
        mode="json", exclude={"receipt_digest_sha256", "custodian_signature_hex"}
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerAwsQualificationManifestCustodyError(
            "manifest custody receipt times must be timezone-aware"
        )
    return value.astimezone(UTC)


def _private_key(value: str) -> Ed25519PrivateKey:
    try:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))
    except (ValueError, TypeError) as exc:
        raise RangerAwsQualificationManifestCustodyError(
            "custodian private key is not 32-byte Ed25519"
        ) from exc


def _public_key(value: str) -> tuple[Ed25519PublicKey | None, str | None]:
    try:
        raw = bytes.fromhex(value)
        key = Ed25519PublicKey.from_public_bytes(raw)
    except (ValueError, TypeError):
        return None, None
    return key, hashlib.sha256(raw).hexdigest()


def _failure(
    reason: str,
    *,
    manifest: bool = False,
    bound: bool = False,
) -> RangerAwsQualificationManifestCustodyVerification:
    return RangerAwsQualificationManifestCustodyVerification(
        valid=False,
        manifest_self_digest_verified=manifest,
        configured_manifest_verification_present=manifest,
        exact_manifest_and_finding_bound=bound,
        reason=reason,
    )


__all__ = [
    "RangerAwsQualificationManifestCustodyError",
    "RangerAwsQualificationManifestCustodyPolicy",
    "RangerAwsQualificationManifestCustodyReceipt",
    "RangerAwsQualificationManifestCustodyVerification",
    "build_aws_qualification_manifest_custody_receipt",
    "verify_aws_qualification_manifest_custody_receipt",
]
