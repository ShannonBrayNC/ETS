from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCapabilities,
    ConnectorCheckpointPolicy,
    ConnectorCollection,
    ConnectorConfigurationSchema,
    ConnectorDefinitionV1,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime_store import ConnectorRuntimeStore
from ets.gateway.connector_management import (
    ConnectorManagementAuthorizationError,
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)

NOW = datetime(2026, 8, 14, 18, 0, tzinfo=UTC)


def _definition() -> ConnectorDefinitionV1:
    return ConnectorDefinitionV1(
        schema_version="ets.connector.definition.v1",
        connector_id="synthetic.authorization",
        display_name="Synthetic Authorization",
        description="Connector authorization fixture.",
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


def _instance(instance_id: str = "authorization-source") -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=instance_id,
        connector_id="synthetic.authorization",
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
        source=ConnectorSource(name=instance_id, environment="test"),
        authentication=ConnectorAuthentication(method="none", credential_ref=None),
        collection=ConnectorCollection(mode="poll", interval_seconds=60),
        checkpoint=ConnectorCheckpointPolicy(strategy="source_cursor", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.synthetic.v1",
            normalization_profile="normalize.synthetic.v1",
        ),
        retry=ConnectorRetryPolicy(),
        gap_detection=ConnectorGapPolicy(),
        settings={},
    )


def _principal(
    *,
    can_read: bool = False,
    can_manage: bool = False,
    tenant_id: str = "tenant-a",
) -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id="auditor@example.test" if not can_manage else "admin@example.test",
        tenant_id=tenant_id,
        workspace_id="workspace-a",
        can_read=can_read,
        can_manage=can_manage,
    )


def _service(tmp_path: Path) -> ConnectorManagementService:
    return ConnectorManagementService(
        registry=ConnectorRegistry([_definition()]),
        store=ConnectorRuntimeStore(tmp_path / "authorization.db"),
        now=lambda: NOW,
    )


def test_management_authority_implies_read_authority(tmp_path: Path) -> None:
    service = _service(tmp_path)
    admin = _principal(can_manage=True)
    service.create_instance(admin, _instance())

    assert len(service.catalog(admin)) == 1
    assert len(service.list_instances(admin)) == 1
    assert service.get_instance(admin, "authorization-source").revision == 1
    assert service.get_runtime(admin, "authorization-source").checkpoint_revision == 0


def test_read_only_principal_can_inspect_connector_scope(tmp_path: Path) -> None:
    service = _service(tmp_path)
    admin = _principal(can_manage=True)
    auditor = _principal(can_read=True)
    service.create_instance(admin, _instance())

    assert len(service.catalog(auditor)) == 1
    assert len(service.list_instances(auditor)) == 1
    assert service.get_instance(auditor, "authorization-source").revision == 1
    assert service.get_runtime(auditor, "authorization-source").checkpoint_revision == 0


def test_read_only_principal_cannot_mutate_connector_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    admin = _principal(can_manage=True)
    auditor = _principal(can_read=True)
    service.create_instance(admin, _instance())

    denied_operations = (
        lambda: service.create_instance(auditor, _instance("new-source")),
        lambda: service.set_enabled(
            auditor,
            "authorization-source",
            enabled=False,
            expected_revision=1,
        ),
        lambda: service.validate_config(auditor, _instance()),
        lambda: service.test_connection(auditor, "authorization-source"),
        lambda: service.mark_gap(auditor, "authorization-source"),
        lambda: service.reconcile_gap(auditor, "authorization-source"),
    )

    for operation in denied_operations:
        with pytest.raises(ConnectorManagementAuthorizationError):
            operation()

    assert service.get_instance(admin, "authorization-source").instance.enabled is True
    assert service.get_runtime(admin, "authorization-source").gap_open is False


def test_read_authority_remains_tenant_workspace_scoped(tmp_path: Path) -> None:
    service = _service(tmp_path)
    admin = _principal(can_manage=True)
    foreign_auditor = _principal(can_read=True, tenant_id="tenant-b")
    service.create_instance(admin, _instance())

    assert service.list_instances(foreign_auditor) == ()
    with pytest.raises(ConnectorManagementAuthorizationError):
        service.get_instance(foreign_auditor, "authorization-source")


def test_principal_without_read_or_manage_authority_is_denied(tmp_path: Path) -> None:
    service = _service(tmp_path)
    unauthorized = _principal()

    with pytest.raises(ConnectorManagementAuthorizationError):
        service.catalog(unauthorized)
    with pytest.raises(ConnectorManagementAuthorizationError):
        service.list_instances(unauthorized)
