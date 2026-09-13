"""Deterministic CloudTrail provider-boundary verification coverage for Ranger R0.2."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from ets.ranger.aws_cloudtrail_provider_evidence import (
    RangerAwsCloudTrailVerificationPolicy,
    verify_aws_cloudtrail_provider_evidence,
)
from ets.ranger.aws_s3_object_lock_capture import (
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ExecutionAuthorizationPolicy,
    RangerAwsS3ExecutionEnvironment,
    RangerAwsS3ObjectLockCapturePlan,
    build_aws_s3_execution_authorization,
)
from ets.ranger.aws_s3_object_lock_execution import (
    RangerAwsS3ExecutionPackage,
    RangerAwsS3ExecutionReceiptPolicy,
    capture_aws_s3_object_lock_qualification_with_receipt,
)

NOW = datetime(2026, 9, 13, 0, 0, tzinfo=UTC)
ARCHIVE = b"ETS Ranger CloudTrail qualification archive\n"
ACCOUNT = "123456789012"
BUCKET = "ets-ranger-qualification"
KEY = "r0.2/cloudtrail-archive.json"
PRINCIPAL = "arn:aws:iam::123456789012:role/ranger-delete-probe"
AUTH_PRIVATE_HEX = "31" * 32
RECORDER_PRIVATE_HEX = "41" * 32
AUTH_PUBLIC_HEX = (
    ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(AUTH_PRIVATE_HEX))
    .public_key()
    .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    .hex()
)
RECORDER_PUBLIC_HEX = (
    ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(RECORDER_PRIVATE_HEX))
    .public_key()
    .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    .hex()
)
DIGEST_BUCKET = "ets-ranger-cloudtrail"
DIGEST_OBJECT = (
    "AWSLogs/123456789012/CloudTrail-Digest/us-east-1/2026/09/13/"
    "123456789012_CloudTrail-Digest_us-east-1_20260913T001000Z.json.gz"
)
LOG_OBJECT = (
    "AWSLogs/123456789012/CloudTrail/us-east-1/2026/09/13/"
    "123456789012_CloudTrail_us-east-1_20260913T0005Z_abc.json.gz"
)
FINGERPRINT = "ab" * 16


class _StubAwsError(RuntimeError):
    def __init__(self, response: dict[str, object]) -> None:
        super().__init__("stub AWS error")
        self.response = response


class _Body:
    def read(self) -> bytes:
        return ARCHIVE


class _S3Stub:
    ets_ranger_simulation = True

    def get_bucket_versioning(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        return {"Status": "Enabled", "ResponseMetadata": _meta(1)}

    def get_object_lock_configuration(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        return {
            "ObjectLockConfiguration": {"ObjectLockEnabled": "Enabled"},
            "ResponseMetadata": _meta(2),
        }

    def put_object(self, **kwargs: object) -> dict[str, object]:
        return {
            "VersionId": "version-123",
            "ChecksumSHA256": kwargs["ChecksumSHA256"],
            "ChecksumType": "FULL_OBJECT",
            "ResponseMetadata": _meta(3),
        }

    def get_object_retention(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        return {
            "Retention": {"Mode": "COMPLIANCE", "RetainUntilDate": NOW + timedelta(days=1)},
            "ResponseMetadata": _meta(4),
        }

    def delete_object(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        raise _StubAwsError(
            {
                "Error": {"Code": "AccessDenied", "Message": "retained object version"},
                "ResponseMetadata": _meta(6, 403),
            }
        )

    def get_object(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        checksum = base64.b64encode(hashlib.sha256(ARCHIVE).digest()).decode("ascii")
        return {
            "Body": _Body(),
            "VersionId": "version-123",
            "ChecksumSHA256": checksum,
            "ChecksumType": "FULL_OBJECT",
            "ContentLength": len(ARCHIVE),
            "ResponseMetadata": _meta(7),
        }


class _IamStub:
    ets_ranger_simulation = True

    def simulate_principal_policy(self, **kwargs: object) -> dict[str, object]:
        del kwargs
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


def _plan() -> RangerAwsS3ObjectLockCapturePlan:
    return RangerAwsS3ObjectLockCapturePlan.model_validate(
        {
            "qualification_id": "qualification-cloudtrail",
            "verifier_challenge_nonce_hex": "c" * 64,
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
    )


def _package_bundle() -> tuple[
    RangerAwsS3ExecutionPackage,
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ObjectLockCapturePlan,
    RangerAwsS3ExecutionReceiptPolicy,
]:
    plan = _plan()
    authorization = build_aws_s3_execution_authorization(
        plan,
        authorization_id="authorization-cloudtrail",
        execution_environment=RangerAwsS3ExecutionEnvironment.SIMULATION,
        issued_at_utc=NOW - timedelta(minutes=2),
        not_before_utc=NOW - timedelta(minutes=1),
        expires_at_utc=NOW + timedelta(minutes=30),
        approved_cost_ceiling_usd_cents=0,
        cloud_execution_authorized=False,
        spending_authorized=False,
        authorizer_id="ets-ranger:test-authorizer",
        authorizer_signing_key_id="auth-key-1",
        authorizer_private_key_hex=AUTH_PRIVATE_HEX,
    )
    authorization_policy = RangerAwsS3ExecutionAuthorizationPolicy(
        expected_authorization_id="authorization-cloudtrail",
        expected_qualification_id=plan.qualification_id,
        expected_verifier_challenge_nonce_hex=plan.verifier_challenge_nonce_hex,
        expected_execution_environment=RangerAwsS3ExecutionEnvironment.SIMULATION,
        expected_authorizer_id="ets-ranger:test-authorizer",
        expected_authorizer_signing_key_id="auth-key-1",
        authorizer_public_key_hex=AUTH_PUBLIC_HEX,
        verification_time_utc=NOW,
        maximum_cost_ceiling_usd_cents=0,
        maximum_authorization_lifetime_seconds=3600,
    )
    package = capture_aws_s3_object_lock_qualification_with_receipt(
        plan,
        authorization=authorization,
        authorization_policy=authorization_policy,
        s3_client=_S3Stub(),
        iam_client=_IamStub(),
        receipt_id="receipt-cloudtrail",
        receipt_issued_at_utc=NOW + timedelta(minutes=5),
        recorder_id="ets-ranger:test-recorder",
        recorder_signing_key_id="recorder-key-1",
        recorder_private_key_hex=RECORDER_PRIVATE_HEX,
    )
    receipt_policy = RangerAwsS3ExecutionReceiptPolicy(
        authorization_policy=authorization_policy,
        expected_receipt_id="receipt-cloudtrail",
        expected_recorder_id="ets-ranger:test-recorder",
        expected_recorder_signing_key_id="recorder-key-1",
        recorder_public_key_hex=RECORDER_PUBLIC_HEX,
        maximum_receipt_delay_seconds=120,
    )
    return package, authorization, plan, receipt_policy


def _event(
    name: str,
    request_id: str,
    minute: int,
    *,
    source: str = "s3.amazonaws.com",
    bucket: bool = True,
    key: bool = False,
    version: bool = False,
    error_code: str | None = None,
) -> dict[str, object]:
    parameters: dict[str, object] = {}
    if bucket:
        parameters["bucketName"] = BUCKET
    if key:
        parameters["key"] = KEY
    if version:
        parameters["versionId"] = "version-123"
    event: dict[str, object] = {
        "eventTime": (NOW + timedelta(minutes=minute)).isoformat().replace("+00:00", "Z"),
        "eventSource": source,
        "eventName": name,
        "awsRegion": "us-east-1",
        "recipientAccountId": ACCOUNT,
        "requestID": request_id,
        "requestParameters": parameters,
    }
    if error_code is not None:
        event["errorCode"] = error_code
    return event


def _cloudtrail_evidence(
    package: RangerAwsS3ExecutionPackage,
) -> tuple[bytes, str, bytes, dict[str, bytes], RangerAwsCloudTrailVerificationPolicy]:
    result = package.capture_result
    events = [
        _event("GetBucketVersioning", result.configuration.get_bucket_versioning.metadata.request_id, 0),
        _event(
            "GetObjectLockConfiguration",
            result.configuration.get_object_lock_configuration.metadata.request_id,
            0,
        ),
        _event("PutObject", result.retention_put.put_object.metadata.request_id, 1, key=True),
        _event(
            "GetObjectRetention",
            result.retention_put.get_object_retention.metadata.request_id,
            1,
            key=True,
            version=True,
        ),
        _event(
            "SimulatePrincipalPolicy",
            result.delete_capability.metadata.request_id,
            2,
            source="iam.amazonaws.com",
            bucket=False,
        ),
        _event(
            "DeleteObject",
            result.delete_attempt.metadata.request_id,
            3,
            key=True,
            version=True,
            error_code="AccessDenied",
        ),
        _event("GetObject", result.retrieval.get_object.metadata.request_id, 4, key=True, version=True),
    ]
    log_bytes = json.dumps({"Records": events}, separators=(",", ":"), sort_keys=True).encode()
    log_path = f"{DIGEST_BUCKET}/{LOG_OBJECT}"
    digest = {
        "digestEndTime": "2026-09-13T00:10:00Z",
        "digestS3Bucket": DIGEST_BUCKET,
        "digestS3Object": DIGEST_OBJECT,
        "digestPublicKeyFingerprint": FINGERPRINT,
        "digestSignatureAlgorithm": "SHA256withRSA",
        "previousDigestSignature": "cd" * 256,
        "logFiles": [
            {
                "s3Bucket": DIGEST_BUCKET,
                "s3Object": LOG_OBJECT,
                "hashValue": hashlib.sha256(log_bytes).hexdigest(),
                "hashAlgorithm": "SHA-256",
            }
        ],
    }
    digest_bytes = json.dumps(digest, separators=(",", ":"), sort_keys=True).encode()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.PKCS1,
    )
    data_to_sign = (
        f"{digest['digestEndTime']}\n{DIGEST_BUCKET}/{DIGEST_OBJECT}\n"
        f"{hashlib.sha256(digest_bytes).hexdigest()}\n{digest['previousDigestSignature']}"
    ).encode()
    signature_hex = private_key.sign(
        data_to_sign,
        padding.PKCS1v15(),
        hashes.SHA256(),
    ).hex()
    policy = RangerAwsCloudTrailVerificationPolicy(
        expected_digest_s3_bucket=DIGEST_BUCKET,
        expected_digest_s3_object=DIGEST_OBJECT,
        expected_public_key_fingerprint=FINGERPRINT,
        expected_public_key_der_sha256=hashlib.sha256(public_der).hexdigest(),
        maximum_log_files=4,
        maximum_log_file_bytes=1024 * 1024,
        maximum_event_time_skew_seconds=60,
    )
    return digest_bytes, signature_hex, public_der, {log_path: log_bytes}, policy


def test_cloudtrail_digest_and_events_bind_to_verified_execution_receipt() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, cloudtrail_policy = _cloudtrail_evidence(package)

    result = verify_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        plan,
        receipt_policy=receipt_policy,
        cloudtrail_policy=cloudtrail_policy,
        digest_file_bytes=digest,
        digest_signature_hex=signature,
        cloudtrail_public_key_der=public_key,
        uncompressed_log_files=logs,
    )

    assert result.valid
    assert result.execution_receipt_verified
    assert result.public_key_material_pinned
    assert result.digest_signature_verified
    assert result.referenced_log_hashes_verified
    assert result.capture_request_ids_correlated
    assert result.matched_request_count == 7
    assert not result.aws_public_key_provenance_independently_verified
    assert not result.complete_cloudtrail_coverage_proven
    assert not result.provider_execution_independently_proven


def test_cloudtrail_verifier_rejects_log_mutation_and_unpinned_key() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, cloudtrail_policy = _cloudtrail_evidence(package)
    log_path = next(iter(logs))
    mutated_logs = {log_path: logs[log_path] + b" "}

    result = verify_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        plan,
        receipt_policy=receipt_policy,
        cloudtrail_policy=cloudtrail_policy,
        digest_file_bytes=digest,
        digest_signature_hex=signature,
        cloudtrail_public_key_der=public_key,
        uncompressed_log_files=mutated_logs,
    )
    assert not result.valid
    assert "hash mismatch" in result.reason

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.PKCS1,
    )
    result = verify_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        plan,
        receipt_policy=receipt_policy,
        cloudtrail_policy=cloudtrail_policy,
        digest_file_bytes=digest,
        digest_signature_hex=signature,
        cloudtrail_public_key_der=other_key,
        uncompressed_log_files=logs,
    )
    assert not result.valid
    assert "pinned SHA-256" in result.reason


def test_cloudtrail_verifier_rejects_request_substitution_even_when_resigned() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    _, _, _, _, cloudtrail_policy = _cloudtrail_evidence(package)
    result = package.capture_result
    events = [
        _event("GetBucketVersioning", "substituted-request", 0),
        _event(
            "GetObjectLockConfiguration",
            result.configuration.get_object_lock_configuration.metadata.request_id,
            0,
        ),
        _event("PutObject", result.retention_put.put_object.metadata.request_id, 1, key=True),
        _event(
            "GetObjectRetention",
            result.retention_put.get_object_retention.metadata.request_id,
            1,
            key=True,
            version=True,
        ),
        _event(
            "SimulatePrincipalPolicy",
            result.delete_capability.metadata.request_id,
            2,
            source="iam.amazonaws.com",
            bucket=False,
        ),
        _event(
            "DeleteObject",
            result.delete_attempt.metadata.request_id,
            3,
            key=True,
            version=True,
            error_code="AccessDenied",
        ),
        _event("GetObject", result.retrieval.get_object.metadata.request_id, 4, key=True, version=True),
    ]
    log_bytes = json.dumps({"Records": events}, separators=(",", ":"), sort_keys=True).encode()
    digest_record = {
        "digestEndTime": "2026-09-13T00:10:00Z",
        "digestS3Bucket": DIGEST_BUCKET,
        "digestS3Object": DIGEST_OBJECT,
        "digestPublicKeyFingerprint": FINGERPRINT,
        "digestSignatureAlgorithm": "SHA256withRSA",
        "previousDigestSignature": "cd" * 256,
        "logFiles": [
            {
                "s3Bucket": DIGEST_BUCKET,
                "s3Object": LOG_OBJECT,
                "hashValue": hashlib.sha256(log_bytes).hexdigest(),
                "hashAlgorithm": "SHA-256",
            }
        ],
    }
    digest_bytes = json.dumps(digest_record, separators=(",", ":"), sort_keys=True).encode()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.PKCS1,
    )
    policy = cloudtrail_policy.model_copy(
        update={"expected_public_key_der_sha256": hashlib.sha256(public_der).hexdigest()}
    )
    data_to_sign = (
        f"{digest_record['digestEndTime']}\n{DIGEST_BUCKET}/{DIGEST_OBJECT}\n"
        f"{hashlib.sha256(digest_bytes).hexdigest()}\n{digest_record['previousDigestSignature']}"
    ).encode()
    signature = private_key.sign(data_to_sign, padding.PKCS1v15(), hashes.SHA256()).hex()

    verification = verify_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        plan,
        receipt_policy=receipt_policy,
        cloudtrail_policy=policy,
        digest_file_bytes=digest_bytes,
        digest_signature_hex=signature,
        cloudtrail_public_key_der=public_der,
        uncompressed_log_files={f"{DIGEST_BUCKET}/{LOG_OBJECT}": log_bytes},
    )

    assert not verification.valid
    assert "exactly one event" in verification.reason
