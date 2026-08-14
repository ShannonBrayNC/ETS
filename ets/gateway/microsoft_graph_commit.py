"""Commit qualified Microsoft Graph resource notifications through shared Gateway ingress.

Graph webhook receipt is not itself ETS evidence. This module maps only validated,
minimized resource notifications into the shared connector candidate contract and
requires local append plus durable sync enqueue before reporting commitment success.
Lifecycle notifications remain operational subscription/gap state.
"""

from __future__ import annotations

from typing import Final, Protocol

from ets.connectors.enterprise.microsoft_graph import MicrosoftGraphNotificationV1
from ets.connectors.models import ConnectorEvidenceCandidateV1
from ets.gateway.connector_capture import GatewayConnectorCandidateRequest
from ets.gateway.connector_ingress import GatewayConnectorIngressService
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressError,
    GatewayIngressReceipt,
    GatewayPartialCommitError,
)
from ets.gateway.source_registry import SourceAuthorizationError

MICROSOFT_GRAPH_SOURCE_SYSTEM: Final = "microsoft.graph"
MICROSOFT_GRAPH_RESOURCE_EVENT_TYPE: Final = "microsoft.graph.resource_notification"
MICROSOFT_GRAPH_TRANSFORMATION_PROFILE: Final = (
    "ets.connector.microsoft.graph-resource-notification.v1"
)


class MicrosoftGraphResourceCommitError(RuntimeError):
    """Base error for the Graph resource-to-Gateway commitment boundary."""


class MicrosoftGraphResourceCommitRetryableError(MicrosoftGraphResourceCommitError):
    """Raised when Graph should retry because qualified commitment is incomplete."""


class MicrosoftGraphResourceCommitTerminalError(MicrosoftGraphResourceCommitError):
    """Raised when a validated resource observation cannot enter this source profile."""


class MicrosoftGraphResourceCommitter(Protocol):
    """Minimal sink accepted by the Graph webhook host."""

    def commit(self, notification: MicrosoftGraphNotificationV1) -> GatewayIngressReceipt: ...


class GatewayMicrosoftGraphResourceCommitter:
    """Join Graph resource notifications to the existing Gateway connector ingress path."""

    def __init__(
        self,
        ingress: GatewayConnectorIngressService,
        *,
        principal: str,
    ) -> None:
        if not 1 <= len(principal) <= 500:
            raise ValueError("Microsoft Graph Gateway principal is outside configured bounds")
        self._ingress = ingress
        self._principal = principal

    def commit(self, notification: MicrosoftGraphNotificationV1) -> GatewayIngressReceipt:
        candidate = graph_resource_notification_to_candidate(notification)
        try:
            receipt = self._ingress.ingest_candidate(
                self._principal,
                GatewayConnectorCandidateRequest(candidate=candidate),
            )
        except (GatewayBackpressureError, GatewayPartialCommitError) as exc:
            raise MicrosoftGraphResourceCommitRetryableError(
                "Microsoft Graph resource observation did not reach durable Gateway queued state"
            ) from exc
        except (
            GatewayConflictError,
            GatewayIngressError,
            SourceAuthorizationError,
            ValueError,
        ) as exc:
            raise MicrosoftGraphResourceCommitTerminalError(
                "Microsoft Graph resource observation failed Gateway admission"
            ) from exc

        if not receipt.committed_local or not receipt.sync_queued:
            raise MicrosoftGraphResourceCommitRetryableError(
                "Microsoft Graph resource observation did not reach durable Gateway queued state"
            )
        return receipt


def graph_resource_notification_to_candidate(
    notification: MicrosoftGraphNotificationV1,
) -> ConnectorEvidenceCandidateV1:
    """Map one validated Graph resource observation without promoting runtime state."""

    if (
        notification.kind != "resource"
        or notification.change_type is None
        or notification.resource is None
        or notification.lifecycle_event is not None
    ):
        raise MicrosoftGraphResourceCommitTerminalError(
            "only Microsoft Graph resource notifications may enter evidence commitment"
        )

    return ConnectorEvidenceCandidateV1(
        schema_version="ets.connector.candidate.v1",
        source_record_id=notification.source_record_id,
        source_system=MICROSOFT_GRAPH_SOURCE_SYSTEM,
        observed_at_utc=None,
        event_type=MICROSOFT_GRAPH_RESOURCE_EVENT_TYPE,
        media_type="application/json",
        transformation_profile=MICROSOFT_GRAPH_TRANSFORMATION_PROFILE,
        lossless=False,
        metadata={
            "provider": "microsoft_graph",
            "source_class": "resource_notification",
            "change_type": notification.change_type,
            "resource": notification.resource,
            "resource_data": notification.resource_data,
        },
    )
