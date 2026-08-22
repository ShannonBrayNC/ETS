from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphSubscriptionStateV1,
    hash_graph_client_state,
)
from ets.connectors.enterprise.microsoft_graph_subscriptions import (
    MicrosoftGraphSubscriptionThrottleError,
)
from ets.gateway.microsoft_graph_lifecycle import (
    MicrosoftGraphSubscriptionLifecycleManager,
    sharepoint_drive_subscription_resource,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
RESOURCE = "drives/drive-001/root"
CLIENT_STATE = "server-owned-client-state"
NOTIFICATION_URL = "https://gateway.example.test/gateway/v1/microsoft/graph"
NOW = datetime(2026, 8, 22, 20, 0, tzinfo=UTC)


class FakeLease:
    def __init__(self) -> None:
        self.closed = False

    def reveal(self) -> bytes:
        assert not self.closed
        return b"fixture-token"

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> FakeLease:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class FakeResolver:
    def __init__(self) -> None:
        self.references: list[CredentialReferenceV1] = []
        self.leases: list[FakeLease] = []

    def resolve(self, reference: CredentialReferenceV1) -> FakeLease:
        self.references.append(reference)
        lease = FakeLease()
        self.leases.append(lease)
        return lease


class FakeStore:
    def __init__(self, state: MicrosoftGraphSubscriptionStateV1 | None = None) -> None:
        self.state = state
        self.registered: list[MicrosoftGraphSubscriptionStateV1] = []
        self.replaced: list[MicrosoftGraphSubscriptionStateV1] = []

    def get_for_resource(
        self,
        *,
        tenant_id: str,
        resource: str,
    ) -> MicrosoftGraphSubscriptionStateV1 | None:
        assert tenant_id == TENANT_ID
        assert resource == RESOURCE
        return self.state

    def register(self, state: MicrosoftGraphSubscriptionStateV1) -> None:
        self.state = state
        self.registered.append(state)

    def replace_for_resource(self, state: MicrosoftGraphSubscriptionStateV1) -> None:
        self.state = state
        self.replaced.append(state)


class FakeClient:
    def __init__(self, *, create_id: str = "subscription-new") -> None:
        self.create_id = create_id
        self.calls: list[tuple[str, object]] = []
        self.closed = False
        self.throttle_create = False

    def create(
        self,
        *,
        resource: str,
        change_type: str,
        expiration_date_time: datetime,
        client_state: str,
    ) -> MicrosoftGraphSubscriptionStateV1:
        self.calls.append(
            (
                "create",
                (resource, change_type, expiration_date_time, client_state),
            )
        )
        if self.throttle_create:
            raise MicrosoftGraphSubscriptionThrottleError(600)
        return _state(
            subscription_id=self.create_id,
            expiration=expiration_date_time,
        )

    def renew(
        self,
        subscription: MicrosoftGraphSubscriptionStateV1,
        *,
        expiration_date_time: datetime,
    ) -> MicrosoftGraphSubscriptionStateV1:
        self.calls.append(("renew", expiration_date_time))
        return subscription.model_copy(
            update={
                "expiration_date_time": expiration_date_time,
                "status": "active",
            }
        )

    def reauthorize(
        self,
        subscription: MicrosoftGraphSubscriptionStateV1,
    ) -> MicrosoftGraphSubscriptionStateV1:
        self.calls.append(("reauthorize", subscription.subscription_id))
        return subscription.model_copy(update={"status": "active"})

    def close(self) -> None:
        self.closed = True


class FakeClientFactory:
    def __init__(self, clients: list[FakeClient]) -> None:
        self.clients = list(clients)
        self.arguments: list[tuple[bytes, str, str]] = []

    def __call__(
        self,
        _tenant_profile: MicrosoftTenantProfileV1,
        material: bytes,
        notification_url: str,
        lifecycle_notification_url: str,
    ) -> FakeClient:
        self.arguments.append((material, notification_url, lifecycle_notification_url))
        return self.clients.pop(0)


def _profile() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=TENANT_ID,
        application_id=APPLICATION_ID,
        cloud="global",
        credential_ref=CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref="azure-mi://microsoft-graph",
        ),
        consent_state="granted",
    )


def _state(
    *,
    subscription_id: str = "subscription-001",
    expiration: datetime = NOW + timedelta(days=10),
    status: str = "active",
    gap_state: str = "none",
) -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_subscription_state.v1",
            "subscription_id": subscription_id,
            "tenant_id": TENANT_ID,
            "cloud": "global",
            "resource": RESOURCE,
            "client_state_sha256": hash_graph_client_state(CLIENT_STATE),
            "expiration_date_time": expiration,
            "status": status,
            "gap_state": gap_state,
        }
    )


def _manager(
    *,
    store: FakeStore,
    resolver: FakeResolver,
    clients: list[FakeClient],
) -> tuple[MicrosoftGraphSubscriptionLifecycleManager, FakeClientFactory]:
    factory = FakeClientFactory(clients)
    return (
        MicrosoftGraphSubscriptionLifecycleManager(
            tenant_profile=_profile(),
            credential_resolver=resolver,
            store=store,
            resource=RESOURCE,
            notification_url=NOTIFICATION_URL,
            client_state=CLIENT_STATE,
            lifetime_seconds=28 * 24 * 60 * 60,
            renewal_window_seconds=24 * 60 * 60,
            client_factory=factory,
        ),
        factory,
    )


def test_create_uses_exact_drive_resource_and_does_not_persist_client_state() -> None:
    store = FakeStore()
    resolver = FakeResolver()
    client = FakeClient()
    manager, factory = _manager(store=store, resolver=resolver, clients=[client])

    result = manager.run_once(now=NOW)

    assert result.action == "created"
    assert store.state is not None
    assert store.state.resource == RESOURCE
    assert store.state.client_state_sha256 == hash_graph_client_state(CLIENT_STATE)
    assert CLIENT_STATE not in store.state.model_dump_json()
    assert client.calls == [
        (
            "create",
            (RESOURCE, "updated", NOW + timedelta(days=28), CLIENT_STATE),
        )
    ]
    assert factory.arguments == [(b"fixture-token", NOTIFICATION_URL, NOTIFICATION_URL)]
    assert client.closed
    assert resolver.leases[0].closed


def test_noop_does_not_acquire_a_managed_identity_token() -> None:
    store = FakeStore(_state())
    resolver = FakeResolver()
    manager, _factory = _manager(store=store, resolver=resolver, clients=[])

    result = manager.run_once(now=NOW)

    assert result.action == "noop"
    assert resolver.references == []


def test_reauthorize_and_renew_preserve_possible_gap() -> None:
    store = FakeStore(
        _state(
            expiration=NOW + timedelta(minutes=30),
            status="reauthorization_required",
            gap_state="possible",
        )
    )
    resolver = FakeResolver()
    reauthorize_client = FakeClient()
    renew_client = FakeClient()
    manager, _factory = _manager(
        store=store,
        resolver=resolver,
        clients=[reauthorize_client, renew_client],
    )

    result = manager.run_once(now=NOW)

    assert result.action == "reauthorized_and_renewed"
    assert store.state is not None
    assert store.state.status == "active"
    assert store.state.gap_state == "possible"
    assert store.state.expiration_date_time == NOW + timedelta(days=28)
    assert len(store.registered) == 2


@pytest.mark.parametrize("status", ["removed", "active"])
def test_removed_or_expired_subscription_is_replaced_with_possible_gap(
    status: str,
) -> None:
    expiration = NOW + timedelta(days=1) if status == "removed" else NOW
    store = FakeStore(_state(expiration=expiration, status=status))
    resolver = FakeResolver()
    client = FakeClient(create_id="subscription-replacement")
    manager, _factory = _manager(store=store, resolver=resolver, clients=[client])

    result = manager.run_once(now=NOW)

    assert result.action == "recreated"
    assert result.state is not None
    assert result.state.subscription_id == "subscription-replacement"
    assert result.state.gap_state == "possible"
    assert store.replaced == [result.state]


def test_throttle_retry_after_defers_without_a_second_token_acquisition() -> None:
    store = FakeStore()
    resolver = FakeResolver()
    client = FakeClient()
    client.throttle_create = True
    manager, _factory = _manager(store=store, resolver=resolver, clients=[client])

    with pytest.raises(MicrosoftGraphSubscriptionThrottleError):
        manager.run_once(now=NOW)
    deferred = manager.run_once(now=NOW + timedelta(minutes=5))

    assert deferred.action == "deferred"
    assert len(resolver.references) == 1


def test_sharepoint_resource_is_server_derived_and_path_bounded() -> None:
    assert sharepoint_drive_subscription_resource("drive ! 001") == (
        "drives/drive%20%21%20001/root"
    )
    with pytest.raises(ValueError, match="unsupported"):
        sharepoint_drive_subscription_resource("drive/other")
