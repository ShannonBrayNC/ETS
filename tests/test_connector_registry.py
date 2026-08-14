from __future__ import annotations

import json
from pathlib import Path

import pytest

from ets.connectors.models import ConnectorDefinitionV1, ConnectorInstanceV1
from ets.connectors.registry import (
    ConnectorCompatibilityError,
    ConnectorRegistry,
    ConnectorRegistryError,
)

ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "schemas" / "connectors" / "v1" / "examples"
FIXTURES = ROOT / "tests" / "fixtures" / "connectors" / "v1"


def definition() -> ConnectorDefinitionV1:
    return ConnectorDefinitionV1.model_validate_json(
        (EXAMPLES / "connector-definition.synthetic.json").read_text(encoding="utf-8")
    )


def instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate_json(
        (EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8")
    )


def test_registry_discovers_manifest_directory_deterministically(tmp_path: Path) -> None:
    (tmp_path / "b.json").write_text(
        (EXAMPLES / "connector-definition.synthetic.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    registry = ConnectorRegistry.from_manifest_directory(tmp_path)
    assert [item.connector_id for item in registry.list_definitions()] == ["synthetic.audit"]


def test_duplicate_connector_ids_fail_closed() -> None:
    registry = ConnectorRegistry([definition()])
    with pytest.raises(ConnectorRegistryError, match="duplicate connector definition"):
        registry.register_definition(definition())


def test_version_mismatch_fails_closed() -> None:
    value = json.loads((EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8"))
    value["connector_version"] = "2.0"
    registry = ConnectorRegistry([definition()])
    with pytest.raises(ConnectorCompatibilityError, match="adapter version"):
        registry.validate_instance(ConnectorInstanceV1.model_validate_json(json.dumps(value)))


def test_delivery_and_authentication_capabilities_are_enforced() -> None:
    value = json.loads((EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8"))
    value["authentication"]["method"] = "oauth2"
    registry = ConnectorRegistry([definition()])
    with pytest.raises(ConnectorCompatibilityError, match="authentication method"):
        registry.validate_instance(ConnectorInstanceV1.model_validate_json(json.dumps(value)))


def test_sdk_gateway_and_capture_version_mismatches_fail_closed() -> None:
    registry = ConnectorRegistry([definition()], sdk_contract_version="ets.connector.sdk.v2")
    with pytest.raises(ConnectorCompatibilityError, match="SDK contract"):
        registry.validate_instance(instance())

    registry = ConnectorRegistry(
        [definition()], gateway_host_version="ets.gateway.connector-host.v2"
    )
    with pytest.raises(ConnectorCompatibilityError, match="Gateway connector host"):
        registry.validate_instance(instance())

    registry = ConnectorRegistry([definition()], capture_envelope_version="ets.capture.v2")
    with pytest.raises(ConnectorCompatibilityError, match="capture envelope"):
        registry.validate_instance(instance())
