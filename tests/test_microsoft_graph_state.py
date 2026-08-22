from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
    hash_graph_client_state,
)
from ets.gateway.microsoft_graph_state import (
    MicrosoftGraphSubscriptionStateStoreError,
    SQLiteMicrosoftGraphSubscriptionStore,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
EXPIRATION = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)


def _state(
    *,
    subscription_id: str = "subscription-001",
    status: str = "active",
    gap_state: str = "none",
) -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1(
        schema_version="ets.connector.microsoft.graph_subscription_state.v1",
        subscription_id=subscription_id,
        tenant_id=TENANT_ID,
        cloud="global",
        resource="drives/drive-001/root",
        client_state_sha256=hash_graph_client_state("server-owned-client-state"),
        expiration_date_time=EXPIRATION,
        status=status,
        gap_state=gap_state,
    )


def _lifecycle(*, event: str = "missed") -> MicrosoftGraphNotificationV1:
    return MicrosoftGraphNotificationV1(
        schema_version="ets.connector.microsoft.graph_notification.v1",
        source_record_id="graph-notification:test",
        kind="lifecycle",
        subscription_id="subscription-001",
        tenant_id=TENANT_ID,
        subscription_expiration_date_time=EXPIRATION + timedelta(minutes=5),
        lifecycle_event=event,
    )


def test_register_and_snapshot_survive_reopen(tmp_path: Path) -> None:
    database = tmp_path / "graph-state.db"
    first = SQLiteMicrosoftGraphSubscriptionStore(database)
    first.register(_state())
    first.close()

    reopened = SQLiteMicrosoftGraphSubscriptionStore(database)
    snapshot = reopened.snapshot()

    assert list(snapshot) == ["subscription-001"]
    assert snapshot["subscription-001"].tenant_id == TENANT_ID
    assert snapshot["subscription-001"].client_state_sha256 == hash_graph_client_state(
        "server-owned-client-state"
    )
    reopened.close()


def test_register_rejects_immutable_identity_changes(tmp_path: Path) -> None:
    store = SQLiteMicrosoftGraphSubscriptionStore(tmp_path / "graph-state.db")
    store.register(_state())

    changed = _state().model_copy(update={"resource": "drives/drive-002/root"})
    with pytest.raises(MicrosoftGraphSubscriptionStateStoreError, match="identity changed"):
        store.register(changed)
    store.close()


def test_lifecycle_transition_is_persisted_atomically(tmp_path: Path) -> None:
    database = tmp_path / "graph-state.db"
    store = SQLiteMicrosoftGraphSubscriptionStore(database)
    store.register(_state())

    updated = store.apply_lifecycle(_lifecycle(event="missed"))
    assert updated.status == "active"
    assert updated.gap_state == "possible"
    assert updated.expiration_date_time == EXPIRATION + timedelta(minutes=5)
    store.close()

    reopened = SQLiteMicrosoftGraphSubscriptionStore(database)
    persisted = reopened.get("subscription-001")
    assert persisted is not None
    assert persisted.gap_state == "possible"
    assert persisted.expiration_date_time == EXPIRATION + timedelta(minutes=5)
    reopened.close()


def test_lifecycle_tenant_mismatch_fails_closed(tmp_path: Path) -> None:
    store = SQLiteMicrosoftGraphSubscriptionStore(tmp_path / "graph-state.db")
    store.register(_state())
    notification = _lifecycle().model_copy(
        update={"tenant_id": "22222222-2222-2222-2222-222222222222"}
    )

    with pytest.raises(MicrosoftGraphSubscriptionStateStoreError, match="tenant does not match"):
        store.apply_lifecycle(notification)
    store.close()


def test_reauthorization_preserves_possible_gap_state(tmp_path: Path) -> None:
    store = SQLiteMicrosoftGraphSubscriptionStore(tmp_path / "graph-state.db")
    store.register(_state(gap_state="possible"))

    updated = store.apply_lifecycle(_lifecycle(event="reauthorizationRequired"))

    assert updated.status == "reauthorization_required"
    assert updated.gap_state == "possible"
    store.close()


def test_replace_for_resource_removes_prior_subscription_atomically(tmp_path: Path) -> None:
    database = tmp_path / "graph-state.db"
    store = SQLiteMicrosoftGraphSubscriptionStore(database)
    store.register(_state(subscription_id="subscription-old"))

    replacement = _state(
        subscription_id="subscription-new",
        gap_state="possible",
    )
    store.replace_for_resource(replacement)

    assert store.get("subscription-old") is None
    assert store.get_for_resource(
        tenant_id=TENANT_ID,
        resource="drives/drive-001/root",
    ) == replacement
    store.close()


def test_resource_lookup_fails_closed_on_duplicate_subscriptions(tmp_path: Path) -> None:
    store = SQLiteMicrosoftGraphSubscriptionStore(tmp_path / "graph-state.db")
    store.register(_state(subscription_id="subscription-one"))
    store.register(_state(subscription_id="subscription-two"))

    with pytest.raises(
        MicrosoftGraphSubscriptionStateStoreError,
        match="multiple Graph subscriptions",
    ):
        store.get_for_resource(
            tenant_id=TENANT_ID,
            resource="drives/drive-001/root",
        )
    store.close()
