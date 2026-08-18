"""Join validated SharePoint Graph notifications to qualified delta recollection.

Microsoft Graph notifications remain operational discovery signals. This boundary
validates the notification against server-owned subscription/profile state, resumes
from the preserved delta checkpoint, and commits only recollected delta observations
through the shared Gateway connector path. The notification source identity is carried
as correlation metadata; the notification payload itself is not promoted to evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphNotificationV1,
    MicrosoftGraphSubscriptionStateV1,
)
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    MicrosoftSharePointDeltaRequestProfile,
)
from ets.connectors.enterprise.microsoft_sharepoint_notifications import (
    SharePointRecollectionDirectiveV1,
    plan_sharepoint_recollection,
)
from ets.connectors.models import ConnectorCheckpointV1, ConnectorInstanceV1
from ets.connectors.sdk import ConnectorAdapter
from ets.gateway.connector_runner import (
    GatewayConnectorCandidateHook,
    GatewayConnectorCollectionRunner,
    GatewayConnectorReleaseHook,
    GatewayConnectorRunResult,
)


@dataclass(frozen=True, slots=True)
class GatewaySharePointRecollectionResultV1:
    """Validated notification plan plus the resulting bounded Gateway collection pass."""

    directive: SharePointRecollectionDirectiveV1
    run: GatewayConnectorRunResult


class GatewayMicrosoftSharePointRecollectionService:
    """Execute notification-triggered SharePoint delta recollection through Gateway."""

    def __init__(
        self,
        runner: GatewayConnectorCollectionRunner,
        *,
        adapter: ConnectorAdapter,
        instance: ConnectorInstanceV1,
        principal: str,
        subscription: MicrosoftGraphSubscriptionStateV1,
        profile: MicrosoftSharePointDeltaRequestProfile,
        candidate_hook: GatewayConnectorCandidateHook | None = None,
        release_hook: GatewayConnectorReleaseHook | None = None,
    ) -> None:
        if not principal:
            raise ValueError("SharePoint Gateway principal is required")
        self._runner = runner
        self._adapter = adapter
        self._instance = instance
        self._principal = principal
        self._subscription = subscription
        self._profile = profile
        self._candidate_hook = candidate_hook
        self._release_hook = release_hook

    def commit(
        self,
        notification: MicrosoftGraphNotificationV1,
        checkpoint: ConnectorCheckpointV1 | None,
    ) -> GatewaySharePointRecollectionResultV1:
        """Recollect from preserved delta state and correlate resulting evidence to the trigger."""

        directive = plan_sharepoint_recollection(
            notification,
            self._subscription,
            self._profile,
            checkpoint,
        )
        run = self._runner.run(
            adapter=self._adapter,
            instance=self._instance,
            principal=self._principal,
            checkpoint=directive.resume_checkpoint,
            correlation_id=directive.source_record_id,
            candidate_hook=self._candidate_hook,
            release_hook=self._release_hook,
        )
        return GatewaySharePointRecollectionResultV1(directive=directive, run=run)
