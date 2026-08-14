from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewContentDescriptorV1,
    purview_management_profile,
)
from ets.connectors.enterprise.microsoft_purview_audit import (
    MicrosoftPurviewAuditError,
    parse_purview_audit_content,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PUBLISHER_ID = "33333333-3333-3333-3333-333333333333"
RECORD_ID = "44444444-4444-4444-4444-444444444444"
CREATED = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)
EXPIRATION = CREATED + timedelta(days=7)
EVENT_TIME = datetime(2026, 8, 14, 19, 57, 30, tzinfo=UTC)


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": "global",
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


def _descriptor() -> MicrosoftPurviewContentDescriptorV1:
    return MicrosoftPurviewContentDescriptorV1(
        content_type="Audit.General",
        content_id="content-001",
        content_uri=(
            f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/"
            "audit/content-001"
        ),
        content_created_utc=CREATED,
        content_expiration_utc=EXPIRATION,
        discovery_source="poll",
    )


def _record(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "Id": RECORD_ID,
        "RecordType": 1,
        "CreationTime": EVENT_TIME.isoformat().replace("+00:00", "Z"),
        "Operation": "FileAccessed",
        "OrganizationId": TENANT_ID,
        "UserType": 0,
        "UserKey": "user-key-001",
        "Workload": "SharePoint",
        "UserId": "alice@example.test",
        "ResultStatus": "Succeeded",
        "ObjectId": "https://contoso.sharepoint.com/sites/a/report.docx",
        "ClientIP": "192.0.2.10",
        "Scope": 0,
        "Version": 1,
        "SiteUrl": "https://contoso.sharepoint.com/sites/a",
        "SourceFileName": "report.docx",
        "RAW_SECRET": "RAW-PURVIEW-MARKER-MUST-NOT-CROSS",
    }
    value.update(updates)
    return value


def test_purview_common_schema_preserves_required_claims_and_source_time() -> None:
    body = json.dumps([_record()]).encode("utf-8")

    content = parse_purview_audit_content(
        body,
        _descriptor(),
        _profile(),
        service_specific_allowlist=frozenset({"SiteUrl", "SourceFileName"}),
    )

    assert content.content_sha256 == hashlib.sha256(body).hexdigest()
    assert content.content_id == "content-001"
    assert len(content.records) == 1
    record = content.records[0]
    assert record.source_record_id == RECORD_ID
    assert record.creation_time_utc == EVENT_TIME
    assert record.operation == "FileAccessed"
    assert record.workload == "SharePoint"
    assert record.user_id == "alice@example.test"
    assert record.client_ip is None
    assert record.service_specific == {
        "SiteUrl": "https://contoso.sharepoint.com/sites/a",
        "SourceFileName": "report.docx",
    }
    assert "RAW_SECRET" not in record.service_specific


def test_purview_client_ip_is_opt_in_and_unknown_fields_do_not_cross_by_default() -> None:
    body = json.dumps([_record()]).encode("utf-8")

    default = parse_purview_audit_content(body, _descriptor(), _profile())
    with_ip = parse_purview_audit_content(
        body,
        _descriptor(),
        _profile(),
        include_client_ip=True,
    )

    assert default.records[0].client_ip is None
    assert default.records[0].service_specific == {}
    assert with_ip.records[0].client_ip == "192.0.2.10"


def test_purview_organization_id_must_match_server_owned_tenant() -> None:
    body = json.dumps(
        [_record(OrganizationId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")]
    ).encode("utf-8")

    with pytest.raises(MicrosoftPurviewAuditError, match="server-owned tenant"):
        parse_purview_audit_content(body, _descriptor(), _profile())


def test_purview_duplicate_record_id_dedupes_identical_and_rejects_conflict() -> None:
    same = _record()
    content = parse_purview_audit_content(
        json.dumps([same, same]).encode("utf-8"),
        _descriptor(),
        _profile(),
    )
    assert len(content.records) == 1

    with pytest.raises(MicrosoftPurviewAuditError, match="conflicting normalized"):
        parse_purview_audit_content(
            json.dumps([same, _record(Operation="FileDeleted")]).encode("utf-8"),
            _descriptor(),
            _profile(),
        )


def test_purview_audit_requires_mandatory_common_schema_fields() -> None:
    missing_operation = _record()
    del missing_operation["Operation"]

    with pytest.raises(MicrosoftPurviewAuditError, match="Operation"):
        parse_purview_audit_content(
            json.dumps([missing_operation]).encode("utf-8"),
            _descriptor(),
            _profile(),
        )


def test_purview_service_specific_allowlist_is_bounded_and_raw_blob_not_retained() -> None:
    raw_marker = "RAW-PURVIEW-CONTENT-MARKER"
    body = json.dumps([_record(RAW_SECRET=raw_marker)]).encode("utf-8")
    content = parse_purview_audit_content(
        body,
        _descriptor(),
        _profile(),
        service_specific_allowlist=frozenset({"SourceFileName"}),
    )

    serialized = repr(content)
    assert raw_marker not in serialized
    assert content.records[0].service_specific == {"SourceFileName": "report.docx"}

    with pytest.raises(ValueError, match="field bound"):
        parse_purview_audit_content(
            body,
            _descriptor(),
            _profile(),
            service_specific_allowlist=frozenset(f"Field{index}" for index in range(33)),
        )
