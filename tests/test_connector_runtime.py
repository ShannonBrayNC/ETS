from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import JsonValue

from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCapabilities,
    ConnectorCheckpointPolicy,
    ConnectorCheckpointV1,
    ConnectorCollection,
    ConnectorCollectionResultV1,
    ConnectorConfigurationSchema,
    ConnectorDefinitionV1,
    ConnectorEvidenceCandidateV1,
    ConnectorGapPolicy,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorReconciliationResultV1,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime import ConnectorOperationReceiptV1
from ets.connectors.runtime_store import (
    ConnectorRevisionConflictError,
    ConnectorRuntimeStore,
)
from ets.gateway.connector_management import (
    ConnectorManagementAuthorizationError,
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)

NOW = datetime(2026, 8, 14, 2, 0, tzinfo=UTC)


class SyntheticAdapter:
    @property
    def definition(self) -> ConnectorDefinitionV1:
        return connector_definition()

    def validate_config(self, instance: ConnectorInstanceV1) -> None:
        if instance.settings.get("reject") is True:
            raise ValueError("synthetic config rejected")

    def test_connection(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="healthy",
            code="ok",
            message=f"connected:{instance.instance_id}",
        )

    def discover(self, instance: ConnectorInstanceV1) -> tuple[str, ...]:
        return (instance.source.name,)

    def collect(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorCollectionResultV1:
        return ConnectorCollectionResultV1(
            schema_version="ets.connector.collection_result.v1",
            code="ok",
            records=(),
            checkpoint=checkpoint,
        )

    def checkpoint(self, result: ConnectorCollectionResultV1) -> ConnectorCheckpointV1 | None:
        return result.checkpoint

    def reconcile(
        self,
        instance: ConnectorInstanceV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> ConnectorReconciliationResultV1:
        return ConnectorReconciliationResultV1(
            schema_version="ets.connector.reconciliation_result.v1",
            code="ok",
            reconciled=True,
            gap_detected=False,
            checkpoint=checkpoint,
        )

    def normalize(
        self,
        instance: ConnectorInstanceV1,
        record: Mapping[str, JsonValue],
    ) -> ConnectorEvidenceCandidateV1:
        return ConnectorEvidenceCandidateV1(
            schema_version="ets.connector.candidate.v1",
            source_record_id="record-1",
            source_system=instance.source.name,
            event_type="synthetic.event",
            transformation_profile="synthetic.v1",
            lossless=True,
            metadata=dict(record),
        )

    def health(self, instance: ConnectorInstanceV1) -> ConnectorHealthV1:
        return self.test_connection(instance)


def connector_definition() -> ConnectorDefinitionV1:
    return ConnectorDefinitionV1(
        schema_version="ets.connector.definition.v1",
        connector_id="synthetic.poll",
        display_name="Synthetic Poll",
        description="Synthetic connector used for G2C qualification.",
        implementation_class="generic",
        source_classes=("synthetic",),
        adapter_version="1.0",
        sdk_contract_version="ets.connector.sdk.v1",
        capture_envelope_versions=("ets.capture.v1",),
        gateway_host_versions=("ets.gateway.connector-host.v1",),
        capabilities=ConnectorCapabilities(
            delivery_modes=("poll",),
            authentication_methods=("none",),
            checkpointing=True,
            reconciliation=True,
        ),
        configuration_schema=ConnectorConfigurationSchema(
            instance_schema="ets.connector.instance.v1"
        ),
    )


def connector_instance(
    instance_id: str = "source-a",
    *,
    enabled: bool = True,
    tenant_id: str = "tenant-a",
    workspace_id: str = "workspace-a",
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=instance_id,
        connector_id="synthetic.poll",
        connector_version="1.0",
        enabled=enabled,
        scope=ConnectorScope(tenant_id=tenant_id, workspace_id=workspace_id),
        source=ConnectorSource(name="synthetic-source", environment="test"),
        authentication=ConnectorAuthentication(method="none", credential_ref=None),
        collection=ConnectorCollection(mode="poll", interval_seconds=60, batch_size=100),
        checkpoint=ConnectorCheckpointPolicy(strategy="source_cursor", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.synthetic.v1",
            normalization_profile="normalize.synthetic.v1",
        ),
        retry=ConnectorRetryPolicy(max_attempts=4, backoff="exponential", max_age_seconds=3600),
        gap_detection=ConnectorGapPolicy(enabled=True),
        settings={},
    )


def principal(
    *,
    tenant_id: str = "tenant-a",
    workspace_id: str = "workspace-a",
    can_manage: bool = True,
) -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id="admin@example.test",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        can_manage=can_manage,
    )


def make_service(path: Path) -> tuple[ConnectorManagementService, ConnectorRuntimeStore]:
    registry = ConnectorRegistry()
    registry.register_adapter(SyntheticAdapter())
    store = ConnectorRuntimeStore(path)
    service = ConnectorManagementService(
        registry=registry,
        store=store,
        now=lambda: NOW,
    )
    return service, store


def test_instance_and_runtime_state_survive_store_restart(tmp_path: Path) -> None:
    database = tmp_path / "connectors.db"
    service, _ = make_service(database)
    created = service.create_instance(principal(), connector_instance())
    assert created.revision == 1

    reopened = ConnectorRuntimeStore(database)
    assert reopened.get_instance("source-a").instance == connector_instance()
    runtime = reopened.get_runtime("source-a")
    assert runtime.checkpoint is None
    assert runtime.observation_state == "unknown_observation"


def test_management_scope_is_server_authorized(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path / "scope.db")
    with pytest.raises(ConnectorManagementAuthorizationError):
        service.create_instance(
            principal(tenant_id="other-tenant"),
            connector_instance(),
        )


def test_instance_updates_use_optimistic_revision_and_audit(tmp_path: Path) -> None:
    service, store = make_service(tmp_path / "revision.db")
    service.create_instance(principal(), connector_instance())
    updated = connector_instance().model_copy(
        update={
            "source": ConnectorSource(
                name="renamed-source",
                environment="test",
            )
        }
    )
    record = service.update_instance(principal(), updated, expected_revision=1)
    assert record.revision == 2

    with pytest.raises(ConnectorRevisionConflictError):
        service.update_instance(principal(), connector_instance(), expected_revision=1)

    actions = tuple(event.action for event in store.list_audit_events("source-a"))
    assert actions == ("connector.created", "connector.updated")


def test_enable_disable_is_revisioned_and_audited(tmp_path: Path) -> None:
    service, store = make_service(tmp_path / "enabled.db")
    service.create_instance(principal(), connector_instance())
    disabled = service.set_enabled(principal(), "source-a", enabled=False, expected_revision=1)
    enabled = service.set_enabled(principal(), "source-a", enabled=True, expected_revision=2)

    assert disabled.instance.enabled is False
    assert enabled.instance.enabled is True
    actions = tuple(event.action for event in store.list_audit_events("source-a"))
    assert actions == (
        "connector.created",
        "connector.disabled",
        "connector.enabled",
    )


def test_validate_and_test_connection_use_registered_adapter(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path / "connection.db")
    instance = connector_instance()
    service.create_instance(principal(), instance)

    validated = service.validate_config(principal(), instance)
    tested = service.test_connection(principal(), "source-a")

    assert validated.code == "ok"
    assert tested.state == "healthy"
    assert tested.message == "connected:source-a"


def test_checkpoint_compare_and_set_and_gap_visibility(tmp_path: Path) -> None:
    service, _ = make_service(tmp_path / "checkpoint.db")
    service.create_instance(principal(), connector_instance())
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor="cursor-1",
        observed_through_utc=NOW,
    )
    state = service.update_checkpoint(
        principal(),
        "source-a",
        checkpoint,
        expected_checkpoint_revision=0,
        observation_state="healthy_observation",
        gap_open=False,
        last_success_at_utc=NOW,
    )
    assert state.checkpoint_revision == 1
    assert state.checkpoint == checkpoint

    with pytest.raises(ConnectorRevisionConflictError):
        service.update_checkpoint(
            principal(),
            "source-a",
            checkpoint,
            expected_checkpoint_revision=0,
            observation_state="healthy_observation",
            gap_open=False,
            last_success_at_utc=NOW,
        )

    gap = service.mark_gap(principal(), "source-a")
    assert gap.gap_open is True
    assert gap.observation_state == "collection_gap"
    reconciled = service.reconcile_gap(principal(), "source-a")
    assert reconciled.gap_open is False
    assert reconciled.observation_state == "healthy_observation"


def test_retry_schedule_and_leases_are_bounded_and_restart_safe(tmp_path: Path) -> None:
    service, store = make_service(tmp_path / "leases.db")
    service.create_instance(principal(), connector_instance())
    retry_at = NOW + timedelta(minutes=5)
    state = store.schedule_retry("source-a", next_attempt_at_utc=retry_at, now=NOW)
    assert state.retry_count == 1
    assert store.claim_due(owner="worker-a", now=NOW, lease_seconds=30, limit=5) == ()

    claimed = store.claim_due(
        owner="worker-a",
        now=retry_at,
        lease_seconds=30,
        limit=5,
    )
    assert claimed == ("source-a",)
    assert store.get_runtime("source-a").lease_owner == "worker-a"

    reopened = ConnectorRuntimeStore(tmp_path / "leases.db")
    assert reopened.recover_expired_leases(now=retry_at + timedelta(seconds=31)) == 1
    assert reopened.get_runtime("source-a").lease_owner is None


def test_disabled_instances_are_not_claimed_by_scheduler(tmp_path: Path) -> None:
    service, store = make_service(tmp_path / "disabled-schedule.db")
    service.create_instance(principal(), connector_instance(enabled=False))
    assert store.claim_due(owner="worker-a", now=NOW, lease_seconds=30, limit=5) == ()


def test_scheduler_claims_only_explicitly_composed_instances(tmp_path: Path) -> None:
    service, store = make_service(tmp_path / "composed-schedule.db")
    service.create_instance(principal(), connector_instance(instance_id="source-a"))
    service.create_instance(principal(), connector_instance(instance_id="source-b"))

    claimed = store.claim_due(
        owner="hosted-worker",
        now=NOW,
        lease_seconds=30,
        limit=5,
        instance_ids=("source-b",),
    )

    assert claimed == ("source-b",)
    assert store.get_runtime("source-a").lease_owner is None
    assert store.get_runtime("source-b").lease_owner == "hosted-worker"

    with pytest.raises(ValueError, match="must not be empty"):
        store.claim_due(
            owner="hosted-worker",
            now=NOW,
            lease_seconds=30,
            limit=5,
            instance_ids=(),
        )


def test_operation_receipt_keeps_commit_and_sync_states_distinct() -> None:
    receipt = ConnectorOperationReceiptV1(
        schema_version="ets.connector.operation_receipt.v1",
        instance_id="source-a",
        stage="committed_local",
        source_received=True,
        committed_local=True,
        sync_queued=False,
        sync_acknowledged=False,
        created_at_utc=NOW,
    )
    assert receipt.committed_local is True
    assert receipt.sync_queued is False

    with pytest.raises(ValueError, match="sync_queued requires committed_local"):
        ConnectorOperationReceiptV1(
            schema_version="ets.connector.operation_receipt.v1",
            instance_id="source-a",
            stage="sync_queued",
            source_received=True,
            committed_local=False,
            sync_queued=True,
            created_at_utc=NOW,
        )
