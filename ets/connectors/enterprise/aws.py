"""AWS CloudTrail Event History connector for G2F2."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn, Protocol, cast

from pydantic import JsonValue

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialProviderNotFoundError,
    CredentialResolutionError,
)
from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorCollectionResultV1,
    ConnectorDefinitionV1,
    ConnectorEvidenceCandidateV1,
    ConnectorHealthState,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorOperationCode,
    ConnectorReconciliationResultV1,
)
from ets.connectors.sdk import ConnectorConfigurationError

AWS_CLOUDTRAIL_RETENTION_DAYS = 90
AWS_CLOUDTRAIL_MAX_PAGE_SIZE = 50
AWS_SOURCE_SYSTEM = "aws.cloudtrail"
AWS_EVENT_TYPE = "aws.cloudtrail.management_event.observed"
AWS_TRANSFORMATION_PROFILE = "ets.connector.aws.cloudtrail-metadata.v1"
AWS_ALLOWED_SETTINGS = frozenset({"region", "request_timeout_seconds"})
AWS_REGION_PATTERN = re.compile(r"^[a-z0-9-]{3,64}$")
AWS_ALLOWED_CREDENTIAL_KEYS = frozenset(
    {"aws_access_key_id", "aws_secret_access_key", "aws_session_token"}
)


class AwsCloudTrailClientError(RuntimeError):
    """Base source-client error without reusable credential material."""


class AwsCloudTrailAuthenticationError(AwsCloudTrailClientError):
    """Raised when AWS rejects the supplied session credentials."""


class AwsCloudTrailAuthorizationError(AwsCloudTrailClientError):
    """Raised when the credential cannot call CloudTrail LookupEvents."""


class AwsCloudTrailThrottleError(AwsCloudTrailClientError):
    """Raised when AWS throttles CloudTrail event lookup."""

    def __init__(self, retry_after_seconds: int = 1) -> None:
        super().__init__("AWS CloudTrail lookup is throttled")
        self.retry_after_seconds = max(retry_after_seconds, 1)


class AwsCloudTrailRetryableError(AwsCloudTrailClientError):
    """Raised for bounded transient AWS/network failures."""


@dataclass(frozen=True, slots=True)
class AwsCloudTrailPage:
    """One bounded CloudTrail Event History page plus opaque pagination state."""

    records: tuple[dict[str, JsonValue], ...]
    next_cursor: str | None
    observed_through_utc: datetime | None


@dataclass(frozen=True, slots=True)
class AwsCloudTrailSettings:
    region: str
    request_timeout_seconds: float


class CredentialResolver(Protocol):
    """Minimal G2B credential boundary required by the adapter."""

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class AwsCloudTrailClient(Protocol):
    """Source client contract used by the adapter and deterministic fixtures."""

    def collect(
        self,
        *,
        region: str,
        per_page: int,
        next_token: str | None,
        observed_at_or_after: datetime | None,
    ) -> AwsCloudTrailPage: ...

    def close(self) -> None: ...


AwsCloudTrailClientFactory = Callable[[AwsCloudTrailSettings, bytes], AwsCloudTrailClient]


class AwsCloudTrailBotoClient:
    """Bounded CloudTrail LookupEvents client using optional boto3 dependencies."""

    def __init__(self, settings: AwsCloudTrailSettings, credential_material: bytes) -> None:
        if not credential_material:
            raise ValueError("AWS credential material must not be empty")
        credential_buffer = bytearray(credential_material)
        try:
            credentials = _decode_session_credentials(bytes(credential_buffer))
            boto3: Any = importlib.import_module("boto3")
            botocore_config: Any = importlib.import_module("botocore.config")
            session = boto3.Session(
                aws_access_key_id=credentials["aws_access_key_id"],
                aws_secret_access_key=credentials["aws_secret_access_key"],
                aws_session_token=credentials.get("aws_session_token"),
                region_name=settings.region,
            )
            config = botocore_config.Config(
                connect_timeout=settings.request_timeout_seconds,
                read_timeout=settings.request_timeout_seconds,
                retries={"max_attempts": 0},
            )
            self._client: Any = session.client(
                "cloudtrail",
                region_name=settings.region,
                config=config,
            )
        except (ImportError, AttributeError) as exc:
            raise AwsCloudTrailClientError(
                "AWS connector requires the optional boto3 Gateway dependency"
            ) from exc
        finally:
            for index in range(len(credential_buffer)):
                credential_buffer[index] = 0
        self._closed = False

    def __repr__(self) -> str:
        return "AwsCloudTrailBotoClient(credential=<redacted>)"

    def collect(
        self,
        *,
        region: str,
        per_page: int,
        next_token: str | None,
        observed_at_or_after: datetime | None,
    ) -> AwsCloudTrailPage:
        if self._closed:
            raise AwsCloudTrailClientError("AWS CloudTrail client is closed")
        if not 1 <= per_page <= AWS_CLOUDTRAIL_MAX_PAGE_SIZE:
            raise ValueError("AWS CloudTrail page size must be 1-50")

        request: dict[str, object] = {"MaxResults": per_page}
        if next_token is not None:
            request["NextToken"] = next_token
        if observed_at_or_after is not None:
            if (
                observed_at_or_after.tzinfo is None
                or observed_at_or_after.utcoffset() is None
            ):
                raise ValueError("AWS CloudTrail checkpoint timestamp must be timezone-aware")
            request["StartTime"] = observed_at_or_after.astimezone(UTC)

        try:
            response = self._client.lookup_events(**request)
        except Exception as exc:
            _raise_aws_error(exc)

        events = response.get("Events", [])
        if not isinstance(events, list):
            raise AwsCloudTrailRetryableError("AWS CloudTrail returned an unexpected event list")
        records: list[dict[str, JsonValue]] = []
        observed_through: datetime | None = None
        for event in events:
            if not isinstance(event, Mapping):
                raise AwsCloudTrailRetryableError("AWS CloudTrail returned a non-object event")
            record = _bounded_source_record(event, region=region)
            records.append(record)
            timestamp = _source_timestamp(record)
            if timestamp is not None and (
                observed_through is None or timestamp > observed_through
            ):
                observed_through = timestamp

        raw_next = response.get("NextToken")
        if raw_next is not None and not isinstance(raw_next, str):
            raise AwsCloudTrailRetryableError(
                "AWS CloudTrail returned an invalid pagination token"
            )
        return AwsCloudTrailPage(
            records=tuple(records),
            next_cursor=raw_next,
            observed_through_utc=observed_through,
        )

    def close(self) -> None:
        if self._closed:
            return
        close = getattr(self._client, "close", None)
        if callable(close):
            close()
        self._closed = True


class AwsCloudTrailAdapter:
    """G2F2 adapter for bounded AWS CloudTrail management-event history."""

    def __init__(
        self,
        definition: ConnectorDefinitionV1,
        credential_resolver: CredentialResolver,
        *,
        client_factory: AwsCloudTrailClientFactory | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if definition.connector_id != "aws.cloudtrail":
            raise ValueError("AWS CloudTrail adapter requires aws.cloudtrail definition")
        if definition.implementation_class != "enterprise_api":
            raise ValueError("AWS CloudTrail adapter requires enterprise_api definition")
        self._definition = definition
        self._credential_resolver = credential_resolver
        self._client_factory = client_factory or AwsCloudTrailBotoClient
        self._now = now or _utc_now

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        _settings(instance)
        if instance.collection.mode != "poll":
            raise ConnectorConfigurationError("AWS CloudTrail connector requires poll collection")
        if instance.collection.batch_size > AWS_CLOUDTRAIL_MAX_PAGE_SIZE:
            raise ConnectorConfigurationError(
                "AWS CloudTrail collection batch_size must not exceed 50"
            )
        if instance.checkpoint.strategy != "time_window":
            raise ConnectorConfigurationError(
                "AWS CloudTrail connector requires time_window checkpoint strategy"
            )
        if instance.authentication.method != "aws_session":
            raise ConnectorConfigurationError(
                "AWS CloudTrail connector requires aws_session authentication"
            )
        if instance.authentication.credential_ref is None:
            raise ConnectorConfigurationError(
                "AWS CloudTrail connector requires an opaque credential reference"
            )

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        settings = _settings(instance)
        try:
            page = self._collect_page(instance, None, per_page=1)
        except CredentialResolutionError as exc:
            return _credential_health(exc)
        except CredentialProviderNotFoundError:
            return _health("failed", "invalid_config", "AWS credential provider is unavailable")
        except AwsCloudTrailAuthenticationError:
            return _health("failed", "authentication_failed", "AWS session was rejected")
        except AwsCloudTrailAuthorizationError:
            return _health("failed", "authorization_failed", "AWS CloudTrail access was denied")
        except AwsCloudTrailThrottleError as exc:
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="degraded",
                code="throttled",
                message="AWS CloudTrail lookup is rate limited",
                retry_after_seconds=exc.retry_after_seconds,
            )
        except AwsCloudTrailRetryableError:
            return _health(
                "degraded",
                "retryable_error",
                "AWS CloudTrail is temporarily unavailable",
            )
        except AwsCloudTrailClientError:
            return _health("failed", "terminal_error", "AWS CloudTrail request failed")
        return _health(
            "healthy",
            "ok",
            f"AWS CloudTrail source is reachable in region {settings.region}; "
            f"sample_count={len(page.records)}",
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return (_settings(instance).region,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        try:
            page = self._collect_page(instance, checkpoint)
        except CredentialResolutionError as exc:
            return _collection(_credential_operation_code(exc), "AWS credential is unavailable")
        except CredentialProviderNotFoundError:
            return _collection("invalid_config", "AWS credential provider is unavailable")
        except AwsCloudTrailAuthenticationError:
            return _collection("authentication_failed", "AWS session was rejected")
        except AwsCloudTrailAuthorizationError:
            return _collection("authorization_failed", "AWS CloudTrail access was denied")
        except AwsCloudTrailThrottleError:
            return _collection("throttled", "AWS CloudTrail lookup is rate limited")
        except AwsCloudTrailRetryableError:
            return _collection("retryable_error", "AWS CloudTrail is temporarily unavailable")
        except AwsCloudTrailClientError:
            return _collection("terminal_error", "AWS CloudTrail request failed")

        observed = _later_timestamp(
            checkpoint.observed_through_utc if checkpoint is not None else None,
            page.observed_through_utc,
        )
        next_checkpoint = ConnectorCheckpointV1(
            schema_version="ets.connector.checkpoint.v1",
            cursor=page.next_cursor,
            observed_through_utc=observed,
        )
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=page.records,
            checkpoint=next_checkpoint,
            has_more=page.next_cursor is not None,
            message="AWS CloudTrail page collected",
        )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        return result.checkpoint

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        self.validate_config(instance)
        if checkpoint is None or checkpoint.observed_through_utc is None:
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code="unknown_observation",
                reconciled=False,
                gap_detected=False,
                checkpoint=checkpoint,
                message=(
                    "AWS CloudTrail continuity cannot be established without a time checkpoint"
                ),
            )
        retention_floor = self._now().astimezone(UTC) - timedelta(
            days=AWS_CLOUDTRAIL_RETENTION_DAYS
        )
        if checkpoint.observed_through_utc < retention_floor:
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code="gap_detected",
                reconciled=False,
                gap_detected=True,
                checkpoint=checkpoint,
                message=(
                    "AWS CloudTrail checkpoint is older than the qualified event-history window"
                ),
            )
        result = self.collect(instance, checkpoint)
        if result.code != "ok":
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code=result.code,
                reconciled=False,
                gap_detected=False,
                checkpoint=checkpoint,
                message=result.message,
            )
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="ok",
            reconciled=True,
            gap_detected=False,
            checkpoint=result.checkpoint,
            message="AWS CloudTrail continuity probe completed",
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        self.validate_config(instance)
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id=_source_record_id(record),
            source_system=AWS_SOURCE_SYSTEM,
            observed_at_utc=_source_timestamp(record),
            event_type=AWS_EVENT_TYPE,
            media_type="application/json",
            transformation_profile=AWS_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata={
                "provider": "aws",
                "source_class": "cloudtrail_event_history",
                "region": _settings(instance).region,
                "audit": _minimized_record(record),
            },
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)

    def _collect_page(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
        *,
        per_page: int | None = None,
    ) -> AwsCloudTrailPage:
        settings = _settings(instance)
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError("AWS credential reference is required")
        reference = CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=credential_ref,
        )
        with self._credential_resolver.resolve(reference) as lease:
            client = self._client_factory(settings, lease.reveal())
            try:
                return client.collect(
                    region=settings.region,
                    per_page=per_page or instance.collection.batch_size,
                    next_token=checkpoint.cursor if checkpoint is not None else None,
                    observed_at_or_after=(
                        checkpoint.observed_through_utc if checkpoint is not None else None
                    ),
                )
            finally:
                client.close()


def _settings(instance: ConnectorInstanceV1) -> AwsCloudTrailSettings:
    unexpected = sorted(set(instance.settings) - AWS_ALLOWED_SETTINGS)
    if unexpected:
        raise ConnectorConfigurationError(
            "unsupported AWS CloudTrail connector settings: " + ", ".join(unexpected)
        )
    region = instance.settings.get("region")
    if not isinstance(region, str) or AWS_REGION_PATTERN.fullmatch(region) is None:
        raise ConnectorConfigurationError("AWS CloudTrail region setting is invalid")
    timeout = instance.settings.get("request_timeout_seconds", 10.0)
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not 0 < timeout <= 60
    ):
        raise ConnectorConfigurationError("AWS request timeout must be between 0 and 60 seconds")
    return AwsCloudTrailSettings(region=region, request_timeout_seconds=float(timeout))


def _decode_session_credentials(material: bytes) -> dict[str, str]:
    try:
        decoded = json.loads(material.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AwsCloudTrailAuthenticationError("AWS credential lease is invalid") from exc
    if not isinstance(decoded, dict):
        raise AwsCloudTrailAuthenticationError("AWS credential lease is invalid")
    unexpected = set(decoded) - AWS_ALLOWED_CREDENTIAL_KEYS
    if unexpected:
        raise AwsCloudTrailAuthenticationError("AWS credential lease has unsupported fields")

    access_key = decoded.get("aws_access_key_id")
    secret_key = decoded.get("aws_secret_access_key")
    session_token = decoded.get("aws_session_token")
    if not isinstance(access_key, str) or not access_key:
        raise AwsCloudTrailAuthenticationError(
            "AWS credential lease is missing access key material"
        )
    if not isinstance(secret_key, str) or not secret_key:
        raise AwsCloudTrailAuthenticationError(
            "AWS credential lease is missing secret key material"
        )
    if session_token is not None and (
        not isinstance(session_token, str) or not session_token
    ):
        raise AwsCloudTrailAuthenticationError(
            "AWS credential lease has invalid session token material"
        )

    result = {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    if isinstance(session_token, str):
        result["aws_session_token"] = session_token
    return result


def _bounded_source_record(
    event: Mapping[str, Any],
    *,
    region: str,
) -> dict[str, JsonValue]:
    record: dict[str, JsonValue] = {"region": region}
    _copy_string(event, record, "EventId", "event_id", 500)
    _copy_string(event, record, "EventName", "event_name", 200)
    _copy_string(event, record, "EventSource", "event_source", 200)
    _copy_string(event, record, "ReadOnly", "read_only", 20)

    event_time = event.get("EventTime")
    if isinstance(event_time, datetime):
        if event_time.tzinfo is None or event_time.utcoffset() is None:
            event_time = event_time.replace(tzinfo=UTC)
        record["event_time"] = event_time.astimezone(UTC).isoformat()

    resources = event.get("Resources")
    if isinstance(resources, list):
        bounded_resources: list[JsonValue] = []
        for raw_resource in resources[:32]:
            if not isinstance(raw_resource, Mapping):
                continue
            resource: dict[str, JsonValue] = {}
            _copy_string(raw_resource, resource, "ResourceType", "resource_type", 300)
            _copy_string(raw_resource, resource, "ResourceName", "resource_name", 500)
            if resource:
                bounded_resources.append(resource)
        if bounded_resources:
            record["resources"] = bounded_resources

    raw_detail = event.get("CloudTrailEvent")
    if isinstance(raw_detail, str):
        detail = _bounded_cloudtrail_detail(raw_detail)
        if detail:
            record["detail"] = detail
    return record


def _bounded_cloudtrail_detail(raw: str) -> dict[str, JsonValue]:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}

    detail: dict[str, JsonValue] = {}
    for key in (
        "eventVersion",
        "eventSource",
        "eventName",
        "awsRegion",
        "eventID",
        "eventType",
        "managementEvent",
        "readOnly",
        "recipientAccountId",
        "sharedEventID",
        "vpcEndpointId",
    ):
        value = decoded.get(key)
        if isinstance(value, (str, bool, int, float)):
            detail[_snake_case(key)] = cast(JsonValue, value)

    event_time = decoded.get("eventTime")
    if isinstance(event_time, str):
        detail["event_time"] = event_time[:100]

    identity = decoded.get("userIdentity")
    if isinstance(identity, dict):
        minimized_identity: dict[str, JsonValue] = {}
        for source_key, target_key in (
            ("type", "type"),
            ("principalId", "principal_id"),
            ("accountId", "account_id"),
            ("invokedBy", "invoked_by"),
        ):
            value = identity.get(source_key)
            if isinstance(value, str) and value:
                minimized_identity[target_key] = value[:500]
        if minimized_identity:
            detail["user_identity"] = minimized_identity
    return detail


def _copy_string(
    source: Mapping[str, Any],
    target: dict[str, JsonValue],
    source_key: str,
    target_key: str,
    maximum: int,
) -> None:
    value = source.get(source_key)
    if isinstance(value, str) and value:
        target[target_key] = value[:maximum]


def _minimized_record(record: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    allowed = (
        "region",
        "event_id",
        "event_name",
        "event_source",
        "event_time",
        "read_only",
    )
    minimized = {key: record[key] for key in allowed if key in record}
    resources = record.get("resources")
    if isinstance(resources, list):
        minimized["resources"] = resources[:32]
    detail = record.get("detail")
    if isinstance(detail, dict):
        minimized["detail"] = detail
    return minimized


def _source_record_id(record: Mapping[str, JsonValue]) -> str:
    event_id = record.get("event_id")
    if isinstance(event_id, str) and event_id:
        return event_id[:500]
    encoded = json.dumps(
        dict(record),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _source_timestamp(record: Mapping[str, JsonValue]) -> datetime | None:
    raw = record.get("event_time")
    if not isinstance(raw, str):
        return None
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _raise_aws_error(exc: Exception) -> NoReturn:
    code = _aws_error_code(exc)
    if code in {
        "ExpiredToken",
        "ExpiredTokenException",
        "InvalidClientTokenId",
        "SignatureDoesNotMatch",
        "UnrecognizedClientException",
    }:
        raise AwsCloudTrailAuthenticationError(
            "AWS session credential was rejected"
        ) from exc
    if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
        raise AwsCloudTrailAuthorizationError("AWS CloudTrail access was denied") from exc
    if code in {"Throttling", "ThrottlingException", "TooManyRequestsException"}:
        raise AwsCloudTrailThrottleError() from exc
    if code in {
        "InternalError",
        "InternalFailure",
        "RequestTimeout",
        "RequestTimeoutException",
        "ServiceUnavailable",
    }:
        raise AwsCloudTrailRetryableError(
            "AWS CloudTrail request is temporarily unavailable"
        ) from exc
    raise AwsCloudTrailRetryableError("AWS CloudTrail request failed") from exc


def _aws_error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None
    error = response.get("Error")
    if not isinstance(error, dict):
        return None
    code = error.get("Code")
    return code if isinstance(code, str) else None


def _credential_operation_code(exc: CredentialResolutionError) -> ConnectorOperationCode:
    if exc.status in {"missing", "expired", "revoked"}:
        return "authentication_failed"
    if exc.status == "unavailable":
        return "retryable_error"
    return "invalid_config"


def _credential_health(exc: CredentialResolutionError) -> ConnectorHealthV1:
    code = _credential_operation_code(exc)
    state: ConnectorHealthState = "degraded" if code == "retryable_error" else "failed"
    return _health(state, code, "AWS connector credential is unavailable")


def _health(
    state: ConnectorHealthState,
    code: ConnectorOperationCode,
    message: str,
) -> ConnectorHealthV1:
    return ConnectorHealthV1(
        schema_version="ets.connector.health.v1",
        state=state,
        code=code,
        message=message,
    )


def _collection(
    code: ConnectorOperationCode,
    message: str,
) -> ConnectorCollectionResultV1:
    return ConnectorCollectionResultV1(
        schema_version="ets.connector.collection_result.v1",
        code=code,
        message=message,
    )


def _later_timestamp(first: datetime | None, second: datetime | None) -> datetime | None:
    if first is None:
        return second
    if second is None:
        return first
    return max(first, second)


def _snake_case(value: str) -> str:
    output: list[str] = []
    for character in value:
        if character.isupper() and output:
            output.append("_")
        output.append(character.lower())
    return "".join(output)


def _utc_now() -> datetime:
    return datetime.now(UTC)
