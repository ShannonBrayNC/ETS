"""Standard G2 connector adapter for Microsoft Purview Management Activity."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from pydantic import JsonValue

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialProviderNotFoundError,
    CredentialResolutionError,
)
from ets.connectors.enterprise.microsoft_purview_activity import (
    PURVIEW_CONTENT_TYPES,
    MicrosoftPurviewManagementProfile,
    PurviewContentType,
)
from ets.connectors.enterprise.microsoft_purview_audit import MicrosoftPurviewAuditRecordV1
from ets.connectors.enterprise.microsoft_purview_http import (
    MicrosoftPurviewActivityHttpClient,
    MicrosoftPurviewAuthenticationError,
    MicrosoftPurviewAuthorizationError,
    MicrosoftPurviewClientError,
    MicrosoftPurviewRetryableError,
    MicrosoftPurviewThrottleError,
)
from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorCollectionResultV1,
    ConnectorDefinitionV1,
    ConnectorEvidenceCandidateV1,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorReconciliationResultV1,
)
from ets.connectors.sdk import ConnectorConfigurationError

PURVIEW_SOURCE_SYSTEM = "microsoft.purview.activity"
PURVIEW_EVENT_TYPE = "microsoft.purview.audit.observed"
PURVIEW_TRANSFORMATION_PROFILE = "ets.connector.microsoft-purview.common-schema.v1"
PURVIEW_MAX_SERVICE_FIELDS = 32

_ALLOWED_SETTINGS = frozenset(
    {
        "management_profile_id",
        "content_type",
        "service_specific_allowlist",
        "include_client_ip",
        "request_timeout_seconds",
        "maximum_discovery_bytes",
        "maximum_content_bytes",
        "poll_window_seconds",
        "overlap_seconds",
    }
)


@dataclass(frozen=True, slots=True)
class MicrosoftPurviewConnectorSettings:
    management_profile_id: str
    content_type: PurviewContentType
    service_specific_allowlist: frozenset[str]
    include_client_ip: bool
    request_timeout_seconds: float
    maximum_discovery_bytes: int
    maximum_content_bytes: int
    poll_window_seconds: int
    overlap_seconds: int


class MicrosoftPurviewManagementProfileResolver(Protocol):
    def resolve(self, profile_id: str) -> MicrosoftPurviewManagementProfile: ...


class MicrosoftPurviewCredentialResolver(Protocol):
    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class MicrosoftPurviewSourceClient(Protocol):
    def list_content(
        self,
        content_type: PurviewContentType,
        *,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        next_page_uri: str | None = None,
    ): ...

    def retrieve_content(
        self,
        descriptor,
        *,
        service_specific_allowlist: frozenset[str] = frozenset(),
        include_client_ip: bool = False,
    ): ...

    def close(self) -> None: ...


MicrosoftPurviewClientFactory = Callable[
    [MicrosoftPurviewManagementProfile, bytes, MicrosoftPurviewConnectorSettings],
    MicrosoftPurviewSourceClient,
]


class MicrosoftPurviewActivityAdapter:
    """Collect qualified Purview audit content without releasing source progress."""

    def __init__(
        self,
        definition: ConnectorDefinitionV1,
        profile_resolver: MicrosoftPurviewManagementProfileResolver,
        credential_resolver: MicrosoftPurviewCredentialResolver,
        *,
        client_factory: MicrosoftPurviewClientFactory | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if definition.connector_id != "microsoft.purview.activity":
            raise ValueError("Purview adapter requires microsoft.purview.activity definition")
        if definition.implementation_class != "enterprise_api":
            raise ValueError("Purview adapter requires enterprise_api implementation class")
        self._definition = definition
        self._profile_resolver = profile_resolver
        self._credential_resolver = credential_resolver
        self._client_factory = client_factory or _default_client_factory
        self._now = now or _utc_now

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        settings = _settings(instance)
        self._profile_resolver.resolve(settings.management_profile_id)
        if instance.collection.mode != "poll":
            raise ConnectorConfigurationError(
                "Purview Management Activity requires poll collection"
            )
        if instance.checkpoint.strategy != "source_cursor":
            raise ConnectorConfigurationError(
                "Purview Management Activity requires source_cursor checkpointing"
            )
        if instance.authentication.method != "bearer":
            raise ConnectorConfigurationError("Purview Management Activity requires bearer auth")
        if instance.authentication.credential_ref is None:
            raise ConnectorConfigurationError(
                "Purview Management Activity requires an opaque credential reference"
            )

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        result = self.collect(instance, None)
        if result.code == "ok":
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="healthy",
                code="ok",
                message="Purview Management Activity source is reachable",
            )
        state = "degraded" if result.code in {"retryable_error", "throttled"} else "failed"
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state=state,
            code=result.code,
            message=result.message or "Purview Management Activity connection test failed",
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return (_settings(instance).content_type,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        settings = _settings(instance)
        profile = self._profile_resolver.resolve(settings.management_profile_id)
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError("Purview credential reference is required")
        reference = CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=credential_ref,
        )

        try:
            with self._credential_resolver.resolve(reference) as lease:
                client = self._client_factory(profile, lease.reveal(), settings)
                try:
                    return self._collect_with_client(client, settings, checkpoint)
                finally:
                    client.close()
        except CredentialProviderNotFoundError:
            return _collection("invalid_config", "Purview credential provider is unavailable")
        except CredentialResolutionError:
            return _collection("authentication_failed", "Purview credential is unavailable")
        except MicrosoftPurviewAuthenticationError:
            return _collection("authentication_failed", "Purview access token was rejected")
        except MicrosoftPurviewAuthorizationError:
            return _collection("authorization_failed", "Purview source access was denied")
        except MicrosoftPurviewThrottleError:
            return _collection("throttled", "Purview Management Activity source is rate limited")
        except MicrosoftPurviewRetryableError:
            return _collection(
                "retryable_error",
                "Purview Management Activity source is unavailable",
            )
        except (MicrosoftPurviewClientError, ValueError):
            return _collection(
                "terminal_error",
                "Purview source response violated the qualified profile",
            )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        return result.checkpoint

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        self.validate_config(instance)
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="unknown_observation",
            reconciled=False,
            gap_detected=False,
            checkpoint=checkpoint,
            message=(
                "Purview polling uses bounded overlap and source pagination but does not prove "
                "complete Microsoft audit history"
            ),
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        self.validate_config(instance)
        source_record_id = _required_string(record, "source_record_id", 500)
        observed = _required_timestamp(record, "observed_at_utc")
        evidence = record.get("evidence")
        if not isinstance(evidence, dict):
            raise ValueError("Purview intermediate evidence must be an object")
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id=source_record_id,
            source_system=PURVIEW_SOURCE_SYSTEM,
            observed_at_utc=observed,
            event_type=PURVIEW_EVENT_TYPE,
            media_type="application/json",
            transformation_profile=PURVIEW_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata={
                "provider": "microsoft_purview",
                "source_class": "management_activity",
                "record": cast(dict[str, JsonValue], evidence),
            },
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)

    def _collect_with_client(
        self,
        client: MicrosoftPurviewSourceClient,
        settings: MicrosoftPurviewConnectorSettings,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        now = _aware_utc(self._now())
        if checkpoint is not None and checkpoint.cursor is not None:
            page = client.list_content(
                settings.content_type,
                next_page_uri=checkpoint.cursor,
            )
            window_end = checkpoint.observed_through_utc or now
        else:
            prior = None if checkpoint is None else checkpoint.observed_through_utc
            if prior is None:
                start = now - timedelta(seconds=settings.poll_window_seconds)
            else:
                start = prior - timedelta(seconds=settings.overlap_seconds)
            window_end = now
            page = client.list_content(
                settings.content_type,
                start_time_utc=start,
                end_time_utc=window_end,
            )

        records: list[dict[str, JsonValue]] = []
        for descriptor in page.descriptors:
            content = client.retrieve_content(
                descriptor,
                service_specific_allowlist=settings.service_specific_allowlist,
                include_client_ip=settings.include_client_ip,
            )
            for audit_record in content.records:
                records.append(_intermediate_record(audit_record))

        proposed = ConnectorCheckpointV1(
            schema_version="ets.connector.checkpoint.v1",
            cursor=page.next_page_uri,
            observed_through_utc=window_end,
        )
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=tuple(records),
            checkpoint=proposed,
            has_more=page.next_page_uri is not None,
            message="Purview audit content retrieved and minimized",
        )


def _settings(instance: ConnectorInstanceV1) -> MicrosoftPurviewConnectorSettings:
    if instance.connector_id != "microsoft.purview.activity":
        raise ConnectorConfigurationError("connector instance is not Microsoft Purview")
    unknown = set(instance.settings) - _ALLOWED_SETTINGS
    if unknown:
        raise ConnectorConfigurationError("Purview connector settings contain unsupported keys")
    profile_id = _required_setting_string(instance.settings, "management_profile_id", 128)
    raw_content_type = _required_setting_string(instance.settings, "content_type", 100)
    if raw_content_type not in PURVIEW_CONTENT_TYPES:
        raise ConnectorConfigurationError("Purview content_type is not qualified")
    content_type = cast(PurviewContentType, raw_content_type)

    raw_allowlist = instance.settings.get("service_specific_allowlist", [])
    if not isinstance(raw_allowlist, list) or len(raw_allowlist) > PURVIEW_MAX_SERVICE_FIELDS:
        raise ConnectorConfigurationError("Purview service-specific allowlist is invalid")
    allowlist: set[str] = set()
    for value in raw_allowlist:
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            raise ConnectorConfigurationError("Purview service-specific allowlist is invalid")
        allowlist.add(value)
    if len(allowlist) != len(raw_allowlist):
        raise ConnectorConfigurationError("Purview service-specific allowlist contains duplicates")

    include_client_ip = instance.settings.get("include_client_ip", False)
    if not isinstance(include_client_ip, bool):
        raise ConnectorConfigurationError("Purview include_client_ip must be boolean")
    timeout = _number(instance.settings.get("request_timeout_seconds", 30), 0.1, 60)
    discovery_bytes = _integer(
        instance.settings.get("maximum_discovery_bytes", 2 * 1024 * 1024),
        1,
        2 * 1024 * 1024,
    )
    content_bytes = _integer(
        instance.settings.get("maximum_content_bytes", 16 * 1024 * 1024),
        1,
        16 * 1024 * 1024,
    )
    poll_window = _integer(instance.settings.get("poll_window_seconds", 3600), 60, 86400)
    overlap = _integer(instance.settings.get("overlap_seconds", 300), 0, 3600)
    if overlap >= poll_window:
        raise ConnectorConfigurationError(
            "Purview overlap_seconds must be below poll_window_seconds"
        )
    return MicrosoftPurviewConnectorSettings(
        management_profile_id=profile_id,
        content_type=content_type,
        service_specific_allowlist=frozenset(allowlist),
        include_client_ip=include_client_ip,
        request_timeout_seconds=timeout,
        maximum_discovery_bytes=discovery_bytes,
        maximum_content_bytes=content_bytes,
        poll_window_seconds=poll_window,
        overlap_seconds=overlap,
    )


def _default_client_factory(
    profile: MicrosoftPurviewManagementProfile,
    credential_material: bytes,
    settings: MicrosoftPurviewConnectorSettings,
) -> MicrosoftPurviewSourceClient:
    return MicrosoftPurviewActivityHttpClient(
        profile,
        credential_material,
        timeout_seconds=settings.request_timeout_seconds,
        maximum_discovery_bytes=settings.maximum_discovery_bytes,
        maximum_content_bytes=settings.maximum_content_bytes,
    )


def _intermediate_record(record: MicrosoftPurviewAuditRecordV1) -> dict[str, JsonValue]:
    evidence: dict[str, JsonValue] = {
        "record_type": record.record_type,
        "operation": record.operation,
        "organization_id": record.organization_id,
        "user_type": record.user_type,
        "user_key": record.user_key,
        "workload": record.workload,
        "user_id": record.user_id,
        "result_status": record.result_status,
        "object_id": record.object_id,
        "client_ip": record.client_ip,
        "scope": record.scope,
        "version": record.version,
        "content_type": record.content_type,
        "content_id": record.content_id,
        "service_specific": record.service_specific,
    }
    return {
        "source_record_id": record.source_record_id,
        "observed_at_utc": record.creation_time_utc.isoformat().replace("+00:00", "Z"),
        "evidence": evidence,
    }


def _collection(code: str, message: str) -> ConnectorCollectionResultV1:
    return ConnectorCollectionResultV1(
        schema_version="ets.connector.collection_result.v1",
        code=cast(object, code),
        message=message,
    )


def _required_setting_string(
    settings: Mapping[str, JsonValue],
    key: str,
    maximum: int,
) -> str:
    value = settings.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ConnectorConfigurationError(f"Purview {key} is invalid")
    return value


def _required_string(value: Mapping[str, JsonValue], key: str, maximum: int) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not 1 <= len(candidate) <= maximum:
        raise ValueError(f"Purview intermediate {key} is invalid")
    return candidate


def _required_timestamp(value: Mapping[str, JsonValue], key: str) -> datetime:
    text = _required_string(value, key, 100)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Purview intermediate source timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _number(value: JsonValue, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConnectorConfigurationError("Purview numeric setting is invalid")
    numeric = float(value)
    if not minimum <= numeric <= maximum:
        raise ConnectorConfigurationError("Purview numeric setting is outside bounds")
    return numeric


def _integer(value: JsonValue, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ConnectorConfigurationError("Purview integer setting is outside bounds")
    return value


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Purview clock must be timezone-aware")
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)
