from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
    CredentialStatus,
)
from ets.connectors.credentials.provider import (
    CredentialProviderError,
    CredentialProviderNotFoundError,
)
from ets.connectors.enterprise.microsoft import (
    MicrosoftTenantProfileV1,
    assess_microsoft_tenant_readiness,
    microsoft_cloud_endpoints,
)

TENANT_ID = "11111111-1111-4111-8111-111111111111"
APPLICATION_ID = "22222222-2222-4222-8222-222222222222"
CREDENTIAL_REF = CredentialReferenceV1(
    schema_version="ets.connector.credential_ref.v1",
    ref="fixture://microsoft/tenant-credential",
)
NOW = datetime(2026, 8, 14, 5, 30, tzinfo=UTC)


class FixtureMetadataResolver:
    def __init__(
        self,
        *,
        status: CredentialStatus = "available",
        error: Exception | None = None,
    ) -> None:
        self.status = status
        self.error = error
        self.describe_count = 0

    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        self.describe_count += 1
        if self.error is not None:
            raise self.error
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status=self.status,
            version="1",
            updated_at_utc=NOW,
        )


def _profile(
    *,
    cloud: str = "global",
    consent_state: str = "granted",
) -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": cloud,
            "credential_ref": CREDENTIAL_REF.model_dump(mode="json"),
            "consent_state": consent_state,
        }
    )


def test_cloud_endpoint_map_is_server_owned_and_explicit() -> None:
    assert microsoft_cloud_endpoints("global").graph_root == "https://graph.microsoft.com"
    assert (
        microsoft_cloud_endpoints("us_government_l4").graph_root
        == "https://graph.microsoft.us"
    )
    assert (
        microsoft_cloud_endpoints("us_government_l5_dod").graph_root
        == "https://dod-graph.microsoft.us"
    )
    china = microsoft_cloud_endpoints("china_21vianet")
    assert china.authority_root == "https://login.partner.microsoftonline.cn"
    assert china.graph_root == "https://microsoftgraph.chinacloudapi.cn"


def test_profile_rejects_customer_endpoint_overrides_and_invalid_clouds() -> None:
    with pytest.raises(ValidationError):
        MicrosoftTenantProfileV1.model_validate(
            {
                **_profile().model_dump(mode="json"),
                "graph_root": "https://attacker.invalid",
            }
        )
    with pytest.raises(ValidationError):
        _profile(cloud="customer_cloud")


def test_profile_requires_canonical_tenant_and_application_guids() -> None:
    payload = _profile().model_dump(mode="json")
    payload["tenant_id"] = "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"
    with pytest.raises(ValidationError, match="canonical GUID"):
        MicrosoftTenantProfileV1.model_validate(payload)


def test_granted_consent_and_available_credential_are_ready_without_secret_disclosure() -> None:
    resolver = FixtureMetadataResolver(status="available")

    result = assess_microsoft_tenant_readiness(_profile(), resolver)
    serialized = str(result.model_dump(mode="json"))

    assert result.state == "ready"
    assert result.code == "ready"
    assert result.credential_status == "available"
    assert result.graph_root == "https://graph.microsoft.com"
    assert resolver.describe_count == 1
    assert "fixture://microsoft/tenant-credential" not in serialized
    assert "credential_ref" not in serialized


@pytest.mark.parametrize(
    ("consent_state", "expected_state", "expected_code"),
    [
        ("pending", "pending", "consent_pending"),
        ("partial", "blocked", "consent_partial"),
        ("revoked", "blocked", "consent_revoked"),
        ("failed", "blocked", "consent_failed"),
    ],
)
def test_non_granted_consent_blocks_before_credential_provider_access(
    consent_state: str,
    expected_state: str,
    expected_code: str,
) -> None:
    resolver = FixtureMetadataResolver()

    result = assess_microsoft_tenant_readiness(
        _profile(consent_state=consent_state),
        resolver,
    )

    assert result.state == expected_state
    assert result.code == expected_code
    assert result.credential_status is None
    assert resolver.describe_count == 0


@pytest.mark.parametrize(
    ("status", "expected_state", "expected_code"),
    [
        ("missing", "blocked", "credential_missing"),
        ("expired", "blocked", "credential_expired"),
        ("revoked", "blocked", "credential_revoked"),
        ("incompatible", "blocked", "credential_incompatible"),
        ("unavailable", "degraded", "credential_unavailable"),
    ],
)
def test_credential_metadata_states_are_classified_without_resolving_material(
    status: CredentialStatus,
    expected_state: str,
    expected_code: str,
) -> None:
    resolver = FixtureMetadataResolver(status=status)

    result = assess_microsoft_tenant_readiness(_profile(), resolver)

    assert result.state == expected_state
    assert result.code == expected_code
    assert result.credential_status == status
    assert resolver.describe_count == 1


def test_missing_credential_provider_is_distinct_from_source_auth_failure() -> None:
    resolver = FixtureMetadataResolver(
        error=CredentialProviderNotFoundError("fixture details must not surface"),
    )

    result = assess_microsoft_tenant_readiness(_profile(), resolver)

    assert result.state == "blocked"
    assert result.code == "credential_provider_unavailable"
    assert "fixture details" not in result.message


def test_credential_provider_operational_failure_is_degraded_and_sanitized() -> None:
    resolver = FixtureMetadataResolver(
        error=CredentialProviderError("provider failed around secret://do-not-disclose"),
    )

    result = assess_microsoft_tenant_readiness(_profile(), resolver)

    assert result.state == "degraded"
    assert result.code == "credential_unavailable"
    assert result.credential_status == "unavailable"
    assert "secret://do-not-disclose" not in result.message
