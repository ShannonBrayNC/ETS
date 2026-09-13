"""Credential-isolated CloudTrail evidence capture for Ranger R0.2.

The adapter accepts caller-constructed, capability-limited CloudTrail and S3 clients. It does not
import an AWS SDK, locate credentials, or select endpoints. Before either client is invoked it
verifies the signed Ranger AWS execution package and a separately signed CloudTrail read scope.
Simulation authorization additionally requires explicitly marked test doubles.

The returned bundle is suitable as input to the provider-boundary verifier. Capturing a public key
or selector response does not independently authenticate it, prove complete CloudTrail coverage,
or prove provider execution; those claims remain false.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, runtime_checkable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import Field, ValidationError, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.ranger.aws_cloudtrail_provider_evidence import (
    RangerAwsCloudTrailVerification,
    RangerAwsCloudTrailVerificationPolicy,
    verify_aws_cloudtrail_provider_evidence,
)
from ets.ranger.aws_s3_object_lock import StrictModel
from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ExecutionEnvironment,
    RangerAwsS3ObjectLockCapturePlan,
    aws_s3_object_lock_capture_plan_digest,
)
from ets.ranger.aws_s3_object_lock_execution import (
    RangerAwsS3ExecutionPackage,
    RangerAwsS3ExecutionReceiptPolicy,
    execution_authorization_record_digest,
    verify_aws_s3_execution_receipt,
)

_MAX_COMPRESSED_OBJECT_BYTES = 32 * 1024 * 1024
_MAX_DIGEST_BYTES = 2 * 1024 * 1024


class RangerAwsCloudTrailCaptureError(RuntimeError):
    """Raised before a partial or ambiguous provider evidence bundle can escape."""


@runtime_checkable
class RangerAwsCloudTrailClient(Protocol):
    """Minimal injected CloudTrail capability required by the passive capture."""

    ets_ranger_simulation: bool

    def list_public_keys(self, **kwargs: object) -> Mapping[str, object]: ...

    def get_event_selectors(self, **kwargs: object) -> Mapping[str, object]: ...


@runtime_checkable
class RangerAwsCloudTrailS3Client(Protocol):
    """Minimal injected S3 read capability required by the passive capture."""

    ets_ranger_simulation: bool

    def get_object(self, **kwargs: object) -> Mapping[str, object]: ...


class RangerAwsCloudTrailCapturePlan(StrictModel):
    """Independent, bounded inputs for one passive CloudTrail evidence read."""

    trail_name: str = Field(min_length=1, max_length=1024)
    aws_account_id: str = Field(pattern=r"^[0-9]{12}$")
    aws_region: str = Field(pattern=r"^[a-z0-9-]{3,32}$")
    digest_s3_bucket: str = Field(min_length=3, max_length=63)
    digest_s3_object: str = Field(min_length=1, max_length=2048)
    expected_public_key_fingerprint: str = Field(pattern=r"^[0-9A-Fa-f]{16,128}$")
    expected_public_key_der_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    window_start_utc: datetime
    window_end_utc: datetime
    maximum_log_files: int = Field(ge=1, le=256)
    maximum_log_file_bytes: int = Field(ge=1, le=128 * 1024 * 1024)
    maximum_event_time_skew_seconds: int = Field(ge=0, le=3600)

    @field_validator("window_start_utc", "window_end_utc")
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("CloudTrail capture times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_bounded_window(self) -> RangerAwsCloudTrailCapturePlan:
        if self.window_start_utc >= self.window_end_utc:
            raise ValueError("CloudTrail capture window is invalid")
        if (self.window_end_utc - self.window_start_utc).total_seconds() > 86_400:
            raise ValueError("CloudTrail capture window exceeds 24 hours")
        return self


def aws_cloudtrail_capture_plan_digest(plan: RangerAwsCloudTrailCapturePlan) -> str:
    """Return the ETS canonical hash for one exact passive-read plan."""

    validated = RangerAwsCloudTrailCapturePlan.model_validate(plan.model_dump())
    return canonical_sha256(
        {
            "schema_version": "ets.ranger.aws-cloudtrail-capture-plan-digest.v1",
            "plan": validated.model_dump(mode="json"),
        }
    )


class RangerAwsCloudTrailReadAuthorization(StrictModel):
    """Separately signed, bounded authority for passive CloudTrail evidence reads."""

    schema_version: Literal["ets.ranger.aws-cloudtrail-read-authorization.v1"] = (
        "ets.ranger.aws-cloudtrail-read-authorization.v1"
    )
    authorization_id: str = Field(min_length=1, max_length=256)
    base_execution_authorization_id: str = Field(min_length=1, max_length=256)
    base_authorization_record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_receipt_id: str = Field(min_length=1, max_length=256)
    execution_receipt_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    s3_capture_plan_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cloudtrail_capture_plan_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_id: str = Field(min_length=1, max_length=256)
    verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_environment: RangerAwsS3ExecutionEnvironment
    aws_partition: Literal["aws", "aws-us-gov", "aws-cn"]
    aws_account_id: str = Field(pattern=r"^[0-9]{12}$")
    aws_region: str = Field(pattern=r"^[a-z0-9-]{3,32}$")
    trail_name: str = Field(min_length=1, max_length=1024)
    digest_s3_bucket: str = Field(min_length=3, max_length=63)
    digest_s3_object: str = Field(min_length=1, max_length=2048)
    expected_public_key_fingerprint: str = Field(pattern=r"^[0-9A-Fa-f]{16,128}$")
    expected_public_key_der_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    window_start_utc: datetime
    window_end_utc: datetime
    maximum_log_files: int = Field(ge=1, le=256)
    maximum_log_file_bytes: int = Field(ge=1, le=128 * 1024 * 1024)
    maximum_event_time_skew_seconds: int = Field(ge=0, le=3600)
    permitted_operation_profile: Literal[
        "cloudtrail_list_public_keys_get_event_selectors_and_s3_get_object"
    ] = "cloudtrail_list_public_keys_get_event_selectors_and_s3_get_object"
    maximum_cloudtrail_calls: Literal[2] = 2
    maximum_s3_get_object_calls: int = Field(ge=2, le=257)
    issued_at_utc: datetime
    not_before_utc: datetime
    expires_at_utc: datetime
    approved_cost_ceiling_usd_cents: int = Field(ge=0, le=100_000)
    cloud_read_authorized: bool
    spending_authorized: bool
    authorizer_id: str = Field(min_length=1, max_length=160)
    authorizer_signing_key_id: str = Field(min_length=1, max_length=256)
    authorizer_public_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_algorithm: Literal["ed25519"] = "ed25519"
    authorization_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorizer_signature_hex: str = Field(pattern=r"^[0-9a-f]{128}$")
    human_identity_proven: Literal[False] = False
    independent_budget_approval_proven: Literal[False] = False
    effective_aws_permissions_proven: Literal[False] = False
    provider_execution_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_read_scope_authority_no_human_budget_permission_or_execution_proof"
    ] = "configured_read_scope_authority_no_human_budget_permission_or_execution_proof"

    @field_validator(
        "window_start_utc",
        "window_end_utc",
        "issued_at_utc",
        "not_before_utc",
        "expires_at_utc",
    )
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("CloudTrail read authorization times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_bounded_authority(self) -> RangerAwsCloudTrailReadAuthorization:
        if self.window_start_utc >= self.window_end_utc:
            raise ValueError("CloudTrail evidence window is invalid")
        if (self.window_end_utc - self.window_start_utc).total_seconds() > 86_400:
            raise ValueError("CloudTrail evidence window exceeds 24 hours")
        if not self.issued_at_utc <= self.not_before_utc < self.expires_at_utc:
            raise ValueError("CloudTrail read authorization interval is invalid")
        if self.maximum_s3_get_object_calls != self.maximum_log_files + 1:
            raise ValueError(
                "CloudTrail read authorization S3 call bound must cover exactly the digest "
                "plus log bound"
            )
        if self.execution_environment is RangerAwsS3ExecutionEnvironment.SIMULATION:
            if self.cloud_read_authorized or self.spending_authorized:
                raise ValueError(
                    "simulation read authorization cannot authorize cloud use or spending"
                )
        elif not (self.cloud_read_authorized and self.spending_authorized):
            raise ValueError(
                "non-production CloudTrail reads require explicit read and spending flags"
            )
        return self


class RangerAwsCloudTrailReadAuthorizationPolicy(StrictModel):
    """Independent trust, freshness, environment, and cost expectations for a read scope."""

    expected_authorization_id: str = Field(min_length=1, max_length=256)
    expected_base_execution_authorization_id: str = Field(min_length=1, max_length=256)
    expected_execution_receipt_id: str = Field(min_length=1, max_length=256)
    expected_qualification_id: str = Field(min_length=1, max_length=256)
    expected_verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_execution_environment: RangerAwsS3ExecutionEnvironment
    expected_authorizer_id: str = Field(min_length=1, max_length=160)
    expected_authorizer_signing_key_id: str = Field(min_length=1, max_length=256)
    authorizer_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_time_utc: datetime
    maximum_cost_ceiling_usd_cents: int = Field(ge=0, le=100_000)
    maximum_authorization_lifetime_seconds: int = Field(ge=1, le=86_400)

    @field_validator("verification_time_utc")
    @classmethod
    def require_verification_time_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("read authorization verification time must be timezone-aware")
        return value.astimezone(UTC)


class RangerAwsCloudTrailReadAuthorizationVerification(StrictModel):
    valid: bool
    authorization_id: str | None = None
    cloudtrail_capture_plan_digest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    configured_authorizer_signature_proven: bool = False
    exact_read_scope_authorized: bool = False
    reason: str


def build_aws_cloudtrail_read_authorization(
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    capture_plan: RangerAwsCloudTrailCapturePlan,
    *,
    authorization_id: str,
    issued_at_utc: datetime,
    not_before_utc: datetime,
    expires_at_utc: datetime,
    approved_cost_ceiling_usd_cents: int,
    cloud_read_authorized: bool,
    spending_authorized: bool,
    authorizer_id: str,
    authorizer_signing_key_id: str,
    authorizer_private_key_hex: str,
) -> RangerAwsCloudTrailReadAuthorization:
    """Build a separately signed authority over exactly one passive-read plan."""

    try:
        record = RangerAwsS3ExecutionPackage.model_validate(package.model_dump())
        base_authorization = RangerAwsS3ExecutionAuthorization.model_validate(
            authorization.model_dump()
        )
        validated_s3_plan = RangerAwsS3ObjectLockCapturePlan.model_validate(s3_plan.model_dump())
        validated_plan = RangerAwsCloudTrailCapturePlan.model_validate(capture_plan.model_dump())
        private_key = Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(authorizer_private_key_hex)
        )
    except (AttributeError, ValidationError, TypeError, ValueError) as exc:
        raise RangerAwsCloudTrailCaptureError(
            "invalid CloudTrail read authorization inputs or 32-byte Ed25519 private key"
        ) from exc
    _require_capture_plan_matches_s3_plan(validated_plan, validated_s3_plan)
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    unsigned: dict[str, Any] = {
        "schema_version": "ets.ranger.aws-cloudtrail-read-authorization.v1",
        "authorization_id": authorization_id,
        "base_execution_authorization_id": base_authorization.authorization_id,
        "base_authorization_record_digest_sha256": execution_authorization_record_digest(
            base_authorization
        ),
        "execution_receipt_id": record.execution_receipt.receipt_id,
        "execution_receipt_digest_sha256": canonical_sha256(
            record.execution_receipt.model_dump(mode="json")
        ),
        "s3_capture_plan_digest_sha256": aws_s3_object_lock_capture_plan_digest(validated_s3_plan),
        "cloudtrail_capture_plan_digest_sha256": aws_cloudtrail_capture_plan_digest(validated_plan),
        "qualification_id": validated_s3_plan.qualification_id,
        "verifier_challenge_nonce_hex": validated_s3_plan.verifier_challenge_nonce_hex,
        "execution_environment": base_authorization.execution_environment,
        "aws_partition": validated_s3_plan.aws_partition,
        "aws_account_id": validated_plan.aws_account_id,
        "aws_region": validated_plan.aws_region,
        "trail_name": validated_plan.trail_name,
        "digest_s3_bucket": validated_plan.digest_s3_bucket,
        "digest_s3_object": validated_plan.digest_s3_object,
        "expected_public_key_fingerprint": validated_plan.expected_public_key_fingerprint,
        "expected_public_key_der_sha256": validated_plan.expected_public_key_der_sha256,
        "window_start_utc": validated_plan.window_start_utc,
        "window_end_utc": validated_plan.window_end_utc,
        "maximum_log_files": validated_plan.maximum_log_files,
        "maximum_log_file_bytes": validated_plan.maximum_log_file_bytes,
        "maximum_event_time_skew_seconds": (validated_plan.maximum_event_time_skew_seconds),
        "permitted_operation_profile": (
            "cloudtrail_list_public_keys_get_event_selectors_and_s3_get_object"
        ),
        "maximum_cloudtrail_calls": 2,
        "maximum_s3_get_object_calls": validated_plan.maximum_log_files + 1,
        "issued_at_utc": issued_at_utc,
        "not_before_utc": not_before_utc,
        "expires_at_utc": expires_at_utc,
        "approved_cost_ceiling_usd_cents": approved_cost_ceiling_usd_cents,
        "cloud_read_authorized": cloud_read_authorized,
        "spending_authorized": spending_authorized,
        "authorizer_id": authorizer_id,
        "authorizer_signing_key_id": authorizer_signing_key_id,
        "authorizer_public_key_fingerprint_sha256": hashlib.sha256(public_bytes).hexdigest(),
        "signing_algorithm": "ed25519",
        "human_identity_proven": False,
        "independent_budget_approval_proven": False,
        "effective_aws_permissions_proven": False,
        "provider_execution_proven": False,
        "claim_boundary": (
            "configured_read_scope_authority_no_human_budget_permission_or_execution_proof"
        ),
    }
    try:
        candidate = RangerAwsCloudTrailReadAuthorization.model_validate(
            {
                **unsigned,
                "authorization_digest_sha256": "0" * 64,
                "authorizer_signature_hex": "0" * 128,
            }
        )
        payload = _read_authorization_payload(candidate)
        return RangerAwsCloudTrailReadAuthorization.model_validate(
            candidate.model_copy(
                update={
                    "authorization_digest_sha256": canonical_sha256(payload),
                    "authorizer_signature_hex": private_key.sign(canonicalize(payload)).hex(),
                }
            ).model_dump()
        )
    except ValidationError as exc:
        raise RangerAwsCloudTrailCaptureError(
            "invalid CloudTrail read authorization fields"
        ) from exc


def verify_aws_cloudtrail_read_authorization(
    read_authorization: RangerAwsCloudTrailReadAuthorization,
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    capture_plan: RangerAwsCloudTrailCapturePlan,
    *,
    policy: RangerAwsCloudTrailReadAuthorizationPolicy,
) -> RangerAwsCloudTrailReadAuthorizationVerification:
    """Verify a dedicated read scope against exact prior and planned evidence."""

    try:
        record = RangerAwsCloudTrailReadAuthorization.model_validate(
            read_authorization.model_dump()
        )
        package_record = RangerAwsS3ExecutionPackage.model_validate(package.model_dump())
        base_authorization = RangerAwsS3ExecutionAuthorization.model_validate(
            authorization.model_dump()
        )
        validated_s3_plan = RangerAwsS3ObjectLockCapturePlan.model_validate(s3_plan.model_dump())
        validated_plan = RangerAwsCloudTrailCapturePlan.model_validate(capture_plan.model_dump())
        configured = RangerAwsCloudTrailReadAuthorizationPolicy.model_validate(policy.model_dump())
    except (AttributeError, ValidationError):
        return _read_authorization_failure("CloudTrail read authorization schema validation failed")
    if (
        record.authorization_id != configured.expected_authorization_id
        or record.base_execution_authorization_id
        != configured.expected_base_execution_authorization_id
        or record.execution_receipt_id != configured.expected_execution_receipt_id
        or record.qualification_id != configured.expected_qualification_id
        or record.verifier_challenge_nonce_hex != configured.expected_verifier_challenge_nonce_hex
        or record.execution_environment != configured.expected_execution_environment
        or record.authorizer_id != configured.expected_authorizer_id
        or record.authorizer_signing_key_id != configured.expected_authorizer_signing_key_id
    ):
        return _read_authorization_failure(
            "CloudTrail read authorization policy identity or scope mismatch"
        )
    if not record.not_before_utc <= configured.verification_time_utc < record.expires_at_utc:
        return _read_authorization_failure("CloudTrail read authorization is not currently valid")
    lifetime_seconds = (record.expires_at_utc - record.issued_at_utc).total_seconds()
    if lifetime_seconds > configured.maximum_authorization_lifetime_seconds:
        return _read_authorization_failure("CloudTrail read authorization lifetime exceeds policy")
    if record.approved_cost_ceiling_usd_cents > configured.maximum_cost_ceiling_usd_cents:
        return _read_authorization_failure(
            "CloudTrail read authorization exceeds the configured cost ceiling"
        )
    try:
        _require_capture_plan_matches_s3_plan(validated_plan, validated_s3_plan)
    except RangerAwsCloudTrailCaptureError as exc:
        return _read_authorization_failure(str(exc))
    if (
        record.base_execution_authorization_id != base_authorization.authorization_id
        or record.base_authorization_record_digest_sha256
        != execution_authorization_record_digest(base_authorization)
        or record.execution_receipt_id != package_record.execution_receipt.receipt_id
        or record.execution_receipt_digest_sha256
        != canonical_sha256(package_record.execution_receipt.model_dump(mode="json"))
        or record.s3_capture_plan_digest_sha256
        != aws_s3_object_lock_capture_plan_digest(validated_s3_plan)
        or record.cloudtrail_capture_plan_digest_sha256
        != aws_cloudtrail_capture_plan_digest(validated_plan)
    ):
        return _read_authorization_failure(
            "CloudTrail read authorization prior-evidence or capture-plan binding mismatch"
        )
    if record.not_before_utc < package_record.execution_receipt.receipt_issued_at_utc:
        return _read_authorization_failure(
            "CloudTrail read authorization begins before the bound execution receipt"
        )
    if (
        record.qualification_id != validated_s3_plan.qualification_id
        or record.verifier_challenge_nonce_hex != validated_s3_plan.verifier_challenge_nonce_hex
        or record.execution_environment != base_authorization.execution_environment
        or record.aws_partition != validated_s3_plan.aws_partition
        or record.aws_account_id != validated_plan.aws_account_id
        or record.aws_region != validated_plan.aws_region
        or record.trail_name != validated_plan.trail_name
        or record.digest_s3_bucket != validated_plan.digest_s3_bucket
        or record.digest_s3_object != validated_plan.digest_s3_object
        or record.expected_public_key_fingerprint.lower()
        != validated_plan.expected_public_key_fingerprint.lower()
        or record.expected_public_key_der_sha256 != validated_plan.expected_public_key_der_sha256
        or record.window_start_utc != validated_plan.window_start_utc
        or record.window_end_utc != validated_plan.window_end_utc
        or record.maximum_log_files != validated_plan.maximum_log_files
        or record.maximum_log_file_bytes != validated_plan.maximum_log_file_bytes
        or record.maximum_event_time_skew_seconds != validated_plan.maximum_event_time_skew_seconds
        or record.maximum_s3_get_object_calls != validated_plan.maximum_log_files + 1
    ):
        return _read_authorization_failure(
            "CloudTrail read authorization resource or bounded-read scope mismatch"
        )
    try:
        public_bytes = bytes.fromhex(configured.authorizer_public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
    except ValueError:
        return _read_authorization_failure(
            "CloudTrail read authorizer public key is not 32-byte Ed25519"
        )
    if record.authorizer_public_key_fingerprint_sha256 != hashlib.sha256(public_bytes).hexdigest():
        return _read_authorization_failure("CloudTrail read authorization key fingerprint mismatch")
    payload = _read_authorization_payload(record)
    if canonical_sha256(payload) != record.authorization_digest_sha256:
        return _read_authorization_failure("CloudTrail read authorization digest mismatch")
    try:
        public_key.verify(bytes.fromhex(record.authorizer_signature_hex), canonicalize(payload))
    except (InvalidSignature, ValueError):
        return _read_authorization_failure("CloudTrail read authorization signature invalid")
    if record.execution_environment is RangerAwsS3ExecutionEnvironment.AUTHORIZED_NON_PRODUCTION:
        if not (record.cloud_read_authorized and record.spending_authorized):
            return _read_authorization_failure(
                "CloudTrail read or spending is not explicitly authorized"
            )
    return RangerAwsCloudTrailReadAuthorizationVerification(
        valid=True,
        authorization_id=record.authorization_id,
        cloudtrail_capture_plan_digest_sha256=(record.cloudtrail_capture_plan_digest_sha256),
        configured_authorizer_signature_proven=True,
        exact_read_scope_authorized=True,
        reason=(
            "configured read-scope signature and policy match the exact receipt-bound "
            "CloudTrail plan; human identity, independent budget approval, effective AWS "
            "permissions, and provider execution are not proven"
        ),
    )


class RangerAwsCloudTrailPublicKeyObservation(StrictModel):
    fingerprint: str = Field(pattern=r"^[0-9A-Fa-f]{16,128}$")
    public_key_der_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validity_start_utc: datetime
    validity_end_utc: datetime
    list_public_keys_request_id: str = Field(min_length=1, max_length=1024)


class RangerAwsCloudTrailSelectorObservation(StrictModel):
    trail_name: str = Field(min_length=1, max_length=1024)
    event_selectors_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    advanced_event_selectors_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    get_event_selectors_request_id: str = Field(min_length=1, max_length=1024)


class RangerAwsCloudTrailCaptureBundle(StrictModel):
    """Secret-free verifier inputs plus bounded capture observations."""

    schema_version: Literal["ets.ranger.aws-cloudtrail-capture.v2"] = (
        "ets.ranger.aws-cloudtrail-capture.v2"
    )
    digest_file_bytes: bytes
    digest_signature_hex: str = Field(pattern=r"^[0-9a-f]+$")
    cloudtrail_public_key_der: bytes
    uncompressed_log_files: dict[str, bytes]
    public_key_observation: RangerAwsCloudTrailPublicKeyObservation
    selector_observation: RangerAwsCloudTrailSelectorObservation
    execution_receipt_verified_before_calls: Literal[True] = True
    injected_client_boundary_enforced: Literal[True] = True
    read_scope_authorization_id: str = Field(min_length=1, max_length=256)
    read_scope_authorization_record_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    configured_read_scope_signature_verified: Literal[True] = True
    read_scope_authorizer_independence_proven: Literal[False] = False
    aws_public_key_provenance_independently_verified: Literal[False] = False
    complete_cloudtrail_coverage_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False


def capture_aws_cloudtrail_provider_evidence(
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    capture_plan: RangerAwsCloudTrailCapturePlan,
    read_authorization: RangerAwsCloudTrailReadAuthorization,
    read_authorization_policy: RangerAwsCloudTrailReadAuthorizationPolicy,
    cloudtrail_client: RangerAwsCloudTrailClient,
    s3_client: RangerAwsCloudTrailS3Client,
) -> RangerAwsCloudTrailCaptureBundle:
    """Read one bounded digest/log/key/selector set through injected clients."""

    receipt = verify_aws_s3_execution_receipt(
        package, authorization, s3_plan, policy=receipt_policy
    )
    if not receipt.valid:
        raise RangerAwsCloudTrailCaptureError(f"execution receipt is invalid: {receipt.reason}")
    read_scope = verify_aws_cloudtrail_read_authorization(
        read_authorization,
        package,
        authorization,
        s3_plan,
        capture_plan,
        policy=read_authorization_policy,
    )
    if not read_scope.valid:
        raise RangerAwsCloudTrailCaptureError(
            f"CloudTrail read authorization is invalid: {read_scope.reason}"
        )
    if read_scope.authorization_id is None:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail read authorization verified without an authorization ID"
        )
    try:
        plan = RangerAwsCloudTrailCapturePlan.model_validate(capture_plan.model_dump())
    except (AttributeError, ValidationError) as exc:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail capture plan schema validation failed"
        ) from exc
    if plan.aws_account_id != s3_plan.aws_account_id or plan.aws_region != s3_plan.aws_region:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail capture account or Region does not match the execution package"
        )
    if authorization.execution_environment is RangerAwsS3ExecutionEnvironment.SIMULATION and not (
        getattr(cloudtrail_client, "ets_ranger_simulation", False) is True
        and getattr(s3_client, "ets_ranger_simulation", False) is True
    ):
        raise RangerAwsCloudTrailCaptureError(
            "simulation authorization requires explicitly marked test-double clients"
        )

    keys_response = _mapping(
        cloudtrail_client.list_public_keys(
            StartTime=plan.window_start_utc,
            EndTime=plan.window_end_utc,
        ),
        "ListPublicKeys response",
    )
    if keys_response.get("NextToken") not in (None, ""):
        raise RangerAwsCloudTrailCaptureError(
            "ListPublicKeys pagination is unsupported for a bounded capture"
        )
    public_key, key_observation = _select_public_key(keys_response, plan)

    selectors_response = _mapping(
        cloudtrail_client.get_event_selectors(TrailName=plan.trail_name),
        "GetEventSelectors response",
    )
    selector_observation = _selector_observation(selectors_response, plan.trail_name)

    digest_response = _mapping(
        s3_client.get_object(
            Bucket=plan.digest_s3_bucket,
            Key=plan.digest_s3_object,
            ExpectedBucketOwner=plan.aws_account_id,
        ),
        "digest GetObject response",
    )
    metadata = _mapping(digest_response.get("Metadata"), "digest metadata")
    signature = _string(metadata, "signature", "digest metadata").lower()
    if metadata.get("signature-algorithm") != "SHA256withRSA":
        raise RangerAwsCloudTrailCaptureError(
            "digest metadata signature algorithm is not SHA256withRSA"
        )
    if any(character not in "0123456789abcdef" for character in signature):
        raise RangerAwsCloudTrailCaptureError("digest metadata signature is not hexadecimal")
    digest_bytes = _uncompressed_body(
        digest_response,
        "CloudTrail digest",
        maximum_uncompressed_bytes=_MAX_DIGEST_BYTES,
    )
    digest = _json_object(digest_bytes, "CloudTrail digest")
    digest_end = _utc_datetime(digest.get("digestEndTime"), "digestEndTime")
    if not (key_observation.validity_start_utc <= digest_end <= key_observation.validity_end_utc):
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail public-key validity does not cover the digest end time"
        )
    references = digest.get("logFiles")
    if not isinstance(references, list) or not references:
        raise RangerAwsCloudTrailCaptureError("CloudTrail digest contains no log-file references")
    if len(references) > plan.maximum_log_files:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail digest exceeds the capture log-file count limit"
        )

    logs: dict[str, bytes] = {}
    for reference in references:
        if not isinstance(reference, dict):
            raise RangerAwsCloudTrailCaptureError("CloudTrail log-file reference is not an object")
        bucket = reference.get("s3Bucket")
        key = reference.get("s3Object")
        if not isinstance(bucket, str) or not isinstance(key, str):
            raise RangerAwsCloudTrailCaptureError(
                "CloudTrail log-file reference location is invalid"
            )
        path = f"{bucket}/{key}"
        if path in logs:
            raise RangerAwsCloudTrailCaptureError(
                "CloudTrail digest contains a duplicate log-file path"
            )
        response = _mapping(
            s3_client.get_object(
                Bucket=bucket,
                Key=key,
                ExpectedBucketOwner=plan.aws_account_id,
            ),
            "log GetObject response",
        )
        content = _uncompressed_body(
            response,
            f"CloudTrail log {path}",
            maximum_uncompressed_bytes=plan.maximum_log_file_bytes,
        )
        logs[path] = content

    return RangerAwsCloudTrailCaptureBundle(
        digest_file_bytes=digest_bytes,
        digest_signature_hex=signature,
        cloudtrail_public_key_der=public_key,
        uncompressed_log_files=logs,
        public_key_observation=key_observation,
        selector_observation=selector_observation,
        read_scope_authorization_id=read_scope.authorization_id,
        read_scope_authorization_record_digest_sha256=canonical_sha256(
            RangerAwsCloudTrailReadAuthorization.model_validate(
                read_authorization.model_dump()
            ).model_dump(mode="json")
        ),
    )


def capture_and_verify_aws_cloudtrail_provider_evidence(
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    capture_plan: RangerAwsCloudTrailCapturePlan,
    read_authorization: RangerAwsCloudTrailReadAuthorization,
    read_authorization_policy: RangerAwsCloudTrailReadAuthorizationPolicy,
    cloudtrail_client: RangerAwsCloudTrailClient,
    s3_client: RangerAwsCloudTrailS3Client,
) -> tuple[RangerAwsCloudTrailCaptureBundle, RangerAwsCloudTrailVerification]:
    """Capture and immediately pass the exact bytes to the independent verifier."""

    bundle = capture_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        s3_plan,
        receipt_policy=receipt_policy,
        capture_plan=capture_plan,
        read_authorization=read_authorization,
        read_authorization_policy=read_authorization_policy,
        cloudtrail_client=cloudtrail_client,
        s3_client=s3_client,
    )
    policy = RangerAwsCloudTrailVerificationPolicy(
        expected_digest_s3_bucket=capture_plan.digest_s3_bucket,
        expected_digest_s3_object=capture_plan.digest_s3_object,
        expected_public_key_fingerprint=capture_plan.expected_public_key_fingerprint,
        expected_public_key_der_sha256=capture_plan.expected_public_key_der_sha256,
        maximum_log_files=capture_plan.maximum_log_files,
        maximum_log_file_bytes=capture_plan.maximum_log_file_bytes,
        maximum_event_time_skew_seconds=(capture_plan.maximum_event_time_skew_seconds),
    )
    verification = verify_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        s3_plan,
        receipt_policy=receipt_policy,
        cloudtrail_policy=policy,
        digest_file_bytes=bundle.digest_file_bytes,
        digest_signature_hex=bundle.digest_signature_hex,
        cloudtrail_public_key_der=bundle.cloudtrail_public_key_der,
        uncompressed_log_files=bundle.uncompressed_log_files,
    )
    return bundle, verification


def _require_capture_plan_matches_s3_plan(
    capture_plan: RangerAwsCloudTrailCapturePlan,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
) -> None:
    if (
        capture_plan.aws_account_id != s3_plan.aws_account_id
        or capture_plan.aws_region != s3_plan.aws_region
    ):
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail capture account or Region does not match the execution package"
        )


def _read_authorization_payload(
    authorization: RangerAwsCloudTrailReadAuthorization,
) -> dict[str, Any]:
    return authorization.model_dump(
        mode="json", exclude={"authorization_digest_sha256", "authorizer_signature_hex"}
    )


def _read_authorization_failure(
    reason: str,
) -> RangerAwsCloudTrailReadAuthorizationVerification:
    return RangerAwsCloudTrailReadAuthorizationVerification(valid=False, reason=reason)


def _select_public_key(
    response: Mapping[str, object], plan: RangerAwsCloudTrailCapturePlan
) -> tuple[bytes, RangerAwsCloudTrailPublicKeyObservation]:
    keys = response.get("PublicKeyList")
    if not isinstance(keys, list):
        raise RangerAwsCloudTrailCaptureError("ListPublicKeys PublicKeyList is missing")
    matches = [
        item
        for item in keys
        if isinstance(item, Mapping)
        and str(item.get("Fingerprint", "")).lower() == plan.expected_public_key_fingerprint.lower()
    ]
    if len(matches) != 1:
        raise RangerAwsCloudTrailCaptureError(
            "ListPublicKeys must contain exactly one pinned fingerprint"
        )
    key = matches[0]
    value = key.get("Value")
    start = key.get("ValidityStartTime")
    end = key.get("ValidityEndTime")
    if not (isinstance(value, bytes) and isinstance(start, datetime) and isinstance(end, datetime)):
        raise RangerAwsCloudTrailCaptureError("ListPublicKeys entry has invalid fields")
    if start.tzinfo is None or end.tzinfo is None:
        raise RangerAwsCloudTrailCaptureError("ListPublicKeys validity times are not aware")
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    if end < plan.window_start_utc or start > plan.window_end_utc:
        raise RangerAwsCloudTrailCaptureError(
            "pinned CloudTrail public-key validity does not intersect the capture window"
        )
    digest = hashlib.sha256(value).hexdigest()
    if digest != plan.expected_public_key_der_sha256:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail public-key bytes do not match the independently pinned SHA-256"
        )
    return value, RangerAwsCloudTrailPublicKeyObservation(
        fingerprint=str(key["Fingerprint"]),
        public_key_der_sha256=digest,
        validity_start_utc=start,
        validity_end_utc=end,
        list_public_keys_request_id=_request_id(response, "ListPublicKeys response"),
    )


def _selector_observation(
    response: Mapping[str, object], trail_name: str
) -> RangerAwsCloudTrailSelectorObservation:
    event_selectors = response.get("EventSelectors", [])
    advanced = response.get("AdvancedEventSelectors", [])
    if not isinstance(event_selectors, list) or not isinstance(advanced, list):
        raise RangerAwsCloudTrailCaptureError("GetEventSelectors arrays are invalid")
    return RangerAwsCloudTrailSelectorObservation(
        trail_name=trail_name,
        event_selectors_sha256=_canonical_digest(event_selectors),
        advanced_event_selectors_sha256=_canonical_digest(advanced),
        get_event_selectors_request_id=_request_id(response, "GetEventSelectors response"),
    )


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _uncompressed_body(
    response: Mapping[str, object],
    label: str,
    *,
    maximum_uncompressed_bytes: int,
) -> bytes:
    body = response.get("Body")
    reader = getattr(body, "read", None)
    if not callable(reader):
        raise RangerAwsCloudTrailCaptureError(f"{label} body is not readable")
    compressed = reader(_MAX_COMPRESSED_OBJECT_BYTES + 1)
    if not isinstance(compressed, bytes) or not compressed:
        raise RangerAwsCloudTrailCaptureError(f"{label} body is empty or non-bytes")
    if len(compressed) > _MAX_COMPRESSED_OBJECT_BYTES:
        raise RangerAwsCloudTrailCaptureError(f"{label} compressed body exceeds limit")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            uncompressed = stream.read(maximum_uncompressed_bytes + 1)
    except (OSError, EOFError) as exc:
        raise RangerAwsCloudTrailCaptureError(f"{label} body is not valid gzip") from exc
    if len(uncompressed) > maximum_uncompressed_bytes:
        raise RangerAwsCloudTrailCaptureError(f"{label} uncompressed body exceeds limit")
    return uncompressed


def _json_object(content: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RangerAwsCloudTrailCaptureError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RangerAwsCloudTrailCaptureError(f"{label} root is not an object")
    return value


def _utc_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise RangerAwsCloudTrailCaptureError(f"CloudTrail {label} is not a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RangerAwsCloudTrailCaptureError(
            f"CloudTrail {label} is not an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RangerAwsCloudTrailCaptureError(f"CloudTrail {label} is not timezone-aware")
    return parsed.astimezone(UTC)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RangerAwsCloudTrailCaptureError(f"{label} is not a mapping")
    return value


def _string(value: Mapping[str, object], key: str, label: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise RangerAwsCloudTrailCaptureError(f"{label} {key} is missing")
    return item


def _request_id(response: Mapping[str, object], label: str) -> str:
    metadata = _mapping(response.get("ResponseMetadata"), f"{label} metadata")
    return _string(metadata, "RequestId", f"{label} metadata")
