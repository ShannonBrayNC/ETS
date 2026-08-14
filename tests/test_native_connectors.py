from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import JsonValue

from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
    ConnectorCollection,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.native import NATIVE_CONNECTOR_BINDINGS, load_native_connector_registry
from ets.connectors.sdk import ConnectorCapabilityError, ConnectorConfigurationError

MANIFESTS = Path("config/connectors/builtin")


def _instance(
    connector_id: str,
    *,
    auth_method: str,
    settings: dict[str, JsonValue] | None = None,
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1(
        schema_version="ets.connector.instance.v1",
        instance_id=connector_id.replace("native.", "test-"),
        connector_id=connector_id,
        connector_version="1.0",
        enabled=True,
        scope=ConnectorScope(tenant_id="tenant-a", workspace_id="workspace-a"),
        source=ConnectorSource(name=connector_id, environment="test"),
        authentication=ConnectorAuthentication(method=auth_method, credential_ref=None),
        collection=ConnectorCollection(mode="push"),
        checkpoint=ConnectorCheckpointPolicy(strategy="none", durable=True),
        policy=ConnectorPolicyBinding(
            capture_profile="capture.native.v1",
            normalization_profile="normalize.native.v1",
        ),
        retry=ConnectorRetryPolicy(),
        gap_detection=ConnectorGapPolicy(enabled=False),
        settings=settings or {},
    )


def test_native_manifest_catalog_loads_all_four_builtins() -> None:
    registry = load_native_connector_registry(MANIFESTS)
    definitions = registry.list_definitions()

    assert tuple(item.connector_id for item in definitions) == (
        "native.file_drop",
        "native.otlp",
        "native.syslog",
        "native.webhook",
    )
    assert set(NATIVE_CONNECTOR_BINDINGS) == {item.connector_id for item in definitions}


def test_native_manifest_settings_schema_references_exist() -> None:
    registry = load_native_connector_registry(MANIFESTS)

    for definition in registry.list_definitions():
        schema_ref = definition.configuration_schema.settings_schema_ref
        assert schema_ref is not None
        assert Path(schema_ref).is_file()


def test_qualified_native_connector_reports_configuration_not_host_liveness() -> None:
    registry = load_native_connector_registry(MANIFESTS)
    instance = _instance(
        "native.webhook",
        auth_method="gateway_principal",
        settings={"bind_port": 8443, "max_body_bytes": 1048576},
    )

    adapter = registry.validate_adapter_instance(instance)
    health = adapter.test_connection(instance)

    assert health.state == "unknown"
    assert health.code == "unknown_observation"
    assert "host liveness" in health.message


def test_otlp_reports_qualified_configuration_without_claiming_host_liveness() -> None:
    registry = load_native_connector_registry(MANIFESTS)
    instance = _instance("native.otlp", auth_method="gateway_principal")

    adapter = registry.validate_adapter_instance(instance)
    health = adapter.health(instance)

    assert NATIVE_CONNECTOR_BINDINGS["native.otlp"].readiness == "qualified"
    assert health.state == "unknown"
    assert health.code == "unknown_observation"
    assert "host liveness" in health.message


def test_native_connector_rejects_unknown_settings() -> None:
    registry = load_native_connector_registry(MANIFESTS)
    instance = _instance(
        "native.file_drop",
        auth_method="gateway_principal",
        settings={"intake_root": "drop", "unexpected": True},
    )

    with pytest.raises(ConnectorConfigurationError, match="unsupported native connector settings"):
        registry.validate_adapter_instance(instance)


def test_native_push_connector_does_not_claim_polling_or_discovery() -> None:
    registry = load_native_connector_registry(MANIFESTS)
    instance = _instance("native.syslog", auth_method="mtls_uri_san")
    adapter = registry.validate_adapter_instance(instance)

    with pytest.raises(ConnectorCapabilityError, match="discovery"):
        adapter.discover(instance)
    with pytest.raises(ConnectorCapabilityError, match="polling"):
        adapter.collect(instance, None)
