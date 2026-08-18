from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ets.connectors.enterprise.microsoft_health import MicrosoftOperationalPostureV1
from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCapabilities,
    ConnectorCollection,
    ConnectorConfigurationSchema,
    ConnectorDefinitionV1,
    ConnectorHealthV1,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.runtime import ConnectorRuntimeStateV1
from ets.connectors.runtime_store import ConnectorRuntimeStore
from ets.gateway.connector_management import (
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.microsoft_operational_posture_api import (
    GatewayMicrosoftOperationalPostureService,
    create_microsoft_operational_posture_router,
)

NOW = datetime(2026, 8, 18, 4, 0, tzinfo=UTC)
MICROSOFT_CONNECTOR = "microsoft.sharepoint.onedrive_delta"
SYNTHETIC_CONNECTOR = "synthetic.poll"
TENANT = "tenant-a"
WORKSPACE = "workspace-a"


def _definition(connector_id: str) -> ConnectorDefinitionV1:
    implementation_class = "enterprise_api" if connector_id == MICROSOFT_CONNECTOR else "generic"
    source_classes = (
        ("microsoft",) if connector_id == MICROSOFT_CONNECTOR else ("synthetic",)
    )
    return ConnectorDefinitionV1(
        schema_version="ets.connector.definition.v1",
        connector_id=connector_id,
        display_name=connector_id,
        description="Operational posture API fixture.",
        implementation_class=implementation_class,
        source_classes=source_classes,
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


def _instance(
    instance_id: str = "microsoft-source",
    connector_id: str = MICROSOFT_CONNECTOR,
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=instance_id,
        connector_id=connector_id,
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id=TENANT, workspace_id=WORKSPACE),
        source=ConnectorSource(name=instance_id, environment="test"),
        authentication=ConnectorAuthentication(method="none", credential_ref=None),
        collection=ConnectorCollection(mode="poll", interval_seconds=60),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.microsoft.test.v1",
            normalization_profile="normalize.microsoft.test.v1",
        ),
        settings={},
    )


def _posture(instance_id: str = "microsoft-source") -> MicrosoftOperationalPostureV1:
    return MicrosoftOperationalPostureV1(
        instance_id=instance_id,
        ets_tenant_id=TENANT,
        workspace_id=WORKSPACE,
        source_id="microsoft-sharepoint-source",
        microsoft_tenant_id="11111111-1111-1111-1111-111111111111",
        subscription_id="subscription-001",
        evaluated_at_utc=NOW,
        policy_profile_id="microsoft-p0-test",
        health=ConnectorHealthV1(
            schema_version="ets.connector.health.v1",
            state="healthy",
            code="ok",
            message="Microsoft connector operational posture is healthy",
        ),
        subscription_status="active",
        subscription_expiration_date_time=NOW + timedelta(hours=8),
        seconds_until_subscription_expiration=8 * 3600,
        collection_lag_seconds=30.0,
        queue_depth=0,
        oldest_unsynchronized_age_seconds=None,
        retryable_failure_count=0,
        terminal_failure_count=0,
        reconciliation_status=None,
        reconciliation_outcome=None,
    )


@dataclass
class _Provider:
    posture: MicrosoftOperationalPostureV1
    calls: int = 0

    def read(
        self,
        instance: ConnectorInstanceV1,
        runtime: ConnectorRuntimeStateV1,
    ) -> MicrosoftOperationalPostureV1:
        assert instance.instance_id == runtime.instance_id
        self.calls += 1
        return self.posture


def _principal(
    *,
    tenant_id: str = TENANT,
    workspace_id: str = WORKSPACE,
    can_read: bool = True,
    can_manage: bool = False,
) -> ConnectorManagementPrincipal:
    return ConnectorManagementPrincipal(
        actor_id="posture-reader",
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        can_read=can_read,
        can_manage=can_manage,
    )


def _setup(
    tmp_path: Path,
    *,
    provider: _Provider | None = None,
) -> tuple[TestClient, ConnectorManagementService, _Provider | None]:
    registry = ConnectorRegistry(
        [_definition(MICROSOFT_CONNECTOR), _definition(SYNTHETIC_CONNECTOR)]
    )
    management = ConnectorManagementService(
        registry=registry,
        store=ConnectorRuntimeStore(tmp_path / "posture-management.db"),
        now=lambda: NOW,
    )
    admin = _principal(can_read=True, can_manage=True)
    management.create_instance(admin, _instance())
    management.create_instance(admin, _instance("synthetic-source", SYNTHETIC_CONNECTOR))
    providers = {} if provider is None else {MICROSOFT_CONNECTOR: provider}
    posture_service = GatewayMicrosoftOperationalPostureService(
        management=management,
        providers=providers,
    )

    def resolve(request: Request) -> ConnectorManagementPrincipal:
        return _principal(
            tenant_id=request.headers.get("x-tenant", TENANT),
            workspace_id=request.headers.get("x-workspace", WORKSPACE),
            can_read=request.headers.get("x-read", "true") == "true",
            can_manage=request.headers.get("x-manage", "false") == "true",
        )

    app = FastAPI()
    app.include_router(
        create_microsoft_operational_posture_router(posture_service, resolve)
    )
    return TestClient(app), management, provider


def test_read_only_principal_can_read_posture_without_mutating_runtime(tmp_path: Path) -> None:
    provider = _Provider(_posture())
    api, management, _ = _setup(tmp_path, provider=provider)
    reader = _principal()
    before = management.get_runtime(reader, "microsoft-source")

    response = api.get(
        "/gateway/connectors/v1/instances/microsoft-source/microsoft/posture"
    )

    after = management.get_runtime(reader, "microsoft-source")
    assert response.status_code == 200
    assert response.json()["ets_tenant_id"] == TENANT
    assert response.json()["workspace_id"] == WORKSPACE
    assert response.json()["verification_claimed"] is False
    assert response.json()["source_truth_claimed"] is False
    assert response.json()["completeness_claimed"] is False
    assert before == after
    assert provider.calls == 1
    serialized = response.text.casefold()
    assert "client_state" not in serialized
    assert "access_token" not in serialized
    assert "raw_content" not in serialized


def test_cross_scope_read_is_denied_before_provider_execution(tmp_path: Path) -> None:
    provider = _Provider(_posture())
    api, _, _ = _setup(tmp_path, provider=provider)

    response = api.get(
        "/gateway/connectors/v1/instances/microsoft-source/microsoft/posture",
        headers={"x-tenant": "tenant-other"},
    )

    assert response.status_code == 403
    assert response.headers["x-ets-connector-diagnostic-code"] == "access_denied"
    assert provider.calls == 0


def test_unsupported_connector_and_missing_instance_are_bounded(tmp_path: Path) -> None:
    provider = _Provider(_posture())
    api, _, _ = _setup(tmp_path, provider=provider)

    unsupported = api.get(
        "/gateway/connectors/v1/instances/synthetic-source/microsoft/posture"
    )
    missing = api.get("/gateway/connectors/v1/instances/missing/microsoft/posture")

    assert unsupported.status_code == 422
    assert (
        unsupported.headers["x-ets-connector-diagnostic-code"]
        == "microsoft_posture_unavailable"
    )
    assert missing.status_code == 404
    assert missing.headers["x-ets-connector-diagnostic-code"] == "instance_not_found"
    assert provider.calls == 0


def test_provider_scope_mismatch_fails_closed(tmp_path: Path) -> None:
    wrong = _posture().model_copy(update={"workspace_id": "workspace-other"})
    provider = _Provider(wrong)
    api, _, _ = _setup(tmp_path, provider=provider)

    response = api.get(
        "/gateway/connectors/v1/instances/microsoft-source/microsoft/posture"
    )

    assert response.status_code == 503
    assert (
        response.headers["x-ets-connector-diagnostic-code"]
        == "microsoft_posture_scope_mismatch"
    )
    assert provider.calls == 1


def test_principal_without_read_or_manage_capability_is_denied(tmp_path: Path) -> None:
    provider = _Provider(_posture())
    api, _, _ = _setup(tmp_path, provider=provider)

    response = api.get(
        "/gateway/connectors/v1/instances/microsoft-source/microsoft/posture",
        headers={"x-read": "false", "x-manage": "false"},
    )

    assert response.status_code == 403
    assert provider.calls == 0
