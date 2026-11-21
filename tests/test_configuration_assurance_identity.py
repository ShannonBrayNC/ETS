from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.configuration_assurance_identity import (
    ConfigurationAssuranceIdentityMatrixV1,
)

TENANT_ID = "11111111-2222-3333-4444-555555555555"


def _principal(index: int, role: str, authority: str) -> dict[str, object]:
    return {
        "role": role,
        "tenant_id": TENANT_ID,
        "principal_object_id": f"00000000-0000-0000-0000-{index:012d}",
        "app_id": f"10000000-0000-0000-0000-{index:012d}",
        "agent_blueprint_id": None,
        "agent_blueprint_not_applicable_reason": "This role is not an Agent 365 instance.",
        "authority": authority,
        "access_mode": "workload_identity",
        "token_audiences": ("https://graph.microsoft.com/.default",),
        "roles": (),
        "scopes": (),
        "resource_allowlist": ("tenant:disposable-pilot",),
        "consent_mode": "managed_identity_role_assignment",
        "cloud": "AzureCloud",
        "licensing": ("pilot-license-unconfirmed",),
        "feature_maturity": "documented_preview",
        "enterprise_mcp_access": "none",
        "broker_registration": "not_applicable",
        "qualification_status": "unqualified",
        "qualification_evidence": (),
    }


def _matrix() -> dict[str, object]:
    principals = [
        _principal(1, "investigator", "read_only"),
        _principal(2, "context_reader", "read_only"),
        _principal(3, "read_broker", "read_only"),
        _principal(4, "executor", "write"),
        _principal(5, "verifier", "verify_only"),
        _principal(6, "exporter", "export_only"),
    ]
    principals[0]["access_mode"] = "delegated_interactive"
    principals[0]["enterprise_mcp_access"] = "delegated_interactive"
    principals[0]["consent_mode"] = "delegated_admin_consent"
    principals[2]["broker_registration"] = "byo_preview"
    return {
        "schema_version": "ets.microsoft.configuration_assurance.identity_matrix.v1",
        "tenant_id": TENANT_ID,
        "cloud": "AzureCloud",
        "principals": tuple(principals),
    }


def _mutable_principals(payload: dict[str, object]) -> list[dict[str, object]]:
    principals = payload["principals"]
    assert isinstance(principals, tuple)
    mutable = [dict(item) for item in principals]
    payload["principals"] = tuple(mutable)
    return mutable


def test_identity_matrix_records_six_separated_authority_profiles() -> None:
    matrix = ConfigurationAssuranceIdentityMatrixV1.model_validate(_matrix())

    assert {item.role for item in matrix.principals} == {
        "investigator",
        "context_reader",
        "read_broker",
        "executor",
        "verifier",
        "exporter",
    }
    assert matrix.principals[0].enterprise_mcp_access == "delegated_interactive"
    assert matrix.principals[2].broker_registration == "byo_preview"


@pytest.mark.parametrize("field", ["principal_object_id", "app_id"])
def test_executor_cannot_reuse_an_investigator_identity(field: str) -> None:
    payload = _matrix()
    principals = _mutable_principals(payload)
    principals[3][field] = principals[0][field]

    with pytest.raises(ValidationError, match="executor .* must be separate from investigator"):
        ConfigurationAssuranceIdentityMatrixV1.model_validate(payload)


def test_enterprise_mcp_rejects_app_only_authorization() -> None:
    payload = _matrix()
    principals = _mutable_principals(payload)
    principals[0]["access_mode"] = "application"
    principals[0]["enterprise_mcp_access"] = "application"

    with pytest.raises(ValidationError, match="must not use app-only"):
        ConfigurationAssuranceIdentityMatrixV1.model_validate(payload)


def test_read_role_cannot_claim_write_authority() -> None:
    payload = _matrix()
    principals = _mutable_principals(payload)
    principals[0]["authority"] = "write"

    with pytest.raises(ValidationError, match="investigator authority must be read_only"):
        ConfigurationAssuranceIdentityMatrixV1.model_validate(payload)


def test_autonomous_broker_requires_separate_registration_metadata() -> None:
    payload = _matrix()
    principals = _mutable_principals(payload)
    principals[2]["broker_registration"] = "not_applicable"

    with pytest.raises(ValidationError, match="must record its registration mode"):
        ConfigurationAssuranceIdentityMatrixV1.model_validate(payload)


def test_qualification_claim_requires_retained_evidence() -> None:
    payload = deepcopy(_matrix())
    principals = _mutable_principals(payload)
    principals[0]["qualification_status"] = "qualified"

    with pytest.raises(ValidationError, match="requires retained qualification evidence"):
        ConfigurationAssuranceIdentityMatrixV1.model_validate(payload)


def test_matrix_requires_all_six_roles() -> None:
    payload = _matrix()
    principals = _mutable_principals(payload)
    principals.pop()
    payload["principals"] = tuple(principals)

    with pytest.raises(ValidationError, match="exactly the six required roles"):
        ConfigurationAssuranceIdentityMatrixV1.model_validate(payload)
