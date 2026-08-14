"""Microsoft SharePoint/OneDrive metadata delta ConnectorAdapter for G2E-D."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from pydantic import JsonValue

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialProviderNotFoundError,
    CredentialResolutionError,
)
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    SHAREPOINT_DELTA_DEFAULT_MAXIMUM_BODY_BYTES,
    SHAREPOINT_DELTA_DEFAULT_MAXIMUM_RECORDS,
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRecordV1,
    MicrosoftSharePointDeltaRequestProfile,
    SharePointDeltaScope,
    sharepoint_drive_delta_request_profile,
    sharepoint_list_delta_request_profile,
)
from ets.connectors.enterprise.microsoft_sharepoint_http import (
    MicrosoftSharePointDeltaAuthenticationError,
    MicrosoftSharePointDeltaAuthorizationError,
    MicrosoftSharePointDeltaClientError,
    MicrosoftSharePointDeltaHttpClient,
    MicrosoftSharePointDeltaRetryableError,
    MicrosoftSharePointDeltaStateExpiredError,
    MicrosoftSharePointDeltaTerminalError,
    MicrosoftSharePointDeltaThrottleError,
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

SHAREPOINT_CONNECTOR_ID = "microsoft.sharepoint.onedrive_delta"
SHAREPOINT_SOURCE_SYSTEM = "microsoft.sharepoint.onedrive_delta"
SHAREPOINT_TRANSFORMATION_PROFILE = "ets.connector.microsoft.sharepoint-onedrive-metadata.v1"
SHAREPOINT_OBSERVED_EVENT_TYPE = "microsoft.sharepoint.metadata.observed"
SHAREPOINT_DELETED_EVENT_TYPE = "microsoft.sharepoint.metadata.deleted"
SHAREPOINT_ALLOWED_SETTINGS = frozenset(
    {
        "tenant_profile_id",
        "scope",
        "drive_id",
        "site_id",
        "list_id",
        "request_timeout_seconds",
        "maximum_response_bytes",
    }
)


@dataclass(frozen=True, slots=True)
class MicrosoftSharePointDeltaSettings:
    tenant_profile_id: str
    tenant_profile: MicrosoftTenantProfileV1
    scope: SharePointDeltaScope
    drive_id: str | None
    site_id: str | None
    list_id: str | None
    request_timeout_seconds: float
    maximum_response_bytes: int


class CredentialResolver(Protocol):
    """Minimal G2B credential boundary required by the SharePoint adapter."""

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class SharePointDeltaSourceClient(Protocol):
    """Source client contract used by the adapter and deterministic fixtures."""

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1: ...

    def close(self) -> None: ...


SharePointDeltaClientFactory = Callable[
    [MicrosoftSharePointDeltaRequestProfile, bytes, float, int],
    SharePointDeltaSourceClient,
]


class MicrosoftSharePointDeltaAdapter:
    """Bounded G2E-D adapter for SharePoint/OneDrive metadata-only delta collection."""

    def __init__(
        self,
        definition: ConnectorDefinitionV1,
        credential_resolver: CredentialResolver,
        tenant_profiles: Mapping[str, MicrosoftTenantProfileV1],
        *,
        client_factory: SharePointDeltaClientFactory | None = None,
    ) -> None:
        if definition.connector_id != SHAREPOINT_CONNECTOR_ID:
            raise ValueError(f"SharePoint adapter requires {SHAREPOINT_CONNECTOR_ID}")
        if definition.implementation_class != "enterprise_api":
            raise ValueError("SharePoint adapter requires enterprise_api definition")
        self._definition = definition
        self._credential_resolver = credential_resolver
        self._tenant_profiles = dict(tenant_profiles)
        self._client_factory = client_factory or _default_client_factory

    @property
    def definition(self) -> ConnectorDefinitionV1:
        return self._definition

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        settings = self._settings(instance)
        if instance.collection.mode != "poll":
            raise ConnectorConfigurationError("SharePoint delta connector requires poll collection")
        if instance.collection.batch_size > SHAREPOINT_DELTA_DEFAULT_MAXIMUM_RECORDS:
            raise ConnectorConfigurationError(
                "SharePoint delta collection batch_size must not exceed 1000"
            )
        if instance.checkpoint.strategy != "source_cursor":
            raise ConnectorConfigurationError(
                "SharePoint delta connector requires source_cursor checkpoint strategy"
            )
        if instance.authentication.method != "bearer":
            raise ConnectorConfigurationError(
                "SharePoint delta connector requires bearer authentication"
            )
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError(
                "SharePoint delta connector requires an opaque credential reference"
            )
        if credential_ref != settings.tenant_profile.credential_ref.ref:
            raise ConnectorConfigurationError(
                "SharePoint delta credential reference does not match server-owned tenant profile"
            )
        if settings.tenant_profile.consent_state != "granted":
            raise ConnectorConfigurationError(
                "SharePoint delta tenant profile requires granted administrator consent"
            )

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        self.validate_config(instance)
        try:
            page = self._collect_page(instance, None)
        except CredentialResolutionError:
            return _health(
                "degraded",
                "retryable_error",
                "Microsoft credential is unavailable",
            )
        except CredentialProviderNotFoundError:
            return _health(
                "failed",
                "invalid_config",
                "Microsoft credential provider is unavailable",
            )
        except MicrosoftSharePointDeltaAuthenticationError:
            return _health(
                "failed",
                "authentication_failed",
                "Microsoft Graph token was rejected",
            )
        except MicrosoftSharePointDeltaAuthorizationError:
            return _health(
                "failed",
                "authorization_failed",
                "SharePoint metadata access was denied",
            )
        except MicrosoftSharePointDeltaThrottleError as exc:
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="degraded",
                code="throttled",
                message="Microsoft Graph SharePoint delta endpoint is rate limited",
                retry_after_seconds=exc.retry_after_seconds,
            )
        except MicrosoftSharePointDeltaStateExpiredError:
            return _health(
                "degraded",
                "gap_detected",
                "SharePoint delta state expired; authorized full resync is required",
            )
        except MicrosoftSharePointDeltaRetryableError:
            return _health(
                "degraded",
                "retryable_error",
                "Microsoft Graph SharePoint delta endpoint is temporarily unavailable",
            )
        except (MicrosoftSharePointDeltaTerminalError, MicrosoftSharePointDeltaClientError):
            return _health("failed", "terminal_error", "SharePoint delta source request failed")
        return _health(
            "healthy",
            "ok",
            f"Microsoft Graph {page.scope} metadata delta source is reachable; "
            f"sample_count={len(page.records)}",
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return (self._settings(instance).scope,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        if checkpoint is not None and checkpoint.cursor is None:
            return _collection(
                "invalid_config",
                "SharePoint source_cursor checkpoint is missing its cursor",
                checkpoint=checkpoint,
            )
        try:
            page = self._collect_page(instance, checkpoint)
        except CredentialResolutionError:
            return _collection(
                "retryable_error",
                "Microsoft credential is unavailable",
                checkpoint=checkpoint,
            )
        except CredentialProviderNotFoundError:
            return _collection(
                "invalid_config",
                "Microsoft credential provider is unavailable",
                checkpoint=checkpoint,
            )
        except MicrosoftSharePointDeltaAuthenticationError:
            return _collection(
                "authentication_failed",
                "Microsoft Graph token was rejected",
                checkpoint=checkpoint,
            )
        except MicrosoftSharePointDeltaAuthorizationError:
            return _collection(
                "authorization_failed",
                "SharePoint metadata access was denied",
                checkpoint=checkpoint,
            )
        except MicrosoftSharePointDeltaThrottleError:
            return _collection(
                "throttled",
                "Microsoft Graph SharePoint delta endpoint is rate limited",
                checkpoint=checkpoint,
            )
        except MicrosoftSharePointDeltaStateExpiredError:
            return _collection(
                "gap_detected",
                "SharePoint delta state expired; explicit resync authorization is required",
                checkpoint=checkpoint,
            )
        except MicrosoftSharePointDeltaRetryableError:
            return _collection(
                "retryable_error",
                "Microsoft Graph SharePoint delta endpoint is temporarily unavailable",
                checkpoint=checkpoint,
            )
        except (MicrosoftSharePointDeltaTerminalError, MicrosoftSharePointDeltaClientError):
            return _collection(
                "terminal_error",
                "Microsoft Graph SharePoint delta request failed",
                checkpoint=checkpoint,
            )

        next_checkpoint = ConnectorCheckpointV1(
            schema_version="ets.connector.checkpoint.v1",
            cursor=page.checkpoint_url,
        )
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=tuple(_record_mapping(record) for record in page.records),
            checkpoint=next_checkpoint,
            has_more=not page.cycle_complete,
            message="SharePoint metadata delta page collected; checkpoint remains pre-commit",
        )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        return result.checkpoint

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        self.validate_config(instance)
        if checkpoint is None:
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code="unknown_observation",
                reconciled=False,
                gap_detected=False,
                checkpoint=None,
                message="SharePoint delta continuity cannot be established without source state",
            )
        result = self.collect(instance, checkpoint)
        if result.code == "gap_detected":
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code="gap_detected",
                reconciled=False,
                gap_detected=True,
                checkpoint=checkpoint,
                message=result.message,
            )
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
            code="unknown_observation" if result.has_more else "ok",
            reconciled=not result.has_more,
            gap_detected=False,
            checkpoint=result.checkpoint,
            message=(
                "SharePoint delta cycle is still in progress"
                if result.has_more
                else "SharePoint delta cycle completed; this is not a source-completeness claim"
            ),
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        self.validate_config(instance)
        source_record_id = _required_record_string(record, "source_record_id")
        scope = _required_scope(record.get("scope"))
        object_id = _required_record_string(record, "object_id")
        deleted = record.get("deleted")
        if not isinstance(deleted, bool):
            raise ValueError("SharePoint intermediate record deleted must be boolean")
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("SharePoint intermediate record metadata must be an object")
        source_modified = _optional_record_datetime(record.get("source_modified_at_utc"))
        event_type = SHAREPOINT_DELETED_EVENT_TYPE if deleted else SHAREPOINT_OBSERVED_EVENT_TYPE
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id=source_record_id,
            source_system=SHAREPOINT_SOURCE_SYSTEM,
            observed_at_utc=source_modified,
            event_type=event_type,
            media_type="application/json",
            transformation_profile=SHAREPOINT_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata={
                "provider": "microsoft",
                "source_class": "sharepoint_onedrive_metadata_delta",
                "cloud": self._settings(instance).tenant_profile.cloud,
                "scope": scope,
                "object_id": object_id,
                "deleted": deleted,
                "metadata": metadata,
            },
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)

    def _collect_page(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> MicrosoftSharePointDeltaPageV1:
        settings = self._settings(instance)
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError("SharePoint delta credential reference is required")
        reference = CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=credential_ref,
        )
        profile = _request_profile(settings)
        with self._credential_resolver.resolve(reference) as lease:
            client = self._client_factory(
                profile,
                lease.reveal(),
                settings.request_timeout_seconds,
                settings.maximum_response_bytes,
            )
            try:
                return client.fetch(checkpoint.cursor if checkpoint is not None else None)
            finally:
                client.close()

    def _settings(self, instance: ConnectorInstanceV1) -> MicrosoftSharePointDeltaSettings:
        unexpected = sorted(set(instance.settings) - SHAREPOINT_ALLOWED_SETTINGS)
        if unexpected:
            raise ConnectorConfigurationError(
                "unsupported SharePoint connector settings: " + ", ".join(unexpected)
            )
        tenant_profile_id = _setting_string(instance, "tenant_profile_id")
        try:
            tenant_profile = self._tenant_profiles[tenant_profile_id]
        except KeyError as exc:
            raise ConnectorConfigurationError(
                "SharePoint connector references an unknown server-owned tenant profile"
            ) from exc
        scope = _required_scope(instance.settings.get("scope"))
        drive_id = _optional_setting_string(instance, "drive_id")
        site_id = _optional_setting_string(instance, "site_id")
        list_id = _optional_setting_string(instance, "list_id")
        if scope == "drive":
            if drive_id is None or site_id is not None or list_id is not None:
                raise ConnectorConfigurationError(
                    "drive scope requires drive_id and forbids site_id/list_id"
                )
        elif site_id is None or list_id is None or drive_id is not None:
            raise ConnectorConfigurationError(
                "list scope requires site_id/list_id and forbids drive_id"
            )
        timeout = _setting_number(instance, "request_timeout_seconds", 30.0)
        maximum = _setting_int(
            instance,
            "maximum_response_bytes",
            SHAREPOINT_DELTA_DEFAULT_MAXIMUM_BODY_BYTES,
        )
        if not 0.1 <= timeout <= 60.0:
            raise ConnectorConfigurationError(
                "SharePoint request_timeout_seconds must be between 0.1 and 60"
            )
        if not 1 <= maximum <= 16 * 1024 * 1024:
            raise ConnectorConfigurationError(
                "SharePoint maximum_response_bytes exceeds qualified bound"
            )
        return MicrosoftSharePointDeltaSettings(
            tenant_profile_id=tenant_profile_id,
            tenant_profile=tenant_profile,
            scope=scope,
            drive_id=drive_id,
            site_id=site_id,
            list_id=list_id,
            request_timeout_seconds=timeout,
            maximum_response_bytes=maximum,
        )


def _request_profile(
    settings: MicrosoftSharePointDeltaSettings,
) -> MicrosoftSharePointDeltaRequestProfile:
    if settings.scope == "drive":
        assert settings.drive_id is not None
        return sharepoint_drive_delta_request_profile(
            settings.tenant_profile_id,
            settings.tenant_profile,
            settings.drive_id,
        )
    assert settings.site_id is not None and settings.list_id is not None
    return sharepoint_list_delta_request_profile(
        settings.tenant_profile_id,
        settings.tenant_profile,
        settings.site_id,
        settings.list_id,
    )


def _default_client_factory(
    profile: MicrosoftSharePointDeltaRequestProfile,
    credential_material: bytes,
    timeout_seconds: float,
    maximum_response_bytes: int,
) -> SharePointDeltaSourceClient:
    return MicrosoftSharePointDeltaHttpClient(
        profile,
        credential_material,
        timeout_seconds=timeout_seconds,
        maximum_response_bytes=maximum_response_bytes,
    )


def _record_mapping(record: MicrosoftSharePointDeltaRecordV1) -> dict[str, JsonValue]:
    modified = (
        record.source_modified_at_utc.isoformat().replace("+00:00", "Z")
        if record.source_modified_at_utc is not None
        else None
    )
    return {
        "source_record_id": record.source_record_id,
        "object_id": record.object_id,
        "scope": record.scope,
        "deleted": record.deleted,
        "source_modified_at_utc": modified,
        "metadata": record.metadata,
    }


def _health(state: str, code: str, message: str) -> ConnectorHealthV1:
    return ConnectorHealthV1.model_validate(
        {
            "schema_version": "ets.connector.health.v1",
            "state": state,
            "code": code,
            "message": message,
        }
    )


def _collection(
    code: str,
    message: str,
    *,
    checkpoint: ConnectorCheckpointV1 | None,
) -> ConnectorCollectionResultV1:
    return ConnectorCollectionResultV1.model_validate(
        {
            "schema_version": "ets.connector.collection_result.v1",
            "code": code,
            "records": (),
            "checkpoint": checkpoint,
            "has_more": False,
            "message": message,
        }
    )


def _setting_string(instance: ConnectorInstanceV1, key: str) -> str:
    value = instance.settings.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= 500:
        raise ConnectorConfigurationError(f"SharePoint setting {key} must be a bounded string")
    return value


def _optional_setting_string(instance: ConnectorInstanceV1, key: str) -> str | None:
    value = instance.settings.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 500:
        raise ConnectorConfigurationError(f"SharePoint setting {key} must be a bounded string")
    return value


def _setting_number(instance: ConnectorInstanceV1, key: str, default: float) -> float:
    value = instance.settings.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConnectorConfigurationError(f"SharePoint setting {key} must be numeric")
    return float(value)


def _setting_int(instance: ConnectorInstanceV1, key: str, default: int) -> int:
    value = instance.settings.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConnectorConfigurationError(f"SharePoint setting {key} must be an integer")
    return value


def _required_scope(value: object) -> SharePointDeltaScope:
    if value not in {"drive", "list"}:
        raise ConnectorConfigurationError("SharePoint scope must be drive or list")
    return cast(SharePointDeltaScope, value)


def _required_record_string(record: Mapping[str, JsonValue], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"SharePoint intermediate record {key} is invalid")
    return value


def _optional_record_datetime(value: JsonValue | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("SharePoint source_modified_at_utc must be a string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("SharePoint source_modified_at_utc must be timezone-aware")
    return parsed
