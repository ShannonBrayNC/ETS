from __future__ import annotations

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaError,
    sharepoint_drive_delta_request_profile,
    sharepoint_list_delta_request_profile,
    validate_sharepoint_delta_url,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=TENANT_ID,
        application_id=APPLICATION_ID,
        cloud="global",
        credential_ref=CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref="env://MICROSOFT_GRAPH_TOKEN",
        ),
        consent_state="granted",
    )


def test_documented_canonical_drive_delta_function_continuation_is_accepted() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")
    continuation = (
        "https://graph.microsoft.com/v1.0/drives/drive-001/"
        "delta(token='opaque-source-state')"
    )

    assert validate_sharepoint_delta_url(profile, continuation) == continuation


def test_canonical_drive_delta_query_continuation_is_accepted() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")
    continuation = (
        "https://graph.microsoft.com/v1.0/drives/drive-001/"
        "delta?token=opaque-source-state"
    )

    assert validate_sharepoint_delta_url(profile, continuation) == continuation


def test_canonical_drive_delta_cannot_escape_the_approved_drive() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")

    for continuation in (
        "https://graph.microsoft.com/v1.0/drives/other/delta(token='opaque')",
        "https://graph.microsoft.com/v1.0/drives/drive-001/delta(token='opaque')/children",
        "https://evil.example/v1.0/drives/drive-001/delta(token='opaque')",
    ):
        with pytest.raises(MicrosoftSharePointDeltaError):
            validate_sharepoint_delta_url(profile, continuation)


def test_list_delta_does_not_gain_drive_root_canonicalization() -> None:
    profile = sharepoint_list_delta_request_profile(
        "tenant-prod",
        _tenant(),
        "site-001",
        "list-001",
    )
    continuation = "https://graph.microsoft.com/v1.0/sites/site-001/lists/list-001/delta"

    with pytest.raises(MicrosoftSharePointDeltaError):
        validate_sharepoint_delta_url(profile, continuation)
