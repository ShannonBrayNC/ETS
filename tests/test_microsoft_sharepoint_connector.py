from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ets.connectors.conformance import ConnectorConformanceHarness
from ets.connectors.credentials.models import (
    CredentialMetadataV1,
    CredentialReferenceV1,
)
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_connector import (
    SHAREPOINT_CONNECTOR_ID,
    MicrosoftSharePointDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRecordV1,
    MicrosoftSharePointDeltaRequestProfile,
)
from ets.connectors.enterprise.microsoft_sharepoint_http import (
    MicrosoftSharePointDeltaStateExpiredError,
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

NOW = datetime(2026, 8, 14, 20, 30, tzinfo=UTC)
MANIFESTS = Path("config/connectors/enterprise")
PROFILE_ID = "sharepoint-prod"
CREDENTIAL_REF = "fixture://microsoft/sharepoint"
CHECKPOINT = "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$skiptoken=next"


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
        return CredentialLease(b"fixture-sharepoint-token", self.describe(reference))


class FixturePageClient:
    def __init__(self, page: MicrosoftSharePointDeltaPageV1) -> None:
        self.page = page
        self.request_urls: list[str | None] = []
        self.closed = False

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        self.request_urls.append(request_url)
        return self.page

    def close(self) -> None:
        self.closed = True


class ExpiredStateClient:
    def __init__(self) -> None:
        self.request_urls: list[str | None] = []

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        self.request_urls.append(request_url)
        raise MicrosoftSharePointDeltaStateExpiredError("fixture expired delta state")

    def close(self) -> None:
        pass


def _tenant_profile() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "application_id": "22222222-2222-2222-2222-222222222222",
            "cloud": "global",
            "credential_ref": {
                "schema_version": "ets.connector.credential_ref.v1",
                "ref": CREDENTIAL_REF,
            },
            "consent_state": "granted",
        }
    )


def _instance(*, scope: str = "drive", credential_ref: str = CREDENTIAL_REF) -> ConnectorInstanceV1:
    settings: dict[str, object] = {
        "tenant_profile_id": PROFILE_ID,
        "scope": scope,
    }
    if scope == "drive":
        settings["drive_id"] = "drive-001"
    else:
        settings["site_id"] = "site-001"
        settings["list_id"] = "list-001"
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "sharepoint-metadata-prod",
            "connector_id": SHAREPOINT_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="instance-tenant-must-not-authorize",
                workspace_id="instance-workspace-must-not-authorize",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="sharepoint-approved-scope",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer",
                credential_ref=credential_ref,
            ).model_dump(mode="json"),
            "collection": ConnectorCollection(
                mode="poll",
                interval_seconds=60,
                batch_size=100,
            ).model_dump(mode="json"),
            "checkpoint": ConnectorCheckpointPolicy(
                strategy="source_cursor",
                durable=True,
            ).model_dump(mode="json"),
            "policy": ConnectorPolicyBinding(
                capture_profile="capture.microsoft.sharepoint.metadata.v1",
                normalization_profile="normalize.microsoft.sharepoint.metadata.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": settings,
        }
    )


def _record(*, deleted: bool = False) -> MicrosoftSharePointDeltaRecordV1:
    return MicrosoftSharePointDeltaRecordV1(
        source_record_id="drive:item-001:" + "a" * 32,
        object_id="item-001",
        scope="drive",
        deleted=deleted,
        source_modified_at_utc=NOW,
        metadata={
            "name": "report.docx",
            "size": 1234,
            "parent": {"id": "folder-001", "drive_id": "drive-001"},
            **({"deleted": True} if deleted else {}),
        },
    )


def _page(*, deleted: bool = False) -> MicrosoftSharePointDeltaPageV1:
    return MicrosoftSharePointDeltaPageV1(
        scope="drive",
        records=(_record(deleted=deleted),),
        checkpoint_url=CHECKPOINT,
        cycle_complete=False,
    )


def _adapter(
    client: FixturePageClient | ExpiredStateClient,
) -> tuple[MicrosoftSharePointDeltaAdapter, ConnectorRegistry]:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: MicrosoftSharePointDeltaRequestProfile,
        material: bytes,
        timeout: float,
        maximum: int,
    ) -> FixturePageClient | ExpiredStateClient:
        assert profile.scope == "drive"
        assert profile.resource_path == "/v1.0/drives/drive-001/root/delta"
        assert material == b"fixture-sharepoint-token"
        assert timeout == 30.0
        assert maximum == 1024 * 1024
        return client

    adapter = MicrosoftSharePointDeltaAdapter(
        registry.get_definition(SHAREPOINT_CONNECTOR_ID),
        FixtureCredentialResolver(),
        {PROFILE_ID: _tenant_profile()},
        client_factory=factory,
    )
    registry.register_adapter(adapter)
    return adapter, registry


def test_sharepoint_adapter_passes_shared_connector_conformance() -> None:
    adapter, registry = _adapter(FixturePageClient(_page()))
    instance = _instance()

    collection = adapter.collect(instance, None)
    assert collection.code == "ok"
    assert collection.checkpoint is not None

    report = ConnectorConformanceHarness(registry).validate_sample(
        adapter,
        instance,
        collection.records[0],
    )

    assert report.connector_id == SHAREPOINT_CONNECTOR_ID
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_sharepoint_adapter_replays_exact_source_cursor() -> None:
    client = FixturePageClient(_page())
    adapter, _ = _adapter(client)

    first = adapter.collect(_instance(), None)
    assert first.checkpoint is not None
    replay = adapter.collect(_instance(), first.checkpoint)

    assert first.checkpoint.cursor == CHECKPOINT
    assert client.request_urls == [None, CHECKPOINT]
    assert replay.code == "ok"


def test_sharepoint_normalization_uses_source_modified_time_and_no_instance_scope() -> None:
    adapter, _ = _adapter(FixturePageClient(_page()))
    instance = _instance()
    collection = adapter.collect(instance, None)
    candidate = adapter.normalize(instance, collection.records[0])
    serialized = json.dumps(candidate.model_dump(mode="json"), sort_keys=True)

    assert candidate.observed_at_utc == NOW
    assert candidate.source_system == SHAREPOINT_CONNECTOR_ID
    assert candidate.event_type == "microsoft.sharepoint.metadata.observed"
    assert candidate.metadata["object_id"] == "item-001"
    assert "instance-tenant-must-not-authorize" not in serialized
    assert "instance-workspace-must-not-authorize" not in serialized
    assert CREDENTIAL_REF not in serialized


def test_sharepoint_deleted_state_is_explicit_without_file_content_custody() -> None:
    adapter, _ = _adapter(FixturePageClient(_page(deleted=True)))
    instance = _instance()
    collection = adapter.collect(instance, None)
    candidate = adapter.normalize(instance, collection.records[0])

    assert candidate.event_type == "microsoft.sharepoint.metadata.deleted"
    assert candidate.metadata["deleted"] is True
    serialized = json.dumps(candidate.model_dump(mode="json"), sort_keys=True)
    assert "content" not in serialized.casefold()


def test_expired_sharepoint_state_returns_gap_and_preserves_old_checkpoint() -> None:
    client = ExpiredStateClient()
    adapter, _ = _adapter(client)
    prior = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=CHECKPOINT,
    )

    result = adapter.collect(_instance(), prior)

    assert result.code == "gap_detected"
    assert result.checkpoint == prior
    assert result.records == ()
    assert client.request_urls == [CHECKPOINT]


def test_sharepoint_instance_cannot_override_server_owned_credential_profile() -> None:
    adapter, _ = _adapter(FixturePageClient(_page()))

    with pytest.raises(ConnectorConfigurationError, match="server-owned tenant profile"):
        adapter.validate_config(_instance(credential_ref="fixture://microsoft/other"))


def test_sharepoint_scope_configuration_fails_closed() -> None:
    adapter, _ = _adapter(FixturePageClient(_page()))
    bad = _instance().model_copy(
        update={
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "scope": "drive",
                "drive_id": "drive-001",
                "site_id": "site-must-not-coexist",
            }
        }
    )

    with pytest.raises(ConnectorConfigurationError, match="forbids site_id/list_id"):
        adapter.validate_config(bad)
