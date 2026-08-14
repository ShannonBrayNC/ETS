from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationError,
    MicrosoftGraphSubscriptionStateV1,
    apply_graph_lifecycle_event,
    hash_graph_client_state,
    parse_graph_notification_collection,
    validate_graph_validation_token,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
SUBSCRIPTION_ID = "subscription-001"
CLIENT_STATE = "fixture-client-state"
NOW = datetime(2026, 8, 14, 5, 30, tzinfo=UTC)
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
            "@odata.id": "Users/user-001",
            "@odata.etag": "W/fixture",
            "mail": "alice@example.test",
            "raw_marker": "RAW-GRAPH-MARKER",
        },
        "actor": {"displayName": "should-not-be-attributed"},
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


def _payload(*notifications: dict[str, object]) -> bytes:
    return json.dumps({"value": list(notifications)}).encode("utf-8")


def test_validation_token_is_preserved_exactly_but_response_controls_are_rejected() -> None:
    token = "opaque%2Btoken-123"

    assert validate_graph_validation_token(token) == token
    with pytest.raises(MicrosoftGraphNotificationError, match="unsafe control"):
        validate_graph_validation_token("bad\r\ntoken")


def test_resource_notification_validates_subscription_tenant_and_client_state() -> None:
    subscription = _subscription()

    batch = parse_graph_notification_collection(
        _payload(_resource_notification()),
        subscriptions={SUBSCRIPTION_ID: subscription},
    )

    assert len(batch.notifications) == 1
    notification = batch.notifications[0]
    assert notification.kind == "resource"
    assert notification.subscription_id == SUBSCRIPTION_ID
    assert notification.tenant_id == TENANT_ID
    assert notification.change_type == "updated"
    assert notification.resource == "users/user-001"
    assert notification.resource_data["id"] == "user-001"
    serialized = json.dumps(notification.model_dump(mode="json"))
    assert CLIENT_STATE not in serialized
    assert "alice@example.test" not in serialized
    assert "RAW-GRAPH-MARKER" not in serialized
    assert "should-not-be-attributed" not in serialized


def test_wrong_client_state_fails_closed_without_observation() -> None:
    subscription = _subscription()

    with pytest.raises(MicrosoftGraphNotificationError, match="clientState validation"):
        parse_graph_notification_collection(
            _payload(_resource_notification(client_state="wrong-client-state")),
            subscriptions={SUBSCRIPTION_ID: subscription},
        )


def test_foreign_tenant_and_unknown_subscription_fail_closed() -> None:
    subscription = _subscription()
    foreign = _resource_notification()
    foreign["tenantId"] = "22222222-2222-2222-2222-222222222222"

    with pytest.raises(MicrosoftGraphNotificationError, match="tenant does not match"):
        parse_graph_notification_collection(
            _payload(foreign),
            subscriptions={SUBSCRIPTION_ID: subscription},
        )
    with pytest.raises(MicrosoftGraphNotificationError, match="unknown subscription"):
        parse_graph_notification_collection(
            _payload(_resource_notification()),
            subscriptions={},
        )


def test_duplicate_delivery_derives_same_bounded_source_record_identity() -> None:
    subscription = _subscription()
    payload = _payload(_resource_notification())

    first = parse_graph_notification_collection(
        payload,
        subscriptions={SUBSCRIPTION_ID: subscription},
    ).notifications[0]
    second = parse_graph_notification_collection(
        payload,
        subscriptions={SUBSCRIPTION_ID: subscription},
    ).notifications[0]

    assert first.source_record_id == second.source_record_id
    assert first.source_record_id.startswith("graph-notification:")
    assert len(first.source_record_id) == len("graph-notification:") + 64


@pytest.mark.parametrize(
    ("event", "expected_status", "expected_gap"),
    [
        ("reauthorizationRequired", "reauthorization_required", "none"),
        ("subscriptionRemoved", "removed", "possible"),
        ("missed", "active", "possible"),
    ],
)
def test_lifecycle_notifications_update_operational_state_without_claiming_recovery(
    event: str,
    expected_status: str,
    expected_gap: str,
) -> None:
    subscription = _subscription()
    notification = parse_graph_notification_collection(
        _payload(_lifecycle_notification(event)),
        subscriptions={SUBSCRIPTION_ID: subscription},
    ).notifications[0]

    updated = apply_graph_lifecycle_event(subscription, notification)

    assert notification.kind == "lifecycle"
    assert notification.change_type is None
    assert notification.resource is None
    assert updated.status == expected_status
    assert updated.gap_state == expected_gap


def test_batch_and_body_bounds_are_enforced_before_processing() -> None:
    subscription = _subscription()
    payload = _payload(_resource_notification())

    with pytest.raises(MicrosoftGraphNotificationError, match="body exceeds"):
        parse_graph_notification_collection(
            payload,
            subscriptions={SUBSCRIPTION_ID: subscription},
            maximum_body_bytes=len(payload) - 1,
        )
    with pytest.raises(MicrosoftGraphNotificationError, match="batch exceeds"):
        parse_graph_notification_collection(
            _payload(_resource_notification(), _resource_notification()),
            subscriptions={SUBSCRIPTION_ID: subscription},
            maximum_notifications=1,
        )


def test_unknown_root_fields_and_unsupported_lifecycle_events_are_rejected() -> None:
    subscription = _subscription()
    malformed = json.dumps(
        {
            "value": [_resource_notification()],
            "validationTokens": ["not-qualified-in-basic-profile"],
        }
    ).encode("utf-8")

    with pytest.raises(MicrosoftGraphNotificationError, match="unsupported root fields"):
        parse_graph_notification_collection(
            malformed,
            subscriptions={SUBSCRIPTION_ID: subscription},
        )
    with pytest.raises(MicrosoftGraphNotificationError, match="lifecycle event"):
        parse_graph_notification_collection(
            _payload(_lifecycle_notification("futureUnknownEvent")),
            subscriptions={SUBSCRIPTION_ID: subscription},
        )
