"""Two-phase Ranger R0.2 AWS qualification orchestration.

The CloudTrail read scope binds the execution receipt, which does not exist until the Object Lock
capture completes. This module therefore makes the post-capture authorization boundary explicit:
it captures and verifies the execution package, asks a caller-supplied authority for the exact
receipt-bound read scope, and only then permits the bounded CloudTrail evidence reads.

All provider clients and the read-scope provider are injected. This module imports no AWS SDK,
discovers no credentials, and does not claim that configured authority, provider execution,
capture completeness, physical WORM storage, or signer independence has been proven.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import ValidationError

from ets.ranger.aws_cloudtrail_capture import (
    RangerAwsCloudTrailCaptureBundle,
    RangerAwsCloudTrailCaptureError,
    RangerAwsCloudTrailCapturePlan,
    RangerAwsCloudTrailClient,
    RangerAwsCloudTrailReadAuthorization,
    RangerAwsCloudTrailReadAuthorizationPolicy,
    RangerAwsCloudTrailS3Client,
    capture_and_verify_aws_cloudtrail_provider_evidence,
)
from ets.ranger.aws_cloudtrail_provider_evidence import RangerAwsCloudTrailVerification
from ets.ranger.aws_s3_object_lock import StrictModel
from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ExecutionAuthorizationPolicy,
    RangerAwsS3ObjectLockCapturePlan,
    RangerAwsS3ObjectLockIamClient,
    RangerAwsS3ObjectLockS3Client,
)
from ets.ranger.aws_s3_object_lock_execution import (
    RangerAwsS3ExecutionPackage,
    RangerAwsS3ExecutionReceiptPolicy,
    capture_aws_s3_object_lock_qualification_with_receipt,
    verify_aws_s3_execution_receipt,
)


class RangerAwsQualificationOrchestrationError(RuntimeError):
    """Raised when the composed qualification cannot advance safely."""

    def __init__(
        self,
        message: str,
        *,
        execution_package: RangerAwsS3ExecutionPackage | None = None,
    ) -> None:
        super().__init__(message)
        self.execution_package = execution_package


class RangerAwsCloudTrailReadScope(StrictModel):
    """Exact signed scope and independent verification policy returned after S3 capture."""

    authorization: RangerAwsCloudTrailReadAuthorization
    policy: RangerAwsCloudTrailReadAuthorizationPolicy


@runtime_checkable
class RangerAwsCloudTrailReadScopeProvider(Protocol):
    """Caller-controlled authority boundary invoked only after receipt verification."""

    def authorize(
        self,
        package: RangerAwsS3ExecutionPackage,
        authorization: RangerAwsS3ExecutionAuthorization,
        s3_plan: RangerAwsS3ObjectLockCapturePlan,
        cloudtrail_plan: RangerAwsCloudTrailCapturePlan,
    ) -> RangerAwsCloudTrailReadScope: ...


class RangerAwsQualificationRun(StrictModel):
    """Successful software evidence chain returned by the two-phase orchestrator."""

    schema_version: Literal["ets.ranger.aws-qualification-run.v1"] = (
        "ets.ranger.aws-qualification-run.v1"
    )
    execution_package: RangerAwsS3ExecutionPackage
    cloudtrail_capture: RangerAwsCloudTrailCaptureBundle
    cloudtrail_verification: RangerAwsCloudTrailVerification
    execution_receipt_verified_before_read_scope_request: Literal[True] = True
    read_scope_verified_before_provider_reads: Literal[True] = True
    injected_provider_boundaries_enforced: Literal[True] = True
    configured_execution_and_read_signatures_verified: Literal[True] = True
    effective_aws_permissions_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False
    capture_completeness_proven: Literal[False] = False
    signer_independence_proven: Literal[False] = False
    physical_worm_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    claim_boundary: Literal[
        "configured_two_phase_authority_and_evidence_binding_no_permission_execution_"
        "completeness_independence_custody_or_physical_outcome_proof"
    ] = (
        "configured_two_phase_authority_and_evidence_binding_no_permission_execution_"
        "completeness_independence_custody_or_physical_outcome_proof"
    )


def run_aws_object_lock_qualification(
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    execution_authorization: RangerAwsS3ExecutionAuthorization,
    execution_authorization_policy: RangerAwsS3ExecutionAuthorizationPolicy,
    object_lock_s3_client: RangerAwsS3ObjectLockS3Client,
    iam_client: RangerAwsS3ObjectLockIamClient,
    receipt_id: str,
    receipt_issued_at_utc: datetime,
    recorder_id: str,
    recorder_signing_key_id: str,
    recorder_private_key_hex: str,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    cloudtrail_plan: RangerAwsCloudTrailCapturePlan,
    read_scope_provider: RangerAwsCloudTrailReadScopeProvider,
    cloudtrail_client: RangerAwsCloudTrailClient,
    cloudtrail_s3_client: RangerAwsCloudTrailS3Client,
) -> RangerAwsQualificationRun:
    """Run the guarded S3 stage, obtain exact post-receipt authority, then verify CloudTrail."""

    package = capture_aws_s3_object_lock_qualification_with_receipt(
        s3_plan,
        authorization=execution_authorization,
        authorization_policy=execution_authorization_policy,
        s3_client=object_lock_s3_client,
        iam_client=iam_client,
        receipt_id=receipt_id,
        receipt_issued_at_utc=receipt_issued_at_utc,
        recorder_id=recorder_id,
        recorder_signing_key_id=recorder_signing_key_id,
        recorder_private_key_hex=recorder_private_key_hex,
    )
    receipt = verify_aws_s3_execution_receipt(
        package,
        execution_authorization,
        s3_plan,
        policy=receipt_policy,
    )
    if not receipt.valid:
        raise RangerAwsQualificationOrchestrationError(
            f"new execution receipt is invalid: {receipt.reason}",
            execution_package=package,
        )
    try:
        scope = RangerAwsCloudTrailReadScope.model_validate(
            read_scope_provider.authorize(
                package,
                execution_authorization,
                s3_plan,
                cloudtrail_plan,
            ).model_dump()
        )
    except (AttributeError, ValidationError) as exc:
        raise RangerAwsQualificationOrchestrationError(
            "read-scope provider returned an invalid response",
            execution_package=package,
        ) from exc
    try:
        bundle, verification = capture_and_verify_aws_cloudtrail_provider_evidence(
            package,
            execution_authorization,
            s3_plan,
            receipt_policy=receipt_policy,
            capture_plan=cloudtrail_plan,
            read_authorization=scope.authorization,
            read_authorization_policy=scope.policy,
            cloudtrail_client=cloudtrail_client,
            s3_client=cloudtrail_s3_client,
        )
    except RangerAwsCloudTrailCaptureError as exc:
        raise RangerAwsQualificationOrchestrationError(
            str(exc), execution_package=package
        ) from exc
    if not verification.valid:
        raise RangerAwsQualificationOrchestrationError(
            f"CloudTrail provider evidence is invalid: {verification.reason}",
            execution_package=package,
        )
    return RangerAwsQualificationRun(
        execution_package=package,
        cloudtrail_capture=bundle,
        cloudtrail_verification=verification,
    )


__all__ = [
    "RangerAwsCloudTrailReadScope",
    "RangerAwsCloudTrailReadScopeProvider",
    "RangerAwsQualificationOrchestrationError",
    "RangerAwsQualificationRun",
    "run_aws_object_lock_qualification",
]
