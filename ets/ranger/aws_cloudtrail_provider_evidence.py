"""CloudTrail provider-boundary evidence verification for Ranger R0.2.

This module composes a verified Ranger AWS execution receipt with AWS CloudTrail digest/log
integrity evidence.  It validates the CloudTrail digest signature under an independently supplied
RSA public key, validates every referenced log hash supplied to the verifier, and correlates the
exact AWS request IDs from the Ranger capture package to CloudTrail events.

The verifier deliberately does *not* establish how the CloudTrail public key was obtained.  A
future controlled live trial must separately preserve and authenticate the ListPublicKeys lookup
(or equivalent trust-anchor evidence).  Therefore a passing result does not, by itself, prove AWS
public-key provenance, complete CloudTrail coverage, physical WORM storage, or semantic truth.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, NamedTuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import Field, ValidationError, field_validator

from ets.ranger.aws_s3_object_lock import StrictModel
from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ObjectLockCapturePlan,
)
from ets.ranger.aws_s3_object_lock_execution import (
    RangerAwsS3ExecutionPackage,
    RangerAwsS3ExecutionReceiptPolicy,
    verify_aws_s3_execution_receipt,
)

_MAX_DIGEST_BYTES = 2 * 1024 * 1024


class RangerAwsCloudTrailEvidenceError(RuntimeError):
    """Raised when CloudTrail evidence input cannot be safely interpreted."""


class RangerAwsCloudTrailVerificationPolicy(StrictModel):
    """Independent verifier inputs for one bounded CloudTrail evidence window."""

    expected_digest_s3_bucket: str = Field(min_length=3, max_length=63)
    expected_digest_s3_object: str = Field(min_length=1, max_length=2048)
    expected_public_key_fingerprint: str = Field(pattern=r"^[0-9A-Fa-f]{16,128}$")
    maximum_log_files: int = Field(ge=1, le=256)
    maximum_log_file_bytes: int = Field(ge=1, le=128 * 1024 * 1024)
    maximum_event_time_skew_seconds: int = Field(ge=0, le=3600)


class RangerAwsCloudTrailVerification(StrictModel):
    valid: bool
    execution_receipt_verified: bool = False
    digest_location_verified: bool = False
    digest_signature_verified: bool = False
    referenced_log_hashes_verified: bool = False
    capture_request_ids_correlated: bool = False
    cloudtrail_event_profile_passed: bool = False
    aws_public_key_provenance_independently_verified: Literal[False] = False
    complete_cloudtrail_coverage_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False
    physical_worm_storage_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    digest_file_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    matched_request_count: int = Field(default=0, ge=0, le=32)
    reason: str


class _RequiredRequest(NamedTuple):
    event_source: str
    event_name: str
    request_id: str
    require_bucket: bool
    require_key: bool
    require_version: bool
    expected_error_code: str | None = None


@field_validator

def _unused_validator_marker() -> None:  # pragma: no cover - prevents accidental pydantic import drift
    """This function is never registered; validation is intentionally performed explicitly below."""


def verify_aws_cloudtrail_provider_evidence(
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    cloudtrail_policy: RangerAwsCloudTrailVerificationPolicy,
    digest_file_bytes: bytes,
    digest_signature_hex: str,
    cloudtrail_public_key_der: bytes,
    uncompressed_log_files: Mapping[str, bytes],
) -> RangerAwsCloudTrailVerification:
    """Verify one receipt-bound CloudTrail digest/log evidence set.

    ``digest_file_bytes`` must be the exact digest content used for the CloudTrail digest hash.
    ``uncompressed_log_files`` is keyed by ``"bucket/object"`` and contains uncompressed CloudTrail
    log JSON bytes, matching AWS's documented log-hash validation procedure.
    """

    receipt_result = verify_aws_s3_execution_receipt(
        package,
        authorization,
        plan,
        policy=receipt_policy,
    )
    if not receipt_result.valid:
        return _failure(f"execution receipt is invalid: {receipt_result.reason}")

    try:
        policy = RangerAwsCloudTrailVerificationPolicy.model_validate(cloudtrail_policy.model_dump())
        record = RangerAwsS3ExecutionPackage.model_validate(package.model_dump())
        validated_plan = RangerAwsS3ObjectLockCapturePlan.model_validate(plan.model_dump())
    except (AttributeError, ValidationError):
        return _failure("CloudTrail verifier input schema validation failed", receipt=True)

    if not digest_file_bytes or len(digest_file_bytes) > _MAX_DIGEST_BYTES:
        return _failure("CloudTrail digest size is outside the bounded verifier limit", receipt=True)

    try:
        digest = json.loads(digest_file_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _failure("CloudTrail digest is not valid JSON", receipt=True)
    if not isinstance(digest, dict):
        return _failure("CloudTrail digest root must be an object", receipt=True)

    location_error = _validate_digest_identity(digest, policy)
    if location_error is not None:
        return _failure(location_error, receipt=True)

    digest_sha256 = hashlib.sha256(digest_file_bytes).hexdigest()
    signature_error = _verify_digest_signature(
        digest,
        digest_file_sha256=digest_sha256,
        signature_hex=digest_signature_hex,
        public_key_der=cloudtrail_public_key_der,
    )
    if signature_error is not None:
        return _failure(
            signature_error,
            receipt=True,
            location=True,
            digest_sha256=digest_sha256,
        )

    logs_result = _verify_log_files(digest, uncompressed_log_files, policy)
    if isinstance(logs_result, str):
        return _failure(
            logs_result,
            receipt=True,
            location=True,
            signature=True,
            digest_sha256=digest_sha256,
        )

    required = _required_requests(record)
    correlation_error = _correlate_required_requests(
        required,
        logs_result,
        validated_plan,
        maximum_skew=timedelta(seconds=policy.maximum_event_time_skew_seconds),
    )
    if correlation_error is not None:
        return _failure(
            correlation_error,
            receipt=True,
            location=True,
            signature=True,
            logs=True,
            digest_sha256=digest_sha256,
        )

    return RangerAwsCloudTrailVerification(
        valid=True,
        execution_receipt_verified=True,
        digest_location_verified=True,
        digest_signature_verified=True,
        referenced_log_hashes_verified=True,
        capture_request_ids_correlated=True,
        cloudtrail_event_profile_passed=True,
        digest_file_sha256=digest_sha256,
        matched_request_count=len(required),
        reason=(
            "CloudTrail digest signature, supplied log hashes, and exact capture request-ID "
            "correlation verified; AWS public-key provenance and complete provider execution "
            "remain separate claims"
        ),
    )


def _validate_digest_identity(
    digest: dict[str, Any], policy: RangerAwsCloudTrailVerificationPolicy
) -> str | None:
    required = {
        "digestEndTime",
        "digestS3Bucket",
        "digestS3Object",
        "digestPublicKeyFingerprint",
        "digestSignatureAlgorithm",
        "previousDigestSignature",
        "logFiles",
    }
    if not required.issubset(digest):
        return "CloudTrail digest is missing required integrity fields"
    if digest["digestS3Bucket"] != policy.expected_digest_s3_bucket:
        return "CloudTrail digest bucket does not match verifier policy"
    if digest["digestS3Object"] != policy.expected_digest_s3_object:
        return "CloudTrail digest object does not match verifier policy"
    if str(digest["digestPublicKeyFingerprint"]).lower() != (
        policy.expected_public_key_fingerprint.lower()
    ):
        return "CloudTrail digest public-key fingerprint does not match verifier policy"
    if digest["digestSignatureAlgorithm"] != "SHA256withRSA":
        return "CloudTrail digest signature algorithm is not SHA256withRSA"
    if not isinstance(digest["logFiles"], list):
        return "CloudTrail digest logFiles must be an array"
    return None


def _verify_digest_signature(
    digest: dict[str, Any],
    *,
    digest_file_sha256: str,
    signature_hex: str,
    public_key_der: bytes,
) -> str | None:
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return "CloudTrail digest signature is not hexadecimal"
    try:
        public_key = serialization.load_der_public_key(public_key_der)
    except (TypeError, ValueError):
        return "CloudTrail public key is not valid DER"
    if not isinstance(public_key, rsa.RSAPublicKey):
        return "CloudTrail public key is not RSA"

    end_time = digest.get("digestEndTime")
    bucket = digest.get("digestS3Bucket")
    object_key = digest.get("digestS3Object")
    previous_signature = digest.get("previousDigestSignature")
    if not all(isinstance(value, str) for value in (end_time, bucket, object_key, previous_signature)):
        return "CloudTrail digest signing fields must be strings"
    data_to_sign = (
        f"{end_time}\n{bucket}/{object_key}\n{digest_file_sha256}\n{previous_signature}"
    ).encode("utf-8")
    try:
        public_key.verify(signature, data_to_sign, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature:
        return "CloudTrail digest signature verification failed"
    return None


def _verify_log_files(
    digest: dict[str, Any],
    supplied: Mapping[str, bytes],
    policy: RangerAwsCloudTrailVerificationPolicy,
) -> list[dict[str, Any]] | str:
    references = digest["logFiles"]
    if len(references) == 0:
        return "CloudTrail digest contains no log-file references for the qualification window"
    if len(references) > policy.maximum_log_files:
        return "CloudTrail digest exceeds the verifier log-file count limit"

    events: list[dict[str, Any]] = []
    expected_paths: set[str] = set()
    for reference in references:
        if not isinstance(reference, dict):
            return "CloudTrail log-file reference is not an object"
        bucket = reference.get("s3Bucket")
        object_key = reference.get("s3Object")
        hash_value = reference.get("hashValue")
        hash_algorithm = reference.get("hashAlgorithm")
        if not all(isinstance(value, str) for value in (bucket, object_key, hash_value, hash_algorithm)):
            return "CloudTrail log-file reference has invalid fields"
        if hash_algorithm not in {"SHA-256", "SHA256"}:
            return "CloudTrail log-file hash algorithm is not SHA-256"
        path = f"{bucket}/{object_key}"
        if path in expected_paths:
            return "CloudTrail digest contains a duplicate log-file path"
        expected_paths.add(path)
        content = supplied.get(path)
        if content is None:
            return f"CloudTrail referenced log file is missing: {path}"
        if len(content) > policy.maximum_log_file_bytes:
            return f"CloudTrail log file exceeds verifier size limit: {path}"
        if hashlib.sha256(content).hexdigest() != hash_value.lower():
            return f"CloudTrail log-file hash mismatch: {path}"
        try:
            log = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return f"CloudTrail log file is not valid JSON: {path}"
        if not isinstance(log, dict) or not isinstance(log.get("Records"), list):
            return f"CloudTrail log file Records array is missing: {path}"
        for event in log["Records"]:
            if not isinstance(event, dict):
                return f"CloudTrail event is not an object: {path}"
            events.append(event)

    if set(supplied) != expected_paths:
        return "CloudTrail supplied log-file set contains unreferenced files"
    return events


def _required_requests(package: RangerAwsS3ExecutionPackage) -> tuple[_RequiredRequest, ...]:
    result = package.capture_result
    return (
        _RequiredRequest(
            "s3.amazonaws.com",
            "GetBucketVersioning",
            result.configuration.get_bucket_versioning.metadata.request_id,
            True,
            False,
            False,
        ),
        _RequiredRequest(
            "s3.amazonaws.com",
            "GetObjectLockConfiguration",
            result.configuration.get_object_lock_configuration.metadata.request_id,
            True,
            False,
            False,
        ),
        _RequiredRequest(
            "s3.amazonaws.com",
            "PutObject",
            result.retention_put.put_object.metadata.request_id,
            True,
            True,
            False,
        ),
        _RequiredRequest(
            "s3.amazonaws.com",
            "GetObjectRetention",
            result.retention_put.get_object_retention.metadata.request_id,
            True,
            True,
            True,
        ),
        _RequiredRequest(
            "iam.amazonaws.com",
            "SimulatePrincipalPolicy",
            result.delete_capability.metadata.request_id,
            False,
            False,
            False,
        ),
        _RequiredRequest(
            "s3.amazonaws.com",
            "DeleteObject",
            result.delete_attempt.metadata.request_id,
            True,
            True,
            True,
            result.delete_attempt.error_code,
        ),
        _RequiredRequest(
            "s3.amazonaws.com",
            "GetObject",
            result.retrieval.get_object.metadata.request_id,
            True,
            True,
            True,
        ),
    )


def _correlate_required_requests(
    required: tuple[_RequiredRequest, ...],
    events: list[dict[str, Any]],
    plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    maximum_skew: timedelta,
) -> str | None:
    by_request_id: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        request_id = event.get("requestID")
        if isinstance(request_id, str):
            by_request_id.setdefault(request_id, []).append(event)

    earliest = plan.configuration_observed_at_utc - maximum_skew
    latest = plan.retrieval_observed_at_utc + maximum_skew
    version_id = plan.model_dump().get("object_version_id")
    if version_id is None:
        version_id = None

    for expectation in required:
        matches = by_request_id.get(expectation.request_id, [])
        if len(matches) != 1:
            return (
                f"CloudTrail request-ID correlation expected exactly one event for "
                f"{expectation.event_name}"
            )
        event = matches[0]
        if event.get("eventSource") != expectation.event_source:
            return f"CloudTrail event source mismatch for {expectation.event_name}"
        if event.get("eventName") != expectation.event_name:
            return f"CloudTrail event name mismatch for request {expectation.request_id}"
        if event.get("awsRegion") != plan.aws_region:
            return f"CloudTrail region mismatch for {expectation.event_name}"
        if event.get("recipientAccountId") != plan.aws_account_id:
            return f"CloudTrail account mismatch for {expectation.event_name}"
        event_time = _parse_event_time(event.get("eventTime"))
        if event_time is None or not earliest <= event_time <= latest:
            return f"CloudTrail event time is outside the bounded capture window for {expectation.event_name}"
        parameters = event.get("requestParameters")
        if not isinstance(parameters, dict):
            parameters = {}
        if expectation.require_bucket and parameters.get("bucketName") != plan.bucket_name:
            return f"CloudTrail bucket mismatch for {expectation.event_name}"
        if expectation.require_key and parameters.get("key") != plan.object_key:
            return f"CloudTrail object-key mismatch for {expectation.event_name}"
        if expectation.require_version:
            observed_version = parameters.get("versionId")
            expected_version = package_version = _package_version_from_required_context(required, events)
            if observed_version != expected_version:
                return f"CloudTrail object-version mismatch for {expectation.event_name}"
        if expectation.expected_error_code is not None:
            if event.get("errorCode") != expectation.expected_error_code:
                return "CloudTrail delete error code does not match captured denial"
    return None


def _package_version_from_required_context(
    required: tuple[_RequiredRequest, ...], events: list[dict[str, Any]]
) -> str | None:
    """Return the unique version ID already carried by correlated version-specific S3 events."""

    del required
    versions = {
        event.get("requestParameters", {}).get("versionId")
        for event in events
        if isinstance(event.get("requestParameters"), dict)
        and isinstance(event.get("requestParameters", {}).get("versionId"), str)
    }
    if len(versions) == 1:
        value = next(iter(versions))
        return value if isinstance(value, str) else None
    return None


def _parse_event_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _failure(
    reason: str,
    *,
    receipt: bool = False,
    location: bool = False,
    signature: bool = False,
    logs: bool = False,
    digest_sha256: str | None = None,
) -> RangerAwsCloudTrailVerification:
    return RangerAwsCloudTrailVerification(
        valid=False,
        execution_receipt_verified=receipt,
        digest_location_verified=location,
        digest_signature_verified=signature,
        referenced_log_hashes_verified=logs,
        digest_file_sha256=digest_sha256,
        reason=reason,
    )
