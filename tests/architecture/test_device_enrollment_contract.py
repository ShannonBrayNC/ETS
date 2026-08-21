from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path("schemas/device/v1/device-enrollment.schema.json")
FORBIDDEN_PROPERTY_TOKENS = {
    "private_key",
    "client_secret",
    "access_token",
    "refresh_token",
    "bearer_token",
    "sas_token",
    "connection_string",
    "symmetric_key",
    "shared_key",
    "password",
}


def _schema() -> dict[str, Any]:
    payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _property_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            names.update(str(name).lower() for name in properties)
        for child in value.values():
            names.update(_property_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(_property_names(child))
    return names


def test_enrollment_contract_is_closed_and_versioned() -> None:
    schema = _schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == "ets.device.enrollment.v1"
    assert "scope_binding" in schema["required"]
    assert schema["properties"]["scope_binding"]["additionalProperties"] is False


def test_production_device_auth_does_not_offer_symmetric_or_sas_credentials() -> None:
    schema = _schema()
    auth_methods = set(schema["properties"]["auth_method"]["enum"])

    assert auth_methods == {"x509", "tpm_attestation"}
    assert not {"symmetric_key", "sas", "shared_access_key"} & auth_methods


def test_schema_has_no_reusable_secret_fields() -> None:
    names = _property_names(_schema())

    assert not names & FORBIDDEN_PROPERTY_TOKENS


def test_virtual_demo_cannot_claim_hardware_attestation() -> None:
    schema = _schema()
    conditionals = schema["allOf"]
    virtual_rules = [
        rule
        for rule in conditionals
        if rule.get("if", {}).get("properties", {}).get("profile", {}).get("const")
        == "virtual_demo"
    ]

    assert len(virtual_rules) == 1
    properties = virtual_rules[0]["then"]["properties"]
    assert properties["key_custody"]["const"] == "software_demo"
    assert properties["hardware_attested"]["const"] is False


def test_pilot_and_production_profiles_prohibit_software_key_custody() -> None:
    schema = _schema()
    conditionals = schema["allOf"]
    hardware_profile_rules = [
        rule
        for rule in conditionals
        if set(
            rule.get("if", {})
            .get("properties", {})
            .get("profile", {})
            .get("enum", [])
        )
        == {"physical_pilot", "production"}
    ]

    assert len(hardware_profile_rules) == 1
    allowed = set(hardware_profile_rules[0]["then"]["properties"]["key_custody"]["enum"])
    assert allowed == {"tpm2", "secure_element", "hsm"}
    assert "software_demo" not in allowed


def test_tpm_attestation_requires_tpm_custody_and_hardware_attested_true() -> None:
    schema = _schema()
    conditionals = schema["allOf"]
    tpm_rules = [
        rule
        for rule in conditionals
        if rule.get("if", {}).get("properties", {}).get("auth_method", {}).get("const")
        == "tpm_attestation"
    ]

    assert len(tpm_rules) == 1
    properties = tpm_rules[0]["then"]["properties"]
    assert properties["attestation_class"]["const"] == "tpm2"
    assert properties["key_custody"]["const"] == "tpm2"
    assert properties["hardware_attested"]["const"] is True


def test_scope_binding_requires_server_owned_tenant_and_workspace_fields() -> None:
    scope = _schema()["properties"]["scope_binding"]

    assert set(scope["required"]) == {"tenant_id", "workspace_id"}
    assert set(scope["properties"]) == {"tenant_id", "workspace_id"}
