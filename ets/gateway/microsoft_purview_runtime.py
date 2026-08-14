"""Operational watermark and gap policy for Microsoft Purview Management Activity."""

from __future__ import annotations

from datetime import datetime

from ets.connectors.runtime import ConnectorRuntimeStateV1
from ets.gateway.connector_management import (
    ConnectorManagementPrincipal,
    ConnectorManagementService,
)
from ets.gateway.connector_runner import GatewayConnectorRunResult

PURVIEW_CONNECTOR_ID = "microsoft.purview.activity"


class MicrosoftPurviewRuntimeError(RuntimeError):
    """Raised when Purview operational state would cross a qualification boundary."""


def mark_microsoft_purview_collection_gap(
    service: ConnectorManagementService,
    principal: ConnectorManagementPrincipal,
    instance_id: str,
) -> ConnectorRuntimeStateV1:
    """Open a Purview observation gap without changing the durable source watermark."""

    _require_purview_instance(service, principal, instance_id)
    return service.mark_gap(principal, instance_id)


def persist_microsoft_purview_gateway_success(
    service: ConnectorManagementService,
    principal: ConnectorManagementPrincipal,
    instance_id: str,
    result: GatewayConnectorRunResult,
    *,
    expected_checkpoint_revision: int,
    completed_at_utc: datetime,
) -> ConnectorRuntimeStateV1:
    """Persist only a Gateway-released Purview checkpoint and reconcile only a final page."""

    _require_purview_instance(service, principal, instance_id)
    checkpoint = result.checkpoint_to_persist
    if result.code != "ok" or checkpoint is None:
        raise MicrosoftPurviewRuntimeError(
            "Purview source progress requires a successful Gateway run with a released checkpoint"
        )

    runtime = service.get_runtime(principal, instance_id)
    if runtime.checkpoint_revision != expected_checkpoint_revision:
        raise MicrosoftPurviewRuntimeError(
            "Purview checkpoint revision changed before source progress could be persisted"
        )

    if runtime.gap_open:
        persisted = service.update_checkpoint(
            principal,
            instance_id,
            checkpoint,
            expected_checkpoint_revision=expected_checkpoint_revision,
            observation_state="collection_gap",
            gap_open=True,
            last_success_at_utc=completed_at_utc,
        )
        if result.has_more:
            return persisted
        return service.reconcile_gap(principal, instance_id)

    return service.update_checkpoint(
        principal,
        instance_id,
        checkpoint,
        expected_checkpoint_revision=expected_checkpoint_revision,
        observation_state="healthy_observation",
        gap_open=False,
        last_success_at_utc=completed_at_utc,
    )


def _require_purview_instance(
    service: ConnectorManagementService,
    principal: ConnectorManagementPrincipal,
    instance_id: str,
) -> None:
    record = service.get_instance(principal, instance_id)
    if record.instance.connector_id != PURVIEW_CONNECTOR_ID:
        raise MicrosoftPurviewRuntimeError(
            "Purview runtime policy may only manage microsoft.purview.activity instances"
        )
