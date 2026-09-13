"""Signed execution receipt for Ranger R0.2 AWS Object Lock qualification capture.

This module binds one verified pre-execution authorization to the five canonical artifacts that
the credential-isolated capture adapter returned. The receipt is an assertion by a configured,
distinct recorder key. It does not prove that AWS produced the observations, that capture was
complete, or that the recorder was independent or uncompromised.
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
from ets.ranger.aws_s3_object_lock import StrictModel
from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ExecutionAuthorizationPolicy,
    RangerAwsS3ExecutionEnvironment,
    RangerAwsS3ObjectLockCapturePlan,
    RangerAwsS3ObjectLockCaptureResult,
    RangerAwsS3ObjectLockIamClient,
    RangerAwsS3ObjectLockS3Client,
    aws_s3_object_lock_capture_plan_digest,
    capture_aws_s3_object_lock_qualification,
    verify_aws_s3_execution_authorization,
)
from ets.ranger.immutable_publication import RangerImmutableEvidenceArtifactKind


class RangerAwsS3ExecutionReceiptError(RuntimeError):
    """Raised when a signed execution package cannot be produced safely."""


class RangerAwsS3ExecutionReceipt(StrictModel):
    """Recorder-signed binding from authorization to exact returned artifacts."""

    schema_version: Literal["ets.ranger.aws-s3-execution-receipt.v1"] = (
        "ets.ranger.aws-s3-execution-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    authorization_id: str = Field(min_length=1, max_length=256)
    authorization_record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capture_plan_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_id: str = Field(min_length=1, max_length=256)
    verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_environment: RangerAwsS3ExecutionEnvironment
    object_version_id: str = Field(min_length=1, max_length=512)
    configuration_artifact_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retention_put_artifact_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    delete_capability_artifact_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    delete_attempt_artifact_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_artifact_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capture_started_at_utc: datetime
    capture_completed_at_utc: datetime
    receipt_issued_at_utc: datetime
    recorder_id: str = Field(min_length=1, max_length=160)
    recorder_signing_key_id: str = Field(min_length=1, max_length=256)
    recorder_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    receipt_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    recorder_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    configured_authorization_verified: Literal[True] = True
    capture_artifacts_bound: Literal[True] = True
    provider_execution_independently_proven: Literal[False] = False
    complete_capture_proven: Literal[False] = False
    recorder_independence_proven: Literal[False] = False
    physical_worm_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_recorder_binding_no_provider_completeness_independence_or_physical_worm_proof"
    ] = (
        "configured_recorder_binding_no_provider_completeness_independence_or_physical_worm_proof"
    )

    @field_validator(
        "capture_started_at_utc", "capture_completed_at_utc", "receipt_issued_at_utc"
    )
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("execution receipt times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_ordered_times(self) -> RangerAwsS3ExecutionReceipt:
        if not (
            self.capture_started_at_utc
            <= self.capture_completed_at_utc
            <= self.receipt_issued_at_utc
        ):
            raise ValueError("execution receipt times must be ordered")
        return self


class RangerAwsS3ExecutionPackage(StrictModel):
    capture_result: RangerAwsS3ObjectLockCaptureResult
    execution_receipt: RangerAwsS3ExecutionReceipt


class RangerAwsS3ExecutionReceiptPolicy(StrictModel):
    authorization_policy: RangerAwsS3ExecutionAuthorizationPolicy
    expected_receipt_id: str = Field(min_length=1, max_length=256)
    expected_recorder_id: str = Field(min_length=1, max_length=160)
    expected_recorder_signing_key_id: str = Field(min_length=1, max_length=256)
    recorder_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    maximum_receipt_delay_seconds: int = Field(ge=0, le=3600)


class RangerAwsS3ExecutionReceiptVerification(StrictModel):
    valid: bool
    receipt_id: str | None = None
    authorization_record_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    receipt_digest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    configured_authorizer_signature_proven: bool = False
    configured_recorder_signature_proven: bool = False
    exact_capture_artifacts_bound: bool = False
    provider_execution_independently_proven: Literal[False] = False
    reason: str


def execution_authorization_record_digest(
    authorization: RangerAwsS3ExecutionAuthorization,
) -> str:
    """Hash the complete signed authorization record, including its signature."""

    record = RangerAwsS3ExecutionAuthorization.model_validate(authorization.model_dump())
    return canonical_sha256(record.model_dump(mode="json"))


def aws_s3_execution_receipt_bytes(receipt: RangerAwsS3ExecutionReceipt) -> bytes:
    """Return the complete receipt in canonical ETS JSON form."""

    record = RangerAwsS3ExecutionReceipt.model_validate(receipt.model_dump())
    return canonicalize(record.model_dump(mode="json"))


def build_aws_s3_execution_receipt(
    authorization: RangerAwsS3ExecutionAuthorization,
    plan: RangerAwsS3ObjectLockCapturePlan,
    capture_result: RangerAwsS3ObjectLockCaptureResult,
    *,
    authorization_policy: RangerAwsS3ExecutionAuthorizationPolicy,
    receipt_id: str,
    receipt_issued_at_utc: datetime,
    recorder_id: str,
    recorder_signing_key_id: str,
    recorder_private_key_hex: str,
) -> RangerAwsS3ExecutionReceipt:
    """Sign a receipt only for a verified authorization and a coherent result."""

    auth_verification = verify_aws_s3_execution_authorization(
        authorization, plan, policy=authorization_policy
    )
    if not auth_verification.valid:
        raise RangerAwsS3ExecutionReceiptError(auth_verification.reason)
    try:
        result = RangerAwsS3ObjectLockCaptureResult.model_validate(capture_result.model_dump())
    except (AttributeError, ValidationError) as exc:
        raise RangerAwsS3ExecutionReceiptError("capture result schema validation failed") from exc
    context_error = _capture_context_error(result, plan)
    if context_error is not None:
        raise RangerAwsS3ExecutionReceiptError(context_error)
    issued_at = _aware_utc(receipt_issued_at_utc)
    if not plan.retrieval_observed_at_utc <= issued_at < authorization.expires_at_utc:
        raise RangerAwsS3ExecutionReceiptError(
            "receipt issue time must follow capture and precede authorization expiry"
        )
    private_key = _private_key(recorder_private_key_hex)
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    fingerprint = hashlib.sha256(public_bytes).hexdigest()
    if fingerprint == authorization.authorizer_public_key_fingerprint_sha256:
        raise RangerAwsS3ExecutionReceiptError(
            "recorder signing key must be distinct from the authorization key"
        )
    artifact_digests = _artifact_digests(result)
    unsigned: dict[str, Any] = {
        "schema_version": "ets.ranger.aws-s3-execution-receipt.v1",
        "receipt_id": receipt_id,
        "authorization_id": authorization.authorization_id,
        "authorization_record_digest_sha256": execution_authorization_record_digest(authorization),
        "authorization_digest_sha256": authorization.authorization_digest_sha256,
        "capture_plan_digest_sha256": aws_s3_object_lock_capture_plan_digest(plan),
        "qualification_id": plan.qualification_id,
        "verifier_challenge_nonce_hex": plan.verifier_challenge_nonce_hex,
        "execution_environment": authorization.execution_environment,
        "object_version_id": result.configuration.context.object_version_id,
        "configuration_artifact_digest_sha256": artifact_digests[
            RangerImmutableEvidenceArtifactKind.CONFIGURATION
        ],
        "retention_put_artifact_digest_sha256": artifact_digests[
            RangerImmutableEvidenceArtifactKind.RETENTION_PUT
        ],
        "delete_capability_artifact_digest_sha256": artifact_digests[
            RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY
        ],
        "delete_attempt_artifact_digest_sha256": artifact_digests[
            RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT
        ],
        "retrieval_artifact_digest_sha256": artifact_digests[
            RangerImmutableEvidenceArtifactKind.RETRIEVAL
        ],
        "capture_started_at_utc": plan.configuration_observed_at_utc,
        "capture_completed_at_utc": plan.retrieval_observed_at_utc,
        "receipt_issued_at_utc": issued_at,
        "recorder_id": recorder_id,
        "recorder_signing_key_id": recorder_signing_key_id,
        "recorder_public_key_fingerprint_sha256": fingerprint,
        "signing_algorithm": "ed25519",
        "configured_authorization_verified": True,
        "capture_artifacts_bound": True,
        "provider_execution_independently_proven": False,
        "complete_capture_proven": False,
        "recorder_independence_proven": False,
        "physical_worm_proven": False,
        "claim_boundary": (
            "configured_recorder_binding_no_provider_completeness_independence_or_physical_worm_proof"
        ),
    }
    try:
        candidate = RangerAwsS3ExecutionReceipt.model_validate(
            {
                **unsigned,
                "receipt_digest_sha256": "0" * 64,
                "recorder_signature_hex": "0" * 128,
            }
        )
        payload = _receipt_payload(candidate)
        return RangerAwsS3ExecutionReceipt.model_validate(
            candidate.model_copy(
                update={
                    "receipt_digest_sha256": canonical_sha256(payload),
                    "recorder_signature_hex": private_key.sign(canonicalize(payload)).hex(),
                }
            ).model_dump()
        )
    except ValidationError as exc:
        raise RangerAwsS3ExecutionReceiptError("invalid execution receipt fields") from exc


def capture_aws_s3_object_lock_qualification_with_receipt(
    plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    authorization: RangerAwsS3ExecutionAuthorization,
    authorization_policy: RangerAwsS3ExecutionAuthorizationPolicy,
    s3_client: RangerAwsS3ObjectLockS3Client,
    iam_client: RangerAwsS3ObjectLockIamClient,
    receipt_id: str,
    receipt_issued_at_utc: datetime,
    recorder_id: str,
    recorder_signing_key_id: str,
    recorder_private_key_hex: str,
) -> RangerAwsS3ExecutionPackage:
    """Capture through the guarded adapter, then issue a receipt over the returned artifacts."""

    result = capture_aws_s3_object_lock_qualification(
        plan,
        authorization=authorization,
        authorization_policy=authorization_policy,
        s3_client=s3_client,
        iam_client=iam_client,
    )
    receipt = build_aws_s3_execution_receipt(
        authorization,
        plan,
        result,
        authorization_policy=authorization_policy,
        receipt_id=receipt_id,
        receipt_issued_at_utc=receipt_issued_at_utc,
        recorder_id=recorder_id,
        recorder_signing_key_id=recorder_signing_key_id,
        recorder_private_key_hex=recorder_private_key_hex,
    )
    return RangerAwsS3ExecutionPackage(capture_result=result, execution_receipt=receipt)


def verify_aws_s3_execution_receipt(
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    policy: RangerAwsS3ExecutionReceiptPolicy,
) -> RangerAwsS3ExecutionReceiptVerification:
    """Independently verify authorization, receipt signature, context, and artifact bindings."""

    try:
        record = RangerAwsS3ExecutionPackage.model_validate(package.model_dump())
        auth = RangerAwsS3ExecutionAuthorization.model_validate(authorization.model_dump())
        validated_plan = RangerAwsS3ObjectLockCapturePlan.model_validate(plan.model_dump())
        configured = RangerAwsS3ExecutionReceiptPolicy.model_validate(policy.model_dump())
    except (AttributeError, ValidationError):
        return _failure("execution receipt package schema validation failed")
    auth_result = verify_aws_s3_execution_authorization(
        auth, validated_plan, policy=configured.authorization_policy
    )
    if not auth_result.valid:
        return _failure(f"authorization verification failed: {auth_result.reason}")
    receipt = record.execution_receipt
    if (
        receipt.receipt_id != configured.expected_receipt_id
        or receipt.recorder_id != configured.expected_recorder_id
        or receipt.recorder_signing_key_id != configured.expected_recorder_signing_key_id
    ):
        return _failure("execution receipt policy identity mismatch")
    if receipt.authorization_record_digest_sha256 != execution_authorization_record_digest(auth):
        return _failure("execution receipt authorization-record digest mismatch")
    if (
        receipt.authorization_id != auth.authorization_id
        or receipt.authorization_digest_sha256 != auth.authorization_digest_sha256
        or receipt.capture_plan_digest_sha256
        != aws_s3_object_lock_capture_plan_digest(validated_plan)
        or receipt.qualification_id != validated_plan.qualification_id
        or receipt.verifier_challenge_nonce_hex != validated_plan.verifier_challenge_nonce_hex
        or receipt.execution_environment != auth.execution_environment
    ):
        return _failure("execution receipt authorization or plan binding mismatch")
    if (
        receipt.capture_started_at_utc != validated_plan.configuration_observed_at_utc
        or receipt.capture_completed_at_utc != validated_plan.retrieval_observed_at_utc
        or receipt.receipt_issued_at_utc >= auth.expires_at_utc
    ):
        return _failure("execution receipt time binding mismatch")
    delay = (receipt.receipt_issued_at_utc - receipt.capture_completed_at_utc).total_seconds()
    if delay > configured.maximum_receipt_delay_seconds:
        return _failure("execution receipt delay exceeds policy")
    context_error = _capture_context_error(record.capture_result, validated_plan)
    if context_error is not None:
        return _failure(context_error)
    if receipt.object_version_id != record.capture_result.configuration.context.object_version_id:
        return _failure("execution receipt object-version binding mismatch")
    if _receipt_artifact_digests(receipt) != _artifact_digests(record.capture_result):
        return _failure("execution receipt artifact digest mismatch")
    public_key, fingerprint = _public_key(configured.recorder_public_key_hex)
    if public_key is None or fingerprint is None:
        return _failure("recorder public key is not 32-byte Ed25519")
    if fingerprint == auth.authorizer_public_key_fingerprint_sha256:
        return _failure("recorder key must be distinct from authorization key")
    if receipt.recorder_public_key_fingerprint_sha256 != fingerprint:
        return _failure("execution receipt recorder key fingerprint mismatch")
    payload = _receipt_payload(receipt)
    if canonical_sha256(payload) != receipt.receipt_digest_sha256:
        return _failure("execution receipt digest mismatch")
    try:
        public_key.verify(bytes.fromhex(receipt.recorder_signature_hex), canonicalize(payload))
    except (InvalidSignature, ValueError):
        return _failure("execution receipt signature invalid")
    return RangerAwsS3ExecutionReceiptVerification(
        valid=True,
        receipt_id=receipt.receipt_id,
        authorization_record_digest_sha256=receipt.authorization_record_digest_sha256,
        receipt_digest_sha256=receipt.receipt_digest_sha256,
        configured_authorizer_signature_proven=True,
        configured_recorder_signature_proven=True,
        exact_capture_artifacts_bound=True,
        reason=(
            "configured authorization and distinct recorder signatures bind the exact plan and "
            "five returned artifacts; provider execution, capture completeness, recorder "
            "independence, and physical WORM are not independently proven"
        ),
    )


def _capture_context_error(
    result: RangerAwsS3ObjectLockCaptureResult,
    plan: RangerAwsS3ObjectLockCapturePlan,
) -> str | None:
    contexts = (
        result.configuration.context,
        result.retention_put.context,
        result.delete_capability.context,
        result.delete_attempt.context,
        result.retrieval.context,
    )
    version_ids = {context.object_version_id for context in contexts}
    if len(version_ids) != 1:
        return "capture result contains mixed object versions"
    expected_times = (
        plan.configuration_observed_at_utc,
        plan.retention_put_observed_at_utc,
        plan.delete_capability_observed_at_utc,
        plan.delete_attempt_observed_at_utc,
        plan.retrieval_observed_at_utc,
    )
    for context, expected_time in zip(contexts, expected_times, strict=True):
        if (
            context.qualification_id != plan.qualification_id
            or context.verifier_challenge_nonce_hex != plan.verifier_challenge_nonce_hex
            or context.aws_partition != plan.aws_partition
            or context.aws_account_id != plan.aws_account_id
            or context.aws_region != plan.aws_region
            or context.bucket_name != plan.bucket_name
            or context.object_key != plan.object_key
            or context.delete_test_principal_arn != plan.delete_test_principal_arn
            or context.observed_at_utc != expected_time
        ):
            return "capture result context does not match the authorized plan"
    return None


def _artifact_digests(
    result: RangerAwsS3ObjectLockCaptureResult,
) -> dict[RangerImmutableEvidenceArtifactKind, str]:
    return {
        kind: hashlib.sha256(value).hexdigest()
        for kind, value in result.evidence_artifacts().items()
    }


def _receipt_artifact_digests(
    receipt: RangerAwsS3ExecutionReceipt,
) -> dict[RangerImmutableEvidenceArtifactKind, str]:
    return {
        RangerImmutableEvidenceArtifactKind.CONFIGURATION: (
            receipt.configuration_artifact_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.RETENTION_PUT: (
            receipt.retention_put_artifact_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY: (
            receipt.delete_capability_artifact_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: (
            receipt.delete_attempt_artifact_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.RETRIEVAL: receipt.retrieval_artifact_digest_sha256,
    }


def _receipt_payload(receipt: RangerAwsS3ExecutionReceipt) -> dict[str, Any]:
    return receipt.model_dump(
        mode="json", exclude={"receipt_digest_sha256", "recorder_signature_hex"}
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangerAwsS3ExecutionReceiptError("receipt issue time must be timezone-aware")
    return value.astimezone(UTC)


def _private_key(value: str) -> Ed25519PrivateKey:
    try:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))
    except (ValueError, TypeError) as exc:
        raise RangerAwsS3ExecutionReceiptError(
            "recorder private key must be a 32-byte Ed25519 key"
        ) from exc


def _public_key(value: str) -> tuple[Ed25519PublicKey | None, str | None]:
    try:
        key_bytes = bytes.fromhex(value)
        return Ed25519PublicKey.from_public_bytes(key_bytes), hashlib.sha256(key_bytes).hexdigest()
    except ValueError:
        return None, None


def _failure(reason: str) -> RangerAwsS3ExecutionReceiptVerification:
    return RangerAwsS3ExecutionReceiptVerification(valid=False, reason=reason)


__all__ = [
    "RangerAwsS3ExecutionPackage",
    "RangerAwsS3ExecutionReceipt",
    "RangerAwsS3ExecutionReceiptError",
    "RangerAwsS3ExecutionReceiptPolicy",
    "RangerAwsS3ExecutionReceiptVerification",
    "aws_s3_execution_receipt_bytes",
    "build_aws_s3_execution_receipt",
    "capture_aws_s3_object_lock_qualification_with_receipt",
    "execution_authorization_record_digest",
    "verify_aws_s3_execution_receipt",
]
