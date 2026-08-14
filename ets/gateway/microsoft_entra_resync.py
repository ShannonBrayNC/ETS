"""Authorized Microsoft Entra delta full-resync control for G2E-C."""

from __future__ import annotations

from ets.connectors.enterprise.microsoft_entra_connector import ENTRA_CONNECTOR_ID
from ets.connectors.runtime import ConnectorRuntimeStateV1
from ets.gateway.connector_management import (
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)


class MicrosoftEntraFullResyncError(RuntimeError):
    """Raised when an Entra full-resync reset is not currently authorized/safe."""


def authorize_microsoft_entra_full_resync(
    service: ConnectorManagementService,
    principal: ConnectorManagementPrincipal,
    instance_id: str,
    *,
    expected_checkpoint_revision: int,
) -> ConnectorRuntimeStateV1:
    """Clear expired Entra source state while deliberately keeping the gap open.

    The management service enforces connector.manage and tenant/workspace scope.
    A reset is permitted only after runtime state has already been marked as a
    collection gap. Clearing the cursor authorizes a fresh source synchronization;
    it does not reconcile or close the gap.
    """

    record = service.get_instance(principal, instance_id)
    if record.instance.connector_id != ENTRA_CONNECTOR_ID:
        raise MicrosoftEntraFullResyncError(
            "full-resync control is only valid for the Entra directory delta connector"
        )

    runtime = service.get_runtime(principal, instance_id)
    if runtime.checkpoint is None or runtime.checkpoint.cursor is None:
        raise MicrosoftEntraFullResyncError(
            "Entra full resync requires an existing source cursor"
        )
    if runtime.observation_state != "collection_gap" or not runtime.gap_open:
        raise MicrosoftEntraFullResyncError(
            "Entra full resync requires an explicitly open collection gap"
        )

    return service.update_checkpoint(
        principal,
        instance_id,
        None,
        expected_checkpoint_revision=expected_checkpoint_revision,
        observation_state="collection_gap",
        gap_open=True,
        last_success_at_utc=runtime.last_success_at_utc,
    )
