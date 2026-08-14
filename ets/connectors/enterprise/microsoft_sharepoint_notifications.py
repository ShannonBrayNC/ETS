"""Operational Graph-notification recollection planning for SharePoint/OneDrive.

Notifications are discovery signals only. This module never creates evidence and never
advances a SharePoint delta checkpoint. The caller must recollect from the preserved
checkpoint through the qualified delta adapter before any new source state can advance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaRequestProfile,
)
from ets.connectors.models import ConnectorCheckpointV1

SharePointRecollectionReason = Literal[
    "resource_notification",
    "missed_notification",
    "subscription_removed",
    "reauthorization_required",
]


class MicrosoftSharePointNotificationError(ValueError):
    """Raised when a Graph notification does not match the approved SharePoint source."""


@dataclass(frozen=True, slots=True)
class SharePointRecollectionDirectiveV1:
    """Pre-commit instruction to recollect from the current authoritative delta state."""

    source_record_id: str
    reason: SharePointRecollectionReason
    possible_gap: bool
    resume_checkpoint: ConnectorCheckpointV1 | None


def plan_sharepoint_recollection(
    notification: MicrosoftGraphNotificationV1,
    subscription: MicrosoftGraphSubscriptionStateV1,
    profile: MicrosoftSharePointDeltaRequestProfile,
    checkpoint: ConnectorCheckpointV1 | None,
) -> SharePointRecollectionDirectiveV1:
    """Validate one notification and request delta recollection without state advancement."""

    if notification.subscription_id != subscription.subscription_id:
        raise MicrosoftSharePointNotificationError(
            "SharePoint notification subscription does not match server-owned subscription"
        )
    if notification.tenant_id.casefold() != subscription.tenant_id.casefold():
        raise MicrosoftSharePointNotificationError(
            "SharePoint notification tenant does not match server-owned subscription"
        )
    if subscription.cloud != profile.cloud:
        raise MicrosoftSharePointNotificationError(
            "SharePoint notification subscription cloud does not match delta profile"
        )
    expected_resource = _expected_subscription_resource(profile)
    if _normalize_subscription_resource(subscription.resource) != expected_resource:
        raise MicrosoftSharePointNotificationError(
            "SharePoint notification subscription escaped the approved delta source"
        )

    if notification.kind == "resource":
        reason: SharePointRecollectionReason = "resource_notification"
        possible_gap = False
    elif notification.lifecycle_event == "missed":
        reason = "missed_notification"
        possible_gap = True
    elif notification.lifecycle_event == "subscriptionRemoved":
        reason = "subscription_removed"
        possible_gap = True
    elif notification.lifecycle_event == "reauthorizationRequired":
        reason = "reauthorization_required"
        possible_gap = subscription.gap_state == "possible"
    else:  # pragma: no cover - strict Graph model guards lifecycle values
        raise MicrosoftSharePointNotificationError(
            "SharePoint notification lifecycle event is not qualified"
        )

    return SharePointRecollectionDirectiveV1(
        source_record_id=notification.source_record_id,
        reason=reason,
        possible_gap=possible_gap,
        resume_checkpoint=checkpoint,
    )


def _expected_subscription_resource(profile: MicrosoftSharePointDeltaRequestProfile) -> str:
    prefix = "/v1.0"
    suffix = "/delta"
    path = profile.resource_path
    if not path.startswith(prefix + "/") or not path.endswith(suffix):
        raise MicrosoftSharePointNotificationError(
            "SharePoint delta profile cannot derive an approved subscription resource"
        )
    return path[len(prefix) : -len(suffix)]


def _normalize_subscription_resource(value: str) -> str:
    if not 1 <= len(value) <= 2000:
        raise MicrosoftSharePointNotificationError(
            "SharePoint Graph subscription resource is outside bounds"
        )
    if "://" in value or any(character in value for character in ("?", "#", "\x00", "\r", "\n")):
        raise MicrosoftSharePointNotificationError(
            "SharePoint Graph subscription resource is not a qualified relative path"
        )
    return "/" + value.strip("/")
