"""Offline verification for a complete Ranger R0.2 AWS qualification run.

The verifier requires both complete signed authorization records, their independent policies,
and both capture plans. It replays the execution receipt, receipt-bound CloudTrail read scope,
and provider evidence verification without invoking an AWS client or discovering credentials.

A valid result proves only configured signatures and internal cross-stage evidence binding. It
does not prove effective provider permissions, provider execution, capture completeness, signer
independence, physical WORM custody, or a physical Ranger outcome.
"""

from __future__ import annotations

from typing import Literal

from pydantic import ValidationError

from ets.core.canonical_json import canonical_sha256
from ets.ranger.aws_cloudtrail_capture import (
    RangerAwsCloudTrailCapturePlan,
    RangerAwsCloudTrailReadAuthorization,
    RangerAwsCloudTrailReadAuthorizationPolicy,
    verify_aws_cloudtrail_read_authorization,
)
from ets.ranger.aws_cloudtrail_provider_evidence import (
    RangerAwsCloudTrailVerificationPolicy,
    verify_aws_cloudtrail_provider_evidence,
)
from ets.ranger.aws_qualification_orchestrator import RangerAwsQualificationRun
from ets.ranger.aws_s3_object_lock import StrictModel
from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ObjectLockCapturePlan,
)
from ets.ranger.aws_s3_object_lock_execution import (
    RangerAwsS3ExecutionReceiptPolicy,
    verify_aws_s3_execution_receipt,
)


class RangerAwsQualificationRunVerification(StrictModel):
    """Offline finding for one complete two-phase qualification run."""

    schema_version: Literal["ets.ranger.aws-qualification-run-verification.v1"] = (
        "ets.ranger.aws-qualification-run-verification.v1"
    )
    valid: bool
    execution_receipt_verified: bool = False
    read_authorization_verified: bool = False
    complete_read_authorization_record_bound: bool = False
    provider_evidence_replayed: bool = False
    stored_verification_matches_replay: bool = False
    cross_stage_binding_verified: bool = False
    effective_aws_permissions_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False
    capture_completeness_proven: Literal[False] = False
    signer_independence_proven: Literal[False] = False
    physical_worm_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


def verify_aws_qualification_run(
    run: RangerAwsQualificationRun,
    execution_authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    cloudtrail_plan: RangerAwsCloudTrailCapturePlan,
    read_authorization: RangerAwsCloudTrailReadAuthorization,
    read_authorization_policy: RangerAwsCloudTrailReadAuthorizationPolicy,
) -> RangerAwsQualificationRunVerification:
    """Replay a complete run offline and reject missing or cross-run signed records."""

    try:
        record = RangerAwsQualificationRun.model_validate(run.model_dump())
        execution_scope = RangerAwsS3ExecutionAuthorization.model_validate(
            execution_authorization.model_dump()
        )
        execution_plan = RangerAwsS3ObjectLockCapturePlan.model_validate(s3_plan.model_dump())
        receipt_trust = RangerAwsS3ExecutionReceiptPolicy.model_validate(
            receipt_policy.model_dump()
        )
        trail_plan = RangerAwsCloudTrailCapturePlan.model_validate(cloudtrail_plan.model_dump())
        read_scope = RangerAwsCloudTrailReadAuthorization.model_validate(
            read_authorization.model_dump()
        )
        read_trust = RangerAwsCloudTrailReadAuthorizationPolicy.model_validate(
            read_authorization_policy.model_dump()
        )
    except (AttributeError, ValidationError):
        return _failure("qualification run or required signed-record input schema is invalid")

    receipt = verify_aws_s3_execution_receipt(
        record.execution_package,
        execution_scope,
        execution_plan,
        policy=receipt_trust,
    )
    if not receipt.valid:
        return _failure(f"execution receipt is invalid: {receipt.reason}")

    read_result = verify_aws_cloudtrail_read_authorization(
        read_scope,
        record.execution_package,
        execution_scope,
        execution_plan,
        trail_plan,
        policy=read_trust,
    )
    if not read_result.valid:
        return _failure(
            f"CloudTrail read authorization is invalid: {read_result.reason}",
            receipt=True,
        )

    bundle = record.cloudtrail_capture
    signed_record_digest = canonical_sha256(read_scope.model_dump(mode="json"))
    if (
        bundle.read_scope_authorization_id != read_scope.authorization_id
        or bundle.read_scope_authorization_record_digest_sha256 != signed_record_digest
    ):
        return _failure(
            "CloudTrail capture is not bound to the supplied complete signed read authorization",
            receipt=True,
            read_scope=True,
        )

    replayed = verify_aws_cloudtrail_provider_evidence(
        record.execution_package,
        execution_scope,
        execution_plan,
        receipt_policy=receipt_trust,
        cloudtrail_policy=RangerAwsCloudTrailVerificationPolicy(
            expected_digest_s3_bucket=trail_plan.digest_s3_bucket,
            expected_digest_s3_object=trail_plan.digest_s3_object,
            expected_public_key_fingerprint=trail_plan.expected_public_key_fingerprint,
            expected_public_key_der_sha256=trail_plan.expected_public_key_der_sha256,
            maximum_log_files=trail_plan.maximum_log_files,
            maximum_log_file_bytes=trail_plan.maximum_log_file_bytes,
            maximum_event_time_skew_seconds=trail_plan.maximum_event_time_skew_seconds,
        ),
        digest_file_bytes=bundle.digest_file_bytes,
        digest_signature_hex=bundle.digest_signature_hex,
        cloudtrail_public_key_der=bundle.cloudtrail_public_key_der,
        uncompressed_log_files=bundle.uncompressed_log_files,
    )
    if not replayed.valid:
        return _failure(
            f"CloudTrail provider evidence replay is invalid: {replayed.reason}",
            receipt=True,
            read_scope=True,
            record_bound=True,
        )
    if replayed != record.cloudtrail_verification:
        return _failure(
            "stored CloudTrail verification does not match independent replay",
            receipt=True,
            read_scope=True,
            record_bound=True,
            evidence=True,
        )

    return RangerAwsQualificationRunVerification(
        valid=True,
        execution_receipt_verified=True,
        read_authorization_verified=True,
        complete_read_authorization_record_bound=True,
        provider_evidence_replayed=True,
        stored_verification_matches_replay=True,
        cross_stage_binding_verified=True,
        reason=(
            "configured execution and read signatures, exact complete-record binding, and "
            "provider evidence replay verified; permissions, provider execution, completeness, "
            "signer independence, physical WORM custody, and physical outcome are not proven"
        ),
    )


def _failure(
    reason: str,
    *,
    receipt: bool = False,
    read_scope: bool = False,
    record_bound: bool = False,
    evidence: bool = False,
) -> RangerAwsQualificationRunVerification:
    return RangerAwsQualificationRunVerification(
        valid=False,
        execution_receipt_verified=receipt,
        read_authorization_verified=read_scope,
        complete_read_authorization_record_bound=record_bound,
        provider_evidence_replayed=evidence,
        reason=reason,
    )


__all__ = [
    "RangerAwsQualificationRunVerification",
    "verify_aws_qualification_run",
]
