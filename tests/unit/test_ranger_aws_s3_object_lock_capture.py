"""Deterministic integration coverage for the credential-isolated S3 capture adapter."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ExecutionAuthorizationPolicy,
    RangerAwsS3ExecutionEnvironment,
    RangerAwsS3ObjectLockCaptureError,
    RangerAwsS3ObjectLockCapturePlan,
    RangerAwsS3ObjectLockCaptureResult,
    build_aws_s3_execution_authorization,
    capture_aws_s3_object_lock_qualification,
    verify_aws_s3_execution_authorization,
)
from ets.ranger.immutable_publication import RangerImmutableEvidenceArtifactKind

NOW = datetime(2026, 9, 12, 20, 0, tzinfo=UTC)
ARCHIVE = b"ETS Ranger synthetic Object Lock qualification archive\n"
ACCOUNT = "123456789012"
BUCKET = "ets-ranger-qualification"
KEY = "r0.2/synthetic-archive.json"
PRINCIPAL = "arn:aws:iam::123456789012:role/ranger-delete-probe"
PRIVATE_KEY_HEX = "11" * 32
PUBLIC_KEY_HEX = (
    Ed25519PrivateKey.from_private_bytes(bytes.fromhex(PRIVATE_KEY_HEX))
    .public_key()
    .public_bytes(Encoding.Raw, PublicFormat.Raw)
    .hex()
)


class _StubAwsError(RuntimeError):
    def __init__(self, response: dict[str, object]) -> None:
        super().__init__("stub AWS error")
        self.response = response


class _Body:
    def __init__(self, value: bytes) -> None:
        self.value = value
        self.read_count = 0

    def read(self) -> bytes:
        self.read_count += 1
        return self.value


class _S3Stub:
    ets_ranger_simulation = True

    def __init__(self, archive: bytes = ARCHIVE, *, delete_succeeds: bool = False) -> None:
        self.archive = archive
        self.delete_succeeds = delete_succeeds
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.body = _Body(archive)

    def get_bucket_versioning(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_bucket_versioning", kwargs))
        return {"Status": "Enabled", "ResponseMetadata": _meta(1)}

    def get_object_lock_configuration(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_object_lock_configuration", kwargs))
        return {
            "ObjectLockConfiguration": {"ObjectLockEnabled": "Enabled"},
            "ResponseMetadata": _meta(2),
        }

    def put_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("put_object", kwargs))
        return {
            "VersionId": "version-123",
            "ChecksumSHA256": kwargs["ChecksumSHA256"],
            "ChecksumType": "FULL_OBJECT",
            "ResponseMetadata": _meta(3),
        }

    def get_object_retention(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_object_retention", kwargs))
        return {
            "Retention": {"Mode": "COMPLIANCE", "RetainUntilDate": _plan().retention_until_utc},
            "ResponseMetadata": _meta(4),
        }

    def delete_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("delete_object", kwargs))
        if self.delete_succeeds:
            return {"ResponseMetadata": _meta(6, 204)}
        raise _StubAwsError(
            {
                "Error": {"Code": "AccessDenied", "Message": "retained object version"},
                "ResponseMetadata": _meta(6, 403),
            }
        )

    def get_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_object", kwargs))
        digest = base64.b64encode(hashlib.sha256(self.archive).digest()).decode("ascii")
        return {
            "Body": self.body,
            "VersionId": "version-123",
            "ChecksumSHA256": digest,
            "ChecksumType": "FULL_OBJECT",
            "ContentLength": len(self.archive),
            "ResponseMetadata": _meta(7),
        }


class _IamStub:
    ets_ranger_simulation = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def simulate_principal_policy(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("simulate_principal_policy", kwargs))
        return {
            "EvaluationResults": [{"EvalDecision": "allowed"}],
            "IsTruncated": False,
            "ResponseMetadata": _meta(5),
        }


def _meta(number: int, status: int = 200) -> dict[str, object]:
    return {
        "HTTPStatusCode": status,
        "RequestId": f"request-{number}",
        "HostId": f"extended-request-{number}",
    }


def _plan(**updates: object) -> RangerAwsS3ObjectLockCapturePlan:
    values: dict[str, object] = {
        "qualification_id": "qualification-123",
        "verifier_challenge_nonce_hex": "a" * 64,
        "aws_partition": "aws",
        "aws_account_id": ACCOUNT,
        "aws_region": "us-east-1",
        "bucket_name": BUCKET,
        "object_key": KEY,
        "delete_test_principal_arn": PRINCIPAL,
        "archive_bundle_bytes": ARCHIVE,
        "retention_until_utc": NOW + timedelta(days=1),
        "configuration_observed_at_utc": NOW,
        "retention_put_observed_at_utc": NOW + timedelta(minutes=1),
        "delete_capability_observed_at_utc": NOW + timedelta(minutes=2),
        "delete_attempt_observed_at_utc": NOW + timedelta(minutes=3),
        "retrieval_observed_at_utc": NOW + timedelta(minutes=4),
    }
    values.update(updates)
    return RangerAwsS3ObjectLockCapturePlan.model_validate(values)


def _authorization_bundle(
    plan: RangerAwsS3ObjectLockCapturePlan,
) -> tuple[RangerAwsS3ExecutionAuthorization, RangerAwsS3ExecutionAuthorizationPolicy]:
    authorization = build_aws_s3_execution_authorization(
        plan,
        authorization_id="authorization-123",
        execution_environment=RangerAwsS3ExecutionEnvironment.SIMULATION,
        issued_at_utc=NOW - timedelta(minutes=2),
        not_before_utc=NOW - timedelta(minutes=1),
        expires_at_utc=NOW + timedelta(minutes=30),
        approved_cost_ceiling_usd_cents=0,
        cloud_execution_authorized=False,
        spending_authorized=False,
        authorizer_id="ets-ranger:test-authorizer",
        authorizer_signing_key_id="test-key-1",
        authorizer_private_key_hex=PRIVATE_KEY_HEX,
    )
    policy = RangerAwsS3ExecutionAuthorizationPolicy(
        expected_authorization_id="authorization-123",
        expected_qualification_id=plan.qualification_id,
        expected_verifier_challenge_nonce_hex=plan.verifier_challenge_nonce_hex,
        expected_execution_environment=RangerAwsS3ExecutionEnvironment.SIMULATION,
        expected_authorizer_id="ets-ranger:test-authorizer",
        expected_authorizer_signing_key_id="test-key-1",
        authorizer_public_key_hex=PUBLIC_KEY_HEX,
        verification_time_utc=NOW,
        maximum_cost_ceiling_usd_cents=0,
        maximum_authorization_lifetime_seconds=3600,
    )
    return authorization, policy


def _capture(
    plan: RangerAwsS3ObjectLockCapturePlan,
    s3: _S3Stub,
    iam: _IamStub,
) -> RangerAwsS3ObjectLockCaptureResult:
    authorization, policy = _authorization_bundle(plan)
    return capture_aws_s3_object_lock_qualification(
        plan,
        authorization=authorization,
        authorization_policy=policy,
        s3_client=s3,
        iam_client=iam,
    )


def test_capture_adapter_emits_five_canonical_artifacts_from_injected_stubs() -> None:
    s3 = _S3Stub()
    iam = _IamStub()

    result = _capture(_plan(), s3, iam)

    assert result.configuration.context.object_version_id == "version-123"
    assert result.retention_put.put_object.requested_body_digest_sha256 == hashlib.sha256(
        ARCHIVE
    ).hexdigest()
    assert result.delete_capability.evaluation_decision == "allowed"
    assert result.delete_attempt.error_code == "AccessDenied"
    assert result.retrieval.get_object.body_digest_sha256 == hashlib.sha256(ARCHIVE).hexdigest()
    assert s3.body.read_count == 1
    assert [name for name, _ in s3.calls] == [
        "get_bucket_versioning",
        "get_object_lock_configuration",
        "put_object",
        "get_object_retention",
        "delete_object",
        "get_object",
    ]
    assert [name for name, _ in iam.calls] == ["simulate_principal_policy"]
    assert s3.calls[2][1]["ObjectLockMode"] == "COMPLIANCE"
    assert s3.calls[4][1]["VersionId"] == "version-123"
    assert s3.calls[4][1]["BypassGovernanceRetention"] is False
    assert s3.calls[5][1]["ChecksumMode"] == "ENABLED"
    assert iam.calls[0][1] == {
        "PolicySourceArn": PRINCIPAL,
        "ActionNames": ["s3:DeleteObjectVersion"],
        "ResourceArns": [f"arn:aws:s3:::{BUCKET}/{KEY}"],
    }

    artifacts = result.evidence_artifacts()
    assert set(artifacts) == set(RangerImmutableEvidenceArtifactKind)
    assert all(value.startswith(b"{") for value in artifacts.values())
    assert ARCHIVE not in b"".join(artifacts.values())


def test_capture_adapter_fails_closed_when_versioned_delete_succeeds() -> None:
    s3 = _S3Stub(delete_succeeds=True)

    with pytest.raises(RangerAwsS3ObjectLockCaptureError, match="unexpectedly succeeded"):
        _capture(_plan(), s3, _IamStub())

    assert [name for name, _ in s3.calls] == [
        "get_bucket_versioning",
        "get_object_lock_configuration",
        "put_object",
        "get_object_retention",
        "delete_object",
    ]


def test_capture_adapter_rejects_mismatched_retrieved_body_before_emitting_artifacts() -> None:
    s3 = _S3Stub(archive=b"substituted bytes")

    with pytest.raises(RangerAwsS3ObjectLockCaptureError, match="body digest"):
        _capture(_plan(), s3, _IamStub())


def test_capture_rejects_expired_authorization_before_any_client_call() -> None:
    plan = _plan()
    authorization, policy = _authorization_bundle(plan)
    expired_policy = policy.model_copy(update={"verification_time_utc": NOW + timedelta(hours=1)})
    s3 = _S3Stub()
    iam = _IamStub()

    with pytest.raises(RangerAwsS3ObjectLockCaptureError, match="not currently valid"):
        capture_aws_s3_object_lock_qualification(
            plan,
            authorization=authorization,
            authorization_policy=expired_policy,
            s3_client=s3,
            iam_client=iam,
        )

    assert s3.calls == []
    assert iam.calls == []


def test_authorization_rejects_plan_substitution_and_invalid_signature() -> None:
    plan = _plan()
    authorization, policy = _authorization_bundle(plan)
    substituted = _plan(object_key="r0.2/substituted.json")

    result = verify_aws_s3_execution_authorization(
        authorization,
        substituted,
        policy=policy,
    )
    assert not result.valid
    assert "capture-plan digest mismatch" in result.reason

    bad_signature = authorization.model_copy(update={"authorizer_signature_hex": "0" * 128})
    result = verify_aws_s3_execution_authorization(bad_signature, plan, policy=policy)
    assert not result.valid
    assert "signature invalid" in result.reason


def test_simulation_authorization_rejects_unmarked_client_before_calls() -> None:
    plan = _plan()
    authorization, policy = _authorization_bundle(plan)
    s3 = _S3Stub()
    iam = _IamStub()
    s3.ets_ranger_simulation = False

    with pytest.raises(RangerAwsS3ObjectLockCaptureError, match="marked test-double"):
        capture_aws_s3_object_lock_qualification(
            plan,
            authorization=authorization,
            authorization_policy=policy,
            s3_client=s3,
            iam_client=iam,
        )

    assert s3.calls == []
    assert iam.calls == []


def test_capture_plan_rejects_stale_retention_and_out_of_order_observations() -> None:
    with pytest.raises(ValueError, match="retention must extend"):
        _plan(retention_until_utc=NOW + timedelta(minutes=2))
    with pytest.raises(ValueError, match="chronologically ordered"):
        _plan(retrieval_observed_at_utc=NOW + timedelta(minutes=1))


def test_capture_module_has_no_aws_sdk_dependency() -> None:
    source = Path("ets/ranger/aws_s3_object_lock_capture.py").read_text(encoding="utf-8")

    assert "import boto3" not in source
    assert "botocore" not in source
