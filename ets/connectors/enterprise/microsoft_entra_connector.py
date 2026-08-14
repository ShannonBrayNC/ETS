"""Microsoft Entra users/groups delta ConnectorAdapter for G2E-C."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import JsonValue

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialProviderNotFoundError,
    CredentialResolutionError,
)
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_entra_delta import (
    ENTRA_DEFAULT_MAXIMUM_BODY_BYTES,
    ENTRA_DEFAULT_MAXIMUM_RECORDS,
    EntraDeltaCollection,
    EntraDeltaRequestProfile,
    MicrosoftEntraDeltaRecordV1,
    entra_delta_request_profile,
)
from ets.connectors.enterprise.microsoft_entra_http import (
    MicrosoftEntraDeltaAuthenticationError,
    MicrosoftEntraDeltaAuthorizationError,
    MicrosoftEntraDeltaClientError,
    MicrosoftEntraDeltaHttpClient,
    MicrosoftEntraDeltaRetryableError,
    MicrosoftEntraDeltaStateExpiredError,
    MicrosoftEntraDeltaTerminalError,
    MicrosoftEntraDeltaThrottleError,
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

ENTRA_CONNECTOR_ID = "microsoft.entra.directory_delta"
ENTRA_SOURCE_SYSTEM = "microsoft.entra.directory_delta"
ENTRA_TRANSFORMATION_PROFILE = "ets.connector.microsoft.entra-directory-delta.v1"
ENTRA_OBSERVED_EVENT_TYPE = "microsoft.entra.directory_object.observed"
ENTRA_REMOVED_EVENT_TYPE = "microsoft.entra.directory_object.removed"
ENTRA_ALLOWED_SETTINGS = frozenset(
    {
        "tenant_profile_id",
        "collection",
        "request_timeout_seconds",
        "maximum_response_bytes",
    }
)


@dataclass(frozen=True, slots=True)
class MicrosoftEntraDeltaSettings:
    tenant_profile_id: str
    tenant_profile: MicrosoftTenantProfileV1
    collection: EntraDeltaCollection
    request_timeout_seconds: float
    maximum_response_bytes: int


class CredentialResolver(Protocol):
    """Minimal G2B credential boundary required by the Entra adapter."""

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease: ...


class EntraDeltaSourceClient(Protocol):
    """Source client contract used by the adapter and deterministic fixtures."""

    def fetch(self, request_url: str | None = None): ...

    def close(self) -> None: ...


EntraDeltaClientFactory = Callable[
    [EntraDeltaRequestProfile, bytes, float, int],
    EntraDeltaSourceClient,
]


class MicrosoftEntraDeltaAdapter:
    """Bounded G2E-C adapter for Microsoft Graph users/groups delta collection."""

    def __init__(
        self,
        definition: ConnectorDefinitionV1,
        credential_resolver: CredentialResolver,
        tenant_profiles: Mapping[str, MicrosoftTenantProfileV1],
        *,
        client_factory: EntraDeltaClientFactory | None = None,
    ) -> None:
        if definition.connector_id != ENTRA_CONNECTOR_ID:
            raise ValueError(f"Entra adapter requires {ENTRA_CONNECTOR_ID} definition")
        if definition.implementation_class != "enterprise_api":
            raise ValueError("Entra adapter requires enterprise_api definition")
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
            raise ConnectorConfigurationError("Entra delta connector requires poll collection")
        if instance.collection.batch_size > ENTRA_DEFAULT_MAXIMUM_RECORDS:
            raise ConnectorConfigurationError(
                "Entra delta collection batch_size must not exceed 1000"
            )
        if instance.checkpoint.strategy != "source_cursor":
            raise ConnectorConfigurationError(
                "Entra delta connector requires source_cursor checkpoint strategy"
            )
        if instance.authentication.method != "bearer":
            raise ConnectorConfigurationError(
                "Entra delta connector requires bearer authentication"
            )
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError(
                "Entra delta connector requires an opaque credential reference"
            )
        if credential_ref != settings.tenant_profile.credential_ref.ref:
            raise ConnectorConfigurationError(
                "Entra delta credential reference does not match the server-owned tenant profile"
            )
        if settings.tenant_profile.consent_state != "granted":
            raise ConnectorConfigurationError(
                "Entra delta tenant profile requires granted administrator consent"
            )

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
                "Microsoft credential provider is unavailable",
            )
        except MicrosoftEntraDeltaAuthenticationError:
            return _health(
                "failed",
                "authentication_failed",
                "Microsoft Graph access token was rejected",
            )
        except MicrosoftEntraDeltaAuthorizationError:
            return _health(
                "failed",
                "authorization_failed",
                "Microsoft Graph directory access was denied",
            )
        except MicrosoftEntraDeltaThrottleError as exc:
            return ConnectorHealthV1(
                schema_version="ets.connector.health.v1",
                state="degraded",
                code="throttled",
                message="Microsoft Graph delta endpoint is rate limited",
                retry_after_seconds=exc.retry_after_seconds,
            )
        except MicrosoftEntraDeltaStateExpiredError:
            return _health(
                "degraded",
                "gap_detected",
                "Microsoft Graph delta state expired; authorized full resync is required",
            )
        except MicrosoftEntraDeltaRetryableError:
            return _health(
                "degraded",
                "retryable_error",
                "Microsoft Graph delta endpoint is temporarily unavailable",
            )
        except (MicrosoftEntraDeltaTerminalError, MicrosoftEntraDeltaClientError):
            return _health(
                "failed",
                "terminal_error",
                "Microsoft Graph delta request failed",
            )
        return _health(
            "healthy",
            "ok",
            f"Microsoft Graph {page.collection} delta source is reachable; "
            f"sample_count={len(page.records)}",
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        self.validate_config(instance)
        return (self._settings(instance).collection,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        self.validate_config(instance)
        if checkpoint is not None and checkpoint.cursor is None:
            return _collection(
                "invalid_config",
                "Entra delta source_cursor checkpoint is missing its cursor",
                checkpoint=checkpoint,
            )
        try:
            page = self._collect_page(instance, checkpoint)
        except CredentialResolutionError as exc:
            return _collection(
                _credential_operation_code(exc),
                "Microsoft credential is unavailable",
                checkpoint=checkpoint,
            )
        except CredentialProviderNotFoundError:
            return _collection(
                "invalid_config",
                "Microsoft credential provider is unavailable",
                checkpoint=checkpoint,
            )
        except MicrosoftEntraDeltaAuthenticationError:
            return _collection(
                "authentication_failed",
                "Microsoft Graph access token was rejected",
                checkpoint=checkpoint,
            )
        except MicrosoftEntraDeltaAuthorizationError:
            return _collection(
                "authorization_failed",
                "Microsoft Graph directory access was denied",
                checkpoint=checkpoint,
            )
        except MicrosoftEntraDeltaThrottleError:
            return _collection(
                "throttled",
                "Microsoft Graph delta endpoint is rate limited",
                checkpoint=checkpoint,
            )
        except MicrosoftEntraDeltaStateExpiredError:
            return _collection(
                "gap_detected",
                "Microsoft Graph delta state expired; explicit full resync authorization is required",
                checkpoint=checkpoint,
            )
        except MicrosoftEntraDeltaRetryableError:
            return _collection(
                "retryable_error",
                "Microsoft Graph delta endpoint is temporarily unavailable",
                checkpoint=checkpoint,
            )
        except (MicrosoftEntraDeltaTerminalError, MicrosoftEntraDeltaClientError):
            return _collection(
                "terminal_error",
                "Microsoft Graph delta request failed",
                checkpoint=checkpoint,
            )

        next_checkpoint = ConnectorCheckpointV1(
            schema_version="ets.connector.checkpoint.v1",
            cursor=page.checkpoint_url,
        )
        records = tuple(record.model_dump(mode="json") for record in page.records)
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=records,
            checkpoint=next_checkpoint,
            has_more=not page.cycle_complete,
            message=(
                "Microsoft Entra delta page collected; source checkpoint remains pre-commit"
            ),
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
                message="Entra delta continuity cannot be established without source state",
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
        if result.has_more:
            return ConnectorReconciliationResultV1(
                schema_version="ets.connector.reconciliation_result.v1",
                code="unknown_observation",
                reconciled=False,
                gap_detected=False,
                checkpoint=result.checkpoint,
                message="Entra delta reconciliation cycle is still in progress",
            )
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="ok",
            reconciled=True,
            gap_detected=False,
            checkpoint=result.checkpoint,
            message=(
                "Entra delta source reconciliation cycle completed; this is not a "
                "real-world completeness claim"
            ),
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        self.validate_config(instance)
        parsed = MicrosoftEntraDeltaRecordV1.model_validate(dict(record))
        event_type = (
            ENTRA_REMOVED_EVENT_TYPE
            if parsed.removed_reason is not None
            else ENTRA_OBSERVED_EVENT_TYPE
        )
        audit: dict[str, JsonValue] = {
            "collection": parsed.collection,
            "object_id": parsed.object_id,
            "directory": parsed.metadata,
        }
        if parsed.removed_reason is not None:
            audit["removed_reason"] = parsed.removed_reason
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id=parsed.source_record_id,
            source_system=ENTRA_SOURCE_SYSTEM,
            observed_at_utc=None,
            event_type=event_type,
            media_type="application/json",
            transformation_profile=ENTRA_TRANSFORMATION_PROFILE,
            lossless=False,
            metadata={
                "provider": "microsoft",
                "source_class": "entra_directory_delta",
                "cloud": self._settings(instance).tenant_profile.cloud,
                "audit": audit,
            },
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)

    def _collect_page(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ):
        settings = self._settings(instance)
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            raise ConnectorConfigurationError("Entra delta credential reference is required")
        reference = CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=credential_ref,
        )
        profile = entra_delta_request_profile(
            settings.tenant_profile,
            settings.collection,
        )
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

    def _settings(self, instance: ConnectorInstanceV1) -> MicrosoftEntraDeltaSettings:
        unexpected = sorted(set(instance.settings) - ENTRA_ALLOWED_SETTINGS)
        if unexpected:
            raise ConnectorConfigurationError(
                "unsupported Entra delta connector settings: " + ", ".join(unexpected)
            )
        profile_id = instance.settings.get("tenant_profile_id")
        if not isinstance(profile_id, str) or not 1 <= len(profile_id) <= 128:
            raise ConnectorConfigurationError("Entra tenant_profile_id setting is invalid")
        try:
            tenant_profile = self._tenant_profiles[profile_id]
        except KeyError as exc:
            raise ConnectorConfigurationError(
                "Entra tenant profile is not registered server-side"
            ) from exc
        collection = instance.settings.get("collection")
        if collection not in {"users", "groups"}:
            raise ConnectorConfigurationError("Entra collection must be users or groups")
        timeout = instance.settings.get("request_timeout_seconds", 30.0)
        if (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or not 0.1 <= float(timeout) <= 60.0
        ):
            raise ConnectorConfigurationError(
                "Entra request_timeout_seconds must be between 0.1 and 60"
            )
        maximum = instance.settings.get(
            "maximum_response_bytes",
            ENTRA_DEFAULT_MAXIMUM_BODY_BYTES,
        )
        if (
            not isinstance(maximum, int)
            or isinstance(maximum, bool)
            or not 1 <= maximum <= ENTRA_DEFAULT_MAXIMUM_BODY_BYTES
        ):
            raise ConnectorConfigurationError(
                "Entra maximum_response_bytes exceeds the qualified bound"
            )
        return MicrosoftEntraDeltaSettings(
            tenant_profile_id=profile_id,
            tenant_profile=tenant_profile,
            collection=collection,
            request_timeout_seconds=float(timeout),
            maximum_response_bytes=maximum,
        )


def _default_client_factory(
    profile: EntraDeltaRequestProfile,
    credential_material: bytes,
    timeout_seconds: float,
    maximum_response_bytes: int,
) -> EntraDeltaSourceClient:
    return MicrosoftEntraDeltaHttpClient(
        profile,
        credential_material,
        timeout_seconds=timeout_seconds,
        maximum_response_bytes=maximum_response_bytes,
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
    return _health(state, code, "Microsoft connector credential is unavailable")


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
    *,
    checkpoint: ConnectorCheckpointV1 | None = None,
) -> ConnectorCollectionResultV1:
    return ConnectorCollectionResultV1(
        schema_version="ets.connector.collection_result.v1",
        code=code,
        checkpoint=checkpoint,
        message=message,
    )
