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
from ets.connectors.enterprise.microsoft_entra_connector import (
    ENTRA_CONNECTOR_ID,
    MicrosoftEntraDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_entra_delta import (
    EntraDeltaRequestProfile,
    MicrosoftEntraDeltaPageV1,
    MicrosoftEntraDeltaRecordV1,
)
from ets.connectors.enterprise.microsoft_entra_http import (
    MicrosoftEntraDeltaStateExpiredError,
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

NOW = datetime(2026, 8, 14, 15, 0, tzinfo=UTC)
MANIFESTS = Path("config/connectors/enterprise")
PROFILE_ID = "entra-prod"
CREDENTIAL_REF = "fixture://microsoft/entra-directory"


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
        return CredentialLease(b"fixture-entra-token", self.describe(reference))


class FixturePageClient:
    def __init__(self, page: MicrosoftEntraDeltaPageV1) -> None:
        self.page = page
        self.request_urls: list[str | None] = []
        self.closed = False

    def fetch(self, request_url: str | None = None) -> MicrosoftEntraDeltaPageV1:
        self.request_urls.append(request_url)
        return self.page

    def close(self) -> None:
        self.closed = True


class ExpiredStateClient:
    def __init__(self) -> None:
        self.request_urls: list[str | None] = []
        self.closed = False

    def fetch(self, request_url: str | None = None) -> MicrosoftEntraDeltaPageV1:
        self.request_urls.append(request_url)
        raise MicrosoftEntraDeltaStateExpiredError("fixture expired delta state")

    def close(self) -> None:
        self.closed = True


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


def _instance(
    *,
    credential_ref: str = CREDENTIAL_REF,
    collection: str = "users",
) -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "entra-directory-prod",
            "connector_id": ENTRA_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="payload-scope-must-not-authorize",
                workspace_id="payload-workspace-must-not-authorize",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="entra-directory",
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
                capture_profile="capture.microsoft.entra.delta.v1",
                normalization_profile="normalize.microsoft.entra.delta.v1",
            ).model_dump(mode="json"),
            "retry": ConnectorRetryPolicy().model_dump(mode="json"),
            "gap_detection": ConnectorGapPolicy().model_dump(mode="json"),
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "collection": collection,
            },
        }
    )


def _record(*, removed_reason: str | None = None) -> MicrosoftEntraDeltaRecordV1:
    return MicrosoftEntraDeltaRecordV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.entra_delta_record.v1",
            "source_record_id": "entra-delta:" + "a" * 64,
            "collection": "users",
            "object_id": "user-001",
            "removed_reason": removed_reason,
            "metadata": {
                "object_type": "user",
                "account_enabled": True,
                "user_type": "Member",
            },
        }
    )


def _page(*, cursor: str | None = None) -> MicrosoftEntraDeltaPageV1:
    next_link = (
        cursor
        or "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=next"
    )
    return MicrosoftEntraDeltaPageV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.entra_delta_page.v1",
            "collection": "users",
            "records": [_record().model_dump(mode="json")],
            "next_link": next_link,
            "delta_link": None,
        }
    )


def _adapter(
    client: FixturePageClient | ExpiredStateClient,
) -> tuple[MicrosoftEntraDeltaAdapter, ConnectorRegistry]:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: EntraDeltaRequestProfile,
        material: bytes,
        timeout: float,
        maximum: int,
    ) -> FixturePageClient | ExpiredStateClient:
        assert profile.collection == "users"
        assert material == b"fixture-entra-token"
        assert timeout == 30.0
        assert maximum == 2 * 1024 * 1024
        return client

    adapter = MicrosoftEntraDeltaAdapter(
        registry.get_definition(ENTRA_CONNECTOR_ID),
        FixtureCredentialResolver(),
        {PROFILE_ID: _tenant_profile()},
        client_factory=factory,
    )
    registry.register_adapter(adapter)
    return adapter, registry


def test_entra_adapter_passes_shared_connector_conformance() -> None:
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

    assert report.connector_id == ENTRA_CONNECTOR_ID
    assert report.instance_valid is True
    assert report.candidate_valid is True


def test_entra_adapter_uses_server_owned_tenant_profile_and_exact_source_cursor() -> None:
    client = FixturePageClient(_page())
    adapter, _ = _adapter(client)
    instance = _instance()

    first = adapter.collect(instance, None)
    assert first.checkpoint is not None
    replay = adapter.collect(instance, first.checkpoint)

    assert first.checkpoint.cursor == _page().next_link
    assert client.request_urls == [None, first.checkpoint.cursor]
    assert replay.code == "ok"


def test_entra_normalization_has_no_invented_source_time_or_raw_identity_fields() -> None:
    adapter, _ = _adapter(FixturePageClient(_page()))
    instance = _instance()
    collection = adapter.collect(instance, None)

    candidate = adapter.normalize(instance, collection.records[0])
    serialized = json.dumps(candidate.model_dump(mode="json"))

    assert candidate.observed_at_utc is None
    assert candidate.source_system == ENTRA_CONNECTOR_ID
    assert candidate.event_type == "microsoft.entra.directory_object.observed"
    assert candidate.metadata["cloud"] == "global"
    assert candidate.metadata["audit"]["object_id"] == "user-001"
    assert "payload-scope-must-not-authorize" not in serialized
    assert "payload-workspace-must-not-authorize" not in serialized
    assert CREDENTIAL_REF not in serialized


def test_entra_removed_object_is_a_source_claim_not_a_new_observation_time() -> None:
    client = FixturePageClient(
        MicrosoftEntraDeltaPageV1.model_validate(
            {
                "schema_version": "ets.connector.microsoft.entra_delta_page.v1",
                "collection": "users",
                "records": [_record(removed_reason="deleted").model_dump(mode="json")],
                "next_link": None,
                "delta_link": (
                    "https://graph.microsoft.com/v1.0/users/delta?"
                    "$deltatoken=done"
                ),
            }
        )
    )
    adapter, _ = _adapter(client)
    instance = _instance()
    collection = adapter.collect(instance, None)
    candidate = adapter.normalize(instance, collection.records[0])

    assert candidate.event_type == "microsoft.entra.directory_object.removed"
    assert candidate.observed_at_utc is None
    assert candidate.metadata["audit"]["removed_reason"] == "deleted"


def test_expired_delta_state_returns_gap_and_preserves_old_checkpoint() -> None:
    client = ExpiredStateClient()
    adapter, _ = _adapter(client)
    checkpoint = _page().checkpoint_url
    prior = ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=checkpoint,
    )

    result = adapter.collect(_instance(), prior)

    assert result.code == "gap_detected"
    assert result.checkpoint is not None
    assert result.checkpoint.cursor == checkpoint
    assert result.records == ()
    assert "full resync authorization" in (result.message or "")
    assert client.request_urls == [checkpoint]


def test_instance_cannot_override_server_owned_credential_profile() -> None:
    adapter, _ = _adapter(FixturePageClient(_page()))

    with pytest.raises(ConnectorConfigurationError, match="server-owned tenant profile"):
        adapter.validate_config(_instance(credential_ref="fixture://microsoft/other"))


def test_unknown_tenant_profile_and_unqualified_collection_fail_closed() -> None:
    adapter, _ = _adapter(FixturePageClient(_page()))
    unknown = _instance().model_copy(
        update={"settings": {"tenant_profile_id": "unknown", "collection": "users"}}
    )

    with pytest.raises(ConnectorConfigurationError, match="not registered server-side"):
        adapter.validate_config(unknown)
    with pytest.raises(ConnectorConfigurationError, match="users or groups"):
        adapter.validate_config(_instance(collection="devices"))
