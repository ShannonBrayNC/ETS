"""Microsoft Graph webhook and subscription operational boundary for G2E-B."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from ets.connectors.enterprise.microsoft import MicrosoftCloud

GRAPH_DEFAULT_MAXIMUM_BODY_BYTES = 1024 * 1024
GRAPH_DEFAULT_MAXIMUM_NOTIFICATIONS = 100
GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS = 255
GRAPH_MAXIMUM_RESOURCE_CHARACTERS = 2000
GRAPH_MAXIMUM_RESOURCE_DATA_FIELDS = 8

GraphSubscriptionStatus = Literal[
    "active",
    "reauthorization_required",
    "removed",
    "disabled",
]
GraphGapState = Literal["none", "possible", "reconciling"]
GraphNotificationKind = Literal["resource", "lifecycle"]
GraphLifecycleEvent = Literal["reauthorizationRequired", "subscriptionRemoved", "missed"]


class MicrosoftGraphNotificationError(ValueError):
    """Raised when a Graph webhook request fails the qualified boundary."""


class StrictGraphModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftGraphSubscriptionStateV1(StrictGraphModel):
    """Operational subscription state; never ETS canonical evidence state."""

    schema_version: Literal["ets.connector.microsoft.graph_subscription_state.v1"]
    subscription_id: str = Field(min_length=1, max_length=200)
    tenant_id: str = Field(min_length=36, max_length=36)
    cloud: MicrosoftCloud
    resource: str = Field(min_length=1, max_length=GRAPH_MAXIMUM_RESOURCE_CHARACTERS)
    client_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expiration_date_time: datetime
    status: GraphSubscriptionStatus
    gap_state: GraphGapState = "none"

    @field_validator("expiration_date_time")
    @classmethod
    def normalize_expiration(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Graph subscription expiration must be timezone-aware")
        return value.astimezone(UTC)


class MicrosoftGraphNotificationV1(StrictGraphModel):
    """Minimized Graph notification observation with no actor-attribution inference."""

    schema_version: Literal["ets.connector.microsoft.graph_notification.v1"]
    source_record_id: str = Field(min_length=1, max_length=100)
    kind: GraphNotificationKind
    subscription_id: str = Field(min_length=1, max_length=200)
    tenant_id: str = Field(min_length=36, max_length=36)
    subscription_expiration_date_time: datetime
    change_type: str | None = Field(default=None, min_length=1, max_length=100)
    resource: str | None = Field(
        default=None,
        min_length=1,
        max_length=GRAPH_MAXIMUM_RESOURCE_CHARACTERS,
    )
    lifecycle_event: GraphLifecycleEvent | None = None
    resource_data: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("subscription_expiration_date_time")
    @classmethod
    def normalize_notification_expiration(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Graph notification expiration must be timezone-aware")
        return value.astimezone(UTC)


class MicrosoftGraphNotificationBatchV1(StrictGraphModel):
    schema_version: Literal["ets.connector.microsoft.graph_notification_batch.v1"] = (
        "ets.connector.microsoft.graph_notification_batch.v1"
    )
    notifications: tuple[MicrosoftGraphNotificationV1, ...]


def hash_graph_client_state(value: str) -> str:
    """Hash the server-owned Graph clientState value before operational persistence."""

    if not 1 <= len(value) <= GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS:
        raise ValueError("Graph clientState length is invalid")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_graph_validation_token(token: str) -> str:
    """Validate an opaque endpoint-validation token for exact plain-text echo."""

    if not 1 <= len(token) <= 4096:
        raise MicrosoftGraphNotificationError(
            "Graph validation token is outside the bounded profile"
        )
    if any(character in token for character in ("\x00", "\r", "\n")):
        raise MicrosoftGraphNotificationError(
            "Graph validation token contains unsafe control data"
        )
    return token


def parse_graph_notification_collection(
    payload: bytes,
    *,
    subscriptions: Mapping[str, MicrosoftGraphSubscriptionStateV1],
    maximum_body_bytes: int = GRAPH_DEFAULT_MAXIMUM_BODY_BYTES,
    maximum_notifications: int = GRAPH_DEFAULT_MAXIMUM_NOTIFICATIONS,
) -> MicrosoftGraphNotificationBatchV1:
    """Parse one basic Graph resource/lifecycle notification collection."""

    if maximum_body_bytes < 1:
        raise ValueError("maximum_body_bytes must be positive")
    if not 1 <= maximum_notifications <= GRAPH_DEFAULT_MAXIMUM_NOTIFICATIONS:
        raise ValueError("maximum_notifications must be between 1 and 100")
    if not payload:
        raise MicrosoftGraphNotificationError("Graph notification body is empty")
    if len(payload) > maximum_body_bytes:
        raise MicrosoftGraphNotificationError("Graph notification body exceeds configured limit")

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftGraphNotificationError("Graph notification body is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise MicrosoftGraphNotificationError("Graph notification body must be an object")
    if set(decoded) != {"value"}:
        raise MicrosoftGraphNotificationError(
            "Graph notification body contains unsupported root fields"
        )
    values = decoded.get("value")
    if not isinstance(values, list):
        raise MicrosoftGraphNotificationError("Graph notification value must be an array")
    if len(values) > maximum_notifications:
        raise MicrosoftGraphNotificationError("Graph notification batch exceeds configured limit")

    observations: list[MicrosoftGraphNotificationV1] = []
    for raw in values:
        if not isinstance(raw, dict):
            raise MicrosoftGraphNotificationError(
                "Graph notification batch contains a non-object item"
            )
        subscription_id = _required_string(raw, "subscriptionId", 200)
        subscription = subscriptions.get(subscription_id)
        if subscription is None:
            raise MicrosoftGraphNotificationError(
                "Graph notification references an unknown subscription"
            )
        observations.append(_parse_notification(raw, subscription))
    return MicrosoftGraphNotificationBatchV1(notifications=tuple(observations))


def apply_graph_lifecycle_event(
    subscription: MicrosoftGraphSubscriptionStateV1,
    notification: MicrosoftGraphNotificationV1,
) -> MicrosoftGraphSubscriptionStateV1:
    """Return new operational state without claiming collection recovery."""

    if notification.kind != "lifecycle" or notification.lifecycle_event is None:
        raise ValueError("notification is not a lifecycle observation")
    if notification.subscription_id != subscription.subscription_id:
        raise ValueError("notification subscription does not match operational state")

    if notification.lifecycle_event == "reauthorizationRequired":
        status: GraphSubscriptionStatus = "reauthorization_required"
        gap_state: GraphGapState = subscription.gap_state
    elif notification.lifecycle_event in {"subscriptionRemoved", "missed"}:
        status = (
            "removed"
            if notification.lifecycle_event == "subscriptionRemoved"
            else subscription.status
        )
        gap_state = "possible"
    else:  # pragma: no cover - guarded by the strict Literal model
        raise ValueError("unsupported lifecycle event")
    return subscription.model_copy(
        update={
            "status": status,
            "gap_state": gap_state,
            "expiration_date_time": notification.subscription_expiration_date_time,
        }
    )


def _parse_notification(
    raw: Mapping[str, object],
    subscription: MicrosoftGraphSubscriptionStateV1,
) -> MicrosoftGraphNotificationV1:
    subscription_id = _required_string(raw, "subscriptionId", 200)
    tenant_id = _required_string(raw, "tenantId", 36)
    if tenant_id.casefold() != subscription.tenant_id.casefold():
        raise MicrosoftGraphNotificationError(
            "Graph notification tenant does not match subscription"
        )

    client_state = _required_string(
        raw,
        "clientState",
        GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS,
    )
    if not _constant_time_equal(
        hash_graph_client_state(client_state),
        subscription.client_state_sha256,
    ):
        raise MicrosoftGraphNotificationError("Graph notification clientState validation failed")

    expiration = _parse_datetime(
        _required_string(raw, "subscriptionExpirationDateTime", 100),
        "subscriptionExpirationDateTime",
    )
    lifecycle_event = raw.get("lifecycleEvent")
    if lifecycle_event is not None:
        if lifecycle_event not in {
            "reauthorizationRequired",
            "subscriptionRemoved",
            "missed",
        }:
            raise MicrosoftGraphNotificationError("Graph lifecycle event is not qualified")
        lifecycle = lifecycle_event
        kind: GraphNotificationKind = "lifecycle"
        change_type = None
        resource = None
        resource_data: dict[str, JsonValue] = {}
    else:
        lifecycle = None
        kind = "resource"
        change_type = _required_string(raw, "changeType", 100)
        resource = _required_string(
            raw,
            "resource",
            GRAPH_MAXIMUM_RESOURCE_CHARACTERS,
        )
        resource_data = _minimized_resource_data(raw.get("resourceData"))

    source_record_id = _source_record_id(
        raw,
        subscription_id=subscription_id,
        tenant_id=tenant_id,
        kind=kind,
        change_type=change_type,
        resource=resource,
        lifecycle_event=lifecycle,
        resource_data=resource_data,
    )
    return MicrosoftGraphNotificationV1(
        schema_version="ets.connector.microsoft.graph_notification.v1",
        source_record_id=source_record_id,
        kind=kind,
        subscription_id=subscription_id,
        tenant_id=tenant_id.lower(),
        subscription_expiration_date_time=expiration,
        change_type=change_type,
        resource=resource,
        lifecycle_event=lifecycle,
        resource_data=resource_data,
    )


def _minimized_resource_data(value: object) -> dict[str, JsonValue]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise MicrosoftGraphNotificationError("Graph resourceData must be an object")
    allowed = ("id", "@odata.type", "@odata.id", "@odata.etag")
    result: dict[str, JsonValue] = {}
    for key in allowed:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            result[key] = candidate[:1000]
    if len(result) > GRAPH_MAXIMUM_RESOURCE_DATA_FIELDS:  # pragma: no cover - bounded allow-list
        raise MicrosoftGraphNotificationError("Graph resourceData exceeds configured field limit")
    return result


def _source_record_id(
    raw: Mapping[str, object],
    *,
    subscription_id: str,
    tenant_id: str,
    kind: GraphNotificationKind,
    change_type: str | None,
    resource: str | None,
    lifecycle_event: GraphLifecycleEvent | None,
    resource_data: Mapping[str, JsonValue],
) -> str:
    notification_id = raw.get("id")
    bounded_notification_id = (
        notification_id[:500]
        if isinstance(notification_id, str) and notification_id
        else None
    )
    material = {
        "schema": "ets.connector.microsoft.graph-notification-id.v1",
        "notification_id": bounded_notification_id,
        "subscription_id": subscription_id,
        "tenant_id": tenant_id.lower(),
        "kind": kind,
        "change_type": change_type,
        "resource": resource,
        "lifecycle_event": lifecycle_event,
        "resource_data": dict(resource_data),
    }
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "graph-notification:" + hashlib.sha256(encoded).hexdigest()


def _required_string(raw: Mapping[str, object], key: str, maximum: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise MicrosoftGraphNotificationError(f"Graph notification {key} is invalid")
    return value


def _parse_datetime(value: str, field_name: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MicrosoftGraphNotificationError(
            f"Graph notification {field_name} is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MicrosoftGraphNotificationError(
            f"Graph notification {field_name} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def _constant_time_equal(left: str, right: str) -> bool:
    return __import__("hmac").compare_digest(left, right)
