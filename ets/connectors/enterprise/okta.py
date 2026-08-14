"""Okta System Log enterprise connector for G2F3."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import NoReturn, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
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

OKTA_SYSTEM_LOG_RETENTION_DAYS = 90
OKTA_MAX_PAGE_SIZE = 100
OKTA_SOURCE_SYSTEM = "okta.system_log"
OKTA_EVENT_TYPE = "okta.system_log.observed"
OKTA_TRANSFORMATION_PROFILE = "ets.connector.okta.system-log-metadata.v1"
OKTA_ALLOWED_SETTINGS = frozenset({"organization", "domain_suffix", "request_timeout_seconds"})
OKTA_ALLOWED_DOMAIN_SUFFIXES = frozenset({"okta.com", "oktapreview.com", "okta-emea.com"})
OKTA_ORGANIZATION_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


class OktaSystemLogClientError(RuntimeError):
    """Base source-client error without reusable credential material."""


class OktaSystemLogAuthenticationError(OktaSystemLogClientError):
    """Raised when Okta rejects the configured API token."""


class OktaSystemLogAuthorizationError(OktaSystemLogClientError):
    """Raised when the token lacks System Log access."""


class OktaSystemLogThrottleError(OktaSystemLogClientError):
    """Raised when Okta rate-limits System Log collection."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Okta System Log API is rate limited")
        self.retry_after_seconds = max(retry_after_seconds, 1)


class OktaSystemLogRetryableError(OktaSystemLogClientError):
    """Raised for bounded transient source/network failures."""


@dataclass(frozen=True, slots=True)
class OktaSystemLogPage:
    records: tuple[dict[str, JsonValue], ...]
    next_cursor: str | None
    observed_through_utc: datetime | None


@dataclass(frozen=True, slots=True)
class OktaSystemLogSettings:
    organization: str
    domain_suffix: str
    request_timeout_seconds: float

    @property
    def host(self) -> str:
        return f"{self.organization}.{self.domain_suffix}".lower()

    @property
    def base_url(self) -> str:
        return f"https://{self.host}"


class CredentialResolver(Protocol):
    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class OktaSystemLogClient(Protocol):
    def collect(
        self,
        *,
        per_page: int,
        next_url: str | None,
        observed_at_or_after: datetime | None,
    ) -> OktaSystemLogPage: ...

    def close(self) -> None: ...


OktaSystemLogClientFactory = Callable[[OktaSystemLogSettings, bytes], OktaSystemLogClient]


class OktaSystemLogHttpClient:
    """Bounded polling client that follows Okta-generated next links."""

    def __init__(self, settings: OktaSystemLogSettings, credential_material: bytes) -> None:
        if not credential_material:
            raise ValueError("Okta credential material must not be empty")
        self._settings = settings
        self._credential = bytearray(credential_material)
        self._closed = False

    def __repr__(self) -> str:
        return f"OktaSystemLogHttpClient(credential=<redacted>, host={self._settings.host!r})"

    def collect(
        self,
        *,
        per_page: int,
        next_url: str | None,
        observed_at_or_after: datetime | None,
    ) -> OktaSystemLogPage:
        if self._closed:
            raise OktaSystemLogClientError("Okta System Log client is closed")
        if not 1 <= per_page <= OKTA_MAX_PAGE_SIZE:
            raise ValueError("Okta System Log page size must be 1-100")

        if next_url is not None:
            url = _validated_next_url(self._settings, next_url)
        else:
            query: dict[str, str | int] = {
                "limit": per_page,
                "sortOrder": "ASCENDING",
            }
            if observed_at_or_after is not None:
                if (
                    observed_at_or_after.tzinfo is None
                    or observed_at_or_after.utcoffset() is None
                ):
                    raise ValueError("Okta checkpoint timestamp must be timezone-aware")
                query["since"] = _format_utc(observed_at_or_after)
            url = f"{self._settings.base_url}/api/v1/logs?{urlencode(query)}"

        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"SSWS {self._credential_text()}",
                "User-Agent": "ets-gateway-okta-system-log/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self._settings.request_timeout_seconds) as response:
                raw = response.read()
                link_header = response.headers.get("Link")
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise OktaSystemLogRetryableError("Okta System Log API request failed") from exc

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OktaSystemLogRetryableError("Okta System Log API returned invalid JSON") from exc
        if not isinstance(decoded, list):
            raise OktaSystemLogRetryableError("Okta System Log API returned an unexpected payload")

        records: list[dict[str, JsonValue]] = []
        observed_through: datetime | None = None
        for item in decoded:
            if not isinstance(item, dict):
                raise OktaSystemLogRetryableError("Okta System Log API returned a non-object event")
            record = _bounded_source_record(item)
            records.append(record)
            timestamp = _source_timestamp(record)
            if timestamp is not None and (observed_through is None or timestamp > observed_through):
                observed_through = timestamp

        next_link = _next_link(link_header)
        if next_link is None:
            raise OktaSystemLogRetryableError(
                "Okta polling response omitted the expected next-link cursor"
            )
        next_link = _validated_next_url(self._settings, next_link)
        return OktaSystemLogPage(
            records=tuple(records),
            next_cursor=next_link,
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
            raise OktaSystemLogAuthenticationError(
                "Okta credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if exc.code == 401:
            raise OktaSystemLogAuthenticationError("Okta API token was rejected") from exc
        if exc.code == 403:
            raise OktaSystemLogAuthorizationError("Okta System Log access was denied") from exc
        if exc.code == 429:
            raise OktaSystemLogThrottleError(_retry_after_seconds(exc)) from exc
        if 500 <= exc.code <= 599:
            raise OktaSystemLogRetryableError("Okta System Log API server error") from exc
        raise OktaSystemLogClientError(
            f"Okta System Log API rejected request with HTTP {exc.code}"
        ) from exc


class OktaSystemLogAdapter:
    """G2F3 adapter for bounded Okta System Log observations."""

    def __init__(
        self,
        definition: ConnectorDefinitionV1,
        credential_resolver: CredentialResolver,
        *,
        client_factory: OktaSystemLogClientFactory | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if definition.connector_id != "okta.system_log":
            raise ValueError("Okta System Log adapter requires okta.system_log definition")
        if definition.implementation_class != "enterprise_api":
            raise ValueError("Okta System Log adapter requires enterprise_api definition")
        self._definition = definition
        self._credential_resolver = credential_resolver
        self._client_factory = client_factory or OktaSystemLogHttpClient
        self._now = now or _utc_now

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        _settings(instance)
        if instance.collection.mode != "poll":
            raise ConnectorConfigurationError("Okta System Log connector requires poll collection")
        if instance.collection.batch_size > OKTA_MAX_PAGE_SIZE:
            raise ConnectorConfigurationError(
                "Okta System Log collection batch_size must not exceed 100"
            )
        if instance.checkpoint.strategy != "time_window":
            raise ConnectorConfigurationError(
                "Okta System Log connector requires time_window checkpoint strategy"
            )
        if instance.authentication.method != "api_token":
            raise ConnectorConfigurationError(
                "Okta System Log connector requires api_token authentication"
            )
        if instance.authentication.credential_ref is None:
            raise ConnectorConfigurationError(
                "Okta System Log connector requires an opaque credential reference"
            )

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        settings = _settings(instance)
        try:
            page = self._collect_page(instance, None, per_page=1)
        except CredentialResolutionError as exc:
            return _credential_health(exc)
        except CredentialProviderNotFoundError:
            return _health("failed", "invalid_config", "Okta credential provider is unavailable")
        except OktaSystemLogAuthenticationError:
            return _health("failed", "authentication_failed", "Okta API token was rejected")
        except OktaSystemLogAuthorizationError:
            return _health("failed", "authorization_failed", "Okta System Log access was denied")
        except OktaSystemLogThrottleError as exc:
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="degraded",
                code="throttled",
                message="Okta System Log API is rate limited",
                retry_after_seconds=exc.retry_after_seconds,
            )
        except OktaSystemLogRetryableError:
            return _health(
                "degraded",
                "retryable_error",
                "Okta System Log API is temporarily unavailable",
            )
        except OktaSystemLogClientError:
            return _health("failed", "terminal_error", "Okta System Log request failed")
        return _health(
            "healthy",
            "ok",
            f"Okta System Log is reachable for {settings.host}; sample_count={len(page.records)}",
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return (_settings(instance).host,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        try:
            page = self._collect_page(instance, checkpoint)
        except CredentialResolutionError as exc:
            return _collection(_credential_operation_code(exc), "Okta credential is unavailable")
        except CredentialProviderNotFoundError:
            return _collection("invalid_config", "Okta credential provider is unavailable")
        except OktaSystemLogAuthenticationError:
            return _collection("authentication_failed", "Okta API token was rejected")
        except OktaSystemLogAuthorizationError:
            return _collection("authorization_failed", "Okta System Log access was denied")
        except OktaSystemLogThrottleError:
            return _collection("throttled", "Okta System Log API is rate limited")
        except OktaSystemLogRetryableError:
            return _collection("retryable_error", "Okta System Log API is temporarily unavailable")
        except OktaSystemLogClientError:
            return _collection("terminal_error", "Okta System Log request failed")

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
            message="Okta System Log page collected",
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
                message="Okta continuity cannot be established without a time checkpoint",
            )
        retention_floor = self._now().astimezone(UTC) - timedelta(
            days=OKTA_SYSTEM_LOG_RETENTION_DAYS
        )
        if checkpoint.observed_through_utc < retention_floor:
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code="gap_detected",
                reconciled=False,
                gap_detected=True,
                checkpoint=checkpoint,
                message="Okta checkpoint is older than the qualified System Log window",
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
            message="Okta System Log continuity probe completed",
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
            source_system=OKTA_SOURCE_SYSTEM,
            observed_at_utc=_source_timestamp(record),
            event_type=OKTA_EVENT_TYPE,
            media_type="application/json",
            transformation_profile=OKTA_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata={
                "provider": "okta",
                "source_class": "system_log",
                "organization": _settings(instance).host,
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
    ) -> OktaSystemLogPage:
        settings = _settings(instance)
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError("Okta credential reference is required")
        reference = CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=credential_ref,
        )
        with self._credential_resolver.resolve(reference) as lease:
            client = self._client_factory(settings, lease.reveal())
            try:
                return client.collect(
                    per_page=per_page or instance.collection.batch_size,
                    next_url=checkpoint.cursor if checkpoint is not None else None,
                    observed_at_or_after=(
                        checkpoint.observed_through_utc if checkpoint is not None else None
                    ),
                )
            finally:
                client.close()


def _settings(instance: ConnectorInstanceV1) -> OktaSystemLogSettings:
    unexpected = sorted(set(instance.settings) - OKTA_ALLOWED_SETTINGS)
    if unexpected:
        raise ConnectorConfigurationError(
            "unsupported Okta System Log connector settings: " + ", ".join(unexpected)
        )
    organization = instance.settings.get("organization")
    if (
        not isinstance(organization, str)
        or OKTA_ORGANIZATION_PATTERN.fullmatch(organization) is None
    ):
        raise ConnectorConfigurationError("Okta organization setting is invalid")
    suffix = instance.settings.get("domain_suffix", "okta.com")
    if not isinstance(suffix, str) or suffix not in OKTA_ALLOWED_DOMAIN_SUFFIXES:
        raise ConnectorConfigurationError("Okta domain_suffix is not in the qualified allowlist")
    timeout = instance.settings.get("request_timeout_seconds", 10.0)
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not 0 < timeout <= 30
    ):
        raise ConnectorConfigurationError("Okta request timeout must be between 0 and 30 seconds")
    return OktaSystemLogSettings(
        organization=organization.lower(),
        domain_suffix=suffix,
        request_timeout_seconds=float(timeout),
    )


def _bounded_source_record(raw: Mapping[str, object]) -> dict[str, JsonValue]:
    record: dict[str, JsonValue] = {}
    _copy_string(raw, record, "uuid", "uuid", 500)
    _copy_string(raw, record, "published", "published", 100)
    _copy_string(raw, record, "eventType", "event_type", 300)
    _copy_string(raw, record, "version", "version", 50)
    _copy_string(raw, record, "severity", "severity", 50)

    actor = raw.get("actor")
    if isinstance(actor, Mapping):
        bounded_actor: dict[str, JsonValue] = {}
        _copy_string(actor, bounded_actor, "id", "id", 500)
        _copy_string(actor, bounded_actor, "type", "type", 200)
        if bounded_actor:
            record["actor"] = bounded_actor

    outcome = raw.get("outcome")
    if isinstance(outcome, Mapping):
        bounded_outcome: dict[str, JsonValue] = {}
        _copy_string(outcome, bounded_outcome, "result", "result", 100)
        _copy_string(outcome, bounded_outcome, "reason", "reason", 500)
        if bounded_outcome:
            record["outcome"] = bounded_outcome

    transaction = raw.get("transaction")
    if isinstance(transaction, Mapping):
        bounded_transaction: dict[str, JsonValue] = {}
        _copy_string(transaction, bounded_transaction, "id", "id", 500)
        _copy_string(transaction, bounded_transaction, "type", "type", 100)
        if bounded_transaction:
            record["transaction"] = bounded_transaction

    targets = raw.get("target")
    if isinstance(targets, list):
        bounded_targets: list[JsonValue] = []
        for item in targets[:32]:
            if not isinstance(item, Mapping):
                continue
            target: dict[str, JsonValue] = {}
            _copy_string(item, target, "id", "id", 500)
            _copy_string(item, target, "type", "type", 200)
            if target:
                bounded_targets.append(target)
        if bounded_targets:
            record["target"] = bounded_targets
    return record


def _copy_string(
    source: Mapping[str, object],
    target: dict[str, JsonValue],
    source_key: str,
    target_key: str,
    maximum: int,
) -> None:
    value = source.get(source_key)
    if isinstance(value, str) and value:
        target[target_key] = value[:maximum]


def _minimized_record(record: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    allowed = ("uuid", "published", "event_type", "version", "severity")
    minimized = {key: record[key] for key in allowed if key in record}
    for key in ("actor", "outcome", "transaction", "target"):
        if key in record:
            minimized[key] = record[key]
    return minimized


def _source_record_id(record: Mapping[str, JsonValue]) -> str:
    value = record.get("uuid")
    if isinstance(value, str) and value:
        return value[:500]
    encoded = json.dumps(
        dict(record),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _source_timestamp(record: Mapping[str, JsonValue]) -> datetime | None:
    raw = record.get("published")
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


def _validated_next_url(settings: OktaSystemLogSettings, value: str) -> str:
    if not 1 <= len(value) <= 4000:
        raise OktaSystemLogRetryableError("Okta next-link cursor exceeds configured limit")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != settings.host:
        raise OktaSystemLogRetryableError("Okta next-link cursor changed the qualified origin")
    if parsed.port not in {None, 443} or parsed.path != "/api/v1/logs":
        raise OktaSystemLogRetryableError("Okta next-link cursor changed the qualified endpoint")
    return value


def _next_link(header: str | None) -> str | None:
    if not header:
        return None
    for part in header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">", start + 1)
        if start >= 0 and end > start:
            return section[start + 1 : end]
    return None


def _retry_after_seconds(exc: HTTPError) -> int:
    retry_after = exc.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(int(retry_after), 1)
        except ValueError:
            pass
    reset = exc.headers.get("X-Rate-Limit-Reset")
    if reset is not None:
        try:
            return max(int(reset) - int(_utc_now().timestamp()), 1)
        except ValueError:
            pass
    return 60


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _credential_operation_code(exc: CredentialResolutionError) -> ConnectorOperationCode:
    if exc.status in {"missing", "expired", "revoked"}:
        return "authentication_failed"
    if exc.status == "unavailable":
        return "retryable_error"
    return "invalid_config"


def _credential_health(exc: CredentialResolutionError) -> ConnectorHealthV1:
    code = _credential_operation_code(exc)
    state: ConnectorHealthState = "degraded" if code == "retryable_error" else "failed"
    return _health(state, code, "Okta connector credential is unavailable")


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


def _collection(code: ConnectorOperationCode, message: str) -> ConnectorCollectionResultV1:
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


def _utc_now() -> datetime:
    return datetime.now(UTC)
