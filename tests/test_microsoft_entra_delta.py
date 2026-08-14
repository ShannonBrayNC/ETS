from __future__ import annotations

import json

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_entra_delta import (
    MicrosoftEntraDeltaError,
    entra_delta_request_profile,
    parse_entra_delta_page,
    validate_entra_delta_cursor_url,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"


def _tenant_profile(*, cloud: str = "global") -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": cloud,
            "credential_ref": CredentialReferenceV1(
                schema_version="ets.connector.credential_ref.v1",
                ref="fixture://microsoft/entra-delta",
            ).model_dump(mode="json"),
            "consent_state": "granted",
        }
    )


def _page(
    *,
    records: list[dict[str, object]],
    next_link: str | None = None,
    delta_link: str | None = None,
) -> bytes:
    body: dict[str, object] = {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
        "value": records,
    }
    if next_link is not None:
        body["@odata.nextLink"] = next_link
    if delta_link is not None:
        body["@odata.deltaLink"] = delta_link
    return json.dumps(body).encode("utf-8")


def test_users_delta_preserves_exact_next_link_and_minimizes_identity_fields() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    request_url = profile.initial_url + "?$select=id,accountEnabled,userType"
    next_link = (
        "https://graph.microsoft.com/v1.0/users/delta?"
        "$skiptoken=opaque-source-token&$select=id,accountEnabled,userType"
    )
    payload = _page(
        records=[
            {
                "id": "user-001",
                "displayName": "Alice Example",
                "userPrincipalName": "alice@example.test",
                "mail": "alice@example.test",
                "accountEnabled": True,
                "userType": "Member",
                "raw_marker": "RAW-ENTRA-MARKER",
            }
        ],
        next_link=next_link,
    )

    page = parse_entra_delta_page(
        payload,
        profile=profile,
        request_url=request_url,
    )

    assert page.cycle_complete is False
    assert page.checkpoint_url == next_link
    assert page.next_link == next_link
    assert len(page.records) == 1
    record = page.records[0]
    assert record.object_id == "user-001"
    assert record.metadata == {
        "object_type": "user",
        "account_enabled": True,
        "user_type": "Member",
    }
    serialized = json.dumps(record.model_dump(mode="json"))
    assert "Alice Example" not in serialized
    assert "alice@example.test" not in serialized
    assert "RAW-ENTRA-MARKER" not in serialized


def test_terminal_delta_link_marks_cycle_complete_and_is_preserved_exactly() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "groups")
    delta_link = "https://graph.microsoft.com/v1.0/groups/delta?$deltatoken=opaque-final-token"

    page = parse_entra_delta_page(
        _page(
            records=[
                {
                    "id": "group-001",
                    "mailEnabled": False,
                    "securityEnabled": True,
                    "groupTypes": ["Unified"],
                }
            ],
            delta_link=delta_link,
        ),
        profile=profile,
        request_url=profile.initial_url,
    )

    assert page.cycle_complete is True
    assert page.delta_link == delta_link
    assert page.checkpoint_url == delta_link
    assert page.records[0].metadata == {
        "object_type": "group",
        "mail_enabled": False,
        "security_enabled": True,
        "group_types": ["Unified"],
    }


def test_removed_changed_and_deleted_reasons_are_preserved_explicitly() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    delta_link = "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=done"

    page = parse_entra_delta_page(
        _page(
            records=[
                {"id": "user-restorable", "@removed": {"reason": "changed"}},
                {"id": "user-deleted", "@removed": {"reason": "deleted"}},
            ],
            delta_link=delta_link,
        ),
        profile=profile,
        request_url=profile.initial_url,
    )

    assert [record.removed_reason for record in page.records] == ["changed", "deleted"]


def test_same_entity_can_appear_multiple_times_without_being_collapsed_by_parser() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    next_link = "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=next"

    page = parse_entra_delta_page(
        _page(
            records=[
                {"id": "user-001", "accountEnabled": True},
                {"id": "user-001", "accountEnabled": False},
            ],
            next_link=next_link,
        ),
        profile=profile,
        request_url=profile.initial_url,
    )

    assert len(page.records) == 2
    assert page.records[0].object_id == page.records[1].object_id
    assert page.records[0].source_record_id != page.records[1].source_record_id


def test_retrying_same_page_produces_same_record_identity() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    request_url = "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=current"
    next_link = "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=next"
    payload = _page(records=[{"id": "user-001", "accountEnabled": True}], next_link=next_link)

    first = parse_entra_delta_page(payload, profile=profile, request_url=request_url)
    retry = parse_entra_delta_page(payload, profile=profile, request_url=request_url)

    assert first.records[0].source_record_id == retry.records[0].source_record_id
    assert first.records[0].source_record_id.startswith("entra-delta:")


def test_cursor_cannot_cross_cloud_host_or_collection_path() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")

    with pytest.raises(MicrosoftEntraDeltaError, match="qualified Graph origin"):
        validate_entra_delta_cursor_url(
            profile,
            "https://attacker.invalid/v1.0/users/delta?$skiptoken=stolen",
        )
    with pytest.raises(MicrosoftEntraDeltaError, match="qualified collection path"):
        validate_entra_delta_cursor_url(
            profile,
            "https://graph.microsoft.com/v1.0/groups/delta?$skiptoken=wrong-collection",
        )


def test_national_cloud_cursor_must_stay_in_qualified_cloud() -> None:
    profile = entra_delta_request_profile(_tenant_profile(cloud="us_government_l4"), "users")
    cursor = "https://graph.microsoft.us/v1.0/users/delta?$deltatoken=gov-token"

    assert validate_entra_delta_cursor_url(profile, cursor) == cursor
    with pytest.raises(MicrosoftEntraDeltaError, match="qualified Graph origin"):
        validate_entra_delta_cursor_url(
            profile,
            "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=wrong-cloud",
        )


def test_response_requires_exactly_one_source_state_link() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    next_link = "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=next"
    delta_link = "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=done"

    with pytest.raises(MicrosoftEntraDeltaError, match="exactly one"):
        parse_entra_delta_page(
            _page(records=[], next_link=None, delta_link=None),
            profile=profile,
            request_url=profile.initial_url,
        )
    with pytest.raises(MicrosoftEntraDeltaError, match="exactly one"):
        parse_entra_delta_page(
            _page(records=[], next_link=next_link, delta_link=delta_link),
            profile=profile,
            request_url=profile.initial_url,
        )


def test_body_record_and_removed_reason_bounds_fail_closed() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    next_link = "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=next"
    payload = _page(records=[{"id": "user-001"}], next_link=next_link)

    with pytest.raises(MicrosoftEntraDeltaError, match="body exceeds"):
        parse_entra_delta_page(
            payload,
            profile=profile,
            request_url=profile.initial_url,
            maximum_body_bytes=len(payload) - 1,
        )
    with pytest.raises(MicrosoftEntraDeltaError, match="record limit"):
        parse_entra_delta_page(
            _page(records=[{"id": "one"}, {"id": "two"}], next_link=next_link),
            profile=profile,
            request_url=profile.initial_url,
            maximum_records=1,
        )
    with pytest.raises(MicrosoftEntraDeltaError, match="removed reason"):
        parse_entra_delta_page(
            _page(
                records=[{"id": "user-001", "@removed": {"reason": "future-reason"}}],
                next_link=next_link,
            ),
            profile=profile,
            request_url=profile.initial_url,
        )
