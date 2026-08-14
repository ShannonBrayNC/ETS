from __future__ import annotations

from pathlib import Path

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_connector import (
    SHAREPOINT_CONNECTOR_ID,
    MicrosoftSharePointDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRequestProfile,
)
from ets.connectors.enterprise.microsoft_sharepoint_http import (
    MicrosoftSharePointDeltaAuthorizationError,
    MicrosoftSharePointDeltaTerminalError,
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

MANIFESTS = Path("config/connectors/enterprise")
PROFILE_ID = "sharepoint-prod"
CREDENTIAL_REF = "fixture://microsoft/sharepoint"
CHECKPOINT = "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$skiptoken=prior"


class FixtureCredentialResolver:
    def describe(self, reference: CredentialReferenceV1) -> CredentialMetadataV1:
        return CredentialMetadataV1(
            schema_version="ets.connector.credential_metadata.v1",
            reference=reference,
            provider="fixture",
            status="available",
            version="1",
            updated_at_utc=None,
        )

    def resolve(self, reference: CredentialReferenceV1) -> CredentialLease:
        return CredentialLease(b"fixture-sharepoint-token", self.describe(reference))


class ErrorClient:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.request_urls: list[str | None] = []

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        self.request_urls.append(request_url)
        raise self.error

    def close(self) -> None:
        return None


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


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "sharepoint-source-state",
            "connector_id": SHAREPOINT_CONNECTOR_ID,
            "connector_version": "1.0",
            "enabled": True,
            "scope": ConnectorScope(
                tenant_id="instance-tenant",
                workspace_id="instance-workspace",
            ).model_dump(mode="json"),
            "source": ConnectorSource(
                name="sharepoint-approved-scope",
                environment="test",
            ).model_dump(mode="json"),
            "authentication": ConnectorAuthentication(
                method="bearer",
                credential_ref=CREDENTIAL_REF,
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
            "settings": {
                "tenant_profile_id": PROFILE_ID,
                "scope": "drive",
                "drive_id": "drive-001",
            },
        }
    )


def _adapter(client: ErrorClient) -> MicrosoftSharePointDeltaAdapter:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: MicrosoftSharePointDeltaRequestProfile,
        material: bytes,
        timeout: float,
        maximum: int,
    ) -> ErrorClient:
        assert profile.resource_path == "/v1.0/drives/drive-001/root/delta"
        assert material == b"fixture-sharepoint-token"
        return client

    return MicrosoftSharePointDeltaAdapter(
        registry.get_definition(SHAREPOINT_CONNECTOR_ID),
        FixtureCredentialResolver(),
        {PROFILE_ID: _tenant_profile()},
        client_factory=factory,
    )


def _prior_checkpoint() -> ConnectorCheckpointV1:
    return ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=CHECKPOINT,
    )


def test_inaccessible_source_is_explicit_and_does_not_advance_state() -> None:
    client = ErrorClient(MicrosoftSharePointDeltaAuthorizationError("fixture denied"))
    adapter = _adapter(client)
    prior = _prior_checkpoint()

    result = adapter.collect(_instance(), prior)
    health = adapter.test_connection(_instance())

    assert result.code == "authorization_failed"
    assert result.records == ()
    assert result.checkpoint == prior
    assert result.message == "SharePoint metadata access was denied"
    assert health.state == "failed"
    assert health.code == "authorization_failed"
    assert client.request_urls == [CHECKPOINT, None]


def test_unsupported_source_failure_is_explicit_and_does_not_invent_observation() -> None:
    client = ErrorClient(MicrosoftSharePointDeltaTerminalError("fixture unsupported source state"))
    adapter = _adapter(client)
    prior = _prior_checkpoint()

    result = adapter.collect(_instance(), prior)

    assert result.code == "terminal_error"
    assert result.records == ()
    assert result.checkpoint == prior
    assert result.message == "Microsoft Graph SharePoint delta request failed"
    assert client.request_urls == [CHECKPOINT]
