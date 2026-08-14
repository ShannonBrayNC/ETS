from __future__ import annotations

import json

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaError,
    parse_sharepoint_delta_page,
    sharepoint_drive_delta_request_profile,
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


def _profile():
    return sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")


def _body(item: dict[str, object]) -> bytes:
    return json.dumps(
        {
            "value": [item],
            "@odata.deltaLink": (
                "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta"
                "?$deltatoken=sharing-state"
            ),
        }
    ).encode("utf-8")


def test_shared_facet_is_allow_listed_without_actor_identity() -> None:
    page = parse_sharepoint_delta_page(
        _body(
            {
                "id": "item-001",
                "name": "shared.docx",
                "shared": {
                    "scope": "users",
                    "sharedDateTime": "2026-08-14T20:00:00Z",
                    "owner": {
                        "user": {
                            "displayName": "Private Owner",
                            "email": "owner@example.test",
                        }
                    },
                    "sharedBy": {
                        "user": {
                            "displayName": "Private Sharer",
                            "email": "sharer@example.test",
                        }
                    },
                },
                "@microsoft.graph.sharedChanged": "True",
            }
        ),
        _profile(),
    )

    metadata = page.records[0].metadata
    assert metadata["shared"] == {
        "scope": "users",
        "shared_at_utc": "2026-08-14T20:00:00Z",
    }
    assert metadata["sharing_changed"] is True
    serialized = json.dumps(metadata, sort_keys=True)
    assert "Private Owner" not in serialized
    assert "Private Sharer" not in serialized
    assert "owner@example.test" not in serialized
    assert "sharer@example.test" not in serialized
    assert "sharedBy" not in serialized
    assert "owner" not in serialized


def test_empty_shared_facet_is_preserved_as_observed_state() -> None:
    page = parse_sharepoint_delta_page(
        _body(
            {
                "id": "item-002",
                "shared": {},
                "@microsoft.graph.sharedChanged": "False",
            }
        ),
        _profile(),
    )

    assert page.records[0].metadata["shared"] == {}
    assert page.records[0].metadata["sharing_changed"] is False


@pytest.mark.parametrize(
    ("shared", "shared_changed"),
    [
        ({"scope": "public-internet"}, None),
        ({"sharedDateTime": "not-a-date"}, None),
        ("not-an-object", None),
        ({}, "yes"),
    ],
)
def test_invalid_sharing_metadata_fails_closed(
    shared: object,
    shared_changed: object,
) -> None:
    item: dict[str, object] = {"id": "item-invalid", "shared": shared}
    if shared_changed is not None:
        item["@microsoft.graph.sharedChanged"] = shared_changed

    with pytest.raises(MicrosoftSharePointDeltaError):
        parse_sharepoint_delta_page(_body(item), _profile())
