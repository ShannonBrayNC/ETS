"""Secret-free artifact inventory for a controlled Ranger AWS qualification.

The manifest contains identifiers and canonical SHA-256 digests only. Complete authorization,
trust-policy, plan, run, and verification artifacts remain separately retained inputs. Building or
verifying a manifest performs no provider calls and discovers no credentials.
"""

from __future__ import annotations

import base64
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.ranger.aws_cloudtrail_capture import (
    RangerAwsCloudTrailCapturePlan,
    RangerAwsCloudTrailReadAuthorization,
    RangerAwsCloudTrailReadAuthorizationPolicy,
)
from ets.ranger.aws_qualification_orchestrator import RangerAwsQualificationRun
from ets.ranger.aws_qualification_run_verifier import (
    RangerAwsQualificationRunVerification,
    verify_aws_qualification_run,
)
from ets.ranger.aws_s3_object_lock import StrictModel
from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ObjectLockCapturePlan,
)
from ets.ranger.aws_s3_object_lock_execution import RangerAwsS3ExecutionReceiptPolicy


class RangerAwsQualificationArtifactKind(str, Enum):
    """Required, separately retained artifact roles for one qualification package."""

    EXECUTION_AUTHORIZATION = "execution_authorization"
    S3_CAPTURE_PLAN = "s3_capture_plan"
    EXECUTION_RECEIPT_POLICY = "execution_receipt_policy"
    CLOUDTRAIL_CAPTURE_PLAN = "cloudtrail_capture_plan"
    CLOUDTRAIL_READ_AUTHORIZATION = "cloudtrail_read_authorization"
    CLOUDTRAIL_READ_AUTHORIZATION_POLICY = "cloudtrail_read_authorization_policy"
    QUALIFICATION_RUN = "qualification_run"
    QUALIFICATION_RUN_VERIFICATION = "qualification_run_verification"


_REQUIRED_KINDS = tuple(RangerAwsQualificationArtifactKind)


class RangerAwsQualificationArtifactInventoryEntry(StrictModel):
    """One content-addressed artifact role without embedding artifact bytes."""

    kind: RangerAwsQualificationArtifactKind
    canonical_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RangerAwsQualificationEvidenceManifest(StrictModel):
    """Secret-free inventory for one complete controlled qualification evidence set."""

    schema_version: Literal["ets.ranger.aws-qualification-evidence-manifest.v1"] = (
        "ets.ranger.aws-qualification-evidence-manifest.v1"
    )
    package_id: str = Field(min_length=1, max_length=256)
    qualification_id: str = Field(min_length=1, max_length=256)
    verifier_challenge_nonce_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_authorization_id: str = Field(min_length=1, max_length=256)
    execution_receipt_id: str = Field(min_length=1, max_length=256)
    cloudtrail_read_authorization_id: str = Field(min_length=1, max_length=256)
    artifacts: tuple[RangerAwsQualificationArtifactInventoryEntry, ...]
    manifest_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_bytes_embedded: Literal[False] = False
    credentials_embedded: Literal[False] = False
    private_keys_embedded: Literal[False] = False
    configured_signatures_replayed: Literal[True] = True
    effective_aws_permissions_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False
    capture_completeness_proven: Literal[False] = False
    physical_worm_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    manifest_authenticity_proven: Literal[False] = False
    claim_boundary: Literal[
        "secret_free_complete_artifact_inventory_no_permission_execution_completeness_"
        "custody_physical_outcome_or_manifest_authenticity_proof"
    ] = (
        "secret_free_complete_artifact_inventory_no_permission_execution_completeness_"
        "custody_physical_outcome_or_manifest_authenticity_proof"
    )

    @model_validator(mode="after")
    def require_exact_artifact_inventory(self) -> RangerAwsQualificationEvidenceManifest:
        kinds = tuple(entry.kind for entry in self.artifacts)
        if kinds != _REQUIRED_KINDS:
            raise ValueError("qualification manifest requires each artifact kind once in order")
        return self


class RangerAwsQualificationEvidenceManifestVerification(StrictModel):
    """Offline finding for manifest completeness and exact artifact identity."""

    schema_version: Literal[
        "ets.ranger.aws-qualification-evidence-manifest-verification.v1"
    ] = "ets.ranger.aws-qualification-evidence-manifest-verification.v1"
    valid: bool
    manifest_digest_verified: bool = False
    complete_inventory_verified: bool = False
    qualification_run_replayed: bool = False
    exact_artifact_digests_verified: bool = False
    manifest_authenticity_proven: Literal[False] = False
    provider_execution_independently_proven: Literal[False] = False
    physical_worm_proven: Literal[False] = False
    physical_outcome_proven: Literal[False] = False
    reason: str


def build_aws_qualification_evidence_manifest(
    package_id: str,
    run: RangerAwsQualificationRun,
    execution_authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    cloudtrail_plan: RangerAwsCloudTrailCapturePlan,
    read_authorization: RangerAwsCloudTrailReadAuthorization,
    read_authorization_policy: RangerAwsCloudTrailReadAuthorizationPolicy,
) -> tuple[RangerAwsQualificationEvidenceManifest, RangerAwsQualificationRunVerification]:
    """Build a digest-only inventory after complete offline run verification succeeds."""

    verification = verify_aws_qualification_run(
        run,
        execution_authorization,
        s3_plan,
        receipt_policy=receipt_policy,
        cloudtrail_plan=cloudtrail_plan,
        read_authorization=read_authorization,
        read_authorization_policy=read_authorization_policy,
    )
    if not verification.valid:
        raise ValueError(f"qualification run is invalid: {verification.reason}")
    artifacts = _inventory(
        run,
        execution_authorization,
        s3_plan,
        receipt_policy,
        cloudtrail_plan,
        read_authorization,
        read_authorization_policy,
        verification,
    )
    candidate = RangerAwsQualificationEvidenceManifest(
        package_id=package_id,
        qualification_id=s3_plan.qualification_id,
        verifier_challenge_nonce_hex=s3_plan.verifier_challenge_nonce_hex,
        execution_authorization_id=execution_authorization.authorization_id,
        execution_receipt_id=run.execution_package.execution_receipt.receipt_id,
        cloudtrail_read_authorization_id=read_authorization.authorization_id,
        artifacts=artifacts,
        manifest_digest_sha256="0" * 64,
    )
    manifest = RangerAwsQualificationEvidenceManifest.model_validate(
        candidate.model_copy(
            update={"manifest_digest_sha256": _manifest_digest(candidate)}
        ).model_dump()
    )
    return manifest, verification


def verify_aws_qualification_evidence_manifest(
    manifest: RangerAwsQualificationEvidenceManifest,
    run_verification: RangerAwsQualificationRunVerification,
    run: RangerAwsQualificationRun,
    execution_authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    cloudtrail_plan: RangerAwsCloudTrailCapturePlan,
    read_authorization: RangerAwsCloudTrailReadAuthorization,
    read_authorization_policy: RangerAwsCloudTrailReadAuthorizationPolicy,
) -> RangerAwsQualificationEvidenceManifestVerification:
    """Require the complete originals, replay verification, and match every manifest digest."""

    try:
        record = RangerAwsQualificationEvidenceManifest.model_validate(manifest.model_dump())
        supplied_finding = RangerAwsQualificationRunVerification.model_validate(
            run_verification.model_dump()
        )
    except (AttributeError, ValidationError):
        return _failure("qualification evidence manifest or run finding schema is invalid")
    if _manifest_digest(record) != record.manifest_digest_sha256:
        return _failure("qualification evidence manifest digest mismatch")
    try:
        expected, replayed = build_aws_qualification_evidence_manifest(
            record.package_id,
            run,
            execution_authorization,
            s3_plan,
            receipt_policy=receipt_policy,
            cloudtrail_plan=cloudtrail_plan,
            read_authorization=read_authorization,
            read_authorization_policy=read_authorization_policy,
        )
    except (AttributeError, ValidationError, ValueError) as exc:
        return _failure(
            f"complete qualification evidence replay failed: {exc}",
            digest=True,
            inventory=True,
        )
    if supplied_finding != replayed:
        return _failure(
            "supplied qualification-run finding does not match independent replay",
            digest=True,
            inventory=True,
            replay=True,
        )
    if record != expected:
        return _failure(
            "qualification evidence manifest identifiers or artifact digests differ",
            digest=True,
            inventory=True,
            replay=True,
        )
    return RangerAwsQualificationEvidenceManifestVerification(
        valid=True,
        manifest_digest_verified=True,
        complete_inventory_verified=True,
        qualification_run_replayed=True,
        exact_artifact_digests_verified=True,
        reason=(
            "complete secret-free artifact inventory and offline run replay verified; manifest "
            "authenticity, provider execution, physical WORM custody, and outcome are not proven"
        ),
    )


def _inventory(
    run: RangerAwsQualificationRun,
    execution_authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    cloudtrail_plan: RangerAwsCloudTrailCapturePlan,
    read_authorization: RangerAwsCloudTrailReadAuthorization,
    read_authorization_policy: RangerAwsCloudTrailReadAuthorizationPolicy,
    run_verification: RangerAwsQualificationRunVerification,
) -> tuple[RangerAwsQualificationArtifactInventoryEntry, ...]:
    values = (
        execution_authorization,
        s3_plan,
        receipt_policy,
        cloudtrail_plan,
        read_authorization,
        read_authorization_policy,
        run,
        run_verification,
    )
    return tuple(
        RangerAwsQualificationArtifactInventoryEntry(
            kind=kind,
            canonical_digest_sha256=_artifact_digest(kind, value),
        )
        for kind, value in zip(_REQUIRED_KINDS, values, strict=True)
    )


def _artifact_digest(kind: RangerAwsQualificationArtifactKind, value: StrictModel) -> str:
    return canonical_sha256(
        {
            "schema_version": "ets.ranger.aws-qualification-artifact-digest.v1",
            "artifact_kind": kind.value,
            "artifact": _json_safe(value.model_dump(mode="python")),
        }
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "base64", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _manifest_digest(manifest: RangerAwsQualificationEvidenceManifest) -> str:
    return canonical_sha256(
        manifest.model_dump(mode="json", exclude={"manifest_digest_sha256"})
    )


def _failure(
    reason: str,
    *,
    digest: bool = False,
    inventory: bool = False,
    replay: bool = False,
) -> RangerAwsQualificationEvidenceManifestVerification:
    return RangerAwsQualificationEvidenceManifestVerification(
        valid=False,
        manifest_digest_verified=digest,
        complete_inventory_verified=inventory,
        qualification_run_replayed=replay,
        reason=reason,
    )


__all__ = [
    "RangerAwsQualificationArtifactInventoryEntry",
    "RangerAwsQualificationArtifactKind",
    "RangerAwsQualificationEvidenceManifest",
    "RangerAwsQualificationEvidenceManifestVerification",
    "build_aws_qualification_evidence_manifest",
    "verify_aws_qualification_evidence_manifest",
]
