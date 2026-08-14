from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphSubscriptionStateV1,
    hash_graph_client_state,
)
from ets.gateway.microsoft_graph_webhook import (
    GRAPH_WEBHOOK_PATH,
    InMemoryMicrosoftGraphSubscriptionStore,
    create_microsoft_graph_webhook_app,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
SUBSCRIPTION_ID = "subscription-001"
CLIENT_STATE = "fixture-client-state"
RAW_MARKER = "RAW-GRAPH-HOST-MARKER"
NOW = datetime(2026, 8, 14, 13, 0, tzinfo=UTC)
EXPIRATION = NOW + timedelta(hours=1)


def _subscription() -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1(
        schema_version="ets.connector.microsoft.graph_subscription_state.v1",
        subscription_id=SUBSCRIPTION_ID,
        tenant_id=TENANT_ID,
        cloud="global",
        resource="users",
        client_state_sha256=hash_graph_client_state(CLIENT_STATE),
        expiration_date_time=EXPIRATION,
        status="active",
        gap_state="none",
    )


def _resource_notification(*, client_state: str = CLIENT_STATE) -> dict[str, object]:
    return {
        "id": "notification-001",
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionExpirationDateTime": EXPIRATION.isoformat(),
        "tenantId": TENANT_ID,
        "clientState": client_state,
        "changeType": "updated",
        "resource": "users/user-001",
        "resourceData": {
            "id": "user-001",
            "@odata.type": "#Microsoft.Graph.User",
            "raw_marker": RAW_MARKER,
            "mail": "alice@example.test",
        },
        "actor": {"displayName": "must-not-be-attributed"},
    }


def _lifecycle_notification(event: str) -> dict[str, object]:
    return {
        "id": f"lifecycle-{event}",
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionExpirationDateTime": EXPIRATION.isoformat(),
        "tenantId": TENANT_ID,
        "clientState": CLIENT_STATE,
        "lifecycleEvent": event,
    }


def _client(
    *,
    maximum_body_bytes: int = 1024 * 1024,
) -> tuple[TestClient, InMemoryMicrosoftGraphSubscriptionStore]:
    store = InMemoryMicrosoftGraphSubscriptionStore(
        {SUBSCRIPTION_ID: _subscription()}
    )
    app = create_microsoft_graph_webhook_app(
        store,
        maximum_body_bytes=maximum_body_bytes,
    )
    return TestClient(app), store


def test_graph_endpoint_validation_echoes_only_the_opaque_token_as_plain_text() -> None:
    client, store = _client()

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        params={"validationToken": "opaque-token-123"},
    )

    assert response.status_code == 200
    assert response.text == "opaque-token-123"
    assert response.headers["content-type"] == "text/plain"
    assert store.snapshot()[SUBSCRIPTION_ID].status == "active"


def test_graph_endpoint_validation_rejects_ambiguous_query_parameters() -> None:
    client, _ = _client()

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        params=[("validationToken", "one"), ("unexpected", "two")],
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid Microsoft Graph webhook request"}


def test_resource_notification_is_accepted_only_as_pre_commit_state() -> None:
    client, store = _client()

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [_resource_notification()]},
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted_pre_commit",
        "notification_count": 1,
        "lifecycle_updates": 0,
    }
    serialized = response.text
    assert RAW_MARKER not in serialized
    assert "alice@example.test" not in serialized
    assert "must-not-be-attributed" not in serialized
    assert CLIENT_STATE not in serialized
    assert store.snapshot()[SUBSCRIPTION_ID].gap_state == "none"


def test_lifecycle_missed_updates_operational_gap_without_claiming_recovery() -> None:
    client, store = _client()

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [_lifecycle_notification("missed")]},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted_pre_commit"
    assert response.json()["lifecycle_updates"] == 1
    state = store.snapshot()[SUBSCRIPTION_ID]
    assert state.status == "active"
    assert state.gap_state == "possible"


def test_subscription_removed_is_preserved_as_removed_with_possible_gap() -> None:
    client, store = _client()

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [_lifecycle_notification("subscriptionRemoved")]},
    )

    assert response.status_code == 202
    state = store.snapshot()[SUBSCRIPTION_ID]
    assert state.status == "removed"
    assert state.gap_state == "possible"


def test_invalid_client_state_fails_closed_without_mutating_subscription_state() -> None:
    client, store = _client()

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [_resource_notification(client_state="wrong-client-state")]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid Microsoft Graph webhook request"}
    state = store.snapshot()[SUBSCRIPTION_ID]
    assert state.status == "active"
    assert state.gap_state == "none"


def test_unknown_subscription_fails_closed() -> None:
    client, _ = _client()
    notification = _resource_notification()
    notification["subscriptionId"] = "unknown-subscription"

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        json={"value": [notification]},
    )

    assert response.status_code == 400


def test_notification_query_parameters_are_rejected_outside_validation_flow() -> None:
    client, _ = _client()

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        params={"unexpected": "value"},
        json={"value": [_resource_notification()]},
    )

    assert response.status_code == 400


def test_graph_webhook_rejects_unqualified_content_type_and_encoding() -> None:
    client, _ = _client()
    payload = json.dumps({"value": [_resource_notification()]})

    wrong_media = client.post(
        GRAPH_WEBHOOK_PATH,
        content=payload,
        headers={"Content-Type": "text/plain"},
    )
    encoded = client.post(
        GRAPH_WEBHOOK_PATH,
        content=payload,
        headers={
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
        },
    )

    assert wrong_media.status_code == 400
    assert encoded.status_code == 415


def test_graph_webhook_rejects_advertised_oversize_before_parsing() -> None:
    client, store = _client(maximum_body_bytes=64)
    payload = json.dumps({"value": [_resource_notification()]})
    assert len(payload.encode("utf-8")) > 64

    response = client.post(
        GRAPH_WEBHOOK_PATH,
        content=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert store.snapshot()[SUBSCRIPTION_ID].gap_state == "none"
