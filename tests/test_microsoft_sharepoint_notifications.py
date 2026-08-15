from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.connectors.credentials.models import CredentialMetadataV1, CredentialReferenceV1
from ets.connectors.credentials.provider import CredentialLease
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
)
from ets.connectors.enterprise.microsoft_sharepoint_connector import (
    SHAREPOINT_CONNECTOR_ID,
    MicrosoftSharePointDeltaAdapter,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRecordV1,
    MicrosoftSharePointDeltaRequestProfile,
    sharepoint_drive_delta_request_profile,
)
from ets.connectors.enterprise.microsoft_sharepoint_notifications import (
    MicrosoftSharePointNotificationError,
    plan_sharepoint_recollection,
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

NOW = datetime(2026, 8, 14, 20, 30, tzinfo=UTC)
TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "33333333-3333-3333-3333-333333333333"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PROFILE_ID = "sharepoint-prod"
CREDENTIAL_REF = "fixture://microsoft/sharepoint"
SUBSCRIPTION_ID = "subscription-001"
CHECKPOINT = "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$skiptoken=prior"
NEXT_CHECKPOINT = (
    "https://graph.microsoft.com/v1.0/drives/drive-001/root/delta?$deltatoken=recovered"
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
        return CredentialLease(b"fixture-sharepoint-token", self.describe(reference))


class FixturePageClient:
    def __init__(self, page: MicrosoftSharePointDeltaPageV1) -> None:
        self.page = page
        self.request_urls: list[str | None] = []

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        self.request_urls.append(request_url)
        return self.page

    def close(self) -> None:
        return None


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=TENANT_ID,
        application_id=APPLICATION_ID,
        cloud="global",
        credential_ref=CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref=CREDENTIAL_REF,
        ),
        consent_state="granted",
    )


def _profile() -> MicrosoftSharePointDeltaRequestProfile:
    return sharepoint_drive_delta_request_profile(PROFILE_ID, _tenant(), "drive-001")


def _subscription(
    *,
    resource: str = "/drives/drive-001/root",
    tenant_id: str = TENANT_ID,
    cloud: str = "global",
    gap_state: str = "none",
) -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_subscription_state.v1",
            "subscription_id": SUBSCRIPTION_ID,
            "tenant_id": tenant_id,
            "cloud": cloud,
            "resource": resource,
            "client_state_sha256": "a" * 64,
            "expiration_date_time": NOW + timedelta(hours=1),
            "status": "active",
            "gap_state": gap_state,
        }
    )


def _resource_notification(
    *,
    subscription_id: str = SUBSCRIPTION_ID,
    tenant_id: str = TENANT_ID,
) -> MicrosoftGraphNotificationV1:
    return MicrosoftGraphNotificationV1(
        schema_version="ets.connector.microsoft.graph_notification.v1",
        source_record_id="notification-resource-001",
        kind="resource",
        subscription_id=subscription_id,
        tenant_id=tenant_id,
        subscription_expiration_date_time=NOW + timedelta(hours=1),
        change_type="updated",
        resource="drives/drive-001/items/item-001",
        resource_data={"id": "item-001"},
    )


def _lifecycle_notification(event: str) -> MicrosoftGraphNotificationV1:
    return MicrosoftGraphNotificationV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_notification.v1",
            "source_record_id": f"notification-{event}",
            "kind": "lifecycle",
            "subscription_id": SUBSCRIPTION_ID,
            "tenant_id": TENANT_ID,
            "subscription_expiration_date_time": NOW + timedelta(hours=1),
            "lifecycle_event": event,
            "resource_data": {},
        }
    )


def _checkpoint() -> ConnectorCheckpointV1:
    return ConnectorCheckpointV1(
        schema_version="ets.connector.checkpoint.v1",
        cursor=CHECKPOINT,
    )


def _instance() -> ConnectorInstanceV1:
    return ConnectorInstanceV1.model_validate(
        {
            "schema_version": "ets.connector.instance.v1",
            "instance_id": "sharepoint-notification-recovery",
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


def _recovery_page() -> MicrosoftSharePointDeltaPageV1:
    return MicrosoftSharePointDeltaPageV1(
        scope="drive",
        records=(
            MicrosoftSharePointDeltaRecordV1(
                source_record_id="drive:item-001:" + "a" * 32,
                object_id="item-001",
                scope="drive",
                deleted=False,
                source_modified_at_utc=NOW,
                metadata={"name": "recovered.docx"},
            ),
        ),
        checkpoint_url=NEXT_CHECKPOINT,
        cycle_complete=True,
    )


def _adapter(client: FixturePageClient) -> MicrosoftSharePointDeltaAdapter:
    registry = ConnectorRegistry.from_manifest_directory(MANIFESTS)

    def factory(
        profile: MicrosoftSharePointDeltaRequestProfile,
        material: bytes,
        timeout: float,
        maximum: int,
    ) -> FixturePageClient:
        assert profile.resource_path == "/v1.0/drives/drive-001/root/delta"
        assert material == b"fixture-sharepoint-token"
        return client

    return MicrosoftSharePointDeltaAdapter(
        registry.get_definition(SHAREPOINT_CONNECTOR_ID),
        FixtureCredentialResolver(),
        {PROFILE_ID: _tenant()},
        client_factory=factory,
    )


def test_duplicate_resource_notifications_only_repeat_the_same_recollection_directive() -> None:
    notification = _resource_notification()
    checkpoint = _checkpoint()

    first = plan_sharepoint_recollection(
        notification,
        _subscription(),
        _profile(),
        checkpoint,
    )
    retry = plan_sharepoint_recollection(
        notification,
        _subscription(),
        _profile(),
        checkpoint,
    )

    assert first == retry
    assert first.reason == "resource_notification"
    assert first.possible_gap is False
    assert first.resume_checkpoint == checkpoint


@pytest.mark.parametrize("event", ["missed", "subscriptionRemoved"])
def test_loss_signals_preserve_delta_checkpoint_and_mark_possible_gap(event: str) -> None:
    directive = plan_sharepoint_recollection(
        _lifecycle_notification(event),
        _subscription(gap_state="possible"),
        _profile(),
        _checkpoint(),
    )

    assert directive.possible_gap is True
    assert directive.resume_checkpoint == _checkpoint()


def test_missed_notification_recovers_through_exact_preserved_delta_cursor() -> None:
    prior = _checkpoint()
    directive = plan_sharepoint_recollection(
        _lifecycle_notification("missed"),
        _subscription(gap_state="possible"),
        _profile(),
        prior,
    )
    client = FixturePageClient(_recovery_page())
    adapter = _adapter(client)

    result = adapter.collect(_instance(), directive.resume_checkpoint)

    assert client.request_urls == [CHECKPOINT]
    assert result.code == "ok"
    assert result.checkpoint is not None
    assert result.checkpoint.cursor == NEXT_CHECKPOINT
    assert prior.cursor == CHECKPOINT


def test_reauthorization_signal_does_not_create_a_gap_without_gap_state() -> None:
    directive = plan_sharepoint_recollection(
        _lifecycle_notification("reauthorizationRequired"),
        _subscription(gap_state="none"),
        _profile(),
        _checkpoint(),
    )

    assert directive.reason == "reauthorization_required"
    assert directive.possible_gap is False
    assert directive.resume_checkpoint == _checkpoint()


@pytest.mark.parametrize(
    ("notification", "subscription"),
    [
        (_resource_notification(subscription_id="other-subscription"), _subscription()),
        (_resource_notification(tenant_id=OTHER_TENANT_ID), _subscription()),
        (_resource_notification(), _subscription(resource="/drives/other/root")),
        (
            _resource_notification(),
            _subscription(resource="https://evil.example/drives/drive-001/root"),
        ),
        (_resource_notification(), _subscription(resource="/drives/drive-001/root?select=id")),
    ],
)
def test_notification_recollection_is_bound_to_server_owned_source(
    notification: MicrosoftGraphNotificationV1,
    subscription: MicrosoftGraphSubscriptionStateV1,
) -> None:
    with pytest.raises(MicrosoftSharePointNotificationError):
        plan_sharepoint_recollection(
            notification,
            subscription,
            _profile(),
            _checkpoint(),
        )
