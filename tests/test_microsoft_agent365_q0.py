from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.connectors.enterprise.microsoft_agent365 import (
    MicrosoftAgent365SourceError,
    agent365_package_detail_url,
    agent365_packages_url,
    build_source_envelope,
    parse_agent365_inventory_response,
    parse_agent365_package_detail,
)

TENANT_ID = "11111111-2222-3333-4444-555555555555"


def _inventory_payload() -> bytes:
    return json.dumps(
        {
            "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#copilot/admin/catalog/packages",
            "value": [
                {
                    "id": "pkg-001",
                    "displayName": "Contoso Sales Agent",
                    "type": "custom",
                    "shortDescription": "Sales support",
                    "isBlocked": False,
                    "supportedHosts": ["Copilot", "Teams"],
                    "lastModifiedDateTime": "2026-09-16T10:00:00Z",
                    "publisher": "Contoso",
                    "availableTo": "all",
                    "deployedTo": "some",
                    "elementTypes": ["declarativeAgent"],
                    "platform": "Copilot Studio",
                    "version": "1.2.3",
                    "manifestVersion": "2.0",
                    "manifestId": "contoso-sales-agent",
                    "appId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "assetId": "asset-00042",
                    "futureMicrosoftField": {"preserve": True},
                }
            ],
        },
        separators=(",", ":"),
    ).encode()


def test_documented_agent365_package_urls_are_server_owned() -> None:
    assert (
        agent365_packages_url()
        == "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages"
    )
    assert (
        agent365_package_detail_url("pkg-001")
        == "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages/pkg-001"
    )
    assert (
        agent365_packages_url(api_version="beta")
        == "https://graph.microsoft.com/beta/copilot/admin/catalog/packages"
    )

    with pytest.raises(ValueError):
        agent365_package_detail_url("../escape")
    with pytest.raises(ValueError):
        agent365_package_detail_url("pkg?select=secret")


def test_inventory_parser_normalizes_known_fields_and_surfaces_schema_drift() -> None:
    page = parse_agent365_inventory_response(_inventory_payload())

    assert len(page.packages) == 1
    package = page.packages[0]
    assert package.package_id == "pkg-001"
    assert package.display_name == "Contoso Sales Agent"
    assert package.supported_hosts == ("Copilot", "Teams")
    assert package.element_types == ("declarativeAgent",)
    assert package.last_modified_date_time == datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    assert package.unknown_field_names == ("futureMicrosoftField",)
    assert len(package.source_record_sha256) == 64
    assert len(package.normalized_configuration_sha256) == 64


def test_source_envelope_hashes_exact_microsoft_bytes_before_interpretation() -> None:
    payload = _inventory_payload()
    envelope = build_source_envelope(
        payload,
        source_type="agent365.package_inventory",
        tenant_id=TENANT_ID.upper(),
        acquisition_time=datetime(2026, 9, 16, 15, 0, tzinfo=UTC),
        api_version="v1.0",
        api_maturity="documented_preview",
        request_path="/v1.0/copilot/admin/catalog/packages",
        collector_identity="ets-agent365-q0",
        collector_version="0.1.0",
        acquisition_sequence=7,
    )

    assert envelope.tenant_id == TENANT_ID
    assert envelope.raw_payload_utf8 == payload.decode()
    assert envelope.raw_payload_sha256 == hashlib.sha256(payload).hexdigest()
    assert envelope.payload_retention == "inline"
    assert envelope.envelope_hash != envelope.raw_payload_sha256


def test_envelope_chain_changes_when_predecessor_changes() -> None:
    payload = _inventory_payload()
    common = dict(
        payload=payload,
        source_type="agent365.package_inventory",
        tenant_id=TENANT_ID,
        acquisition_time=datetime(2026, 9, 16, 15, 0, tzinfo=UTC),
        api_version="v1.0",
        api_maturity="documented_preview",
        request_path="/v1.0/copilot/admin/catalog/packages",
        collector_identity="ets-agent365-q0",
        collector_version="0.1.0",
        acquisition_sequence=8,
    )
    first = build_source_envelope(**common, previous_envelope_hash="0" * 64)
    second = build_source_envelope(**common, previous_envelope_hash="1" * 64)

    assert first.raw_payload_sha256 == second.raw_payload_sha256
    assert first.envelope_hash != second.envelope_hash


def test_payload_retention_modes_do_not_confuse_hash_with_content_custody() -> None:
    payload = _inventory_payload()
    protected = build_source_envelope(
        payload,
        source_type="agent365.package_inventory",
        tenant_id=TENANT_ID,
        acquisition_time=datetime(2026, 9, 16, 15, 0, tzinfo=UTC),
        api_version="v1.0",
        api_maturity="documented_preview",
        request_path="/v1.0/copilot/admin/catalog/packages",
        collector_identity="ets-agent365-q0",
        collector_version="0.1.0",
        acquisition_sequence=9,
        payload_retention="protected_reference",
        protected_payload_reference="vault://agent365/acquisition/9",
    )
    digest_only = build_source_envelope(
        payload,
        source_type="agent365.package_inventory",
        tenant_id=TENANT_ID,
        acquisition_time=datetime(2026, 9, 16, 15, 1, tzinfo=UTC),
        api_version="v1.0",
        api_maturity="documented_preview",
        request_path="/v1.0/copilot/admin/catalog/packages",
        collector_identity="ets-agent365-q0",
        collector_version="0.1.0",
        acquisition_sequence=10,
        payload_retention="digest_only",
    )

    assert protected.raw_payload_utf8 is None
    assert protected.protected_payload_reference == "vault://agent365/acquisition/9"
    assert digest_only.raw_payload_utf8 is None
    assert digest_only.protected_payload_reference is None
    assert protected.raw_payload_sha256 == digest_only.raw_payload_sha256


def test_detail_parser_commits_long_description_without_copying_it_into_normalized_object() -> None:
    detail = {
        "id": "pkg-001",
        "displayName": "Contoso Sales Agent",
        "type": "custom",
        "isBlocked": False,
        "supportedHosts": ["Copilot"],
        "elementTypes": ["declarativeAgent"],
        "longDescription": "Detailed internal description",
        "categories": ["Productivity"],
        "sensitivity": "general",
        "allowedUsersAndGroups": [{"resourceId": "user-123", "resourceType": "user"}],
        "acquireUsersAndGroups": [],
        "elementDetails": [
            {
                "elementType": "declarativeAgent",
                "elements": [{"id": "dcp-001", "definition": "{\"name\":\"Agent\"}"}],
            }
        ],
        "newDetailField": "future",
    }
    parsed = parse_agent365_package_detail(
        json.dumps(detail, separators=(",", ":")).encode()
    )

    assert parsed.package.package_id == "pkg-001"
    assert parsed.categories == ("Productivity",)
    assert parsed.sensitivity == "general"
    assert parsed.allowed_principal_count == 1
    assert parsed.acquire_principal_count == 0
    assert parsed.element_detail_count == 1
    assert parsed.long_description_sha256 == hashlib.sha256(
        b"Detailed internal description"
    ).hexdigest()
    assert parsed.unknown_detail_field_names == ("newDetailField",)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"[]",
        b'{"value":{}}',
        b'{"value":[1]}',
        b'{"value":[{"displayName":"missing id"}]}',
    ],
)
def test_inventory_parser_fails_closed_on_unqualified_shapes(payload: bytes) -> None:
    with pytest.raises(MicrosoftAgent365SourceError):
        parse_agent365_inventory_response(payload)


def test_envelope_requires_timezone_aware_acquisition_time() -> None:
    with pytest.raises(ValueError):
        build_source_envelope(
            _inventory_payload(),
            source_type="agent365.package_inventory",
            tenant_id=TENANT_ID,
            acquisition_time=datetime(2026, 9, 16, 15, 0),
            api_version="v1.0",
            api_maturity="documented_preview",
            request_path="/v1.0/copilot/admin/catalog/packages",
            collector_identity="ets-agent365-q0",
            collector_version="0.1.0",
            acquisition_sequence=1,
        )


def test_source_envelope_model_rejects_retention_shape_mismatch() -> None:
    envelope = build_source_envelope(
        _inventory_payload(),
        source_type="agent365.package_inventory",
        tenant_id=TENANT_ID,
        acquisition_time=datetime(2026, 9, 16, 15, 0, tzinfo=UTC),
        api_version="v1.0",
        api_maturity="documented_preview",
        request_path="/v1.0/copilot/admin/catalog/packages",
        collector_identity="ets-agent365-q0",
        collector_version="0.1.0",
        acquisition_sequence=1,
    )

    invalid = envelope.model_copy(
        update={
            "payload_retention": "digest_only",
            "raw_payload_utf8": "should-not-be-here",
        }
    )
    with pytest.raises(ValidationError):
        type(envelope).model_validate(invalid.model_dump())
