"""GitHub organization audit-log connector reference implementation for G2F."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import Request, urlopen

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

GITHUB_AUDIT_RETENTION_DAYS = 180
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_DEFAULT_API_VERSION = "2022-11-28"
GITHUB_SOURCE_SYSTEM = "github.audit"
GITHUB_EVENT_TYPE = "github.audit.observed"
GITHUB_TRANSFORMATION_PROFILE = "ets.connector.github.audit-metadata.v1"
GITHUB_ALLOWED_SETTINGS = frozenset(
    {
        "organization",
        "api_version",
        "include",
        "request_timeout_seconds",
    }
)
GITHUB_ORGANIZATION_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,98}[A-Za-z0-9])?$")
GITHUB_INCLUDE_VALUES = frozenset({"web", "git", "all"})
GITHUB_PROVENANCE_FIELDS = (
    "@timestamp",
    "_document_id",
    "action",
    "actor",
    "actor_id",
    "actor_is_bot",
    "business",
    "business_id",
    "category_type",
    "created_at",
    "operation_type",
    "org",
    "org_id",
    "repo",
    "repo_id",
    "repository",
    "repository_id",
    "request_id",
    "user",
    "user_id",
)


class GitHubAuditClientError(RuntimeError):
    """Base source-client error without reusable credential material."""


class GitHubAuditAuthenticationError(GitHubAuditClientError):
    """Raised when source credentials are rejected."""


class GitHubAuditAuthorizationError(GitHubAuditClientError):
    """Raised when credentials cannot access the requested organization audit log."""


class GitHubAuditThrottleError(GitHubAuditClientError):
    """Raised when GitHub instructs the connector to wait before retrying."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("GitHub audit API rate limit reached")
        self.retry_after_seconds = max(retry_after_seconds, 1)


class GitHubAuditRetryableError(GitHubAuditClientError):
    """Raised for bounded transient source/network failures."""


@dataclass(frozen=True, slots=True)
class GitHubAuditPage:
    """One bounded source page plus opaque pagination state."""

    records: tuple[dict[str, JsonValue], ...]
    next_cursor: str | None
    observed_through_utc: datetime | None


@dataclass(frozen=True, slots=True)
class GitHubAuditSettings:
    organization: str
    api_version: str
    include: str
    request_timeout_seconds: float


class CredentialResolver(Protocol):
    """Minimal G2B boundary required by enterprise API adapters."""

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class GitHubAuditClient(Protocol):
    """Source client contract used by the adapter and deterministic fixtures."""

    def collect(
        self,
        *,
        organization: str,
        include: str,
        per_page: int,
        after: str | None,
        observed_at_or_after: datetime | None,
    ) -> GitHubAuditPage: ...

    def close(self) -> None: ...


GitHubAuditClientFactory = Callable[[GitHubAuditSettings, bytes], GitHubAuditClient]


class GitHubAuditHttpClient:
    """Minimal bounded REST client for GitHub.com organization audit-log collection."""

    def __init__(self, settings: GitHubAuditSettings, credential_material: bytes) -> None:
        if not credential_material:
            raise ValueError("GitHub credential material must not be empty")
        self._settings = settings
        self._credential = bytearray(credential_material)
        self._closed = False

    def __repr__(self) -> str:
        return "GitHubAuditHttpClient(credential=<redacted>, api_base_url='https://api.github.com')"

    def collect(
        self,
        *,
        organization: str,
        include: str,
        per_page: int,
        after: str | None,
        observed_at_or_after: datetime | None,
    ) -> GitHubAuditPage:
        if self._closed:
            raise GitHubAuditClientError("GitHub audit client is closed")
        query: dict[str, str | int] = {
            "include": include,
            "order": "asc",
            "per_page": per_page,
        }
        if after is not None:
            query["after"] = after
        elif observed_at_or_after is not None:
            query["phrase"] = f"created:>={_github_search_time(observed_at_or_after)}"

        url = (
            f"{GITHUB_API_BASE_URL}/orgs/{quote(organization, safe='')}/"
            f"audit-log?{urlencode(query)}"
        )
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._credential_text()}",
                "User-Agent": "ets-gateway-github-audit/1.0",
                "X-GitHub-Api-Version": self._settings.api_version,
            },
        )
        try:
            with urlopen(request, timeout=self._settings.request_timeout_seconds) as response:
                raw = response.read()
                link_header = response.headers.get("Link")
        except HTTPError as exc:
            self._raise_http_error(exc)
            raise AssertionError("unreachable")
        except (TimeoutError, URLError, OSError) as exc:
            raise GitHubAuditRetryableError("GitHub audit API request failed") from exc

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubAuditRetryableError("GitHub audit API returned invalid JSON") from exc
        if not isinstance(decoded, list):
            raise GitHubAuditRetryableError("GitHub audit API returned an unexpected payload")

        records: list[dict[str, JsonValue]] = []
        observed_through: datetime | None = None
        for item in decoded:
            if not isinstance(item, dict):
                raise GitHubAuditRetryableError("GitHub audit API returned a non-object event")
            record = cast(dict[str, JsonValue], item)
            records.append(record)
            timestamp = _source_timestamp(record)
            if timestamp is not None and (observed_through is None or timestamp > observed_through):
                observed_through = timestamp

        return GitHubAuditPage(
            records=tuple(records),
            next_cursor=_next_after_cursor(link_header),
            observed_through_utc=observed_through,
        )

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._credential)):
            self._credential[index] = 0
        self._closed = True

    def _credential_text(self) -> str:
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise GitHubAuditAuthenticationError(
                "GitHub credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> None:
        if exc.code == 401:
            raise GitHubAuditAuthenticationError("GitHub audit API authentication failed") from exc
        if exc.code in {403, 429}:
            remaining = exc.headers.get("X-RateLimit-Remaining")
            retry_after = exc.headers.get("Retry-After")
            if exc.code == 429 or remaining == "0" or retry_after is not None:
                raise GitHubAuditThrottleError(_retry_after_seconds(exc)) from exc
            raise GitHubAuditAuthorizationError("GitHub audit API authorization failed") from exc
        if exc.code == 404:
            raise GitHubAuditAuthorizationError("GitHub audit organization is not accessible") from exc
        if 500 <= exc.code <= 599:
            raise GitHubAuditRetryableError("GitHub audit API server error") from exc
        raise GitHubAuditClientError(f"GitHub audit API rejected request with HTTP {exc.code}") from exc


class GitHubAuditAdapter:
    """G2F reference adapter for GitHub organization audit observations."""

    def __init__(
        self,
        definition: ConnectorDefinitionV1,
        credential_resolver: CredentialResolver,
        *,
        client_factory: GitHubAuditClientFactory | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if definition.connector_id != "github.audit":
            raise ValueError("GitHub audit adapter requires github.audit definition")
        if definition.implementation_class != "enterprise_api":
            raise ValueError("GitHub audit adapter requires enterprise_api definition")
        self._definition = definition
        self._credential_resolver = credential_resolver
        self._client_factory = client_factory or GitHubAuditHttpClient
        self._now = now or _utc_now

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        _settings(instance)
        if instance.collection.mode != "poll":
            raise ConnectorConfigurationError("GitHub audit connector requires poll collection")
        if instance.collection.batch_size > 100:
            raise ConnectorConfigurationError("GitHub audit collection batch_size must not exceed 100")
        if instance.checkpoint.strategy != "time_window":
            raise ConnectorConfigurationError(
                "GitHub audit connector requires time_window checkpoint strategy"
            )
        if instance.authentication.method != "bearer":
            raise ConnectorConfigurationError("GitHub audit connector requires bearer authentication")
        if instance.authentication.credential_ref is None:
            raise ConnectorConfigurationError(
                "GitHub audit connector requires an opaque credential reference"
            )

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        settings = _settings(instance)
        try:
            page = self._collect_page(instance, None, per_page=1)
        except CredentialResolutionError as exc:
            return _credential_health(exc)
        except CredentialProviderNotFoundError:
            return _health("failed", "invalid_config", "GitHub credential provider is unavailable")
        except GitHubAuditAuthenticationError:
            return _health("failed", "authentication_failed", "GitHub credential was rejected")
        except GitHubAuditAuthorizationError:
            return _health("failed", "authorization_failed", "GitHub audit access was denied")
        except GitHubAuditThrottleError as exc:
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="degraded",
                code="throttled",
                message="GitHub audit API is rate limited",
                retry_after_seconds=exc.retry_after_seconds,
            )
        except GitHubAuditRetryableError:
            return _health("degraded", "retryable_error", "GitHub audit API is temporarily unavailable")
        except GitHubAuditClientError:
            return _health("failed", "terminal_error", "GitHub audit API request failed")
        message = (
            f"GitHub audit source is reachable for organization {settings.organization}; "
            f"sample_count={len(page.records)}"
        )
        return _health("healthy", "ok", message)

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return (_settings(instance).organization,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        try:
            page = self._collect_page(instance, checkpoint)
        except CredentialResolutionError as exc:
            return _collection(_credential_operation_code(exc), "GitHub credential is unavailable")
        except CredentialProviderNotFoundError:
            return _collection("invalid_config", "GitHub credential provider is unavailable")
        except GitHubAuditAuthenticationError:
            return _collection("authentication_failed", "GitHub credential was rejected")
        except GitHubAuditAuthorizationError:
            return _collection("authorization_failed", "GitHub audit access was denied")
        except GitHubAuditThrottleError:
            return _collection("throttled", "GitHub audit API is rate limited")
        except GitHubAuditRetryableError:
            return _collection("retryable_error", "GitHub audit API is temporarily unavailable")
        except GitHubAuditClientError:
            return _collection("terminal_error", "GitHub audit API request failed")

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
            message="GitHub audit page collected",
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
                message="GitHub audit continuity cannot be established without a time checkpoint",
            )
        retention_floor = self._now().astimezone(UTC) - timedelta(days=GITHUB_AUDIT_RETENTION_DAYS)
        if checkpoint.observed_through_utc < retention_floor:
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code="gap_detected",
                reconciled=False,
                gap_detected=True,
                checkpoint=checkpoint,
                message="GitHub audit checkpoint is older than the qualified retention window",
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
            message="GitHub audit source continuity probe completed",
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        self.validate_config(instance)
        source_record_id = _source_record_id(record)
        metadata: dict[str, JsonValue] = {
            "provider": "github",
            "source_class": "organization_audit_log",
            "organization": _settings(instance).organization,
            "audit": _minimized_record(record),
        }
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id=source_record_id,
            source_system=GITHUB_SOURCE_SYSTEM,
            observed_at_utc=_source_timestamp(record),
            event_type=GITHUB_EVENT_TYPE,
            media_type="application/vnd.github+json",
            transformation_profile=GITHUB_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata=metadata,
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)

    def _collect_page(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
        *,
        per_page: int | None = None,
    ) -> GitHubAuditPage:
        settings = _settings(instance)
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError("GitHub credential reference is required")
        reference = CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=credential_ref,
        )
        with self._credential_resolver.resolve(reference) as lease:
            client = self._client_factory(settings, lease.reveal())
            try:
                return client.collect(
                    organization=settings.organization,
                    include=settings.include,
                    per_page=per_page or instance.collection.batch_size,
                    after=checkpoint.cursor if checkpoint is not None else None,
                    observed_at_or_after=(
                        checkpoint.observed_through_utc if checkpoint is not None else None
                    ),
                )
            finally:
                client.close()


def _settings(instance: ConnectorInstanceV1) -> GitHubAuditSettings:
    unexpected = sorted(set(instance.settings) - GITHUB_ALLOWED_SETTINGS)
    if unexpected:
        raise ConnectorConfigurationError(
            "unsupported GitHub audit connector settings: " + ", ".join(unexpected)
        )
    organization = instance.settings.get("organization")
    if (
        not isinstance(organization, str)
        or GITHUB_ORGANIZATION_PATTERN.fullmatch(organization) is None
    ):
        raise ConnectorConfigurationError("GitHub organization setting is invalid")

    api_version = instance.settings.get("api_version", GITHUB_DEFAULT_API_VERSION)
    if not isinstance(api_version, str) or not 1 <= len(api_version) <= 40:
        raise ConnectorConfigurationError("GitHub api_version setting is invalid")
    include = instance.settings.get("include", "all")
    if not isinstance(include, str) or include not in GITHUB_INCLUDE_VALUES:
        raise ConnectorConfigurationError("GitHub include must be one of web, git, or all")
    timeout = instance.settings.get("request_timeout_seconds", 10.0)
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not 0 < timeout <= 60
    ):
        raise ConnectorConfigurationError("GitHub request timeout must be between 0 and 60 seconds")
    return GitHubAuditSettings(
        organization=organization,
        api_version=api_version,
        include=include,
        request_timeout_seconds=float(timeout),
    )


def _minimized_record(record: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {key: record[key] for key in GITHUB_PROVENANCE_FIELDS if key in record}


def _source_record_id(record: Mapping[str, JsonValue]) -> str:
    document_id = record.get("_document_id")
    if isinstance(document_id, str) and document_id:
        return document_id[:500]
    encoded = json.dumps(
        dict(record),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _source_timestamp(record: Mapping[str, JsonValue]) -> datetime | None:
    raw = record.get("@timestamp", record.get("created_at"))
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(raw) / 1000.0, UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _later_timestamp(first: datetime | None, second: datetime | None) -> datetime | None:
    if first is None:
        return second
    if second is None:
        return first
    return max(first, second)


def _github_search_time(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("GitHub audit checkpoint timestamp must be timezone-aware")
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def _next_after_cursor(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">", start + 1)
        if start < 0 or end < 0:
            continue
        query = parse_qs(urlsplit(section[start + 1 : end]).query)
        values = query.get("after")
        if values and values[0]:
            return values[0]
    return None


def _retry_after_seconds(exc: HTTPError) -> int:
    retry_after = exc.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(int(retry_after), 1)
        except ValueError:
            pass
    reset = exc.headers.get("X-RateLimit-Reset")
    if reset is not None:
        try:
            return max(int(reset) - int(_utc_now().timestamp()), 1)
        except ValueError:
            pass
    return 60


def _credential_operation_code(exc: CredentialResolutionError) -> ConnectorOperationCode:
    if exc.status in {"missing", "expired", "revoked"}:
        return "authentication_failed"
    if exc.status == "unavailable":
        return "retryable_error"
    return "invalid_config"


def _credential_health(exc: CredentialResolutionError) -> ConnectorHealthV1:
    code = _credential_operation_code(exc)
    state: ConnectorHealthState = "degraded" if code == "retryable_error" else "failed"
    return _health(state, code, "GitHub connector credential is unavailable")


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


def _utc_now() -> datetime:
    return datetime.now(UTC)
