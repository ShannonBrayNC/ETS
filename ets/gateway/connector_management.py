"""Governed connector instance and runtime management service for Gateway G2C."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ets.connectors.credentials.broker import CredentialBroker
from ets.connectors.credentials.models import (
    CREDENTIAL_REFERENCE_SCHEMA_VERSION,
    CredentialReferenceV1,
)
from ets.connectors.models import (
    ConnectorCheckpointV1,
    ConnectorDefinitionV1,
    ConnectorHealthV1,
    ConnectorInstanceV1,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime import (
    ConnectorInstanceRecordV1,
    ConnectorObservationState,
    ConnectorRuntimeStateV1,
)
from ets.connectors.runtime_store import ConnectorRuntimeStore


class ConnectorManagementAuthorizationError(PermissionError):
    """Raised when a management principal cannot administer a connector scope."""


@dataclass(frozen=True, slots=True)
class ConnectorManagementPrincipal:
    """Authenticated management identity supplied by the outer Gateway auth boundary."""

    actor_id: str
    tenant_id: str
    workspace_id: str
    can_manage: bool = True

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("actor_id", self.actor_id, 200),
            ("tenant_id", self.tenant_id, 128),
            ("workspace_id", self.workspace_id, 128),
        ):
            if not 1 <= len(value) <= maximum:
                raise ValueError(f"{name} must be 1-{maximum} characters")


class ConnectorManagementService:
    """Apply authorization, connector validation, credentials, and durable runtime state."""

    def __init__(
        self,
        *,
        registry: ConnectorRegistry,
        store: ConnectorRuntimeStore,
        credential_broker: CredentialBroker | None = None,
        now: callable_datetime | None = None,
    ) -> None:
        self._registry = registry
        self._store = store
        self._credential_broker = credential_broker
        self._now = now or _utc_now

    def catalog(self) -> tuple[ConnectorDefinitionV1, ...]:
        return self._registry.list_definitions()

    def create_instance(
        self,
        principal: ConnectorManagementPrincipal,
        instance: ConnectorInstanceV1,
    ) -> ConnectorInstanceRecordV1:
        self._authorize(principal, instance)
        self._registry.validate_instance(instance)
        self._validate_credential_reference(instance)
        return self._store.create_instance(
            instance,
            actor_id=principal.actor_id,
            now=self._now(),
        )

    def get_instance(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
    ) -> ConnectorInstanceRecordV1:
        record = self._store.get_instance(instance_id)
        self._authorize(principal, record.instance)
        return record

    def list_instances(
        self,
        principal: ConnectorManagementPrincipal,
    ) -> tuple[ConnectorInstanceRecordV1, ...]:
        records = self._store.list_instances()
        return tuple(
            record
            for record in records
            if self._is_authorized(principal, record.instance)
        )

    def update_instance(
        self,
        principal: ConnectorManagementPrincipal,
        instance: ConnectorInstanceV1,
        *,
        expected_revision: int,
    ) -> ConnectorInstanceRecordV1:
        current = self._store.get_instance(instance.instance_id)
        self._authorize(principal, current.instance)
        self._authorize(principal, instance)
        self._registry.validate_instance(instance)
        self._validate_credential_reference(instance)
        return self._store.replace_instance(
            instance,
            expected_revision=expected_revision,
            actor_id=principal.actor_id,
            action="connector.updated",
            now=self._now(),
        )

    def set_enabled(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
        *,
        enabled: bool,
        expected_revision: int,
    ) -> ConnectorInstanceRecordV1:
        record = self.get_instance(principal, instance_id)
        updated = record.instance.model_copy(update={"enabled": enabled})
        action = "connector.enabled" if enabled else "connector.disabled"
        return self._store.replace_instance(
            updated,
            expected_revision=expected_revision,
            actor_id=principal.actor_id,
            action=action,
            now=self._now(),
        )

    def validate_config(
        self,
        principal: ConnectorManagementPrincipal,
        instance: ConnectorInstanceV1,
    ) -> ConnectorHealthV1:
        self._authorize(principal, instance)
        self._registry.validate_adapter_instance(instance)
        self._validate_credential_reference(instance)
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="healthy",
            code="ok",
            message="connector configuration is compatible with the registered adapter",
        )

    def test_connection(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
    ) -> ConnectorHealthV1:
        record = self.get_instance(principal, instance_id)
        instance = record.instance
        adapter = self._registry.validate_adapter_instance(instance)
        credential_ref = instance.authentication.credential_ref
        if credential_ref is not None:
            if self._credential_broker is None:
                raise RuntimeError("connector credential broker is not configured")
            reference = CredentialReferenceV1(
                schema_version=CREDENTIAL_REFERENCE_SCHEMA_VERSION,
                ref=credential_ref,
            )
            with self._credential_broker.resolve(reference):
                return adapter.test_connection(instance)
        return adapter.test_connection(instance)

    def get_runtime(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
    ) -> ConnectorRuntimeStateV1:
        self.get_instance(principal, instance_id)
        return self._store.get_runtime(instance_id)

    def update_checkpoint(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
        checkpoint: ConnectorCheckpointV1 | None,
        *,
        expected_checkpoint_revision: int,
        observation_state: ConnectorObservationState,
        gap_open: bool,
        last_success_at_utc: datetime | None,
    ) -> ConnectorRuntimeStateV1:
        self.get_instance(principal, instance_id)
        return self._store.set_checkpoint(
            instance_id,
            checkpoint,
            expected_checkpoint_revision=expected_checkpoint_revision,
            observation_state=observation_state,
            gap_open=gap_open,
            last_success_at_utc=last_success_at_utc,
            now=self._now(),
        )

    def mark_gap(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
    ) -> ConnectorRuntimeStateV1:
        self.get_instance(principal, instance_id)
        return self._store.mark_gap(instance_id, now=self._now())

    def reconcile_gap(
        self,
        principal: ConnectorManagementPrincipal,
        instance_id: str,
    ) -> ConnectorRuntimeStateV1:
        self.get_instance(principal, instance_id)
        return self._store.reconcile_gap(instance_id, now=self._now())

    def _validate_credential_reference(self, instance: ConnectorInstanceV1) -> None:
        credential_ref = instance.authentication.credential_ref
        if credential_ref is None:
            return
        reference = CredentialReferenceV1(
            schema_version=CREDENTIAL_REFERENCE_SCHEMA_VERSION,
            ref=credential_ref,
        )
        if self._credential_broker is not None:
            self._credential_broker.describe(reference)

    @staticmethod
    def _is_authorized(
        principal: ConnectorManagementPrincipal,
        instance: ConnectorInstanceV1,
    ) -> bool:
        return (
            principal.can_manage
            and principal.tenant_id == instance.scope.tenant_id
            and principal.workspace_id == instance.scope.workspace_id
        )

    def _authorize(
        self,
        principal: ConnectorManagementPrincipal,
        instance: ConnectorInstanceV1,
    ) -> None:
        if not self._is_authorized(principal, instance):
            raise ConnectorManagementAuthorizationError(
                "management principal is not authorized for connector scope"
            )


class callable_datetime:
    """Minimal callable protocol without importing product runtime dependencies."""

    def __call__(self) -> datetime:
        raise NotImplementedError


def _utc_now() -> datetime:
    return datetime.now(UTC)
