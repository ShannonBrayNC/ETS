"""Microsoft Graph webhook subscription and lifecycle boundary for G2E-B."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from ets.connectors.enterprise.microsoft import MicrosoftCloud

GRAPH_NOTIFICATION_SCHEMA_VERSION = "ets.connector.microsoft.graph_notification.v1"
GRAPH_SUBSCRIPTION_STATE_SCHEMA_VERSION = "ets.connector.microsoft.graph_subscription_state.v1"
GRAPH_DEFAULT_MAXIMUM_BODY_BYTES = 1024 * 1024
GRAPH_DEFAULT_MAXIMUM_NOTIFICATIONS = 100
GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS = 128

GraphLifecycleEvent = Literal[
    "reauthorizationRequired",
    "subscriptionRemoved",
    "missed",
]
GraphSubscriptionStatus = Literal[
    "active",
    "reauthorization_required",
    "removed",
]
GraphGapState = Literal["none", "possible"]
GraphNotificationKind = Literal["resource", "lifecycle"]


class MicrosoftGraphNotificationError(ValueError):
    """Raised when a Microsoft Graph notification fails the qualified boundary."""


class StrictGraphModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftGraphSubscriptionStateV1(StrictGraphModel):
    """Operational subscription state; separate from ETS canonical evidence state."""

    schema_version: Literal["ets.connector.microsoft.graph_subscription_state.v1"]
    subscription_id: str = Field(min_length=1, max_length=200)
    tenant_id: str = Field(min_length=36, max_length=36)
    cloud: MicrosoftCloud
    resource: str = Field(min_length=1, max_length=2000)
    client_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expiration_date_time: datetime
    status: GraphSubscriptionStatus = "active"
    gap_state: GraphGapState = "none"

    @field_validator("expiration_date_time")
    @classmethod
    def normalize_expiration(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Graph subscription expiration must be timezone-aware")
        return value.astimezone(UTC)


class MicrosoftGraphNotificationV1(StrictGraphModel):
    """Minimized Graph webhook observation with no reusable clientState or actor inference."""

    schema_version: Literal["ets.connector.microsoft.graph_notification.v1"]
    source_record_id: str = Field(min_length=1, max_length=100)
    kind: GraphNotificationKind
    subscription_id: str = Field(min_length=1, max_length=200)
    tenant_id: str = Field(min_length=36, max_length=36)
    subscription_expiration_date_time: datetime
    change_type: str | None = Field(default=None, min_length=1, max_length=100)
    resource: str | None = Field(default=None, min_length=1, max_length=2000)
    resource_data: dict[str, JsonValue] = Field(default_factory=dict)
    lifecycle_event: GraphLifecycleEvent | None = None

    @field_validator("subscription_expiration_date_time")
    @classmethod
    def normalize_expiration(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Graph notification expiration must be timezone-aware")
        return value.astimezone(UTC)


class MicrosoftGraphNotificationBatchV1(StrictGraphModel):
    notifications: tuple[MicrosoftGraphNotificationV1, ...]


def hash_graph_client_state(client_state: str) -> str:
    """Hash the bounded secret clientState so runtime state need not retain it in plaintext."""

    if not 1 <= len(client_state) <= GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS:
        raise ValueError("Graph clientState must be 1-128 characters")
    if any(ord(character) < 0x20 for character in client_state):
        raise ValueError("Graph clientState must not contain control characters")
    return hashlib.sha256(client_state.encode("utf-8")).hexdigest()


def validate_graph_validation_token(token: str) -> str:
    """Validate only safe response framing and otherwise preserve the opaque token exactly."""

    if not 1 <= len(token) <= 4096:
        raise MicrosoftGraphNotificationError("Graph validation token is outside the bounded profile")
    if any(character in token for character in ("\x00", "\r", "\n")):
        raise MicrosoftGraphNotificationError("Graph validation token contains unsafe control data")
    return token


def parse_graph_notification_collection(
    payload: bytes,
    *,
    subscriptions: Mapping[str, MicrosoftGraphSubscriptionStateV1],
    maximum_body_bytes: int = GRAPH_DEFAULT_MAXIMUM_BODY_BYTES,
    maximum_notifications: int = GRAPH_DEFAULT_MAXIMUM_NOTIFICATIONS,
) -> MicrosoftGraphNotificationBatchV1:
    """Decode and authenticate one bounded Graph webhook notification collection."""

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
        raise MicrosoftGraphNotificationError("Graph notification body contains unsupported root fields")
    values = decoded.get("value")
    if not isinstance(values, list):
        raise MicrosoftGraphNotificationError("Graph notification value must be an array")
    if len(values) > maximum_notifications:
        raise MicrosoftGraphNotificationError("Graph notification batch exceeds configured limit")

    observations: list[MicrosoftGraphNotificationV1] = []
    for raw in values:
        if not isinstance(raw, dict):
            raise MicrosoftGraphNotificationError("Graph notification batch contains a non-object item")
        subscription_id = _required_string(raw, "subscriptionId", 200)
        subscription = subscriptions.get(subscription_id)
        if subscription is None:
            raise MicrosoftGraphNotificationError("Graph notification references an unknown subscription")
        observations.append(_parse_notification(raw, subscription))
    return MicrosoftGraphNotificationBatchV1(notifications=tuple(observations))


def apply_graph_lifecycle_event(
    subscription: MicrosoftGraphSubscriptionStateV1,
    notification: MicrosoftGraphNotificationV1,
) -> MicrosoftGraphSubscriptionStateV1:
    """Return the fail-honest operational state after one lifecycle notification."""

    if notification.kind != "lifecycle" or notification.lifecycle_event is None:
        raise ValueError("notification must be a Graph lifecycle observation")
    if notification.subscription_id != subscription.subscription_id:
        raise ValueError("lifecycle notification subscription does not match state")

    if notification.lifecycle_event == "reauthorizationRequired":
        status: GraphSubscriptionStatus = "reauthorization_required"
        gap_state: GraphGapState = subscription.gap_state
    elif notification.lifecycle_event in {"subscriptionRemoved", "missed"}:
        status = "removed" if notification.lifecycle_event == "subscriptionRemoved" else subscription.status
        gap_state = "possible"
    else:  # pragma: no cover - guarded by the strict Literal model
        raise ValueError("unsupported Graph lifecycle event")

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
    tenant_id = _required_string(raw, "tenantId", 36)
    if tenant_id.casefold() != subscription.tenant_id.casefold():
        raise MicrosoftGraphNotificationError("Graph notification tenant does not match subscription")

    client_state = _required_string(raw, "clientState", GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS)
    provided_hash = hash_graph_client_state(client_state)
    if not hmac.compare_digest(provided_hash, subscription.client_state_sha256):
        raise MicrosoftGraphNotificationError("Graph notification clientState validation failed")

    expiration = _required_timestamp(raw, "subscriptionExpirationDateTime")
    lifecycle_event = raw.get("lifecycleEvent")
    if lifecycle_event is not None:
        if lifecycle_event not in {"reauthorizationRequired", "subscriptionRemoved", "missed"}:
            raise MicrosoftGraphNotificationError("Graph lifecycle event is not supported")
        return MicrosoftGraphNotificationV1(
            schema_version="ets.connector.microsoft.graph_notification.v1",
            source_record_id=_source_record_id(raw, subscription.subscription_id),
            kind="lifecycle",
            subscription_id=subscription.subscription_id,
            tenant_id=subscription.tenant_id,
            subscription_expiration_date_time=expiration,
            lifecycle_event=lifecycle_event,
        )

    change_type = _required_string(raw, "changeType", 100)
    resource = _required_string(raw, "resource", 2000)
    resource_data = _bounded_resource_data(raw.get("resourceData"))
    return MicrosoftGraphNotificationV1(
        schema_version="ets.connector.microsoft.graph_notification.v1",
        source_record_id=_source_record_id(raw, subscription.subscription_id),
        kind="resource",
        subscription_id=subscription.subscription_id,
        tenant_id=subscription.tenant_id,
        subscription_expiration_date_time=expiration,
        change_type=change_type,
        resource=resource,
        resource_data=resource_data,
    )


def _bounded_resource_data(value: object) -> dict[str, JsonValue]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise MicrosoftGraphNotificationError("Graph resourceData must be an object")
    result: dict[str, JsonValue] = {}
    for key in ("id", "@odata.type", "@odata.id", "@odata.etag"):
        item = value.get(key)
        if isinstance(item, str) and item:
            result[key] = item[:2000]
    return result


def _source_record_id(raw: Mapping[str, object], subscription_id: str) -> str:
    notification_id = raw.get("id")
    if isinstance(notification_id, str) and notification_id:
        material: object = [
            "ets.connector.microsoft.graph-notification-id.v1",
            subscription_id,
            notification_id[:1000],
        ]
    else:
        material = {
            "schema": "ets.connector.microsoft.graph-notification-id.v1",
            "subscription_id": subscription_id,
            "tenant_id": raw.get("tenantId"),
            "change_type": raw.get("changeType"),
            "resource": raw.get("resource"),
            "lifecycle_event": raw.get("lifecycleEvent"),
            "expiration": raw.get("subscriptionExpirationDateTime"),
            "resource_data": _bounded_resource_data(raw.get("resourceData")),
        }
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "graph-notification:" + hashlib.sha256(encoded).hexdigest()


def _required_string(source: Mapping[str, object], key: str, maximum: int) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise MicrosoftGraphNotificationError(f"Graph notification field {key} is invalid")
    return value


def _required_timestamp(source: Mapping[str, object], key: str) -> datetime:
    raw = _required_string(source, key, 100)
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise MicrosoftGraphNotificationError(
            f"Graph notification field {key} is not an ISO timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MicrosoftGraphNotificationError(
            f"Graph notification field {key} must be timezone-aware"
        )
    return parsed.astimezone(UTC)
