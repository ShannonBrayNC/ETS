"""Microsoft tenant/cloud onboarding and credential-readiness boundary for G2E."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
    CredentialStatus,
)
from ets.connectors.credentials.provider import (
    CredentialProviderError,
    CredentialProviderNotFoundError,
)

MICROSOFT_TENANT_PROFILE_SCHEMA_VERSION = "ets.connector.microsoft.tenant_profile.v1"
MICROSOFT_READINESS_SCHEMA_VERSION = "ets.connector.microsoft.readiness.v1"

_GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

MicrosoftCloud = Literal[
    "global",
    "us_government_l4",
    "us_government_l5_dod",
    "china_21vianet",
]
MicrosoftConsentState = Literal["pending", "granted", "partial", "revoked", "failed"]
MicrosoftReadinessState = Literal["ready", "pending", "degraded", "blocked"]
MicrosoftReadinessCode = Literal[
    "ready",
    "consent_pending",
    "consent_partial",
    "consent_revoked",
    "consent_failed",
    "credential_missing",
    "credential_expired",
    "credential_revoked",
    "credential_incompatible",
    "credential_unavailable",
    "credential_provider_unavailable",
]


@dataclass(frozen=True, slots=True)
class MicrosoftCloudEndpoints:
    """Server-owned Microsoft cloud authority roots; never customer-supplied URLs."""

    authority_root: str
    graph_root: str


_MICROSOFT_CLOUD_ENDPOINTS: dict[MicrosoftCloud, MicrosoftCloudEndpoints] = {
    "global": MicrosoftCloudEndpoints(
        authority_root="https://login.microsoftonline.com",
        graph_root="https://graph.microsoft.com",
    ),
    "us_government_l4": MicrosoftCloudEndpoints(
        authority_root="https://login.microsoftonline.us",
        graph_root="https://graph.microsoft.us",
    ),
    "us_government_l5_dod": MicrosoftCloudEndpoints(
        authority_root="https://login.microsoftonline.us",
        graph_root="https://dod-graph.microsoft.us",
    ),
    "china_21vianet": MicrosoftCloudEndpoints(
        authority_root="https://login.partner.microsoftonline.cn",
        graph_root="https://microsoftgraph.chinacloudapi.cn",
    ),
}


class StrictMicrosoftModel(BaseModel):
    """Strict immutable management model without reusable credential material."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftTenantProfileV1(StrictMicrosoftModel):
    """Server-approved Microsoft tenant/cloud onboarding profile."""

    schema_version: Literal["ets.connector.microsoft.tenant_profile.v1"]
    tenant_id: str = Field(min_length=36, max_length=36)
    application_id: str = Field(min_length=36, max_length=36)
    cloud: MicrosoftCloud
    credential_ref: CredentialReferenceV1
    consent_state: MicrosoftConsentState

    @field_validator("tenant_id", "application_id")
    @classmethod
    def normalize_guid(cls, value: str) -> str:
        if _GUID_PATTERN.fullmatch(value) is None:
            raise ValueError("Microsoft tenant/application IDs must be canonical GUID strings")
        return value.lower()

    @property
    def endpoints(self) -> MicrosoftCloudEndpoints:
        return microsoft_cloud_endpoints(self.cloud)


class MicrosoftConnectorReadinessV1(StrictMicrosoftModel):
    """Management-safe readiness result, separate from evidence verification state."""

    schema_version: Literal["ets.connector.microsoft.readiness.v1"]
    state: MicrosoftReadinessState
    code: MicrosoftReadinessCode
    tenant_id: str = Field(min_length=36, max_length=36)
    application_id: str = Field(min_length=36, max_length=36)
    cloud: MicrosoftCloud
    authority_root: str = Field(min_length=8, max_length=200)
    graph_root: str = Field(min_length=8, max_length=200)
    consent_state: MicrosoftConsentState
    credential_status: CredentialStatus | None = None
    message: str = Field(min_length=1, max_length=500)


class MicrosoftCredentialMetadataResolver(Protocol):
    """Read-only G2B boundary required for onboarding readiness."""

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1: ...


def microsoft_cloud_endpoints(cloud: MicrosoftCloud) -> MicrosoftCloudEndpoints:
    """Return the qualified authority roots for one explicit Microsoft cloud."""

    return _MICROSOFT_CLOUD_ENDPOINTS[cloud]


def assess_microsoft_tenant_readiness(
    profile: MicrosoftTenantProfileV1,
    credential_resolver: MicrosoftCredentialMetadataResolver,
) -> MicrosoftConnectorReadinessV1:
    """Classify onboarding readiness without resolving or returning reusable credential bytes."""

    consent_result = _consent_readiness(profile)
    if consent_result is not None:
        return consent_result

    try:
        metadata = credential_resolver.describe(profile.credential_ref)
    except CredentialProviderNotFoundError:
        return _readiness(
            profile,
            state="blocked",
            code="credential_provider_unavailable",
            credential_status=None,
            message="Microsoft connector credential provider is unavailable",
        )
    except CredentialProviderError:
        return _readiness(
            profile,
            state="degraded",
            code="credential_unavailable",
            credential_status="unavailable",
            message="Microsoft connector credential metadata is temporarily unavailable",
        )

    return _credential_readiness(profile, metadata.status)


def _consent_readiness(profile: MicrosoftTenantProfileV1) -> MicrosoftConnectorReadinessV1 | None:
    if profile.consent_state == "granted":
        return None
    mapping: dict[
        MicrosoftConsentState,
        tuple[MicrosoftReadinessState, MicrosoftReadinessCode, str],
    ] = {
        "pending": (
            "pending",
            "consent_pending",
            "Microsoft administrator consent is pending",
        ),
        "partial": (
            "blocked",
            "consent_partial",
            "Microsoft administrator consent is incomplete",
        ),
        "revoked": (
            "blocked",
            "consent_revoked",
            "Microsoft administrator consent was revoked",
        ),
        "failed": (
            "blocked",
            "consent_failed",
            "Microsoft administrator consent failed",
        ),
        "granted": (
            "ready",
            "ready",
            "Microsoft administrator consent is granted",
        ),
    }
    state, code, message = mapping[profile.consent_state]
    return _readiness(
        profile,
        state=state,
        code=code,
        credential_status=None,
        message=message,
    )


def _credential_readiness(
    profile: MicrosoftTenantProfileV1,
    status: CredentialStatus,
) -> MicrosoftConnectorReadinessV1:
    mapping: dict[
        CredentialStatus,
        tuple[MicrosoftReadinessState, MicrosoftReadinessCode, str],
    ] = {
        "available": (
            "ready",
            "ready",
            "Microsoft connector tenant, consent, and credential metadata are ready",
        ),
        "missing": (
            "blocked",
            "credential_missing",
            "Microsoft connector credential is missing",
        ),
        "expired": (
            "blocked",
            "credential_expired",
            "Microsoft connector credential is expired",
        ),
        "revoked": (
            "blocked",
            "credential_revoked",
            "Microsoft connector credential is revoked",
        ),
        "incompatible": (
            "blocked",
            "credential_incompatible",
            "Microsoft connector credential is incompatible with the configured provider",
        ),
        "unavailable": (
            "degraded",
            "credential_unavailable",
            "Microsoft connector credential is temporarily unavailable",
        ),
    }
    state, code, message = mapping[status]
    return _readiness(
        profile,
        state=state,
        code=code,
        credential_status=status,
        message=message,
    )


def _readiness(
    profile: MicrosoftTenantProfileV1,
    *,
    state: MicrosoftReadinessState,
    code: MicrosoftReadinessCode,
    credential_status: CredentialStatus | None,
    message: str,
) -> MicrosoftConnectorReadinessV1:
    endpoints = profile.endpoints
    return MicrosoftConnectorReadinessV1(
        schema_version=MICROSOFT_READINESS_SCHEMA_VERSION,
        state=state,
        code=code,
        tenant_id=profile.tenant_id,
        application_id=profile.application_id,
        cloud=profile.cloud,
        authority_root=endpoints.authority_root,
        graph_root=endpoints.graph_root,
        consent_state=profile.consent_state,
        credential_status=credential_status,
        message=message,
    )
