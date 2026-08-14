from __future__ import annotations

import json
from pathlib import Path

from ets.connectors.models import ConnectorDefinitionV1, ConnectorInstanceV1

ROOT = Path(__file__).parents[1]
SCHEMA_ROOT = ROOT / "schemas" / "connectors" / "v1"


def schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def test_definition_schema_declares_strict_versioned_contract() -> None:
    value = schema("connector-definition.schema.json")
    assert value["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert value["$id"].endswith("/connector-definition.schema.json")
    assert value["additionalProperties"] is False
    properties = value["properties"]
    assert isinstance(properties, dict)
    schema_version = properties["schema_version"]
    assert isinstance(schema_version, dict)
    assert schema_version["const"] == "ets.connector.definition.v1"


def test_instance_schema_declares_strict_versioned_contract() -> None:
    value = schema("connector-instance.schema.json")
    assert value["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert value["$id"].endswith("/connector-instance.schema.json")
    assert value["additionalProperties"] is False
    properties = value["properties"]
    assert isinstance(properties, dict)
    schema_version = properties["schema_version"]
    assert isinstance(schema_version, dict)
    assert schema_version["const"] == "ets.connector.instance.v1"


def test_normative_examples_match_runtime_models() -> None:
    ConnectorDefinitionV1.model_validate_json(
        (SCHEMA_ROOT / "examples" / "connector-definition.synthetic.json").read_text(
            encoding="utf-8"
        )
    )
    ConnectorInstanceV1.model_validate_json(
        (SCHEMA_ROOT / "examples" / "connector-instance.synthetic.json").read_text(
            encoding="utf-8"
        )
    )
