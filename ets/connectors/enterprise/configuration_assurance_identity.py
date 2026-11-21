"""Fail-closed identity matrix for the Microsoft configuration-assurance pilot."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONFIGURATION_ASSURANCE_IDENTITY_SCHEMA_VERSION: Literal[
    "ets.microsoft.configuration_assurance.identity_matrix.v1"
] = (
    "ets.microsoft.configuration_assurance.identity_matrix.v1"
)

_GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

IdentityRole = Literal[
    "investigator",
    "context_reader",
    "read_broker",
    "executor",
    "verifier",
    "exporter",
]
AuthorityClass = Literal["read_only", "write", "verify_only", "export_only"]
AccessMode = Literal[
    "delegated_interactive",
    "application",
    "managed_identity",
    "workload_identity",
]
EnterpriseMcpAccess = Literal["none", "delegated_interactive", "application"]
ConsentMode = Literal[
    "none",
    "delegated_admin_consent",
    "application_admin_consent",
    "managed_identity_role_assignment",
]
Cloud = Literal["AzureCloud", "AzureUSGovernment", "AzureChinaCloud"]
FeatureMaturity = Literal["stable", "documented_preview", "private_preview", "unknown"]
BrokerRegistration = Literal["not_applicable", "platform_managed", "byo_preview"]
QualificationStatus = Literal["unqualified", "qualified"]

_EXPECTED_AUTHORITY: dict[str, AuthorityClass] = {
    "investigator": "read_only",
    "context_reader": "read_only",
    "read_broker": "read_only",
    "executor": "write",
    "verifier": "verify_only",
    "exporter": "export_only",
}
_REQUIRED_ROLES = frozenset(_EXPECTED_AUTHORITY)


class StrictIdentityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ConfigurationAssurancePrincipalV1(StrictIdentityModel):
    """One explicitly bounded principal in the six-role pilot identity matrix."""

    role: IdentityRole
    tenant_id: str = Field(min_length=36, max_length=36)
    principal_object_id: str = Field(min_length=36, max_length=36)
    app_id: str = Field(min_length=36, max_length=36)
    agent_blueprint_id: str | None = Field(default=None, min_length=1, max_length=256)
    agent_blueprint_not_applicable_reason: str | None = Field(
        default=None, min_length=1, max_length=512
    )
    authority: AuthorityClass
    access_mode: AccessMode
    token_audiences: tuple[str, ...]
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    resource_allowlist: tuple[str, ...]
    consent_mode: ConsentMode
    cloud: Cloud
    licensing: tuple[str, ...]
    feature_maturity: FeatureMaturity
    enterprise_mcp_access: EnterpriseMcpAccess = "none"
    broker_registration: BrokerRegistration = "not_applicable"
    qualification_status: QualificationStatus = "unqualified"
    qualification_evidence: tuple[str, ...] = ()

    @field_validator("tenant_id", "principal_object_id", "app_id")
    @classmethod
    def normalize_guid(cls, value: str) -> str:
        if _GUID_PATTERN.fullmatch(value) is None:
            raise ValueError("identity identifiers must be canonical GUID strings")
        return value.lower()

    @field_validator(
        "token_audiences",
        "roles",
        "scopes",
        "resource_allowlist",
        "licensing",
        "qualification_evidence",
    )
    @classmethod
    def reject_duplicate_or_blank_entries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("identity matrix lists cannot contain blank entries")
        if len(set(value)) != len(value):
            raise ValueError("identity matrix lists cannot contain duplicate entries")
        return value

    @model_validator(mode="after")
    def validate_role_boundary(self) -> ConfigurationAssurancePrincipalV1:
        expected = _EXPECTED_AUTHORITY[self.role]
        if self.authority != expected:
            raise ValueError(f"{self.role} authority must be {expected}")

        has_blueprint = self.agent_blueprint_id is not None
        has_reason = self.agent_blueprint_not_applicable_reason is not None
        if has_blueprint == has_reason:
            raise ValueError(
                "record either agent_blueprint_id or an explicit not-applicable reason"
            )

        if self.enterprise_mcp_access == "application":
            raise ValueError("Enterprise MCP access must not use app-only authorization")
        if (
            self.enterprise_mcp_access == "delegated_interactive"
            and self.access_mode != "delegated_interactive"
        ):
            raise ValueError("Enterprise MCP delegated access requires an interactive principal")

        if self.role == "read_broker":
            if self.access_mode == "delegated_interactive":
                raise ValueError(
                    "the autonomous read broker requires its own non-interactive identity"
                )
            if self.broker_registration == "not_applicable":
                raise ValueError("the read broker must record its registration mode")
        elif self.broker_registration != "not_applicable":
            raise ValueError("broker registration applies only to the read broker")

        if self.qualification_status == "qualified" and not self.qualification_evidence:
            raise ValueError("a qualified identity requires retained qualification evidence")
        if self.qualification_status == "unqualified" and self.qualification_evidence:
            raise ValueError("unqualified identities cannot cite qualification evidence as passed")
        return self


class ConfigurationAssuranceIdentityMatrixV1(StrictIdentityModel):
    """Complete identity claim; validation does not itself qualify live access."""

    schema_version: Literal[
        "ets.microsoft.configuration_assurance.identity_matrix.v1"
    ] = CONFIGURATION_ASSURANCE_IDENTITY_SCHEMA_VERSION
    tenant_id: str = Field(min_length=36, max_length=36)
    cloud: Cloud
    principals: tuple[ConfigurationAssurancePrincipalV1, ...]

    @field_validator("tenant_id")
    @classmethod
    def normalize_tenant_id(cls, value: str) -> str:
        if _GUID_PATTERN.fullmatch(value) is None:
            raise ValueError("tenant_id must be a canonical GUID string")
        return value.lower()

    @model_validator(mode="after")
    def validate_complete_separation(self) -> ConfigurationAssuranceIdentityMatrixV1:
        by_role = {principal.role: principal for principal in self.principals}
        if len(by_role) != len(self.principals):
            raise ValueError("the identity matrix cannot contain duplicate roles")
        missing = _REQUIRED_ROLES - set(by_role)
        extra = set(by_role) - _REQUIRED_ROLES
        if missing or extra:
            raise ValueError(
                f"identity matrix must contain exactly the six required roles; "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        if any(item.tenant_id != self.tenant_id for item in self.principals):
            raise ValueError("all principals must belong to the matrix tenant")
        if any(item.cloud != self.cloud for item in self.principals):
            raise ValueError("all principals must use the matrix cloud")

        executor = by_role["executor"]
        for role in ("investigator", "context_reader", "read_broker"):
            principal = by_role[role]
            if principal.principal_object_id == executor.principal_object_id:
                raise ValueError(f"executor principal must be separate from {role}")
            if principal.app_id == executor.app_id:
                raise ValueError(f"executor application must be separate from {role}")
        return self


__all__ = [
    "CONFIGURATION_ASSURANCE_IDENTITY_SCHEMA_VERSION",
    "ConfigurationAssuranceIdentityMatrixV1",
    "ConfigurationAssurancePrincipalV1",
]
