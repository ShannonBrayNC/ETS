from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaError,
    parse_sharepoint_delta_page,
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


def _drive_page(profile: object, value: list[dict[str, object]]) -> bytes:
    initial_url = getattr(profile, "initial_url")
    return json.dumps(
        {
            "value": value,
            "@odata.nextLink": initial_url + "?$skiptoken=page-two",
        }
    ).encode("utf-8")


def test_drive_profile_is_server_owned_and_continuation_stays_on_approved_path() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")

    assert profile.initial_url == "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta"
    next_link = profile.initial_url + "?$skiptoken=opaque-source-state"
    assert validate_sharepoint_delta_url(profile, next_link) == next_link

    with pytest.raises(MicrosoftSharePointDeltaError):
        validate_sharepoint_delta_url(
            profile,
            "https://evil.example/v1.0/drives/drive-001/root/delta?$skiptoken=opaque",
        )
    with pytest.raises(MicrosoftSharePointDeltaError):
        validate_sharepoint_delta_url(
            profile,
            "https://graph.microsoft.com/v1.0/drives/other/root/delta?$skiptoken=opaque",
        )
    with pytest.raises(MicrosoftSharePointDeltaError):
        validate_sharepoint_delta_url(profile, "https://graph.microsoft.com/" + "x" * 4000)


def test_list_profile_is_server_owned() -> None:
    profile = sharepoint_list_delta_request_profile(
        "tenant-prod",
        _tenant(),
        "site-001",
        "list-001",
    )

    assert profile.initial_url == (
        "https://graph.microsoft.com/v1.0/sites/site-001/lists/list-001/items/delta"
    )


def test_delta_page_minimizes_metadata_and_excludes_content_and_actor_fields() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")
    body = json.dumps(
        {
            "value": [
                {
                    "id": "item-001",
                    "name": "report.docx",
                    "size": 1234,
                    "eTag": "etag-value",
                    "cTag": "ctag-value",
                    "createdDateTime": "2026-08-14T18:00:00Z",
                    "lastModifiedDateTime": "2026-08-14T18:30:00Z",
                    "parentReference": {
                        "id": "folder-001",
                        "driveId": "drive-001",
                        "path": "/drive/root:/Reports",
                        "shareId": "must-not-copy",
                    },
                    "file": {
                        "mimeType": (
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),
                        "hashes": {
                            "crc32Hash": "A1B2C3D4",
                            "quickXorHash": "quick-source-fingerprint",
                            "sha1Hash": "sha1-source-fingerprint",
                            "sha256Hash": "unsupported-must-not-copy",
                            "futureHash": "unknown-must-not-copy",
                        },
                    },
                    "webUrl": "https://contoso.sharepoint.com/raw-location",
                    "@microsoft.graph.downloadUrl": "https://download.example/secret",
                    "createdBy": {"user": {"displayName": "Alice"}},
                    "lastModifiedBy": {"user": {"displayName": "Bob"}},
                    "content": "RAW-FILE-CONTENT-MUST-NOT-COPY",
                }
            ],
            "@odata.nextLink": profile.initial_url + "?$skiptoken=page-two",
        }
    ).encode("utf-8")

    page = parse_sharepoint_delta_page(body, profile)

    assert page.cycle_complete is False
    assert len(page.records) == 1
    record = page.records[0]
    assert record.object_id == "item-001"
    assert record.deleted is False
    assert record.source_modified_at_utc == datetime(2026, 8, 14, 18, 30, tzinfo=UTC)
    assert record.metadata["name"] == "report.docx"
    assert record.metadata["size"] == 1234
    assert record.metadata["parent"] == {
        "id": "folder-001",
        "drive_id": "drive-001",
        "path": "/drive/root:/Reports",
    }
    assert record.metadata["file"] == {
        "mime_type": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        "hashes": {
            "crc32_hash": "A1B2C3D4",
            "quick_xor_hash": "quick-source-fingerprint",
            "sha1_hash": "sha1-source-fingerprint",
        },
    }
    serialized = json.dumps(record.metadata, sort_keys=True)
    for forbidden in (
        "RAW-FILE-CONTENT-MUST-NOT-COPY",
        "download.example",
        "contoso.sharepoint.com",
        "Alice",
        "Bob",
        "unsupported-must-not-copy",
        "unknown-must-not-copy",
        "sha256Hash",
        "futureHash",
    ):
        assert forbidden not in serialized


def test_source_hash_change_changes_observation_fingerprint() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")
    page = parse_sharepoint_delta_page(
        _drive_page(
            profile,
            [
                {
                    "id": "item-001",
                    "name": "same.txt",
                    "file": {"hashes": {"quickXorHash": "fingerprint-one"}},
                },
                {
                    "id": "item-001",
                    "name": "same.txt",
                    "file": {"hashes": {"quickXorHash": "fingerprint-two"}},
                },
            ],
        ),
        profile,
    )

    assert page.records[0].source_record_id != page.records[1].source_record_id


def test_file_hashes_fail_closed_when_malformed_or_unbounded() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")

    with pytest.raises(MicrosoftSharePointDeltaError, match="file hashes facet"):
        parse_sharepoint_delta_page(
            _drive_page(profile, [{"id": "item-001", "file": {"hashes": "invalid"}}]),
            profile,
        )

    with pytest.raises(MicrosoftSharePointDeltaError, match="quickXorHash"):
        parse_sharepoint_delta_page(
            _drive_page(
                profile,
                [
                    {
                        "id": "item-001",
                        "file": {"hashes": {"quickXorHash": "x" * 1025}},
                    }
                ],
            ),
            profile,
        )


def test_deleted_and_repeated_latest_state_records_remain_explicit_observations() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")
    delta_link = profile.initial_url + "?$deltatoken=cycle-complete"
    body = json.dumps(
        {
            "value": [
                {"id": "item-001", "name": "same.txt"},
                {"id": "item-001", "name": "same.txt"},
                {"id": "item-002", "deleted": {}},
            ],
            "@odata.deltaLink": delta_link,
        }
    ).encode("utf-8")

    page = parse_sharepoint_delta_page(body, profile)

    assert page.cycle_complete is True
    assert page.checkpoint_url == delta_link
    assert page.records[0].source_record_id == page.records[1].source_record_id
    assert page.records[2].deleted is True
    assert page.records[2].metadata["deleted"] is True


def test_delta_page_rejects_ambiguous_or_unbounded_source_state() -> None:
    profile = sharepoint_drive_delta_request_profile("tenant-prod", _tenant(), "drive-001")
    value = [{"id": "item-001"}]

    with pytest.raises(MicrosoftSharePointDeltaError):
        parse_sharepoint_delta_page(
            json.dumps(
                {
                    "value": value,
                    "@odata.nextLink": profile.initial_url + "?$skiptoken=one",
                    "@odata.deltaLink": profile.initial_url + "?$deltatoken=two",
                }
            ).encode("utf-8"),
            profile,
        )

    with pytest.raises(MicrosoftSharePointDeltaError):
        parse_sharepoint_delta_page(
            json.dumps({"value": value}).encode("utf-8"),
            profile,
        )

    with pytest.raises(MicrosoftSharePointDeltaError):
        parse_sharepoint_delta_page(b"{}", profile)