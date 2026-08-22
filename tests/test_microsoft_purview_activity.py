from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewActivityError,
    build_purview_content_list_url,
    parse_purview_discovery_page,
    purview_management_profile,
    validate_purview_content_uri,
    validate_purview_next_page_uri,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PUBLISHER_ID = "33333333-3333-3333-3333-333333333333"
CREATED = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)
EXPIRATION = CREATED + timedelta(days=7)


def _tenant(cloud: str = "global") -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": cloud,
            "credential_ref": CredentialReferenceV1(
                schema_version="ets.connector.credential_ref.v1",
                ref="fixture://microsoft/purview",
            ).model_dump(mode="json"),
            "consent_state": "granted",
        }
    )


def _profile():
    return purview_management_profile(
        "purview-prod",
        _tenant(),
        plan="enterprise",
        publisher_identifier=PUBLISHER_ID,
    )


def _descriptor(*, content_id: str = "content-001") -> dict[str, object]:
    profile = _profile()
    return {
        "contentType": "Audit.General",
        "contentId": content_id,
        "contentUri": (
            f"{profile.management_root}/api/v1.0/{TENANT_ID}/activity/feed/"
            f"audit/{content_id}"
        ),
        "contentCreated": CREATED.isoformat().replace("+00:00", "Z"),
        "contentExpiration": EXPIRATION.isoformat().replace("+00:00", "Z"),
    }


def test_purview_management_plan_is_server_owned_and_cloud_qualified() -> None:
    assert _profile().management_root == "https://manage.office.com"
    assert (
        purview_management_profile(
            "gcc-high",
            _tenant("us_government_l4"),
            plan="gcc_high",
            publisher_identifier=PUBLISHER_ID,
        ).management_root
        == "https://manage.office365.us"
    )
    assert (
        purview_management_profile(
            "dod",
            _tenant("us_government_l5_dod"),
            plan="dod",
            publisher_identifier=PUBLISHER_ID,
        ).management_root
        == "https://manage.protection.apps.mil"
    )

    with pytest.raises(ValueError, match="incompatible"):
        purview_management_profile(
            "wrong",
            _tenant("us_government_l4"),
            plan="enterprise",
            publisher_identifier=PUBLISHER_ID,
        )
    with pytest.raises(ValueError, match="unsupported for China"):
        purview_management_profile(
            "china",
            _tenant("china_21vianet"),
            plan="enterprise",
            publisher_identifier=PUBLISHER_ID,
        )


def test_purview_poll_url_binds_content_type_publisher_and_bounded_window() -> None:
    profile = _profile()
    start = datetime(2026, 8, 14, 0, 0, tzinfo=UTC)
    end = start + timedelta(hours=1)

    url = build_purview_content_list_url(
        profile,
        "Audit.General",
        start_time_utc=start,
        end_time_utc=end,
    )

    assert url.startswith(
        f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/subscriptions/content?"
    )
    assert "contentType=Audit.General" in url
    assert f"PublisherIdentifier={PUBLISHER_ID}" in url
    assert "startTime=2026-08-14T00%3A00%3A00Z" in url
    assert "endTime=2026-08-14T01%3A00%3A00Z" in url

    with pytest.raises(ValueError, match="24 hours"):
        build_purview_content_list_url(
            profile,
            "Audit.General",
            start_time_utc=start,
            end_time_utc=start + timedelta(hours=25),
        )


def test_purview_poll_discovery_dedupes_same_content_id_and_validates_pagination() -> None:
    profile = _profile()
    next_page = (
        f"{profile.management_root}/api/v1.0/{TENANT_ID}/activity/feed/"
        "subscriptions/content?contentType=Audit.General&PublisherIdentifier="
        f"{PUBLISHER_ID}&nextpage=opaque"
    )

    page = parse_purview_discovery_page(
        [_descriptor(), _descriptor()],
        profile,
        "Audit.General",
        discovery_source="poll",
        next_page_uri=next_page,
    )

    assert len(page.descriptors) == 1
    assert page.descriptors[0].content_id == "content-001"
    assert page.next_page_uri == next_page

    with pytest.raises(MicrosoftPurviewActivityError, match="approved content type"):
        validate_purview_next_page_uri(
            profile,
            "Audit.General",
            next_page.replace("Audit.General", "Audit.Exchange"),
        )


def test_purview_webhook_is_discovery_only_and_requires_profile_tenant_and_client() -> None:
    profile = _profile()
    notification = {
        **_descriptor(),
        "tenantId": TENANT_ID,
        "clientId": APPLICATION_ID,
    }

    page = parse_purview_discovery_page(
        [notification],
        profile,
        "Audit.General",
        discovery_source="webhook",
    )

    assert page.discovery_source == "webhook"
    assert page.next_page_uri is None
    assert page.descriptors[0].discovery_source == "webhook"

    with pytest.raises(MicrosoftPurviewActivityError, match="tenantId"):
        parse_purview_discovery_page(
            [{**notification, "tenantId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}],
            profile,
            "Audit.General",
            discovery_source="webhook",
        )
    with pytest.raises(MicrosoftPurviewActivityError, match="clientId"):
        parse_purview_discovery_page(
            [{**notification, "clientId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}],
            profile,
            "Audit.General",
            discovery_source="webhook",
        )


def test_purview_cross_origin_content_uri_is_rejected_before_retrieval() -> None:
    profile = _profile()
    good = _descriptor()["contentUri"]
    assert isinstance(good, str)
    assert validate_purview_content_uri(profile, good) == (
        f"{good}?PublisherIdentifier={PUBLISHER_ID}"
    )

    with pytest.raises(MicrosoftPurviewActivityError, match="management origin"):
        validate_purview_content_uri(
            profile,
            f"https://evil.example/api/v1.0/{TENANT_ID}/activity/feed/audit/content-001",
        )
    with pytest.raises(MicrosoftPurviewActivityError, match="audit-content path"):
        validate_purview_content_uri(
            profile,
            f"{profile.management_root}/api/v1.0/{TENANT_ID}/activity/feed/subscriptions/content",
        )
    with pytest.raises(MicrosoftPurviewActivityError, match="unsupported query"):
        validate_purview_content_uri(profile, f"{good}?PublisherIdentifier=attacker")


def test_purview_same_content_id_with_changed_descriptor_fails_closed() -> None:
    profile = _profile()
    first = _descriptor()
    second = {
        **first,
        "contentExpiration": (EXPIRATION + timedelta(hours=1)).isoformat().replace(
            "+00:00",
            "Z",
        ),
    }

    with pytest.raises(MicrosoftPurviewActivityError, match="conflicting immutable"):
        parse_purview_discovery_page(
            [first, second],
            profile,
            "Audit.General",
            discovery_source="poll",
        )
