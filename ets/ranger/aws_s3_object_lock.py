"""AWS S3 Object Lock evidence verification for Ranger R0.2.

This module composes the provider-neutral immutable-publication qualification with a
provider-specific, versioned capture format for Amazon S3 Object Lock.  It verifies only the
supplied, evidence-issuer-signed control-plane account: versioning and Object Lock configuration,
an explicitly retained object version, a bounded IAM capability simulation, version-specific
delete denial, and exact post-denial retrieval.

The result is not proof that AWS generated the captured bytes, that IAM simulation represents all
effective authorization paths, that retention caused an ``AccessDenied`` response, that storage
media is physically WORM, or that custody is organizationally independent.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonicalize
from ets.ranger.external_publication import RangerExternalPublicationReceipt
from ets.ranger.immutable_publication import (
    RangerImmutableEvidenceArtifactKind,
    RangerImmutableEvidenceEnvironment,
    RangerImmutablePublicationQualification,
    RangerImmutablePublicationVerificationPolicy,
    RangerImmutableRetentionMode,
    verify_immutable_publication_qualification,
)
from ets.ranger.publication_archive import RangerPublicationRetrievalAudit
from ets.ranger.publication_key_lifecycle import (
    RangerPublicationKeyAuthorityEvent,
    RangerPublicationSourceKeyStanding,
)

AWS_S3_OBJECT_LOCK_PROVIDER_ID = "aws:s3-object-lock"
_MAX_ARTIFACT_BYTES = 1024 * 1024


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class RangerAwsS3ObjectLockError(RuntimeError):
    """Raised when an AWS S3 Object Lock evidence artifact cannot be encoded safely."""


class RangerAwsS3ResponseMetadata(StrictModel):
    """Preserved request identity from one AWS API response or error."""

    http_status_code: int = Field(ge=100, le=599)
    request_id: str = Field(min_length=1, max_length=256)
    extended_request_id: str | None = Field(default=None, min_length=1, max_length=2048)


class RangerAwsS3ObjectLockCaptureContext(StrictModel):
    """Verifier-correlatable identity repeated in every trial artifact."""

    qualification_id: str = Field(min_length=1, max_length=256)
    verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    aws_partition: Literal["aws", "aws-us-gov", "aws-cn"]
    aws_account_id: str = Field(pattern=r"^[0-9]{12}$")
    aws_region: str = Field(pattern=r"^[a-z0-9-]{3,32}$")
    bucket_name: str = Field(min_length=3, max_length=63, pattern=r"^[a-z0-9][a-z0-9.-]+[a-z0-9]$")
    expected_bucket_owner: str = Field(pattern=r"^[0-9]{12}$")
    object_key: str = Field(min_length=1, max_length=1024)
    object_version_id: str = Field(min_length=1, max_length=512)
    delete_test_principal_arn: str = Field(min_length=20, max_length=2048)
    observed_at_utc: datetime

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("AWS evidence observation time must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("bucket_name")
    @classmethod
    def reject_ambiguous_bucket_name(cls, value: str) -> str:
        if ".." in value or ".-" in value or "-." in value:
            raise ValueError("AWS S3 bucket name contains an ambiguous dot/hyphen sequence")
        return value

    @field_validator("object_version_id")
    @classmethod
    def require_real_version(cls, value: str) -> str:
        if value == "null":
            raise ValueError("AWS Object Lock evidence requires a non-null object version ID")
        return value

    @model_validator(mode="after")
    def bind_account_identity(self) -> RangerAwsS3ObjectLockCaptureContext:
        if self.expected_bucket_owner != self.aws_account_id:
            raise ValueError("expected bucket owner must equal the pinned AWS account")
        prefix = f"arn:{self.aws_partition}:iam::{self.aws_account_id}:"
        if not self.delete_test_principal_arn.startswith(prefix):
            raise ValueError("delete-test principal ARN is outside the pinned AWS account")
        principal_kind = self.delete_test_principal_arn.removeprefix(prefix).split("/", 1)[0]
        if principal_kind not in {"role", "user"}:
            raise ValueError("delete-test principal must be an AWS IAM role or user ARN")
        return self


class RangerAwsS3DefaultRetention(StrictModel):
    mode: Literal["COMPLIANCE", "GOVERNANCE"]
    days: int | None = Field(default=None, ge=1)
    years: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_one_period(self) -> RangerAwsS3DefaultRetention:
        if (self.days is None) == (self.years is None):
            raise ValueError("AWS default retention must specify exactly one of days or years")
        return self


class RangerAwsS3BucketVersioningObservation(StrictModel):
    status: str
    metadata: RangerAwsS3ResponseMetadata


class RangerAwsS3BucketObjectLockObservation(StrictModel):
    object_lock_enabled: str
    default_retention: RangerAwsS3DefaultRetention | None = None
    metadata: RangerAwsS3ResponseMetadata


class RangerAwsS3ObjectLockConfigurationArtifact(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "aws-s3-object-lock/configuration/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.aws-s3-object-lock.configuration.v1"] = (
        "ets.ranger.aws-s3-object-lock.configuration.v1"
    )
    artifact_kind: Literal[RangerImmutableEvidenceArtifactKind.CONFIGURATION] = (
        RangerImmutableEvidenceArtifactKind.CONFIGURATION
    )
    context: RangerAwsS3ObjectLockCaptureContext
    get_bucket_versioning: RangerAwsS3BucketVersioningObservation
    get_object_lock_configuration: RangerAwsS3BucketObjectLockObservation


class RangerAwsS3PutObjectObservation(StrictModel):
    requested_body_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_checksum_algorithm: str
    requested_checksum_sha256_base64: str = Field(min_length=1, max_length=128)
    requested_object_lock_mode: str
    requested_retain_until_utc: datetime
    result_version_id: str = Field(min_length=1, max_length=512)
    result_checksum_sha256_base64: str = Field(min_length=1, max_length=128)
    result_checksum_type: str
    metadata: RangerAwsS3ResponseMetadata

    @field_validator("requested_retain_until_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("AWS requested retention time must be timezone-aware")
        return value.astimezone(UTC)


class RangerAwsS3GetObjectRetentionObservation(StrictModel):
    mode: str
    retain_until_utc: datetime
    metadata: RangerAwsS3ResponseMetadata

    @field_validator("retain_until_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("AWS observed retention time must be timezone-aware")
        return value.astimezone(UTC)


class RangerAwsS3ObjectLockRetentionPutArtifact(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "aws-s3-object-lock/retention-put/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.aws-s3-object-lock.retention-put.v1"] = (
        "ets.ranger.aws-s3-object-lock.retention-put.v1"
    )
    artifact_kind: Literal[RangerImmutableEvidenceArtifactKind.RETENTION_PUT] = (
        RangerImmutableEvidenceArtifactKind.RETENTION_PUT
    )
    context: RangerAwsS3ObjectLockCaptureContext
    put_object: RangerAwsS3PutObjectObservation
    get_object_retention: RangerAwsS3GetObjectRetentionObservation


class RangerAwsIamDeleteCapabilityArtifact(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "aws-iam/delete-capability/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.aws-iam.delete-capability.v1"] = (
        "ets.ranger.aws-iam.delete-capability.v1"
    )
    artifact_kind: Literal[RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY] = (
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY
    )
    context: RangerAwsS3ObjectLockCaptureContext
    api_operation: Literal["iam:SimulatePrincipalPolicy"] = "iam:SimulatePrincipalPolicy"
    policy_source_arn: str = Field(min_length=20, max_length=2048)
    action_name: Literal["s3:DeleteObjectVersion"] = "s3:DeleteObjectVersion"
    resource_arn: str = Field(min_length=12, max_length=3072)
    evaluation_decision: str
    response_truncated: bool
    metadata: RangerAwsS3ResponseMetadata
    actual_runtime_authorization_proven: Literal[False] = False


class RangerAwsS3DeleteAttemptArtifact(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "aws-s3-object-lock/delete-attempt/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.aws-s3-object-lock.delete-attempt.v1"] = (
        "ets.ranger.aws-s3-object-lock.delete-attempt.v1"
    )
    artifact_kind: Literal[RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT] = (
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT
    )
    context: RangerAwsS3ObjectLockCaptureContext
    api_operation: Literal["s3:DeleteObject"] = "s3:DeleteObject"
    requested_version_id: str = Field(min_length=1, max_length=512)
    requested_bypass_governance_retention: bool
    error_code: str = Field(min_length=1, max_length=256)
    error_message: str = Field(min_length=1, max_length=2048)
    metadata: RangerAwsS3ResponseMetadata
    retention_causality_proven: Literal[False] = False


class RangerAwsS3GetObjectObservation(StrictModel):
    requested_version_id: str = Field(min_length=1, max_length=512)
    requested_checksum_mode: str
    result_version_id: str = Field(min_length=1, max_length=512)
    result_checksum_sha256_base64: str = Field(min_length=1, max_length=128)
    result_checksum_type: str
    body_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_length_bytes: int = Field(ge=1)
    metadata: RangerAwsS3ResponseMetadata


class RangerAwsS3PostDenialRetrievalArtifact(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "$id": (
                "https://lanternprotocol.org/schemas/ets/ranger/"
                "aws-s3-object-lock/retrieval/v1"
            )
        },
    )

    schema_version: Literal["ets.ranger.aws-s3-object-lock.retrieval.v1"] = (
        "ets.ranger.aws-s3-object-lock.retrieval.v1"
    )
    artifact_kind: Literal[RangerImmutableEvidenceArtifactKind.RETRIEVAL] = (
        RangerImmutableEvidenceArtifactKind.RETRIEVAL
    )
    context: RangerAwsS3ObjectLockCaptureContext
    api_operation: Literal["s3:GetObject"] = "s3:GetObject"
    get_object: RangerAwsS3GetObjectObservation


type RangerAwsS3ObjectLockArtifact = (
    RangerAwsS3ObjectLockConfigurationArtifact
    | RangerAwsS3ObjectLockRetentionPutArtifact
    | RangerAwsIamDeleteCapabilityArtifact
    | RangerAwsS3DeleteAttemptArtifact
    | RangerAwsS3PostDenialRetrievalArtifact
)


class RangerAwsS3ObjectLockVerificationPolicy(StrictModel):
    """Independent verifier input; no expected identity is discovered from artifacts."""

    expected_qualification_id: str = Field(min_length=1, max_length=256)
    expected_verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_backend_instance_id: str = Field(min_length=1, max_length=256)
    expected_backend_namespace: str = Field(min_length=1, max_length=512)
    expected_aws_partition: Literal["aws", "aws-us-gov", "aws-cn"]
    expected_aws_account_id: str = Field(pattern=r"^[0-9]{12}$")
    expected_aws_region: str = Field(pattern=r"^[a-z0-9-]{3,32}$")
    expected_bucket_name: str = Field(min_length=3, max_length=63)
    expected_object_key: str = Field(min_length=1, max_length=1024)
    expected_object_version_id: str = Field(min_length=1, max_length=512)
    expected_delete_test_principal_arn: str = Field(min_length=20, max_length=2048)
    expected_archive_bundle_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def require_principal_account(self) -> RangerAwsS3ObjectLockVerificationPolicy:
        prefix = f"arn:{self.expected_aws_partition}:iam::{self.expected_aws_account_id}:"
        if not self.expected_delete_test_principal_arn.startswith(prefix):
            raise ValueError("expected delete-test principal is outside the pinned AWS account")
        return self


class RangerAwsS3ObjectLockQualificationVerification(StrictModel):
    valid: bool
    provider_neutral_qualification_verified: bool = False
    provider_artifact_schemas_verified: bool = False
    provider_artifact_digest_bindings_verified: bool = False
    provider_resource_identity_verified: bool = False
    bucket_versioning_enabled: bool = False
    bucket_object_lock_enabled: bool = False
    full_object_put_checksum_verified: bool = False
    object_compliance_retention_verified: bool = False
    delete_principal_identity_policy_capability_reported: bool = False
    version_specific_delete_access_denied_while_retained: bool = False
    post_denial_version_retrieval_verified: bool = False
    provider_specific_artifact_profile_passed: bool = False
    provider_generated_artifact_authenticity_proven: Literal[False] = False
    complete_effective_authorization_proven: Literal[False] = False
    retention_causality_proven: Literal[False] = False
    physical_worm_storage_proven: Literal[False] = False
    organizational_independence_proven: Literal[False] = False
    hardware_rollback_resistance_proven: Literal[False] = False
    trusted_time_proven: Literal[False] = False
    globally_current_state_proven: Literal[False] = False
    continued_availability_proven: Literal[False] = False
    operational_authorization_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    actuator_response_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


class _ParsedArtifacts(NamedTuple):
    configuration: RangerAwsS3ObjectLockConfigurationArtifact
    retention_put: RangerAwsS3ObjectLockRetentionPutArtifact
    delete_capability: RangerAwsIamDeleteCapabilityArtifact
    delete_attempt: RangerAwsS3DeleteAttemptArtifact
    retrieval: RangerAwsS3PostDenialRetrievalArtifact


def aws_s3_object_lock_artifact_bytes(artifact: RangerAwsS3ObjectLockArtifact) -> bytes:
    """Serialize one normalized provider capture deterministically for content addressing."""

    return canonicalize(artifact.model_dump(mode="json"))


def verify_aws_s3_object_lock_qualification(
    qualification: RangerImmutablePublicationQualification,
    receipts: Iterable[RangerExternalPublicationReceipt],
    publisher_standings: Iterable[RangerPublicationSourceKeyStanding],
    retrieval_audit: RangerPublicationRetrievalAudit,
    retrieval_audit_standing: RangerPublicationSourceKeyStanding,
    authority_events: Iterable[RangerPublicationKeyAuthorityEvent],
    evidence_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
    *,
    qualification_policy: RangerImmutablePublicationVerificationPolicy,
    aws_policy: RangerAwsS3ObjectLockVerificationPolicy,
) -> RangerAwsS3ObjectLockQualificationVerification:
    """Compose generic qualification verification with strict AWS artifact semantics."""

    generic = verify_immutable_publication_qualification(
        qualification,
        receipts,
        publisher_standings,
        retrieval_audit,
        retrieval_audit_standing,
        authority_events,
        evidence_artifacts,
        policy=qualification_policy,
    )
    if not generic.valid:
        return _failure(f"provider-neutral qualification is invalid: {generic.reason}")
    if not generic.provider_control_plane_evidence_profile_passed:
        return _failure(
            "provider-neutral qualification is not a provider-control-plane record",
            provider_neutral_qualification_verified=True,
            provider_artifact_digest_bindings_verified=True,
        )

    try:
        policy = RangerAwsS3ObjectLockVerificationPolicy.model_validate(aws_policy.model_dump())
        record = RangerImmutablePublicationQualification.model_validate(qualification.model_dump())
        artifacts = _parse_artifacts(evidence_artifacts)
    except (AttributeError, RangerAwsS3ObjectLockError, ValidationError) as exc:
        return _failure(
            f"AWS S3 Object Lock artifact schema validation failed: {exc}",
            provider_neutral_qualification_verified=True,
            provider_artifact_digest_bindings_verified=True,
        )

    binding_error = _binding_error(record, artifacts, policy, evidence_artifacts)
    if binding_error is not None:
        return _failure(
            binding_error,
            provider_neutral_qualification_verified=True,
            provider_artifact_schemas_verified=True,
            provider_artifact_digest_bindings_verified=True,
        )

    return RangerAwsS3ObjectLockQualificationVerification(
        valid=True,
        provider_neutral_qualification_verified=True,
        provider_artifact_schemas_verified=True,
        provider_artifact_digest_bindings_verified=True,
        provider_resource_identity_verified=True,
        bucket_versioning_enabled=True,
        bucket_object_lock_enabled=True,
        full_object_put_checksum_verified=True,
        object_compliance_retention_verified=True,
        delete_principal_identity_policy_capability_reported=True,
        version_specific_delete_access_denied_while_retained=True,
        post_denial_version_retrieval_verified=True,
        provider_specific_artifact_profile_passed=True,
        reason=(
            "the evidence issuer signed a provider-neutral qualification whose five canonical "
            "AWS captures report versioned S3 Object Lock COMPLIANCE retention, an IAM "
            "identity-policy delete capability, version-specific AccessDenied, and exact "
            "post-denial retrieval; provider-generated artifact authenticity, complete effective "
            "authorization, denial causality, physical WORM, independence, trusted time, "
            "availability, truth, and physical outcome remain unproven"
        ),
    )


def _binding_error(
    record: RangerImmutablePublicationQualification,
    artifacts: _ParsedArtifacts,
    policy: RangerAwsS3ObjectLockVerificationPolicy,
    raw_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
) -> str | None:
    configured: tuple[tuple[object, object, str], ...] = (
        (record.backend_provider_id, AWS_S3_OBJECT_LOCK_PROVIDER_ID, "backend provider"),
        (record.qualification_id, policy.expected_qualification_id, "qualification identity"),
        (
            record.verifier_challenge_nonce_hex,
            policy.expected_verifier_challenge_nonce_hex,
            "verifier challenge",
        ),
        (
            record.backend_instance_id,
            policy.expected_backend_instance_id,
            "backend instance",
        ),
        (
            record.backend_namespace,
            policy.expected_backend_namespace,
            "backend namespace",
        ),
        (record.object_key, policy.expected_object_key, "object key"),
        (record.object_version_id, policy.expected_object_version_id, "object version"),
        (
            record.delete_test_principal_id,
            policy.expected_delete_test_principal_arn,
            "delete-test principal",
        ),
        (
            record.publication_archive_bundle_digest_sha256,
            policy.expected_archive_bundle_digest_sha256,
            "archive bundle digest",
        ),
        (
            record.evidence_environment,
            RangerImmutableEvidenceEnvironment.PROVIDER_CONTROL_PLANE,
            "evidence environment",
        ),
        (record.versioning_enabled, True, "reported versioning state"),
        (record.retention_mode, RangerImmutableRetentionMode.COMPLIANCE, "retention mode"),
        (record.retention_bypass_permitted, False, "retention bypass state"),
    )
    for observed, expected, label in configured:
        if observed != expected:
            return f"AWS qualification {label} does not match verifier policy"

    artifact_by_kind: dict[RangerImmutableEvidenceArtifactKind, RangerAwsS3ObjectLockArtifact] = {
        RangerImmutableEvidenceArtifactKind.CONFIGURATION: artifacts.configuration,
        RangerImmutableEvidenceArtifactKind.RETENTION_PUT: artifacts.retention_put,
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY: artifacts.delete_capability,
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: artifacts.delete_attempt,
        RangerImmutableEvidenceArtifactKind.RETRIEVAL: artifacts.retrieval,
    }
    digest_error = _artifact_digest_error(record, artifact_by_kind, raw_artifacts)
    if digest_error is not None:
        return digest_error

    expected_context = (
        policy.expected_qualification_id,
        policy.expected_verifier_challenge_nonce_hex,
        policy.expected_aws_partition,
        policy.expected_aws_account_id,
        policy.expected_aws_region,
        policy.expected_bucket_name,
        policy.expected_aws_account_id,
        policy.expected_object_key,
        policy.expected_object_version_id,
        policy.expected_delete_test_principal_arn,
    )
    for kind, artifact in artifact_by_kind.items():
        if _context_identity(artifact.context) != expected_context:
            return f"AWS {kind.value} artifact resource identity does not match verifier policy"

    if artifacts.configuration.context.observed_at_utc != record.configuration_observed_at_utc:
        return "AWS configuration observation time does not match qualification"
    if artifacts.retention_put.context.observed_at_utc != record.retained_at_utc:
        return "AWS retention-put observation time does not match qualification"
    if not (
        record.retained_at_utc
        <= artifacts.delete_capability.context.observed_at_utc
        <= record.delete_attempted_at_utc
    ):
        return "AWS delete-capability observation is outside the retained-to-delete interval"
    if artifacts.delete_attempt.context.observed_at_utc != record.delete_attempted_at_utc:
        return "AWS delete-attempt observation time does not match qualification"
    if artifacts.retrieval.context.observed_at_utc != record.retrieval_observed_at_utc:
        return "AWS retrieval observation time does not match qualification"

    request_ids = _request_ids(artifacts)
    if len(request_ids) != len(set(request_ids)):
        return "AWS artifacts reuse a provider request ID"

    config = artifacts.configuration
    if (
        config.get_bucket_versioning.status != "Enabled"
        or config.get_bucket_versioning.metadata.http_status_code != 200
    ):
        return "AWS GetBucketVersioning did not report Enabled with HTTP 200"
    if (
        config.get_object_lock_configuration.object_lock_enabled != "Enabled"
        or config.get_object_lock_configuration.metadata.http_status_code != 200
    ):
        return "AWS GetObjectLockConfiguration did not report Enabled with HTTP 200"
    if (
        config.get_bucket_versioning.metadata.extended_request_id is None
        or config.get_object_lock_configuration.metadata.extended_request_id is None
    ):
        return "AWS S3 configuration responses are missing extended request IDs"

    retention = artifacts.retention_put
    put = retention.put_object
    observed_retention = retention.get_object_retention
    archive_digest = policy.expected_archive_bundle_digest_sha256
    if (
        put.requested_checksum_algorithm != "SHA256"
        or put.requested_body_digest_sha256 != archive_digest
        or _checksum_hex(put.requested_checksum_sha256_base64) != archive_digest
        or _checksum_hex(put.result_checksum_sha256_base64) != archive_digest
        or put.result_checksum_type != "FULL_OBJECT"
    ):
        return "AWS PutObject does not bind a full-object SHA-256 to the archive bundle"
    if put.result_version_id != policy.expected_object_version_id:
        return "AWS PutObject result version does not match the pinned object version"
    if (
        put.requested_object_lock_mode != "COMPLIANCE"
        or observed_retention.mode != "COMPLIANCE"
        or put.requested_retain_until_utc != record.retention_until_utc
        or observed_retention.retain_until_utc != record.retention_until_utc
    ):
        return "AWS object version does not report the exact COMPLIANCE retention interval"
    if (
        put.metadata.http_status_code != 200
        or observed_retention.metadata.http_status_code != 200
        or put.metadata.extended_request_id is None
        or observed_retention.metadata.extended_request_id is None
    ):
        return "AWS retention-put evidence lacks successful S3 response metadata"

    capability = artifacts.delete_capability
    expected_resource_arn = (
        f"arn:{policy.expected_aws_partition}:s3:::"
        f"{policy.expected_bucket_name}/{policy.expected_object_key}"
    )
    if (
        capability.policy_source_arn != policy.expected_delete_test_principal_arn
        or capability.resource_arn != expected_resource_arn
        or capability.evaluation_decision != "allowed"
        or capability.response_truncated
        or capability.metadata.http_status_code != 200
    ):
        return "AWS IAM evidence does not report a complete allowed DeleteObjectVersion decision"

    deletion = artifacts.delete_attempt
    if (
        deletion.requested_version_id != policy.expected_object_version_id
        or deletion.requested_bypass_governance_retention
        or deletion.error_code != "AccessDenied"
        or deletion.metadata.http_status_code != 403
        or deletion.metadata.extended_request_id is None
    ):
        return "AWS deletion evidence is not a version-specific HTTP 403 AccessDenied response"
    expected_detail = "aws_s3:AccessDenied:http_403"
    if record.delete_result_detail != expected_detail:
        return "AWS deletion detail does not match the normalized provider error"

    retrieval = artifacts.retrieval.get_object
    if (
        retrieval.requested_version_id != policy.expected_object_version_id
        or retrieval.result_version_id != policy.expected_object_version_id
        or retrieval.requested_checksum_mode != "ENABLED"
        or retrieval.result_checksum_type != "FULL_OBJECT"
        or retrieval.body_digest_sha256 != archive_digest
        or _checksum_hex(retrieval.result_checksum_sha256_base64) != archive_digest
        or retrieval.metadata.http_status_code != 200
        or retrieval.metadata.extended_request_id is None
    ):
        return "AWS post-denial GetObject does not return the exact version and archive digest"
    return None


def _artifact_digest_error(
    record: RangerImmutablePublicationQualification,
    artifacts: Mapping[RangerImmutableEvidenceArtifactKind, RangerAwsS3ObjectLockArtifact],
    raw_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
) -> str | None:
    expected = {
        RangerImmutableEvidenceArtifactKind.CONFIGURATION: (
            record.configuration_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.RETENTION_PUT: (
            record.retention_put_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY: (
            record.delete_capability_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT: (
            record.delete_attempt_evidence_digest_sha256
        ),
        RangerImmutableEvidenceArtifactKind.RETRIEVAL: record.retrieval_evidence_digest_sha256,
    }
    normalized = _normalize_raw_artifacts(raw_artifacts)
    for kind, artifact in artifacts.items():
        raw = normalized[kind]
        if hashlib.sha256(raw).hexdigest() != expected[kind]:
            return f"AWS {kind.value} artifact digest does not match qualification"
        if raw != aws_s3_object_lock_artifact_bytes(artifact):
            return f"AWS {kind.value} artifact is not the canonical validated capture"
    return None


def _parse_artifacts(
    evidence_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
) -> _ParsedArtifacts:
    normalized = _normalize_raw_artifacts(evidence_artifacts)
    configuration = _parse_artifact(
        normalized[RangerImmutableEvidenceArtifactKind.CONFIGURATION],
        RangerAwsS3ObjectLockConfigurationArtifact,
    )
    retention_put = _parse_artifact(
        normalized[RangerImmutableEvidenceArtifactKind.RETENTION_PUT],
        RangerAwsS3ObjectLockRetentionPutArtifact,
    )
    delete_capability = _parse_artifact(
        normalized[RangerImmutableEvidenceArtifactKind.DELETE_CAPABILITY],
        RangerAwsIamDeleteCapabilityArtifact,
    )
    delete_attempt = _parse_artifact(
        normalized[RangerImmutableEvidenceArtifactKind.DELETE_ATTEMPT],
        RangerAwsS3DeleteAttemptArtifact,
    )
    retrieval = _parse_artifact(
        normalized[RangerImmutableEvidenceArtifactKind.RETRIEVAL],
        RangerAwsS3PostDenialRetrievalArtifact,
    )
    return _ParsedArtifacts(
        configuration=configuration,
        retention_put=retention_put,
        delete_capability=delete_capability,
        delete_attempt=delete_attempt,
        retrieval=retrieval,
    )


def _normalize_raw_artifacts(
    evidence_artifacts: Mapping[RangerImmutableEvidenceArtifactKind | str, bytes],
) -> dict[RangerImmutableEvidenceArtifactKind, bytes]:
    normalized: dict[RangerImmutableEvidenceArtifactKind, bytes] = {}
    for raw_kind, raw in evidence_artifacts.items():
        try:
            kind = RangerImmutableEvidenceArtifactKind(raw_kind)
        except ValueError as exc:
            raise RangerAwsS3ObjectLockError(f"unexpected AWS artifact kind: {raw_kind}") from exc
        if kind in normalized:
            raise RangerAwsS3ObjectLockError(f"duplicate AWS artifact kind: {kind.value}")
        if not isinstance(raw, bytes) or not raw:
            raise RangerAwsS3ObjectLockError(f"AWS {kind.value} artifact must be non-empty bytes")
        if len(raw) > _MAX_ARTIFACT_BYTES:
            raise RangerAwsS3ObjectLockError(f"AWS {kind.value} artifact exceeds 1 MiB")
        normalized[kind] = raw
    required = set(RangerImmutableEvidenceArtifactKind)
    if set(normalized) != required:
        missing = sorted(kind.value for kind in required - set(normalized))
        unexpected = sorted(kind.value for kind in set(normalized) - required)
        raise RangerAwsS3ObjectLockError(
            f"AWS artifact set is incomplete (missing={missing}, unexpected={unexpected})"
        )
    return normalized


def _parse_artifact[ModelT: BaseModel](raw: bytes, model: type[ModelT]) -> ModelT:
    try:
        decoded = raw.decode("utf-8")
        parsed = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RangerAwsS3ObjectLockError) as exc:
        raise RangerAwsS3ObjectLockError("AWS artifact is not strict UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise RangerAwsS3ObjectLockError("AWS artifact root must be a JSON object")
    if canonicalize(parsed) != raw:
        raise RangerAwsS3ObjectLockError("AWS artifact JSON must use ETS canonical encoding")
    try:
        return model.model_validate_json(raw, strict=True)
    except ValidationError as exc:
        raise RangerAwsS3ObjectLockError(str(exc)) from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RangerAwsS3ObjectLockError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise RangerAwsS3ObjectLockError(f"invalid JSON numeric constant: {value}")


def _context_identity(context: RangerAwsS3ObjectLockCaptureContext) -> tuple[str, ...]:
    return (
        context.qualification_id,
        context.verifier_challenge_nonce_hex,
        context.aws_partition,
        context.aws_account_id,
        context.aws_region,
        context.bucket_name,
        context.expected_bucket_owner,
        context.object_key,
        context.object_version_id,
        context.delete_test_principal_arn,
    )


def _request_ids(artifacts: _ParsedArtifacts) -> list[str]:
    return [
        artifacts.configuration.get_bucket_versioning.metadata.request_id,
        artifacts.configuration.get_object_lock_configuration.metadata.request_id,
        artifacts.retention_put.put_object.metadata.request_id,
        artifacts.retention_put.get_object_retention.metadata.request_id,
        artifacts.delete_capability.metadata.request_id,
        artifacts.delete_attempt.metadata.request_id,
        artifacts.retrieval.get_object.metadata.request_id,
    ]


def _checksum_hex(value: str) -> str | None:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(decoded) != 32:
        return None
    return decoded.hex()


def _failure(
    reason: str,
    *,
    provider_neutral_qualification_verified: bool = False,
    provider_artifact_schemas_verified: bool = False,
    provider_artifact_digest_bindings_verified: bool = False,
) -> RangerAwsS3ObjectLockQualificationVerification:
    return RangerAwsS3ObjectLockQualificationVerification(
        valid=False,
        provider_neutral_qualification_verified=provider_neutral_qualification_verified,
        provider_artifact_schemas_verified=provider_artifact_schemas_verified,
        provider_artifact_digest_bindings_verified=(
            provider_artifact_digest_bindings_verified
        ),
        reason=reason,
    )


__all__ = [
    "AWS_S3_OBJECT_LOCK_PROVIDER_ID",
    "RangerAwsIamDeleteCapabilityArtifact",
    "RangerAwsS3BucketObjectLockObservation",
    "RangerAwsS3BucketVersioningObservation",
    "RangerAwsS3DefaultRetention",
    "RangerAwsS3DeleteAttemptArtifact",
    "RangerAwsS3GetObjectObservation",
    "RangerAwsS3GetObjectRetentionObservation",
    "RangerAwsS3ObjectLockCaptureContext",
    "RangerAwsS3ObjectLockConfigurationArtifact",
    "RangerAwsS3ObjectLockError",
    "RangerAwsS3ObjectLockQualificationVerification",
    "RangerAwsS3ObjectLockRetentionPutArtifact",
    "RangerAwsS3ObjectLockVerificationPolicy",
    "RangerAwsS3PostDenialRetrievalArtifact",
    "RangerAwsS3PutObjectObservation",
    "RangerAwsS3ResponseMetadata",
    "aws_s3_object_lock_artifact_bytes",
    "verify_aws_s3_object_lock_qualification",
]
