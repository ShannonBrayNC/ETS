"""Deterministic CloudTrail provider-boundary verification coverage for Ranger R0.2."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from ets.ranger.aws_cloudtrail_capture import (
    RangerAwsCloudTrailCaptureError,
    RangerAwsCloudTrailCapturePlan,
    RangerAwsCloudTrailReadAuthorization,
    RangerAwsCloudTrailReadAuthorizationPolicy,
    build_aws_cloudtrail_read_authorization,
    capture_and_verify_aws_cloudtrail_provider_evidence,
    capture_aws_cloudtrail_provider_evidence,
    verify_aws_cloudtrail_read_authorization,
)
from ets.ranger.aws_cloudtrail_provider_evidence import (
    RangerAwsCloudTrailVerificationPolicy,
    verify_aws_cloudtrail_provider_evidence,
)
from ets.ranger.aws_qualification_orchestrator import (
    RangerAwsCloudTrailReadScope,
    RangerAwsQualificationOrchestrationError,
    run_aws_object_lock_qualification,
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
READ_SCOPE_PRIVATE_HEX = "51" * 32
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
READ_SCOPE_PUBLIC_HEX = (
    ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(READ_SCOPE_PRIVATE_HEX))
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

    def get_object_lock_configuration(
        self,
        **kwargs: object,
    ) -> dict[str, object]:
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
            "Retention": {
                "Mode": "COMPLIANCE",
                "RetainUntilDate": NOW + timedelta(days=1),
            },
            "ResponseMetadata": _meta(4),
        }

    def delete_object(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        raise _StubAwsError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "retained object version",
                },
                "ResponseMetadata": _meta(6, 403),
            }
        )

    def get_object(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        checksum = base64.b64encode(hashlib.sha256(ARCHIVE).digest()).decode()
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


def _package_bundle(
    *,
    execution_environment: RangerAwsS3ExecutionEnvironment = (
        RangerAwsS3ExecutionEnvironment.SIMULATION
    ),
) -> tuple[
    RangerAwsS3ExecutionPackage,
    RangerAwsS3ExecutionAuthorization,
    RangerAwsS3ObjectLockCapturePlan,
    RangerAwsS3ExecutionReceiptPolicy,
]:
    plan = _plan()
    live = execution_environment is RangerAwsS3ExecutionEnvironment.AUTHORIZED_NON_PRODUCTION
    authorization = build_aws_s3_execution_authorization(
        plan,
        authorization_id="authorization-cloudtrail",
        execution_environment=execution_environment,
        issued_at_utc=NOW - timedelta(minutes=2),
        not_before_utc=NOW - timedelta(minutes=1),
        expires_at_utc=NOW + timedelta(minutes=30),
        approved_cost_ceiling_usd_cents=25 if live else 0,
        cloud_execution_authorized=live,
        spending_authorized=live,
        authorizer_id="ets-ranger:test-authorizer",
        authorizer_signing_key_id="auth-key-1",
        authorizer_private_key_hex=AUTH_PRIVATE_HEX,
    )
    authorization_policy = RangerAwsS3ExecutionAuthorizationPolicy(
        expected_authorization_id="authorization-cloudtrail",
        expected_qualification_id=plan.qualification_id,
        expected_verifier_challenge_nonce_hex=plan.verifier_challenge_nonce_hex,
        expected_execution_environment=execution_environment,
        expected_authorizer_id="ets-ranger:test-authorizer",
        expected_authorizer_signing_key_id="auth-key-1",
        authorizer_public_key_hex=AUTH_PUBLIC_HEX,
        verification_time_utc=NOW,
        maximum_cost_ceiling_usd_cents=25 if live else 0,
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


def _events(package: RangerAwsS3ExecutionPackage) -> list[dict[str, object]]:
    result = package.capture_result
    return [
        _event(
            "GetBucketVersioning",
            result.configuration.get_bucket_versioning.metadata.request_id,
            0,
        ),
        _event(
            "GetObjectLockConfiguration",
            result.configuration.get_object_lock_configuration.metadata.request_id,
            0,
        ),
        _event(
            "PutObject",
            result.retention_put.put_object.metadata.request_id,
            1,
            key=True,
        ),
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
        _event(
            "GetObject",
            result.retrieval.get_object.metadata.request_id,
            4,
            key=True,
            version=True,
        ),
    ]


def _signed_evidence(
    events: list[dict[str, object]],
) -> tuple[
    bytes,
    str,
    bytes,
    dict[str, bytes],
    RangerAwsCloudTrailVerificationPolicy,
]:
    log_bytes = json.dumps(
        {"Records": events},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
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
    digest_bytes = json.dumps(
        digest,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.PKCS1,
    )
    data_to_sign = (
        f"{digest['digestEndTime']}\n{DIGEST_BUCKET}/{DIGEST_OBJECT}\n"
        f"{hashlib.sha256(digest_bytes).hexdigest()}\n"
        f"{digest['previousDigestSignature']}"
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
    return (
        digest_bytes,
        signature_hex,
        public_der,
        {log_path: log_bytes},
        policy,
    )


def _cloudtrail_evidence(
    package: RangerAwsS3ExecutionPackage,
) -> tuple[
    bytes,
    str,
    bytes,
    dict[str, bytes],
    RangerAwsCloudTrailVerificationPolicy,
]:
    return _signed_evidence(_events(package))


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

    other_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    other_key = other_private_key.public_key().public_bytes(
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
    events = _events(package)
    events[0] = _event("GetBucketVersioning", "substituted-request", 0)
    digest, signature, public_key, logs, policy = _signed_evidence(events)

    verification = verify_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        plan,
        receipt_policy=receipt_policy,
        cloudtrail_policy=policy,
        digest_file_bytes=digest,
        digest_signature_hex=signature,
        cloudtrail_public_key_der=public_key,
        uncompressed_log_files=logs,
    )

    assert not verification.valid
    assert "exactly one event" in verification.reason


class _CaptureBody:
    def __init__(self, value: bytes) -> None:
        self.value = value

    def read(self, amount: int = -1) -> bytes:
        return self.value if amount < 0 else self.value[:amount]


class _CloudTrailCaptureStub:
    ets_ranger_simulation = True

    def __init__(self, public_key: bytes) -> None:
        self.public_key = public_key
        self.calls: list[tuple[str, dict[str, object]]] = []

    def list_public_keys(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("list_public_keys", kwargs))
        return {
            "PublicKeyList": [
                {
                    "Value": self.public_key,
                    "ValidityStartTime": NOW - timedelta(days=1),
                    "ValidityEndTime": NOW + timedelta(days=1),
                    "Fingerprint": FINGERPRINT,
                }
            ],
            "ResponseMetadata": _meta(20),
        }

    def get_event_selectors(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_event_selectors", kwargs))
        return {
            "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/ranger",
            "EventSelectors": [{"ReadWriteType": "All", "IncludeManagementEvents": True}],
            "AdvancedEventSelectors": [],
            "ResponseMetadata": _meta(21),
        }


class _CloudTrailS3CaptureStub:
    ets_ranger_simulation = True

    def __init__(
        self,
        digest: bytes,
        signature: str,
        logs: dict[str, bytes],
        *,
        include_signature: bool = True,
    ) -> None:
        self.digest = digest
        self.signature = signature
        self.logs = logs
        self.include_signature = include_signature
        self.calls: list[dict[str, object]] = []

    def get_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        path = f"{bucket}/{key}"
        if bucket == DIGEST_BUCKET and key == DIGEST_OBJECT:
            metadata = {"signature-algorithm": "SHA256withRSA"}
            if self.include_signature:
                metadata["signature"] = self.signature
            return {
                "Body": _CaptureBody(gzip.compress(self.digest)),
                "Metadata": metadata,
                "ResponseMetadata": _meta(22),
            }
        return {
            "Body": _CaptureBody(gzip.compress(self.logs[path])),
            "ResponseMetadata": _meta(23),
        }


def _capture_plan(public_key: bytes) -> RangerAwsCloudTrailCapturePlan:
    return RangerAwsCloudTrailCapturePlan(
        trail_name="ranger-qualification-trail",
        aws_account_id=ACCOUNT,
        aws_region="us-east-1",
        digest_s3_bucket=DIGEST_BUCKET,
        digest_s3_object=DIGEST_OBJECT,
        expected_public_key_fingerprint=FINGERPRINT,
        expected_public_key_der_sha256=hashlib.sha256(public_key).hexdigest(),
        window_start_utc=NOW - timedelta(minutes=1),
        window_end_utc=NOW + timedelta(minutes=10),
        maximum_log_files=4,
        maximum_log_file_bytes=1024 * 1024,
        maximum_event_time_skew_seconds=60,
    )


def _read_scope(
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    plan: RangerAwsS3ObjectLockCapturePlan,
    public_key: bytes,
    *,
    capture_plan: RangerAwsCloudTrailCapturePlan | None = None,
    authorization_id: str = "cloudtrail-read-authorization-1",
) -> tuple[
    RangerAwsCloudTrailCapturePlan,
    RangerAwsCloudTrailReadAuthorization,
    RangerAwsCloudTrailReadAuthorizationPolicy,
]:
    capture = capture_plan or _capture_plan(public_key)
    live = (
        authorization.execution_environment
        is RangerAwsS3ExecutionEnvironment.AUTHORIZED_NON_PRODUCTION
    )
    read_authorization = build_aws_cloudtrail_read_authorization(
        package,
        authorization,
        plan,
        capture,
        authorization_id=authorization_id,
        issued_at_utc=NOW + timedelta(minutes=5),
        not_before_utc=NOW + timedelta(minutes=5),
        expires_at_utc=NOW + timedelta(minutes=15),
        approved_cost_ceiling_usd_cents=25 if live else 0,
        cloud_read_authorized=live,
        spending_authorized=live,
        authorizer_id="ets-ranger:test-cloudtrail-authorizer",
        authorizer_signing_key_id="cloudtrail-auth-key-1",
        authorizer_private_key_hex=READ_SCOPE_PRIVATE_HEX,
    )
    policy = RangerAwsCloudTrailReadAuthorizationPolicy(
        expected_authorization_id=authorization_id,
        expected_base_execution_authorization_id=authorization.authorization_id,
        expected_execution_receipt_id=package.execution_receipt.receipt_id,
        expected_qualification_id=plan.qualification_id,
        expected_verifier_challenge_nonce_hex=plan.verifier_challenge_nonce_hex,
        expected_execution_environment=authorization.execution_environment,
        expected_authorizer_id="ets-ranger:test-cloudtrail-authorizer",
        expected_authorizer_signing_key_id="cloudtrail-auth-key-1",
        authorizer_public_key_hex=READ_SCOPE_PUBLIC_HEX,
        verification_time_utc=NOW + timedelta(minutes=5),
        maximum_cost_ceiling_usd_cents=25 if live else 0,
        maximum_authorization_lifetime_seconds=3600,
    )
    return capture, read_authorization, policy


def test_cloudtrail_capture_uses_injected_clients_and_composes_with_verifier() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )
    cloudtrail = _CloudTrailCaptureStub(public_key)
    s3 = _CloudTrailS3CaptureStub(digest, signature, logs)

    bundle, verification = capture_and_verify_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        plan,
        receipt_policy=receipt_policy,
        capture_plan=capture_plan,
        read_authorization=read_authorization,
        read_authorization_policy=read_policy,
        cloudtrail_client=cloudtrail,
        s3_client=s3,
    )

    assert verification.valid
    assert bundle.schema_version == "ets.ranger.aws-cloudtrail-capture.v2"
    assert bundle.execution_receipt_verified_before_calls
    assert bundle.injected_client_boundary_enforced
    assert bundle.configured_read_scope_signature_verified
    assert not bundle.read_scope_authorizer_independence_proven
    assert not bundle.aws_public_key_provenance_independently_verified
    assert len(bundle.uncompressed_log_files) == 1
    assert [name for name, _ in cloudtrail.calls] == [
        "list_public_keys",
        "get_event_selectors",
    ]
    assert len(s3.calls) == 2
    assert all(call["ExpectedBucketOwner"] == ACCOUNT for call in s3.calls)


def test_cloudtrail_capture_rejects_invalid_receipt_before_client_calls() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )
    cloudtrail = _CloudTrailCaptureStub(public_key)
    s3 = _CloudTrailS3CaptureStub(digest, signature, logs)
    wrong_policy = receipt_policy.model_copy(update={"expected_receipt_id": "wrong-receipt"})

    try:
        capture_aws_cloudtrail_provider_evidence(
            package,
            authorization,
            plan,
            receipt_policy=wrong_policy,
            capture_plan=capture_plan,
            read_authorization=read_authorization,
            read_authorization_policy=read_policy,
            cloudtrail_client=cloudtrail,
            s3_client=s3,
        )
    except RangerAwsCloudTrailCaptureError as exc:
        assert "execution receipt is invalid" in str(exc)
    else:
        raise AssertionError("invalid receipt unexpectedly reached provider clients")
    assert cloudtrail.calls == []
    assert s3.calls == []


def test_cloudtrail_capture_rejects_unmarked_simulation_clients_before_calls() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )
    cloudtrail = _CloudTrailCaptureStub(public_key)
    s3 = _CloudTrailS3CaptureStub(digest, signature, logs)
    cloudtrail.ets_ranger_simulation = False

    try:
        capture_aws_cloudtrail_provider_evidence(
            package,
            authorization,
            plan,
            receipt_policy=receipt_policy,
            capture_plan=capture_plan,
            read_authorization=read_authorization,
            read_authorization_policy=read_policy,
            cloudtrail_client=cloudtrail,
            s3_client=s3,
        )
    except RangerAwsCloudTrailCaptureError as exc:
        assert "marked test-double" in str(exc)
    else:
        raise AssertionError("unmarked simulation client was accepted")
    assert cloudtrail.calls == []
    assert s3.calls == []


def test_cloudtrail_capture_rejects_substituted_key_before_s3_reads() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    substituted = (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.PKCS1,
        )
    )
    cloudtrail = _CloudTrailCaptureStub(substituted)
    s3 = _CloudTrailS3CaptureStub(digest, signature, logs)
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )

    try:
        capture_aws_cloudtrail_provider_evidence(
            package,
            authorization,
            plan,
            receipt_policy=receipt_policy,
            capture_plan=capture_plan,
            read_authorization=read_authorization,
            read_authorization_policy=read_policy,
            cloudtrail_client=cloudtrail,
            s3_client=s3,
        )
    except RangerAwsCloudTrailCaptureError as exc:
        assert "pinned SHA-256" in str(exc)
    else:
        raise AssertionError("substituted CloudTrail key was accepted")
    assert len(cloudtrail.calls) == 1
    assert s3.calls == []


def test_cloudtrail_capture_requires_digest_signature_metadata() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    cloudtrail = _CloudTrailCaptureStub(public_key)
    s3 = _CloudTrailS3CaptureStub(digest, signature, logs, include_signature=False)
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )

    try:
        capture_aws_cloudtrail_provider_evidence(
            package,
            authorization,
            plan,
            receipt_policy=receipt_policy,
            capture_plan=capture_plan,
            read_authorization=read_authorization,
            read_authorization_policy=read_policy,
            cloudtrail_client=cloudtrail,
            s3_client=s3,
        )
    except RangerAwsCloudTrailCaptureError as exc:
        assert "signature is missing" in str(exc)
    else:
        raise AssertionError("unsigned digest metadata was accepted")


def test_cloudtrail_capture_accepts_separately_signed_controlled_live_scope() -> None:
    package, authorization, plan, receipt_policy = _package_bundle(
        execution_environment=RangerAwsS3ExecutionEnvironment.AUTHORIZED_NON_PRODUCTION
    )
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    cloudtrail = _CloudTrailCaptureStub(public_key)
    s3 = _CloudTrailS3CaptureStub(digest, signature, logs)
    cloudtrail.ets_ranger_simulation = False
    s3.ets_ranger_simulation = False
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )

    bundle = capture_aws_cloudtrail_provider_evidence(
        package,
        authorization,
        plan,
        receipt_policy=receipt_policy,
        capture_plan=capture_plan,
        read_authorization=read_authorization,
        read_authorization_policy=read_policy,
        cloudtrail_client=cloudtrail,
        s3_client=s3,
    )

    assert bundle.read_scope_authorization_id == read_authorization.authorization_id
    assert len(cloudtrail.calls) == 2
    assert len(s3.calls) == 2


def test_cloudtrail_capture_rejects_plan_substitution_before_client_calls() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    capture_plan = _capture_plan(public_key)
    _, read_authorization, read_policy = _read_scope(
        package,
        authorization,
        plan,
        public_key,
        capture_plan=capture_plan.model_copy(update={"trail_name": "substituted-trail"}),
    )
    cloudtrail = _CloudTrailCaptureStub(public_key)
    s3 = _CloudTrailS3CaptureStub(digest, signature, logs)

    try:
        capture_aws_cloudtrail_provider_evidence(
            package,
            authorization,
            plan,
            receipt_policy=receipt_policy,
            capture_plan=capture_plan,
            read_authorization=read_authorization,
            read_authorization_policy=read_policy,
            cloudtrail_client=cloudtrail,
            s3_client=s3,
        )
    except RangerAwsCloudTrailCaptureError as exc:
        assert "prior-evidence or capture-plan binding mismatch" in str(exc)
    else:
        raise AssertionError("substituted CloudTrail plan was accepted")
    assert cloudtrail.calls == []
    assert s3.calls == []


def test_cloudtrail_read_authorization_rejects_signature_and_pre_receipt_start() -> None:
    package, authorization, plan, _ = _package_bundle()
    _, _, public_key, _, _ = _cloudtrail_evidence(package)
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )

    forged = read_authorization.model_copy(update={"authorizer_signature_hex": "00" * 64})
    verification = verify_aws_cloudtrail_read_authorization(
        forged,
        package,
        authorization,
        plan,
        capture_plan,
        policy=read_policy,
    )
    assert not verification.valid
    assert "signature invalid" in verification.reason

    expired_policy = read_policy.model_copy(
        update={"verification_time_utc": NOW + timedelta(minutes=16)}
    )
    verification = verify_aws_cloudtrail_read_authorization(
        read_authorization,
        package,
        authorization,
        plan,
        capture_plan,
        policy=expired_policy,
    )
    assert not verification.valid
    assert "not currently valid" in verification.reason

    early = build_aws_cloudtrail_read_authorization(
        package,
        authorization,
        plan,
        capture_plan,
        authorization_id="cloudtrail-read-authorization-early",
        issued_at_utc=NOW,
        not_before_utc=NOW,
        expires_at_utc=NOW + timedelta(minutes=10),
        approved_cost_ceiling_usd_cents=0,
        cloud_read_authorized=False,
        spending_authorized=False,
        authorizer_id="ets-ranger:test-cloudtrail-authorizer",
        authorizer_signing_key_id="cloudtrail-auth-key-1",
        authorizer_private_key_hex=READ_SCOPE_PRIVATE_HEX,
    )
    early_policy = read_policy.model_copy(
        update={
            "expected_authorization_id": "cloudtrail-read-authorization-early",
            "verification_time_utc": NOW,
        }
    )
    verification = verify_aws_cloudtrail_read_authorization(
        early,
        package,
        authorization,
        plan,
        capture_plan,
        policy=early_policy,
    )
    assert not verification.valid
    assert "begins before the bound execution receipt" in verification.reason


def test_cloudtrail_capture_bounds_gzip_expansion() -> None:
    package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(package)
    oversized_logs = {path: b"x" * (1024 * 1024 + 1) for path in logs}
    cloudtrail = _CloudTrailCaptureStub(public_key)
    s3 = _CloudTrailS3CaptureStub(digest, signature, oversized_logs)
    capture_plan, read_authorization, read_policy = _read_scope(
        package, authorization, plan, public_key
    )

    try:
        capture_aws_cloudtrail_provider_evidence(
            package,
            authorization,
            plan,
            receipt_policy=receipt_policy,
            capture_plan=capture_plan,
            read_authorization=read_authorization,
            read_authorization_policy=read_policy,
            cloudtrail_client=cloudtrail,
            s3_client=s3,
        )
    except RangerAwsCloudTrailCaptureError as exc:
        assert "uncompressed body exceeds limit" in str(exc)
    else:
        raise AssertionError("oversized gzip expansion was accepted")


class _ReadScopeProvider:
    def __init__(self, public_key: bytes, *, forge_signature: bool = False) -> None:
        self.public_key = public_key
        self.forge_signature = forge_signature
        self.calls = 0

    def authorize(
        self,
        package: RangerAwsS3ExecutionPackage,
        authorization: RangerAwsS3ExecutionAuthorization,
        s3_plan: RangerAwsS3ObjectLockCapturePlan,
        cloudtrail_plan: RangerAwsCloudTrailCapturePlan,
    ) -> RangerAwsCloudTrailReadScope:
        self.calls += 1
        _, read_authorization, policy = _read_scope(
            package,
            authorization,
            s3_plan,
            self.public_key,
            capture_plan=cloudtrail_plan,
        )
        if self.forge_signature:
            read_authorization = read_authorization.model_copy(
                update={"authorizer_signature_hex": "00" * 64}
            )
        return RangerAwsCloudTrailReadScope(
            authorization=read_authorization,
            policy=policy,
        )


def test_two_phase_orchestrator_composes_execution_authority_and_provider_evidence() -> None:
    prior_package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(prior_package)
    provider = _ReadScopeProvider(public_key)
    cloudtrail = _CloudTrailCaptureStub(public_key)
    cloudtrail_s3 = _CloudTrailS3CaptureStub(digest, signature, logs)

    run = run_aws_object_lock_qualification(
        plan,
        execution_authorization=authorization,
        execution_authorization_policy=receipt_policy.authorization_policy,
        object_lock_s3_client=_S3Stub(),
        iam_client=_IamStub(),
        receipt_id="receipt-cloudtrail",
        receipt_issued_at_utc=NOW + timedelta(minutes=5),
        recorder_id="ets-ranger:test-recorder",
        recorder_signing_key_id="recorder-key-1",
        recorder_private_key_hex=RECORDER_PRIVATE_HEX,
        receipt_policy=receipt_policy,
        cloudtrail_plan=_capture_plan(public_key),
        read_scope_provider=provider,
        cloudtrail_client=cloudtrail,
        cloudtrail_s3_client=cloudtrail_s3,
    )

    assert run.cloudtrail_verification.valid
    assert run.execution_receipt_verified_before_read_scope_request
    assert run.read_scope_verified_before_provider_reads
    assert provider.calls == 1
    assert len(cloudtrail.calls) == 2
    assert len(cloudtrail_s3.calls) == 2
    assert not run.effective_aws_permissions_proven
    assert not run.physical_worm_proven


def test_two_phase_orchestrator_rejects_forged_post_receipt_scope_before_reads() -> None:
    prior_package, authorization, plan, receipt_policy = _package_bundle()
    digest, signature, public_key, logs, _ = _cloudtrail_evidence(prior_package)
    provider = _ReadScopeProvider(public_key, forge_signature=True)
    cloudtrail = _CloudTrailCaptureStub(public_key)
    cloudtrail_s3 = _CloudTrailS3CaptureStub(digest, signature, logs)

    try:
        run_aws_object_lock_qualification(
            plan,
            execution_authorization=authorization,
            execution_authorization_policy=receipt_policy.authorization_policy,
            object_lock_s3_client=_S3Stub(),
            iam_client=_IamStub(),
            receipt_id="receipt-cloudtrail",
            receipt_issued_at_utc=NOW + timedelta(minutes=5),
            recorder_id="ets-ranger:test-recorder",
            recorder_signing_key_id="recorder-key-1",
            recorder_private_key_hex=RECORDER_PRIVATE_HEX,
            receipt_policy=receipt_policy,
            cloudtrail_plan=_capture_plan(public_key),
            read_scope_provider=provider,
            cloudtrail_client=cloudtrail,
            cloudtrail_s3_client=cloudtrail_s3,
        )
    except RangerAwsQualificationOrchestrationError as exc:
        assert "read authorization is invalid" in str(exc)
        assert exc.execution_package is not None
        assert exc.execution_package.execution_receipt.receipt_id == "receipt-cloudtrail"
    else:
        raise AssertionError("forged post-receipt read scope was accepted")
    assert provider.calls == 1
    assert cloudtrail.calls == []
    assert cloudtrail_s3.calls == []
