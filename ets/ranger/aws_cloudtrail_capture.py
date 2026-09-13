"""Credential-isolated CloudTrail evidence capture for Ranger R0.2.

The adapter accepts caller-constructed, capability-limited CloudTrail and S3 clients. It does not
import an AWS SDK, locate credentials, or select endpoints. Before either client is invoked it
verifies the signed Ranger AWS execution package. Simulation authorization additionally requires
explicitly marked test doubles.

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
from typing import Literal, Protocol, runtime_checkable

from pydantic import Field, ValidationError, field_validator, model_validator

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
)
from ets.ranger.aws_s3_object_lock_execution import (
    RangerAwsS3ExecutionPackage,
    RangerAwsS3ExecutionReceiptPolicy,
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

    schema_version: Literal["ets.ranger.aws-cloudtrail-capture.v1"] = (
        "ets.ranger.aws-cloudtrail-capture.v1"
    )
    digest_file_bytes: bytes
    digest_signature_hex: str = Field(pattern=r"^[0-9a-f]+$")
    cloudtrail_public_key_der: bytes
    uncompressed_log_files: dict[str, bytes]
    public_key_observation: RangerAwsCloudTrailPublicKeyObservation
    selector_observation: RangerAwsCloudTrailSelectorObservation
    execution_receipt_verified_before_calls: Literal[True] = True
    injected_client_boundary_enforced: Literal[True] = True
    capture_scope_independently_signed: Literal[False] = False
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
    cloudtrail_client: RangerAwsCloudTrailClient,
    s3_client: RangerAwsCloudTrailS3Client,
) -> RangerAwsCloudTrailCaptureBundle:
    """Read one bounded digest/log/key/selector set through injected clients."""

    receipt = verify_aws_s3_execution_receipt(
        package, authorization, s3_plan, policy=receipt_policy
    )
    if not receipt.valid:
        raise RangerAwsCloudTrailCaptureError(
            f"execution receipt is invalid: {receipt.reason}"
        )
    try:
        plan = RangerAwsCloudTrailCapturePlan.model_validate(capture_plan.model_dump())
    except (AttributeError, ValidationError) as exc:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail capture plan schema validation failed"
        ) from exc
    if (
        plan.aws_account_id != s3_plan.aws_account_id
        or plan.aws_region != s3_plan.aws_region
    ):
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail capture account or Region does not match the execution package"
        )
    if authorization.execution_environment is not RangerAwsS3ExecutionEnvironment.SIMULATION:
        raise RangerAwsCloudTrailCaptureError(
            "live CloudTrail evidence reads require a separately signed capture-scope extension"
        )
    if not (
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
    if not (
        key_observation.validity_start_utc
        <= digest_end
        <= key_observation.validity_end_utc
    ):
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail public-key validity does not cover the digest end time"
        )
    references = digest.get("logFiles")
    if not isinstance(references, list) or not references:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail digest contains no log-file references"
        )
    if len(references) > plan.maximum_log_files:
        raise RangerAwsCloudTrailCaptureError(
            "CloudTrail digest exceeds the capture log-file count limit"
        )

    logs: dict[str, bytes] = {}
    for reference in references:
        if not isinstance(reference, dict):
            raise RangerAwsCloudTrailCaptureError(
                "CloudTrail log-file reference is not an object"
            )
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
    )


def capture_and_verify_aws_cloudtrail_provider_evidence(
    package: RangerAwsS3ExecutionPackage,
    authorization: RangerAwsS3ExecutionAuthorization,
    s3_plan: RangerAwsS3ObjectLockCapturePlan,
    *,
    receipt_policy: RangerAwsS3ExecutionReceiptPolicy,
    capture_plan: RangerAwsCloudTrailCapturePlan,
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
        maximum_event_time_skew_seconds=(
            capture_plan.maximum_event_time_skew_seconds
        ),
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
        and str(item.get("Fingerprint", "")).lower()
        == plan.expected_public_key_fingerprint.lower()
    ]
    if len(matches) != 1:
        raise RangerAwsCloudTrailCaptureError(
            "ListPublicKeys must contain exactly one pinned fingerprint"
        )
    key = matches[0]
    value = key.get("Value")
    start = key.get("ValidityStartTime")
    end = key.get("ValidityEndTime")
    if not (
        isinstance(value, bytes)
        and isinstance(start, datetime)
        and isinstance(end, datetime)
    ):
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
        get_event_selectors_request_id=_request_id(
            response, "GetEventSelectors response"
        ),
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
        raise RangerAwsCloudTrailCaptureError(
            f"{label} uncompressed body exceeds limit"
        )
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
