"""Credential-isolated AWS S3 Object Lock capture adapter for Ranger R0.2.

The adapter accepts already-constructed, capability-limited S3 and IAM clients.  It neither
imports an AWS SDK nor discovers credentials, regions, accounts, or endpoints.  A caller that has
separately been authorized to run a qualification can inject clients; ordinary CI injects stubs.

Only canonical, secret-free observations are returned.  The supplied archive bytes are streamed
to the injected S3 client and hashed locally, but are never retained in the capture result.
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import Field, field_validator, model_validator

from ets.ranger.aws_s3_object_lock import (
    RangerAwsIamDeleteCapabilityArtifact,
    RangerAwsS3BucketObjectLockObservation,
    RangerAwsS3BucketVersioningObservation,
    RangerAwsS3DefaultRetention,
    RangerAwsS3DeleteAttemptArtifact,
    RangerAwsS3GetObjectObservation,
    RangerAwsS3GetObjectRetentionObservation,
    RangerAwsS3ObjectLockCaptureContext,
    RangerAwsS3ObjectLockConfigurationArtifact,
    RangerAwsS3ObjectLockRetentionPutArtifact,
    RangerAwsS3PostDenialRetrievalArtifact,
    RangerAwsS3PutObjectObservation,
    RangerAwsS3ResponseMetadata,
    StrictModel,
    aws_s3_object_lock_artifact_bytes,
)
from ets.ranger.immutable_publication import RangerImmutableEvidenceArtifactKind

_MAX_QUALIFICATION_ARCHIVE_BYTES = 1024 * 1024


class RangerAwsS3ObjectLockCaptureError(RuntimeError):
    """Raised when a client response cannot form a bounded canonical capture."""


@runtime_checkable
class RangerAwsS3ObjectLockS3Client(Protocol):
    """Minimal injected S3 capability required for one qualification capture."""

    def get_bucket_versioning(self, **kwargs: object) -> Mapping[str, object]: ...

    def get_object_lock_configuration(self, **kwargs: object) -> Mapping[str, object]: ...

    def put_object(self, **kwargs: object) -> Mapping[str, object]: ...

    def get_object_retention(self, **kwargs: object) -> Mapping[str, object]: ...

    def delete_object(self, **kwargs: object) -> Mapping[str, object]: ...

    def get_object(self, **kwargs: object) -> Mapping[str, object]: ...


@runtime_checkable
class RangerAwsS3ObjectLockIamClient(Protocol):
    """Minimal injected IAM capability required for one qualification capture."""

    def simulate_principal_policy(self, **kwargs: object) -> Mapping[str, object]: ...


class RangerAwsS3ObjectLockCapturePlan(StrictModel):
    """Pre-authorized, bounded inputs for one synthetic Object Lock qualification object."""

    qualification_id: str = Field(min_length=1, max_length=256)
    verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    aws_partition: Literal["aws", "aws-us-gov", "aws-cn"]
    aws_account_id: str = Field(pattern=r"^[0-9]{12}$")
    aws_region: str = Field(pattern=r"^[a-z0-9-]{3,32}$")
    bucket_name: str = Field(min_length=3, max_length=63)
    object_key: str = Field(min_length=1, max_length=1024)
    delete_test_principal_arn: str = Field(min_length=20, max_length=2048)
    archive_bundle_bytes: bytes = Field(min_length=1, max_length=_MAX_QUALIFICATION_ARCHIVE_BYTES)
    retention_until_utc: datetime
    configuration_observed_at_utc: datetime
    retention_put_observed_at_utc: datetime
    delete_capability_observed_at_utc: datetime
    delete_attempt_observed_at_utc: datetime
    retrieval_observed_at_utc: datetime

    @field_validator(
        "retention_until_utc",
        "configuration_observed_at_utc",
        "retention_put_observed_at_utc",
        "delete_capability_observed_at_utc",
        "delete_attempt_observed_at_utc",
        "retrieval_observed_at_utc",
    )
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("qualification capture times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_bounded_order_and_identity(self) -> RangerAwsS3ObjectLockCapturePlan:
        prefix = f"arn:{self.aws_partition}:iam::{self.aws_account_id}:"
        if not self.delete_test_principal_arn.startswith(prefix):
            raise ValueError("delete-test principal must be within the pinned AWS account")
        ordered = (
            self.configuration_observed_at_utc,
            self.retention_put_observed_at_utc,
            self.delete_capability_observed_at_utc,
            self.delete_attempt_observed_at_utc,
            self.retrieval_observed_at_utc,
        )
        if tuple(sorted(ordered)) != ordered:
            raise ValueError("qualification capture observations must be chronologically ordered")
        if self.retention_until_utc <= self.delete_attempt_observed_at_utc:
            raise ValueError("retention must extend beyond the planned delete attempt")
        return self


class RangerAwsS3ObjectLockCaptureResult(StrictModel):
    """Five canonical artifacts; deliberately excludes clients, credentials, and object bytes."""

    configuration: RangerAwsS3ObjectLockConfigurationArtifact
    retention_put: RangerAwsS3ObjectLockRetentionPutArtifact
    delete_capability: RangerAwsIamDeleteCapabilityArtifact
    delete_attempt: RangerAwsS3DeleteAttemptArtifact
    retrieval: RangerAwsS3PostDenialRetrievalArtifact

    def evidence_artifacts(self) -> dict[RangerImmutableEvidenceArtifactKind, bytes]:
        return {
            RangerImmutableEvidenceArtifactKind.CONFIGURATION: aws_s3_object_lock_artifact_bytes(
                self.configuration
            ),
            RangerImmutableEvidenceArtifactKind.RETENTION_PUT: aws_s3_object_lock_artifact_bytes(
                self.retention_put
            ),
            RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY: (
                aws_s3_object_lock_artifact_bytes(self.delete_capability)
            ),
            RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: aws_s3_object_lock_artifact_bytes(
                self.delete_attempt
            ),
            RangerImmutableEvidenceArtifactKind.RETRIEVAL: aws_s3_object_lock_artifact_bytes(
                self.retrieval
            ),
        }


def capture_aws_s3_object_lock_qualification(
    plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    s3_client: RangerAwsS3ObjectLockS3Client,
    iam_client: RangerAwsS3ObjectLockIamClient,
) -> RangerAwsS3ObjectLockCaptureResult:
    """Run the fixed, bounded capture sequence through caller-injected clients.

    This function makes the capability use explicit: configuration, synthetic object put and
    retention readback, IAM identity-policy simulation, version-specific delete attempt, then
    version-specific retrieval.  It refuses a successful delete and never performs unversioned
    operations or governance-bypass requests.
    """

    digest = hashlib.sha256(plan.archive_bundle_bytes).hexdigest()
    checksum = base64.b64encode(bytes.fromhex(digest)).decode("ascii")
    common = {"Bucket": plan.bucket_name, "ExpectedBucketOwner": plan.aws_account_id}

    versioning_response = _mapping(
        s3_client.get_bucket_versioning(**common), "GetBucketVersioning response"
    )
    lock_response = _mapping(
        s3_client.get_object_lock_configuration(**common), "GetObjectLockConfiguration response"
    )
    put_response = _mapping(
        s3_client.put_object(
            **common,
            Key=plan.object_key,
            Body=plan.archive_bundle_bytes,
            ChecksumAlgorithm="SHA256",
            ChecksumSHA256=checksum,
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=plan.retention_until_utc,
        ),
        "PutObject response",
    )
    version_id = _string(put_response, "VersionId", "PutObject response")
    context = _context(plan, version_id, plan.configuration_observed_at_utc)
    retention_context = _context(plan, version_id, plan.retention_put_observed_at_utc)
    capability_context = _context(plan, version_id, plan.delete_capability_observed_at_utc)
    delete_context = _context(plan, version_id, plan.delete_attempt_observed_at_utc)
    retrieval_context = _context(plan, version_id, plan.retrieval_observed_at_utc)

    retention_response = _mapping(
        s3_client.get_object_retention(
            **common, Key=plan.object_key, VersionId=version_id
        ),
        "GetObjectRetention response",
    )
    resource_arn = f"arn:{plan.aws_partition}:s3:::{plan.bucket_name}/{plan.object_key}"
    capability_response = _mapping(
        iam_client.simulate_principal_policy(
            PolicySourceArn=plan.delete_test_principal_arn,
            ActionNames=["s3:DeleteObjectVersion"],
            ResourceArns=[resource_arn],
        ),
        "SimulatePrincipalPolicy response",
    )

    delete_response = _delete_denial(
        s3_client,
        **common,
        Key=plan.object_key,
        VersionId=version_id,
        BypassGovernanceRetention=False,
    )
    get_response = _mapping(
        s3_client.get_object(
            **common, Key=plan.object_key, VersionId=version_id, ChecksumMode="ENABLED"
        ),
        "GetObject response",
    )
    body = _body_bytes(get_response)
    if len(body) > _MAX_QUALIFICATION_ARCHIVE_BYTES:
        raise RangerAwsS3ObjectLockCaptureError(
            "GetObject body exceeds the qualification size bound"
        )
    if hashlib.sha256(body).hexdigest() != digest:
        raise RangerAwsS3ObjectLockCaptureError("GetObject body digest does not match the put body")
    if _integer(get_response, "ContentLength", "GetObject response") != len(body):
        raise RangerAwsS3ObjectLockCaptureError(
            "GetObject content length does not match retrieved bytes"
        )

    lock_configuration = _mapping(lock_response, "GetObjectLockConfiguration response").get(
        "ObjectLockConfiguration"
    )
    lock_configuration = _mapping(lock_configuration, "ObjectLockConfiguration")
    default_retention = _default_retention(lock_configuration)
    retention = _mapping(retention_response.get("Retention"), "GetObjectRetention Retention")
    results = _sequence(capability_response.get("EvaluationResults"), "IAM EvaluationResults")
    if len(results) != 1:
        raise RangerAwsS3ObjectLockCaptureError("IAM evaluation must contain exactly one result")
    evaluation = _mapping(results[0], "IAM EvaluationResults[0]")

    return RangerAwsS3ObjectLockCaptureResult(
        configuration=RangerAwsS3ObjectLockConfigurationArtifact(
            context=context,
            get_bucket_versioning=RangerAwsS3BucketVersioningObservation(
                status=_string(versioning_response, "Status", "GetBucketVersioning response"),
                metadata=_metadata(versioning_response, "GetBucketVersioning response"),
            ),
            get_object_lock_configuration=RangerAwsS3BucketObjectLockObservation(
                object_lock_enabled=_string(
                    lock_configuration, "ObjectLockEnabled", "ObjectLockConfiguration"
                ),
                default_retention=default_retention,
                metadata=_metadata(lock_response, "GetObjectLockConfiguration response"),
            ),
        ),
        retention_put=RangerAwsS3ObjectLockRetentionPutArtifact(
            context=retention_context,
            put_object=RangerAwsS3PutObjectObservation(
                requested_body_digest_sha256=digest,
                requested_checksum_algorithm="SHA256",
                requested_checksum_sha256_base64=checksum,
                requested_object_lock_mode="COMPLIANCE",
                requested_retain_until_utc=plan.retention_until_utc,
                result_version_id=version_id,
                result_checksum_sha256_base64=_string(
                    put_response, "ChecksumSHA256", "PutObject response"
                ),
                result_checksum_type=_string(put_response, "ChecksumType", "PutObject response"),
                metadata=_metadata(put_response, "PutObject response"),
            ),
            get_object_retention=RangerAwsS3GetObjectRetentionObservation(
                mode=_string(retention, "Mode", "GetObjectRetention Retention"),
                retain_until_utc=_datetime(
                    retention, "RetainUntilDate", "GetObjectRetention Retention"
                ),
                metadata=_metadata(retention_response, "GetObjectRetention response"),
            ),
        ),
        delete_capability=RangerAwsIamDeleteCapabilityArtifact(
            context=capability_context,
            policy_source_arn=plan.delete_test_principal_arn,
            resource_arn=resource_arn,
            evaluation_decision=_string(evaluation, "EvalDecision", "IAM EvaluationResults[0]"),
            response_truncated=_boolean(capability_response, "IsTruncated", "IAM response"),
            metadata=_metadata(capability_response, "SimulatePrincipalPolicy response"),
        ),
        delete_attempt=RangerAwsS3DeleteAttemptArtifact(
            context=delete_context,
            requested_version_id=version_id,
            requested_bypass_governance_retention=False,
            error_code=_string(
                _mapping(delete_response.get("Error"), "DeleteObject Error"),
                "Code",
                "DeleteObject Error",
            ),
            error_message=_string(
                _mapping(delete_response.get("Error"), "DeleteObject Error"),
                "Message",
                "DeleteObject Error",
            ),
            metadata=_metadata(delete_response, "DeleteObject error"),
        ),
        retrieval=RangerAwsS3PostDenialRetrievalArtifact(
            context=retrieval_context,
            get_object=RangerAwsS3GetObjectObservation(
                requested_version_id=version_id,
                requested_checksum_mode="ENABLED",
                result_version_id=_string(get_response, "VersionId", "GetObject response"),
                result_checksum_sha256_base64=_string(
                    get_response, "ChecksumSHA256", "GetObject response"
                ),
                result_checksum_type=_string(get_response, "ChecksumType", "GetObject response"),
                body_digest_sha256=digest,
                content_length_bytes=len(body),
                metadata=_metadata(get_response, "GetObject response"),
            ),
        ),
    )


def _context(
    plan: RangerAwsS3ObjectLockCapturePlan, version_id: str, observed_at_utc: datetime
) -> RangerAwsS3ObjectLockCaptureContext:
    return RangerAwsS3ObjectLockCaptureContext(
        qualification_id=plan.qualification_id,
        verifier_challenge_nonce_hex=plan.verifier_challenge_nonce_hex,
        aws_partition=plan.aws_partition,
        aws_account_id=plan.aws_account_id,
        aws_region=plan.aws_region,
        bucket_name=plan.bucket_name,
        expected_bucket_owner=plan.aws_account_id,
        object_key=plan.object_key,
        object_version_id=version_id,
        delete_test_principal_arn=plan.delete_test_principal_arn,
        observed_at_utc=observed_at_utc,
    )


def _delete_denial(
    s3_client: RangerAwsS3ObjectLockS3Client, **kwargs: object
) -> Mapping[str, object]:
    try:
        s3_client.delete_object(**kwargs)
    except Exception as exc:  # AWS SDKs expose structured errors on the exception instance.
        response = getattr(exc, "response", None)
        return _mapping(response, "DeleteObject error response")
    raise RangerAwsS3ObjectLockCaptureError(
        "DeleteObject unexpectedly succeeded; no denial capture exists"
    )


def _default_retention(configuration: Mapping[str, object]) -> RangerAwsS3DefaultRetention | None:
    rule = configuration.get("Rule")
    if rule is None:
        return None
    default = _mapping(
        _mapping(rule, "ObjectLockConfiguration Rule").get("DefaultRetention"),
        "DefaultRetention",
    )
    observed_mode = _string(default, "Mode", "DefaultRetention")
    if observed_mode == "COMPLIANCE":
        mode: Literal["COMPLIANCE", "GOVERNANCE"] = "COMPLIANCE"
    elif observed_mode == "GOVERNANCE":
        mode = "GOVERNANCE"
    else:
        raise RangerAwsS3ObjectLockCaptureError("DefaultRetention Mode is not recognized")
    return RangerAwsS3DefaultRetention(
        mode=mode,
        days=_optional_positive_integer(default.get("Days"), "DefaultRetention Days"),
        years=_optional_positive_integer(default.get("Years"), "DefaultRetention Years"),
    )


def _metadata(response: Mapping[str, object], label: str) -> RangerAwsS3ResponseMetadata:
    metadata = _mapping(response.get("ResponseMetadata"), f"{label} ResponseMetadata")
    return RangerAwsS3ResponseMetadata(
        http_status_code=_integer(metadata, "HTTPStatusCode", f"{label} ResponseMetadata"),
        request_id=_string(metadata, "RequestId", f"{label} ResponseMetadata"),
        extended_request_id=_optional_string(
            metadata.get("HostId"), f"{label} ResponseMetadata HostId"
        ),
    )


def _body_bytes(response: Mapping[str, object]) -> bytes:
    body = response.get("Body")
    if isinstance(body, bytes):
        return body
    read = getattr(body, "read", None)
    if not callable(read):
        raise RangerAwsS3ObjectLockCaptureError("GetObject Body must be bytes or a readable stream")
    value = read()
    if not isinstance(value, bytes):
        raise RangerAwsS3ObjectLockCaptureError("GetObject Body stream did not return bytes")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RangerAwsS3ObjectLockCaptureError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise RangerAwsS3ObjectLockCaptureError(f"{label} must be a sequence")
    return tuple(value)


def _string(mapping: Mapping[str, object], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise RangerAwsS3ObjectLockCaptureError(f"{label} {key} must be a non-empty string")
    return value


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise RangerAwsS3ObjectLockCaptureError(f"{label} must be a non-empty string when present")
    return value


def _integer(mapping: Mapping[str, object], key: str, label: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RangerAwsS3ObjectLockCaptureError(f"{label} {key} must be an integer")
    return value


def _optional_positive_integer(value: object, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RangerAwsS3ObjectLockCaptureError(f"{label} must be a positive integer when present")
    return value


def _boolean(mapping: Mapping[str, object], key: str, label: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise RangerAwsS3ObjectLockCaptureError(f"{label} {key} must be a boolean")
    return value


def _datetime(mapping: Mapping[str, object], key: str, label: str) -> datetime:
    value = mapping.get(key)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise RangerAwsS3ObjectLockCaptureError(f"{label} {key} must be a timezone-aware datetime")
    return value.astimezone(UTC)


__all__ = [
    "RangerAwsS3ObjectLockCaptureError",
    "RangerAwsS3ObjectLockCapturePlan",
    "RangerAwsS3ObjectLockCaptureResult",
    "RangerAwsS3ObjectLockIamClient",
    "RangerAwsS3ObjectLockS3Client",
    "capture_aws_s3_object_lock_qualification",
]
