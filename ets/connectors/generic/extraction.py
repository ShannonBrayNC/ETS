"""Bounded declarative JSON extraction and checkpoint semantics for Generic REST."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast
from urllib.parse import urlsplit

from pydantic import JsonValue

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialProviderNotFoundError,
    CredentialResolutionError,
)
from ets.connectors.generic.rest import (
    GenericRestAuthenticationError,
    GenericRestAuthorizationError,
    GenericRestClientError,
    GenericRestHostPolicy,
    GenericRestHttpClient,
    GenericRestRequestProfile,
    GenericRestResponse,
    GenericRestRetryableError,
    GenericRestTerminalError,
    GenericRestThrottleError,
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

GENERIC_REST_SOURCE_SYSTEM = "generic.rest"
GENERIC_REST_DEFAULT_EVENT_TYPE = "generic.rest.observed"
GENERIC_REST_TRANSFORMATION_PROFILE = "ets.connector.generic-rest.declarative-json.v1"
GENERIC_REST_MAX_RECORDS = 1000
GENERIC_REST_MAX_FIELDS = 32
GENERIC_REST_MAX_POINTER_SEGMENTS = 12
GENERIC_REST_MAX_POINTER_LENGTH = 1000
GENERIC_REST_MAX_SELECTED_VALUE_BYTES = 8192
GENERIC_REST_MAX_OVERLAP_SECONDS = 86_400

_EVENT_TYPE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_FIELD_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_INVALID_POINTER_ESCAPE = re.compile(r"~(?:[^01]|$)")
_MISSING = object()

_ALLOWED_SETTINGS = frozenset(
    {
        "endpoint_url",
        "records_path",
        "source_record_id_path",
        "observed_at_path",
        "evidence_fields",
        "event_type",
        "checkpoint_cursor_path",
        "has_more_path",
        "cursor_query_parameter",
        "time_window_query_parameter",
        "window_overlap_seconds",
        "request_timeout_seconds",
        "max_response_bytes",
        "headers",
        "query",
    }
)


class GenericRestExtractionError(ValueError):
    """Raised when a source response cannot enter the declarative profile."""


@dataclass(frozen=True, slots=True)
class JsonObjectPointer:
    """Small RFC 6901-style selector restricted to object traversal."""

    segments: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> JsonObjectPointer:
        if not 1 <= len(value) <= GENERIC_REST_MAX_POINTER_LENGTH:
            raise ValueError("Generic REST JSON pointer length is invalid")
        if not value.startswith("/"):
            raise ValueError("Generic REST JSON pointers must start with '/'")
        raw_segments = value[1:].split("/")
        if not 1 <= len(raw_segments) <= GENERIC_REST_MAX_POINTER_SEGMENTS:
            raise ValueError("Generic REST JSON pointer depth exceeds the qualified bound")
        segments: list[str] = []
        for raw in raw_segments:
            if not raw or len(raw) > 128 or _INVALID_POINTER_ESCAPE.search(raw):
                raise ValueError("Generic REST JSON pointer segment is invalid")
            segments.append(raw.replace("~1", "/").replace("~0", "~"))
        return cls(tuple(segments))

    def resolve(self, document: object) -> object:
        current = document
        for segment in self.segments:
            if not isinstance(current, dict) or segment not in current:
                return _MISSING
            current = current[segment]
        return current


@dataclass(frozen=True, slots=True)
class GenericRestExtractionProfile:
    """Validated transport/extraction settings for one Generic REST instance."""

    endpoint_url: str
    records_path: JsonObjectPointer
    source_record_id_path: JsonObjectPointer
    observed_at_path: JsonObjectPointer | None
    evidence_fields: tuple[tuple[str, JsonObjectPointer], ...]
    event_type: str
    checkpoint_cursor_path: JsonObjectPointer | None
    has_more_path: JsonObjectPointer | None
    cursor_query_parameter: str | None
    time_window_query_parameter: str | None
    window_overlap_seconds: int
    request_timeout_seconds: float
    max_response_bytes: int
    headers: tuple[tuple[str, str], ...]
    query: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class GenericRestExtractedPage:
    """Minimized intermediate records plus proposed source progress."""

    records: tuple[dict[str, JsonValue], ...]
    checkpoint: ConnectorCheckpointV1 | None
    has_more: bool


class GenericRestCredentialResolver(Protocol):
    """Minimal G2B boundary used by Generic REST bearer profiles."""

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class GenericRestSourceClient(Protocol):
    """Injected bounded source client used by deterministic fixtures."""

    def get(self) -> GenericRestResponse: ...

    def close(self) -> None: ...


GenericRestClientFactory = Callable[
    [GenericRestRequestProfile, GenericRestHostPolicy, bytes | None],
    GenericRestSourceClient,
]


class GenericRestAdapter:
    """G2H adapter joining qualified transport to declarative extraction only."""

    def __init__(
        self,
        definition: ConnectorDefinitionV1,
        host_policy: GenericRestHostPolicy,
        *,
        credential_resolver: GenericRestCredentialResolver | None = None,
        client_factory: GenericRestClientFactory | None = None,
    ) -> None:
        if definition.connector_id != "generic.rest":
            raise ValueError("Generic REST adapter requires generic.rest definition")
        if definition.implementation_class != "generic":
            raise ValueError("Generic REST adapter requires generic implementation class")
        self._definition = definition
        self._host_policy = host_policy
        self._credential_resolver = credential_resolver
        self._client_factory = client_factory or _default_client_factory

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        profile = _profile(instance)
        self._host_policy.authorize(profile.endpoint_url)
        if instance.collection.mode != "poll":
            raise ConnectorConfigurationError("Generic REST requires poll collection")
        if instance.collection.batch_size > GENERIC_REST_MAX_RECORDS:
            raise ConnectorConfigurationError(
                "Generic REST batch_size must not exceed 1000"
            )
        if instance.checkpoint.strategy not in {"none", "source_cursor", "time_window"}:
            raise ConnectorConfigurationError(
                "Generic REST supports none, source_cursor, or time_window checkpoints"
            )
        if instance.authentication.method not in {"none", "bearer"}:
            raise ConnectorConfigurationError(
                "Generic REST reference profile supports none or bearer authentication"
            )
        if instance.authentication.method == "none":
            if instance.authentication.credential_ref is not None:
                raise ConnectorConfigurationError(
                    "Generic REST none authentication must not carry a credential reference"
                )
        else:
            if instance.authentication.credential_ref is None:
                raise ConnectorConfigurationError(
                    "Generic REST bearer authentication requires a credential reference"
                )
            if self._credential_resolver is None:
                raise ConnectorConfigurationError(
                    "Generic REST bearer authentication requires a credential resolver"
                )
        _validate_checkpoint_profile(instance, profile)
        _build_request_profile(instance, profile, None)
        _validate_dynamic_query_parameter(instance, profile)

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        try:
            page = self._collect_page(instance, None)
        except CredentialResolutionError as exc:
            return _credential_health(exc)
        except CredentialProviderNotFoundError:
            return _health(
                "failed",
                "invalid_config",
                "Generic REST credential provider is unavailable",
            )
        except GenericRestAuthenticationError:
            return _health(
                "failed",
                "authentication_failed",
                "Generic REST credential was rejected",
            )
        except GenericRestAuthorizationError:
            return _health(
                "failed",
                "authorization_failed",
                "Generic REST source access was denied",
            )
        except GenericRestThrottleError as exc:
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="degraded",
                code="throttled",
                message="Generic REST source is rate limited",
                retry_after_seconds=exc.retry_after_seconds,
            )
        except GenericRestRetryableError:
            return _health(
                "degraded",
                "retryable_error",
                "Generic REST source is temporarily unavailable",
            )
        except (GenericRestTerminalError, GenericRestExtractionError):
            return _health(
                "failed",
                "terminal_error",
                "Generic REST source response does not satisfy the configured profile",
            )
        except GenericRestClientError:
            return _health("failed", "terminal_error", "Generic REST source request failed")
        return _health(
            "healthy",
            "ok",
            f"Generic REST source is reachable; sample_count={len(page.records)}",
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return ()

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        try:
            page = self._collect_page(instance, checkpoint)
        except CredentialResolutionError as exc:
            return _collection(
                _credential_operation_code(exc),
                "Generic REST credential is unavailable",
            )
        except CredentialProviderNotFoundError:
            return _collection(
                "invalid_config",
                "Generic REST credential provider is unavailable",
            )
        except GenericRestAuthenticationError:
            return _collection(
                "authentication_failed",
                "Generic REST credential was rejected",
            )
        except GenericRestAuthorizationError:
            return _collection(
                "authorization_failed",
                "Generic REST source access was denied",
            )
        except GenericRestThrottleError:
            return _collection("throttled", "Generic REST source is rate limited")
        except GenericRestRetryableError:
            return _collection(
                "retryable_error",
                "Generic REST source is temporarily unavailable",
            )
        except (GenericRestTerminalError, GenericRestExtractionError):
            return _collection(
                "terminal_error",
                "Generic REST response does not satisfy the configured extraction profile",
            )
        except GenericRestClientError:
            return _collection("terminal_error", "Generic REST source request failed")
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=page.records,
            checkpoint=page.checkpoint,
            has_more=page.has_more,
            message="Generic REST page collected and minimized",
        )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        return result.checkpoint

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        self.validate_config(instance)
        strategy = instance.checkpoint.strategy
        if strategy == "none":
            message = "Generic REST source exposes no configured continuity checkpoint"
        elif strategy == "time_window":
            message = (
                "Generic REST time-window overlap is best-effort and does not prove "
                "source completeness"
            )
        else:
            message = (
                "Generic REST preserves the configured opaque source cursor but cannot "
                "independently prove source cursor completeness"
            )
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="unknown_observation",
            reconciled=False,
            gap_detected=False,
            checkpoint=checkpoint,
            message=message,
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        self.validate_config(instance)
        source_record_id = _intermediate_string(record, "source_record_id")
        observed = _intermediate_observed_at(record)
        evidence = record.get("evidence")
        if not isinstance(evidence, dict):
            raise GenericRestExtractionError(
                "Generic REST intermediate record evidence must be an object"
            )
        selected = cast(dict[str, JsonValue], evidence)
        profile = _profile(instance)
        metadata: dict[str, JsonValue] = {
            "provider": "generic_rest",
            "source_class": "http_json",
            "source_name": instance.source.name,
            "record": selected,
        }
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id=source_record_id,
            source_system=GENERIC_REST_SOURCE_SYSTEM,
            observed_at_utc=observed,
            event_type=profile.event_type,
            media_type="application/json",
            transformation_profile=GENERIC_REST_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata=metadata,
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)

    def _collect_page(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> GenericRestExtractedPage:
        profile = _profile(instance)
        request_profile = _build_request_profile(instance, profile, checkpoint)
        response = self._fetch_response(instance, request_profile)
        return extract_generic_rest_page(
            response,
            profile,
            checkpoint_strategy=instance.checkpoint.strategy,
            previous_checkpoint=checkpoint,
            maximum_records=instance.collection.batch_size,
        )

    def _fetch_response(
        self,
        instance: ConnectorInstanceV1,
        request_profile: GenericRestRequestProfile,
    ) -> GenericRestResponse:
        if instance.authentication.method == "none":
            client = self._client_factory(request_profile, self._host_policy, None)
            try:
                return client.get()
            finally:
                client.close()

        resolver = self._credential_resolver
        credential_ref = instance.authentication.credential_ref
        if resolver is None or credential_ref is None:
            raise ConnectorConfigurationError(
                "Generic REST bearer credential boundary is not configured"
            )
        reference = CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=credential_ref,
        )
        with resolver.resolve(reference) as lease:
            client = self._client_factory(
                request_profile,
                self._host_policy,
                lease.reveal(),
            )
            try:
                return client.get()
            finally:
                client.close()


def extract_generic_rest_page(
    response: GenericRestResponse,
    profile: GenericRestExtractionProfile,
    *,
    checkpoint_strategy: str,
    previous_checkpoint: ConnectorCheckpointV1 | None,
    maximum_records: int,
) -> GenericRestExtractedPage:
    """Decode one bounded JSON response into minimized intermediate records."""

    if not 1 <= maximum_records <= GENERIC_REST_MAX_RECORDS:
        raise ValueError("maximum_records exceeds the Generic REST qualified bound")
    _validate_json_content_type(response.content_type)
    root = _decode_json_object(response.body)
    selected_records = profile.records_path.resolve(root)
    if not isinstance(selected_records, list):
        raise GenericRestExtractionError(
            "Generic REST records_path must resolve to a JSON array"
        )
    if len(selected_records) > maximum_records:
        raise GenericRestExtractionError(
            "Generic REST response record count exceeds configured batch_size"
        )

    records: list[dict[str, JsonValue]] = []
    observed_through: datetime | None = None
    for raw in selected_records:
        if not isinstance(raw, dict):
            raise GenericRestExtractionError(
                "Generic REST configured record array contains a non-object value"
            )
        source_record_id = _extract_source_record_id(raw, profile.source_record_id_path)
        observed = _extract_observed_at(raw, profile.observed_at_path)
        evidence = _extract_evidence(raw, profile.evidence_fields)
        intermediate: dict[str, JsonValue] = {
            "source_record_id": source_record_id,
            "evidence": evidence,
        }
        if observed is not None:
            intermediate["observed_at_utc"] = _format_utc(observed)
            if observed_through is None or observed > observed_through:
                observed_through = observed
        records.append(intermediate)

    has_more = _extract_has_more(root, profile.has_more_path)
    checkpoint = _proposed_checkpoint(
        root,
        profile,
        checkpoint_strategy=checkpoint_strategy,
        previous_checkpoint=previous_checkpoint,
        observed_through=observed_through,
    )
    if has_more and checkpoint_strategy != "source_cursor":
        raise GenericRestExtractionError(
            "Generic REST has_more requires source_cursor checkpoint strategy"
        )
    return GenericRestExtractedPage(
        records=tuple(records),
        checkpoint=checkpoint,
        has_more=has_more,
    )


def _profile(instance: ConnectorInstanceV1) -> GenericRestExtractionProfile:
    unexpected = sorted(set(instance.settings) - _ALLOWED_SETTINGS)
    if unexpected:
        raise ConnectorConfigurationError(
            "unsupported Generic REST settings: " + ", ".join(unexpected)
        )
    endpoint_url = _required_string_setting(instance, "endpoint_url", 2000)
    records_path = _required_pointer_setting(instance, "records_path")
    source_record_id_path = _required_pointer_setting(
        instance,
        "source_record_id_path",
    )
    observed_at_path = _optional_pointer_setting(instance, "observed_at_path")
    evidence_fields = _evidence_field_settings(instance)
    event_type = instance.settings.get("event_type", GENERIC_REST_DEFAULT_EVENT_TYPE)
    if not isinstance(event_type, str) or _EVENT_TYPE_PATTERN.fullmatch(event_type) is None:
        raise ConnectorConfigurationError("Generic REST event_type setting is invalid")

    timeout = instance.settings.get("request_timeout_seconds", 30.0)
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not 0.1 <= float(timeout) <= 60.0
    ):
        raise ConnectorConfigurationError(
            "Generic REST request_timeout_seconds must be between 0.1 and 60"
        )
    max_response_bytes = instance.settings.get("max_response_bytes", 1024 * 1024)
    if (
        not isinstance(max_response_bytes, int)
        or isinstance(max_response_bytes, bool)
        or not 1 <= max_response_bytes <= 16 * 1024 * 1024
    ):
        raise ConnectorConfigurationError(
            "Generic REST max_response_bytes exceeds the qualified bound"
        )
    overlap = instance.settings.get("window_overlap_seconds", 300)
    if (
        not isinstance(overlap, int)
        or isinstance(overlap, bool)
        or not 1 <= overlap <= GENERIC_REST_MAX_OVERLAP_SECONDS
    ):
        raise ConnectorConfigurationError(
            "Generic REST window_overlap_seconds must be between 1 and 86400"
        )

    return GenericRestExtractionProfile(
        endpoint_url=endpoint_url,
        records_path=records_path,
        source_record_id_path=source_record_id_path,
        observed_at_path=observed_at_path,
        evidence_fields=evidence_fields,
        event_type=event_type,
        checkpoint_cursor_path=_optional_pointer_setting(
            instance,
            "checkpoint_cursor_path",
        ),
        has_more_path=_optional_pointer_setting(instance, "has_more_path"),
        cursor_query_parameter=_optional_string_setting(
            instance,
            "cursor_query_parameter",
            128,
        ),
        time_window_query_parameter=_optional_string_setting(
            instance,
            "time_window_query_parameter",
            128,
        ),
        window_overlap_seconds=overlap,
        request_timeout_seconds=float(timeout),
        max_response_bytes=max_response_bytes,
        headers=_string_mapping_setting(instance, "headers", 64),
        query=_string_mapping_setting(instance, "query", 64),
    )


def _validate_checkpoint_profile(
    instance: ConnectorInstanceV1,
    profile: GenericRestExtractionProfile,
) -> None:
    strategy = instance.checkpoint.strategy
    if strategy == "source_cursor":
        if profile.checkpoint_cursor_path is None or profile.cursor_query_parameter is None:
            raise ConnectorConfigurationError(
                "Generic REST source_cursor requires checkpoint_cursor_path and "
                "cursor_query_parameter"
            )
        if profile.time_window_query_parameter is not None:
            raise ConnectorConfigurationError(
                "Generic REST source_cursor must not configure a time-window parameter"
            )
    elif strategy == "time_window":
        if profile.observed_at_path is None or profile.time_window_query_parameter is None:
            raise ConnectorConfigurationError(
                "Generic REST time_window requires observed_at_path and "
                "time_window_query_parameter"
            )
        if profile.checkpoint_cursor_path is not None or profile.cursor_query_parameter is not None:
            raise ConnectorConfigurationError(
                "Generic REST time_window must not configure source-cursor fields"
            )
        if profile.has_more_path is not None:
            raise ConnectorConfigurationError(
                "Generic REST time_window reference profile does not support has_more"
            )
    else:
        if any(
            value is not None
            for value in (
                profile.checkpoint_cursor_path,
                profile.has_more_path,
                profile.cursor_query_parameter,
                profile.time_window_query_parameter,
            )
        ):
            raise ConnectorConfigurationError(
                "Generic REST checkpoint fields require source_cursor or time_window strategy"
            )


def _validate_dynamic_query_parameter(
    instance: ConnectorInstanceV1,
    profile: GenericRestExtractionProfile,
) -> None:
    parameter: str | None
    if instance.checkpoint.strategy == "source_cursor":
        parameter = profile.cursor_query_parameter
    elif instance.checkpoint.strategy == "time_window":
        parameter = profile.time_window_query_parameter
    else:
        return
    assert parameter is not None
    base_query = dict(profile.query)
    if parameter in base_query:
        raise ConnectorConfigurationError(
            "Generic REST checkpoint query parameter must not collide with static query"
        )
    base_query[parameter] = "validation-probe"
    GenericRestRequestProfile(
        endpoint_url=profile.endpoint_url,
        timeout_seconds=profile.request_timeout_seconds,
        max_response_bytes=profile.max_response_bytes,
        headers=dict(profile.headers),
        query=base_query,
    )


def _build_request_profile(
    instance: ConnectorInstanceV1,
    profile: GenericRestExtractionProfile,
    checkpoint: ConnectorCheckpointV1 | None,
) -> GenericRestRequestProfile:
    query = dict(profile.query)
    if checkpoint is not None and instance.checkpoint.strategy == "source_cursor":
        if checkpoint.cursor is None:
            raise ConnectorConfigurationError(
                "Generic REST source_cursor checkpoint is missing its cursor"
            )
        assert profile.cursor_query_parameter is not None
        query[profile.cursor_query_parameter] = checkpoint.cursor
    elif checkpoint is not None and instance.checkpoint.strategy == "time_window":
        if checkpoint.observed_through_utc is not None:
            assert profile.time_window_query_parameter is not None
            start = checkpoint.observed_through_utc - timedelta(
                seconds=profile.window_overlap_seconds
            )
            query[profile.time_window_query_parameter] = _format_utc(start)
    return GenericRestRequestProfile(
        endpoint_url=profile.endpoint_url,
        timeout_seconds=profile.request_timeout_seconds,
        max_response_bytes=profile.max_response_bytes,
        headers=dict(profile.headers),
        query=query,
    )


def _decode_json_object(body: bytes) -> dict[str, JsonValue]:
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GenericRestExtractionError(
            "Generic REST response is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise GenericRestExtractionError("Generic REST response root must be a JSON object")
    return cast(dict[str, JsonValue], decoded)


def _validate_json_content_type(content_type: str | None) -> None:
    if content_type is None:
        return
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise GenericRestExtractionError(
            "Generic REST declarative profile requires a JSON response content type"
        )


def _extract_source_record_id(
    record: Mapping[str, object],
    pointer: JsonObjectPointer,
) -> str:
    value = pointer.resolve(record)
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise GenericRestExtractionError(
            "Generic REST source_record_id_path must resolve to a string or integer"
        )
    result = str(value)
    if not 1 <= len(result) <= 500:
        raise GenericRestExtractionError(
            "Generic REST source record identity exceeds the qualified bound"
        )
    return result


def _extract_observed_at(
    record: Mapping[str, object],
    pointer: JsonObjectPointer | None,
) -> datetime | None:
    if pointer is None:
        return None
    value = pointer.resolve(record)
    if value is _MISSING or value is None:
        return None
    if not isinstance(value, str):
        raise GenericRestExtractionError(
            "Generic REST observed_at_path must resolve to an RFC3339 string"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise GenericRestExtractionError(
            "Generic REST source observation timestamp is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GenericRestExtractionError(
            "Generic REST source observation timestamp must include a timezone"
        )
    return parsed.astimezone(UTC)


def _extract_evidence(
    record: Mapping[str, object],
    fields: tuple[tuple[str, JsonObjectPointer], ...],
) -> dict[str, JsonValue]:
    evidence: dict[str, JsonValue] = {}
    for output_name, pointer in fields:
        value = pointer.resolve(record)
        if value is _MISSING:
            continue
        selected = cast(JsonValue, value)
        if _json_size(selected) > GENERIC_REST_MAX_SELECTED_VALUE_BYTES:
            raise GenericRestExtractionError(
                f"Generic REST selected field {output_name!r} exceeds the qualified bound"
            )
        evidence[output_name] = selected
    if _json_size(evidence) > 32 * 1024:
        raise GenericRestExtractionError(
            "Generic REST selected evidence mapping exceeds 32 KiB"
        )
    return evidence


def _extract_has_more(
    root: Mapping[str, object],
    pointer: JsonObjectPointer | None,
) -> bool:
    if pointer is None:
        return False
    value = pointer.resolve(root)
    if not isinstance(value, bool):
        raise GenericRestExtractionError(
            "Generic REST has_more_path must resolve to a boolean"
        )
    return value


def _proposed_checkpoint(
    root: Mapping[str, object],
    profile: GenericRestExtractionProfile,
    *,
    checkpoint_strategy: str,
    previous_checkpoint: ConnectorCheckpointV1 | None,
    observed_through: datetime | None,
) -> ConnectorCheckpointV1 | None:
    prior_observed = (
        previous_checkpoint.observed_through_utc
        if previous_checkpoint is not None
        else None
    )
    latest_observed = _later_timestamp(prior_observed, observed_through)
    if checkpoint_strategy == "none":
        return None
    if checkpoint_strategy == "time_window":
        return ConnectorCheckpointV1(
            schema_version="ets.connector.checkpoint.v1",
            observed_through_utc=latest_observed,
        )
    if checkpoint_strategy != "source_cursor" or profile.checkpoint_cursor_path is None:
        raise GenericRestExtractionError(
            "Generic REST checkpoint strategy is not qualified by this profile"
        )
    raw_cursor = profile.checkpoint_cursor_path.resolve(root)
    if isinstance(raw_cursor, bool) or not isinstance(raw_cursor, (str, int)):
        raise GenericRestExtractionError(
            "Generic REST checkpoint_cursor_path must resolve to a string or integer"
        )
    cursor = str(raw_cursor)
    if not 1 <= len(cursor) <= 4000:
        raise GenericRestExtractionError(
            "Generic REST source cursor exceeds the qualified bound"
        )
    return ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=cursor,
        observed_through_utc=latest_observed,
    )


def _evidence_field_settings(
    instance: ConnectorInstanceV1,
) -> tuple[tuple[str, JsonObjectPointer], ...]:
    raw = instance.settings.get("evidence_fields")
    if not isinstance(raw, dict) or not 1 <= len(raw) <= GENERIC_REST_MAX_FIELDS:
        raise ConnectorConfigurationError(
            "Generic REST evidence_fields must contain between 1 and 32 mappings"
        )
    fields: list[tuple[str, JsonObjectPointer]] = []
    for output_name, raw_pointer in sorted(raw.items()):
        if (
            not isinstance(output_name, str)
            or _FIELD_NAME_PATTERN.fullmatch(output_name) is None
            or output_name.startswith("_ets_")
        ):
            raise ConnectorConfigurationError(
                "Generic REST evidence field output name is invalid"
            )
        if not isinstance(raw_pointer, str):
            raise ConnectorConfigurationError(
                "Generic REST evidence field selector must be a JSON pointer string"
            )
        try:
            pointer = JsonObjectPointer.parse(raw_pointer)
        except ValueError as exc:
            raise ConnectorConfigurationError(
                "Generic REST evidence field selector is invalid"
            ) from exc
        fields.append((output_name, pointer))
    return tuple(fields)


def _required_pointer_setting(
    instance: ConnectorInstanceV1,
    key: str,
) -> JsonObjectPointer:
    raw = instance.settings.get(key)
    if not isinstance(raw, str):
        raise ConnectorConfigurationError(f"Generic REST {key} setting is required")
    try:
        return JsonObjectPointer.parse(raw)
    except ValueError as exc:
        raise ConnectorConfigurationError(f"Generic REST {key} setting is invalid") from exc


def _optional_pointer_setting(
    instance: ConnectorInstanceV1,
    key: str,
) -> JsonObjectPointer | None:
    raw = instance.settings.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ConnectorConfigurationError(f"Generic REST {key} setting is invalid")
    try:
        return JsonObjectPointer.parse(raw)
    except ValueError as exc:
        raise ConnectorConfigurationError(f"Generic REST {key} setting is invalid") from exc


def _required_string_setting(
    instance: ConnectorInstanceV1,
    key: str,
    maximum: int,
) -> str:
    raw = instance.settings.get(key)
    if not isinstance(raw, str) or not 1 <= len(raw) <= maximum:
        raise ConnectorConfigurationError(f"Generic REST {key} setting is invalid")
    return raw


def _optional_string_setting(
    instance: ConnectorInstanceV1,
    key: str,
    maximum: int,
) -> str | None:
    raw = instance.settings.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str) or not 1 <= len(raw) <= maximum:
        raise ConnectorConfigurationError(f"Generic REST {key} setting is invalid")
    return raw


def _string_mapping_setting(
    instance: ConnectorInstanceV1,
    key: str,
    maximum: int,
) -> tuple[tuple[str, str], ...]:
    raw = instance.settings.get(key, {})
    if not isinstance(raw, dict) or len(raw) > maximum:
        raise ConnectorConfigurationError(f"Generic REST {key} setting is invalid")
    result: list[tuple[str, str]] = []
    for name, value in sorted(raw.items()):
        if not isinstance(name, str) or not isinstance(value, str):
            raise ConnectorConfigurationError(f"Generic REST {key} setting is invalid")
        result.append((name, value))
    return tuple(result)


def _intermediate_string(record: Mapping[str, JsonValue], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise GenericRestExtractionError(
            f"Generic REST intermediate record {key} is invalid"
        )
    return value


def _intermediate_observed_at(record: Mapping[str, JsonValue]) -> datetime | None:
    value = record.get("observed_at_utc")
    if value is None:
        return None
    if not isinstance(value, str):
        raise GenericRestExtractionError(
            "Generic REST intermediate observed_at_utc is invalid"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GenericRestExtractionError(
            "Generic REST intermediate observed_at_utc must include timezone"
        )
    return parsed.astimezone(UTC)


def _json_size(value: JsonValue) -> int:
    try:
        return len(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        raise GenericRestExtractionError(
            "Generic REST selected evidence value is not JSON-native"
        ) from exc


def _later_timestamp(first: datetime | None, second: datetime | None) -> datetime | None:
    if first is None:
        return second
    if second is None:
        return first
    return max(first, second)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Generic REST checkpoint timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _default_client_factory(
    profile: GenericRestRequestProfile,
    host_policy: GenericRestHostPolicy,
    credential_material: bytes | None,
) -> GenericRestSourceClient:
    return GenericRestHttpClient(
        profile,
        host_policy,
        credential_material=credential_material,
    )


def _credential_operation_code(exc: CredentialResolutionError) -> ConnectorOperationCode:
    if exc.status in {"missing", "expired", "revoked"}:
        return "authentication_failed"
    if exc.status == "unavailable":
        return "retryable_error"
    return "invalid_config"


def _credential_health(exc: CredentialResolutionError) -> ConnectorHealthV1:
    code = _credential_operation_code(exc)
    state: ConnectorHealthState = "degraded" if code == "retryable_error" else "failed"
    return _health(state, code, "Generic REST connector credential is unavailable")


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
