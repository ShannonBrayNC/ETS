from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.connectors.conformance import ConnectorConformanceHarness
from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
)
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewContentDescriptorV1,
    MicrosoftPurviewDiscoveryPageV1,
    MicrosoftPurviewManagementProfile,
    PurviewContentType,
    purview_management_profile,
)
from ets.connectors.enterprise.microsoft_purview_audit import (
    MicrosoftPurviewAuditContentV1,
    MicrosoftPurviewAuditRecordV1,
)
from ets.connectors.enterprise.microsoft_purview_connector import (
    MicrosoftPurviewActivityAdapter,
    MicrosoftPurviewConnectorSettings,
)
from ets.connectors.models import (
    ConnectorAuthentication,
    ConnectorCheckpointPolicy,
    ConnectorCheckpointV1,
    ConnectorCollection,
    ConnectorGapPolicy,
    ConnectorInstanceV1,
    ConnectorPolicyBinding,
    ConnectorRetryPolicy,
    ConnectorScope,
    ConnectorSource,
)
from ets.connectors.registry import ConnectorRegistry
from ets.connectors.sdk import ConnectorConfigurationError

NOW = datetime(2026, 8, 14, 21, 0, tzinfo=UTC)
EVENT_TIME = NOW - timedelta(minutes=3)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PUBLISHER_ID = "33333333-3333-3333-3333-333333333333"
RECORD_ID = "44444444-4444-4444-4444-444444444444"
PROFILE_ID = "purview-prod"
CREDENTIAL_REF = "fixture://microsoft/purview"
NEXT_URI = (
    f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/"
    "subscriptions/content?contentType=Audit.General&nextpage=opaque"
)
MANIFESTS = Path("config/connectors/enterprise")


class FixtureCredentialResolver:
    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status="available",
            version="1",
            updated_at_utc=NOW,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        return CredentialLease(b"fixture-purview-token", self.describe(reference))


class FixtureProfileResolver:
    def __init__(self, profile: MicrosoftPurviewManagementProfile) -> None:
        self.profile = profile

    def resolve(self, profile_id: str) -> MicrosoftPurviewManagementProfile:
        if profile_id != self.profile.profile_id:
            raise ValueError("unknown Purview profile")
        return self.profile


class FixturePurviewClient:
    def __init__(self, *, next_page_uri: str | None = NEXT_URI) -> None:
        self.next_page_uri = next_page_uri
        self.list_calls: list[tuple[datetime | None, datetime | None, str | None]] = []
        self.closed = False

    def list_content(
        self,
        content_type: PurviewContentType,
        *,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        next_page_uri: str | None = None,
    ) -> MicrosoftPurviewDiscoveryPageV1:
        assert content_type == "Audit.General"
        self.list_calls.append((start_time_utc, end_time_utc, next_page_uri))
        return MicrosoftPurviewDiscoveryPageV1(
            content_type="Audit.General",
            descriptors=(_descriptor(),),
            next_page_uri=self.next_page_uri if next_page_uri is None else None,
            discovery_source="poll",
        )

    def retrieve_content(
        self,
        descriptor: MicrosoftPurviewContentDescriptorV1,
        *,
        service_specific_allowlist: frozenset[str] = frozenset(),
        include_client_ip: bool = False,
    ) -> MicrosoftPurviewAuditContentV1:
        assert descriptor.content_id == "content-001"
        assert service_specific_allowlist == frozenset({"SiteUrl"})
        assert include_client_ip is False
        return _content()

    def close(self) -> None:
        self.closed = True


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": "global",
            "credential_ref": {
                "schema_version": "ets.connector.credential_ref.v1",
                "ref": CREDENTIAL_REF,
            },
            "consent_state": "granted",
        }
    )


def _profile() -> MicrosoftPurviewManagementProfile:
    return purview_management_profile(
        PROFILE_ID,
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
        content_created_utc=NOW - timedelta(minutes=5),
        content_expiration_utc=NOW + timedelta(days=7),
        discovery_source="poll",
    )


def _record() -> MicrosoftPurviewAuditRecordV1:
    return MicrosoftPurviewAuditRecordV1(
        source_record_id=RECORD_ID,
        record_type=1,
        creation_time_utc=EVENT_TIME,
        operation="FileAccessed",
        organization_id=TENANT_ID,
        user_type=0,
        user_key="user-key-001",
        workload="SharePoint",
        user_id="alice@example.test",
        result_status="Succeeded",
        object_id="https://contoso.sharepoint.com/sites/a/report.docx",
        client_ip=None,
        scope=0,
        version=1,
        content_type="Audit.General",
        content_id="content-001",
        service_specific={"SiteUrl": "https://contoso.sharepoint.com/sites/a"},
    )


def _content() -> MicrosoftPurviewAuditContentV1:
    descriptor = _descriptor()
    return MicrosoftPurviewAuditContentV1(
        content_type="Audit.General",
        content_id=descriptor.content_id,
        content_sha256="a" * 64,
        content_created_utc=descriptor.content_created_utc,
        content_expiration_utc=descriptor.content_expiration_utc,
        records=(_record(),),
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "purview-prod",
            "connector_id": "microsoft.purview.activity",
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="instance-tenant-must-not-authorize",
                workspace_id="instance-workspace-must-not-authorize",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="purview-audit",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer",
                credential_ref=CREDENTIAL_REF,
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll",
                interval_seconds=60,
                batch_size=500,
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor",
                durable=True,
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.purview.audit.v1",
                normalization_profile="normalize.microsoft.purview.audit.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "management_profile_id": PROFILE_ID,
                "content_type": "Audit.General",
                "service_specific_allowlist": ["SiteUrl"],
                "poll_window_seconds": 3600,
                "overlap_seconds": 300,
            },
        }
    )


def _adapter(
    client: FixturePurviewClient,
) -> tuple[MicrosoftPurviewActivityAdapter, ConnectorRegistry]:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: MicrosoftPurviewManagementProfile,
        material: bytes,
        settings: MicrosoftPurviewConnectorSettings,
    ) -> FixturePurviewClient:
        assert profile.profile_id == PROFILE_ID
        assert material == b"fixture-purview-token"
        assert settings.content_type == "Audit.General"
        return client

    adapter = MicrosoftPurviewActivityAdapter(
        registry.get_definition("microsoft.purview.activity"),
        FixtureProfileResolver(_profile()),
        FixtureCredentialResolver(),
        client_factory=factory,
        now=lambda: NOW,
    )
    registry.register_adapter(adapter)
    return adapter, registry


def test_purview_adapter_passes_shared_connector_conformance() -> None:
    adapter, registry = _adapter(FixturePurviewClient())
    instance = _instance()
    collection = adapter.collect(instance, None)

    assert collection.code == "ok"
    assert collection.checkpoint is not None
    report = ConnectorConformanceHarness(registry).validate_sample(
        adapter,
        instance,
        collection.records[0],
    )

    assert report.connector_id == "microsoft.purview.activity"
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_purview_adapter_rejects_credential_reference_profile_fallback() -> None:
    adapter, _ = _adapter(FixturePurviewClient())
    instance = _instance().model_copy(
        update={
            "authentication": ConnectorAuthentication(
                method="bearer",
                credential_ref="fixture://microsoft/directory",
            )
        }
    )

    with pytest.raises(ConnectorConfigurationError, match="server-owned profile"):
        adapter.validate_config(instance)


def test_purview_initial_window_and_exact_next_page_cursor_replay() -> None:
    client = FixturePurviewClient()
    adapter, _ = _adapter(client)
    instance = _instance()

    first = adapter.collect(instance, None)
    assert first.checkpoint is not None
    second = adapter.collect(instance, first.checkpoint)

    assert client.list_calls[0] == (NOW - timedelta(hours=1), NOW, None)
    assert first.checkpoint.cursor == NEXT_URI
    assert first.checkpoint.observed_through_utc == NOW
    assert client.list_calls[1] == (None, None, NEXT_URI)
    assert second.code == "ok"


def test_purview_completed_window_restarts_with_bounded_overlap() -> None:
    client = FixturePurviewClient(next_page_uri=None)
    adapter, _ = _adapter(client)
    instance = _instance()
    checkpoint = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        observed_through_utc=NOW - timedelta(minutes=20),
    )

    result = adapter.collect(instance, checkpoint)

    assert result.code == "ok"
    assert client.list_calls == [
        (NOW - timedelta(minutes=25), NOW, None),
    ]


def test_purview_normalization_is_minimized_and_preserves_source_event_time() -> None:
    adapter, _ = _adapter(FixturePurviewClient())
    instance = _instance()
    collection = adapter.collect(instance, None)

    candidate = adapter.normalize(instance, collection.records[0])
    serialized = json.dumps(candidate.model_dump(mode="json"), sort_keys=True)

    assert candidate.source_system == "microsoft.purview.activity"
    assert candidate.source_record_id == RECORD_ID
    assert candidate.observed_at_utc == EVENT_TIME
    assert candidate.event_type == "microsoft.purview.audit.observed"
    assert candidate.lossless is False
    assert candidate.metadata["record"]["operation"] == "FileAccessed"
    assert "instance-tenant-must-not-authorize" not in serialized
    assert "fixture-purview-token" not in serialized
    assert "RAW" not in serialized
