from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.connectors.models import ConnectorDefinitionV1, ConnectorInstanceV1

ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "schemas" / "connectors" / "v1" / "examples"
FIXTURES = ROOT / "tests" / "fixtures" / "connectors" / "v1"


def test_definition_and_instance_parse_strictly() -> None:
    definition = ConnectorDefinitionV1.model_validate_json(
        (EXAMPLES / "connector-definition.synthetic.json").read_text(encoding="utf-8")
    )
    instance = ConnectorInstanceV1.model_validate_json(
        (EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8")
    )
    assert definition.connector_id == "synthetic.audit"
    assert instance.scope.tenant_id == "tenant_demo"


def test_unknown_fields_are_rejected() -> None:
    value = json.loads((EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8"))
    value["unexpected"] = True
    with pytest.raises(ValidationError):
        ConnectorInstanceV1.model_validate_json(json.dumps(value))


def test_poll_requires_interval_and_push_forbids_it() -> None:
    value = json.loads((EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8"))
    value["collection"]["interval_seconds"] = None
    with pytest.raises(ValidationError):
        ConnectorInstanceV1.model_validate_json(json.dumps(value))

    value["collection"]["mode"] = "push"
    value["collection"]["interval_seconds"] = 60
    with pytest.raises(ValidationError):
        ConnectorInstanceV1.model_validate_json(json.dumps(value))


def test_embedded_reusable_secret_keys_are_rejected() -> None:
    value = json.loads((EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8"))
    value["settings"] = {"nested": {"client_secret": "do-not-store"}}
    with pytest.raises(ValidationError, match="embedded key"):
        ConnectorInstanceV1.model_validate_json(json.dumps(value))


def test_credential_reference_is_allowed() -> None:
    value = json.loads((EXAMPLES / "connector-instance.synthetic.json").read_text(encoding="utf-8"))
    value["authentication"] = {
        "method": "none",
        "credential_ref": "secrets://connectors/synthetic-audit-production"
    }
    parsed = ConnectorInstanceV1.model_validate_json(json.dumps(value))
    assert parsed.authentication.credential_ref is not None


def test_native_and_enterprise_api_definitions_share_one_contract() -> None:
    value = json.loads(
        (EXAMPLES / "connector-definition.synthetic.json").read_text(encoding="utf-8")
    )
    enterprise = ConnectorDefinitionV1.model_validate_json(json.dumps(value))
    assert enterprise.implementation_class == "enterprise_api"

    value["connector_id"] = "native.syslog"
    value["implementation_class"] = "native"
    value["source_classes"] = ["syslog"]
    value["capabilities"]["delivery_modes"] = ["push"]
    native = ConnectorDefinitionV1.model_validate_json(json.dumps(value))
    assert native.implementation_class == "native"


def test_source_native_record_keys_are_not_restricted_by_settings_key_rules() -> None:
    from ets.connectors.models import ConnectorCollectionResultV1

    result = ConnectorCollectionResultV1.model_validate(
        {
            "schema_version": "ets.connector.collection_result.v1",
            "code": "ok",
            "records": ({"@odata.context": "fixture", "$source": "synthetic"},),
            "checkpoint": None,
            "has_more": False,
            "message": None,
        }
    )
    assert result.records[0]["@odata.context"] == "fixture"
