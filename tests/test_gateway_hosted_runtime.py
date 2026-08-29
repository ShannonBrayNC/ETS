from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
)
from ets.connectors.models import ConnectorCheckpointV1
from ets.gateway import hosted_runtime
from ets.gateway.connector_runner import GatewayConnectorRunResult
from ets.gateway.hosted_runtime import (
    HostedMicrosoftGatewaySettings,
    _connector_instance,
    _entra_connector_instance,
    _purview_connector_instance,
)

ROOT = Path(__file__).resolve().parents[1]


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID": "11111111-1111-1111-1111-111111111111",
        "ETS_GATEWAY_DIRECTORY_MANAGED_IDENTITY_CLIENT_ID": (
            "44444444-4444-4444-4444-444444444444"
        ),
        "ETS_GATEWAY_PURVIEW_MANAGED_IDENTITY_CLIENT_ID": (
            "55555555-5555-5555-5555-555555555555"
        ),
        "ETS_GATEWAY_CORE_BASE_URL": "https://core.internal.example",
        "ETS_GATEWAY_CORE_SCOPE": "api://ets-core/.default",
        "ETS_GATEWAY_TENANT_ID": "tenant_echo",
        "ETS_GATEWAY_WORKSPACE_ID": "workspace_echo",
        "ETS_GATEWAY_INSTANCE_ID": "echomedia-sharepoint",
        "ETS_GATEWAY_SOURCE_ID": "echomedia-sharepoint-prod",
        "ETS_GATEWAY_SOURCE_PRINCIPAL": "gateway://microsoft/sharepoint",
        "ETS_GATEWAY_MICROSOFT_TENANT_ID": "22222222-2222-2222-2222-222222222222",
        "ETS_GATEWAY_MICROSOFT_APPLICATION_ID": "11111111-1111-1111-1111-111111111111",
        "ETS_GATEWAY_SHAREPOINT_DRIVE_ID": "drive-1",
        "ETS_AUTH_JWKS_JSON": '{"keys":[]}',
        "ETS_AUTH_ISSUER": "https://issuer.example/",
        "ETS_AUTH_AUDIENCE": "api://ets-gateway",
        "ETS_AUTH_TENANT_ID": "22222222-2222-2222-2222-222222222222",
        "ETS_AUTH_APP_SCOPE_MAP_JSON": json.dumps(
            {
                "33333333-3333-3333-3333-333333333333": {
                    "tenant_id": "tenant_echo",
                    "workspace_id": "workspace_echo",
                }
            }
        ),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ETS_AUTH_JWKS_URL", raising=False)
    monkeypatch.delenv("ETS_GATEWAY_GRAPH_NOTIFICATION_URL", raising=False)
    monkeypatch.delenv("ETS_GATEWAY_GRAPH_CLIENT_STATE", raising=False)
    monkeypatch.delenv("ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON", raising=False)


def _enable_graph_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "ETS_GATEWAY_GRAPH_NOTIFICATION_URL",
        "https://gateway.example.test/gateway/v1/microsoft/graph",
    )
    monkeypatch.setenv("ETS_GATEWAY_GRAPH_CLIENT_STATE", "server-owned-client-state")
    monkeypatch.setenv(
        "ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON",
        json.dumps(
            {
                "schema_version": (
                    "ets.connector.microsoft.operational_health_policy.v1"
                ),
                "profile_id": "microsoft-p0",
                "subscription_renewal_warning_seconds": 86_400,
                "maximum_collection_lag_seconds": 900,
                "maximum_unsynchronized_age_seconds": 900,
                "maximum_source_queue_depth": 100,
            }
        ),
    )


def test_settings_require_production_jwks_and_server_scope_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)

    settings = HostedMicrosoftGatewaySettings.from_env()

    assert settings.auth_jwks_json == '{"keys":[]}'
    assert settings.auth_jwks_url is None
    assert settings.auth_app_scope_map[
        "33333333-3333-3333-3333-333333333333"
    ] == ("tenant_echo", "workspace_echo")
    assert settings.poll_interval_seconds == 60
    assert settings.directory_managed_identity_client_id.startswith("44444444")
    assert settings.purview_managed_identity_client_id.startswith("55555555")


def test_settings_reject_ambiguous_jwks_source(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ETS_AUTH_JWKS_URL", "https://issuer.example/jwks")

    with pytest.raises(RuntimeError, match="exactly one"):
        HostedMicrosoftGatewaySettings.from_env()


def test_settings_require_graph_subscription_and_policy_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv(
        "ETS_GATEWAY_GRAPH_NOTIFICATION_URL",
        "https://gateway.example.test/gateway/v1/microsoft/graph",
    )

    with pytest.raises(RuntimeError, match="configured together"):
        HostedMicrosoftGatewaySettings.from_env()


def test_settings_accept_exact_server_owned_graph_lifecycle_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    _enable_graph_lifecycle(monkeypatch)

    settings = HostedMicrosoftGatewaySettings.from_env()

    assert settings.graph_notification_url == (
        "https://gateway.example.test/gateway/v1/microsoft/graph"
    )
    assert settings.graph_client_state == "server-owned-client-state"
    assert settings.graph_subscription_lifetime_seconds == 28 * 24 * 60 * 60
    assert settings.graph_subscription_renewal_window_seconds == 24 * 60 * 60


def test_settings_reject_graph_notification_url_with_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    _enable_graph_lifecycle(monkeypatch)
    monkeypatch.setenv(
        "ETS_GATEWAY_GRAPH_NOTIFICATION_URL",
        "https://gateway.example.test/gateway/v1/microsoft/graph?source=payload",
    )

    with pytest.raises(RuntimeError, match="exact HTTPS"):
        HostedMicrosoftGatewaySettings.from_env()


def test_connector_instance_uses_deployment_authoritative_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    settings = HostedMicrosoftGatewaySettings.from_env()

    instance = _connector_instance(settings, "1.0.0")

    assert instance.scope.tenant_id == "tenant_echo"
    assert instance.scope.workspace_id == "workspace_echo"
    assert instance.authentication.credential_ref == "azure-mi://microsoft-graph"
    assert instance.checkpoint.strategy == "source_cursor"
    assert instance.settings == {
        "tenant_profile_id": "hosted-microsoft",
        "scope": "drive",
        "drive_id": "drive-1",
    }


def test_settings_require_three_distinct_microsoft_managed_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv(
        "ETS_GATEWAY_PURVIEW_MANAGED_IDENTITY_CLIENT_ID",
        "44444444-4444-4444-4444-444444444444",
    )

    with pytest.raises(RuntimeError, match="three distinct managed identities"):
        HostedMicrosoftGatewaySettings.from_env()


def test_hosted_connector_instances_isolate_credentials_sources_and_checkpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    settings = HostedMicrosoftGatewaySettings.from_env()

    sharepoint = _connector_instance(settings, "1.0")
    users = _entra_connector_instance(settings, "1.0", "users")
    groups = _entra_connector_instance(settings, "1.0", "groups")
    purview = _purview_connector_instance(settings, "1.0")

    assert len({item.instance_id for item in (sharepoint, users, groups, purview)}) == 4
    assert {
        item.authentication.credential_ref
        for item in (sharepoint, users, groups, purview)
    } == {
        MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
        MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
        MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
    }
    assert users.settings["collection"] == "users"
    assert groups.settings["collection"] == "groups"
    assert purview.settings["content_type"] == "Audit.General"
    assert purview.settings["include_client_ip"] is False
    assert all(
        item.checkpoint.strategy == "source_cursor" and item.checkpoint.durable
        for item in (sharepoint, users, groups, purview)
    )


def test_runtime_composes_four_durable_workers_without_identity_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ETS_GATEWAY_STATE_DIR", str(tmp_path))
    monkeypatch.setenv(
        "ETS_GATEWAY_MANIFEST_DIR",
        str(ROOT / "config" / "connectors" / "enterprise"),
    )

    class FakeCoreTokens:
        def close(self) -> None:
            pass

    monkeypatch.setattr(
        hosted_runtime,
        "AzureManagedIdentityCoreTokenProvider",
        lambda **_kwargs: FakeCoreTokens(),
    )
    monkeypatch.setattr(hosted_runtime, "_auth_policy", lambda _settings: object())
    settings = HostedMicrosoftGatewaySettings.from_env()

    runtime, _management, _auth, _posture = hosted_runtime._compose_runtime(settings)

    assert len(runtime.workers) == 4
    assert len({id(worker.runner) for worker in runtime.workers}) == 4
    assert len({worker.principal for worker in runtime.workers}) == 4
    assert tuple(
        runtime.store.get_runtime(instance.instance_id).checkpoint
        for instance in runtime.instances
    ) == (None, None, None, None)
    assert {
        worker.instance.authentication.credential_ref for worker in runtime.workers
    } == {
        MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
        MICROSOFT_DIRECTORY_CREDENTIAL_REFERENCE,
        MICROSOFT_PURVIEW_CREDENTIAL_REFERENCE,
    }
    collected: list[str] = []

    def run_composed_worker(**kwargs: object) -> GatewayConnectorRunResult:
        instance = kwargs["instance"]
        assert hasattr(instance, "instance_id")
        instance_id = str(instance.instance_id)
        collected.append(instance_id)
        return GatewayConnectorRunResult(
            code="ok",
            source_records=0,
            committed_local=0,
            sync_queued=0,
            partial_commit=0,
            checkpoint_to_persist=ConnectorCheckpointV1(
                schema_version="ets.connector.checkpoint.v1",
                cursor=f"fixture://{instance_id}",
            ),
            has_more=False,
            message="fixture collection",
        )

    for worker in runtime.workers:
        monkeypatch.setattr(worker.runner, "run", run_composed_worker)

    purview_instance = next(
        instance
        for instance in runtime.instances
        if instance.connector_id == "microsoft.purview.activity"
    )
    runtime.store.mark_gap(
        purview_instance.instance_id,
        now=datetime(2026, 8, 29, 0, 0, tzinfo=UTC),
    )

    runtime.run_cycle()

    assert set(collected) == {instance.instance_id for instance in runtime.instances}
    assert all(
        runtime.store.get_runtime(instance.instance_id).checkpoint_revision == 1
        for instance in runtime.instances
    )
    purview_runtime = runtime.store.get_runtime(purview_instance.instance_id)
    assert purview_runtime.gap_open is False
    assert purview_runtime.observation_state == "healthy_observation"

    class FailingGraphLifecycle:
        def run_once(self, *, now: object) -> None:
            raise RuntimeError("fixture Graph lifecycle failure")

    runtime.graph_subscription_lifecycle = FailingGraphLifecycle()  # type: ignore[assignment]
    collected.clear()

    with pytest.raises(RuntimeError, match="1 bounded operation"):
        runtime.run_cycle()

    assert set(collected) == {instance.instance_id for instance in runtime.instances}
    runtime.graph_subscription_lifecycle = None

    failed_worker = runtime.workers[1]

    def fail_one_worker(**_kwargs: object) -> GatewayConnectorRunResult:
        raise RuntimeError("fixture source failure")

    monkeypatch.setattr(failed_worker.runner, "run", fail_one_worker)
    collected.clear()

    with pytest.raises(RuntimeError, match="1 bounded operation"):
        runtime.run_cycle()

    assert set(collected) == {
        worker.instance.instance_id
        for worker in runtime.workers
        if worker is not failed_worker
    }
    assert all(
        runtime.store.get_runtime(instance.instance_id).lease_owner is None
        for instance in runtime.instances
    )
    runtime.microsoft_credentials.close()
    runtime.core_tokens.close()
    runtime.event_store.close()


def test_runtime_composes_graph_lifecycle_for_exact_sharepoint_drive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    _enable_graph_lifecycle(monkeypatch)
    monkeypatch.setenv("ETS_GATEWAY_STATE_DIR", str(tmp_path))
    monkeypatch.setenv(
        "ETS_GATEWAY_MANIFEST_DIR",
        str(ROOT / "config" / "connectors" / "enterprise"),
    )

    class FakeCoreTokens:
        def close(self) -> None:
            pass

    monkeypatch.setattr(
        hosted_runtime,
        "AzureManagedIdentityCoreTokenProvider",
        lambda **_kwargs: FakeCoreTokens(),
    )
    monkeypatch.setattr(hosted_runtime, "_auth_policy", lambda _settings: object())

    runtime, _management, _auth, posture = hosted_runtime._compose_runtime(
        HostedMicrosoftGatewaySettings.from_env()
    )

    assert runtime.graph_subscription_store is not None
    assert runtime.graph_subscription_store.snapshot() == {}
    assert runtime.graph_subscription_lifecycle is not None
    assert runtime.graph_subscription_lifecycle.resource == "drives/drive-1/root"
    assert runtime.graph_resource_committer is not None
    assert posture is not None
    runtime.microsoft_credentials.close()
    runtime.core_tokens.close()
    runtime.graph_subscription_store.close()
    runtime.event_store.close()


def test_hosted_app_installs_bounded_graph_webhook_when_lifecycle_is_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    _enable_graph_lifecycle(monkeypatch)
    monkeypatch.setenv("ETS_GATEWAY_STATE_DIR", str(tmp_path))
    monkeypatch.setenv(
        "ETS_GATEWAY_MANIFEST_DIR",
        str(ROOT / "config" / "connectors" / "enterprise"),
    )

    class FakeCoreTokens:
        def close(self) -> None:
            pass

    monkeypatch.setattr(
        hosted_runtime,
        "AzureManagedIdentityCoreTokenProvider",
        lambda **_kwargs: FakeCoreTokens(),
    )
    monkeypatch.setattr(hosted_runtime, "_auth_policy", lambda _settings: object())

    app = hosted_runtime.create_app_from_env()

    assert "/gateway/v1/microsoft/graph" in {
        getattr(route, "path", None) for route in app.routes
    }
    asyncio.run(app.router.on_shutdown[0]())


def test_hosted_runtime_runbook_preserves_identity_and_live_claim_boundaries() -> None:
    text = (
        ROOT
        / "docs"
        / "connectors"
        / "MICROSOFT_P0_HOSTED_RUNTIME_COMPOSITION_V1.md"
    ).read_text(encoding="utf-8")

    for required in (
        "four explicit",
        "azure-mi://microsoft-graph/directory",
        "azure-mi://office-365-management/purview",
        "four distinct internal source principals",
        "explicit allowlist of the four composed instance IDs",
        "include_client_ip=false",
        "empty service-specific allowlist",
        "PublisherIdentifier",
        "does not prove live token acquisition",
        "does not start live qualification",
        "MICROSOFT_P0_GRAPH_LIFECYCLE_COMPOSITION_V1.md",
    ):
        assert required in text


def test_hosted_graph_lifecycle_runbook_preserves_live_activation_boundaries() -> None:
    text = (
        ROOT
        / "docs"
        / "connectors"
        / "MICROSOFT_P0_GRAPH_LIFECYCLE_COMPOSITION_V1.md"
    ).read_text(encoding="utf-8")

    for required in (
        "drives/{percent-encoded-drive-id}/root",
        "requests only the `updated` change type",
        "42,300-minute OneDrive maximum",
        "atomically distrust the old ID",
        "never promoted to ETS evidence",
        "Container Apps `secretRef`",
        "retains `external: false`",
        "does not acquire a live token",
        "does not start the 72-hour soak",
    ):
        assert required in text


@pytest.mark.parametrize("value", ["29", "3601", "not-an-int"])
def test_poll_interval_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ETS_GATEWAY_POLL_INTERVAL_SECONDS", value)

    with pytest.raises(RuntimeError):
        HostedMicrosoftGatewaySettings.from_env()
