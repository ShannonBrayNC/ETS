"""Pre-hardware launch gate for the first fully live Agent 365 -> physical R0 mission."""

from __future__ import annotations

from ets.demos.agent365_r0_correlation import Agent365R0CorrelationBundleV1
from ets.demos.agent365_r0_profile_qualification import Agent365ProfileQualificationResultV1
from ets.demos.agent365_r0_sharepoint_live import SharePointMissionLiveObservationV1


class Agent365R0LiveLaunchError(RuntimeError):
    """Raised before hardware initialization when the live launch gate is not satisfied."""


def authorize_live_hardware_launch(
    *,
    qualification: Agent365ProfileQualificationResultV1,
    sharepoint_observation: SharePointMissionLiveObservationV1,
    correlation_bundle: Agent365R0CorrelationBundleV1,
    confirmed_mission_id: str,
    execute_live_mission: bool,
) -> str:
    """Return the exact mission_id only when the operator and retained evidence agree.

    This gate must execute before GPIO, motor, or sensor backends are initialized.
    """

    mission_id = sharepoint_observation.mission.mission_id
    packet = qualification.packet

    if not execute_live_mission:
        raise Agent365R0LiveLaunchError(
            "live physical motion requires the explicit --execute-live-mission flag"
        )
    if confirmed_mission_id != mission_id:
        raise Agent365R0LiveLaunchError(
            "operator confirmation mission_id does not match the live SharePoint mission"
        )
    if packet.qualification_state != "qualified" or packet.live_attestation is None:
        raise Agent365R0LiveLaunchError(
            "live physical motion requires an exactly qualified Agent 365 profile"
        )
    if packet.mission_id != mission_id:
        raise Agent365R0LiveLaunchError(
            "qualified Agent 365 packet belongs to another mission_id"
        )
    if correlation_bundle.mission_id != mission_id:
        raise Agent365R0LiveLaunchError(
            "sanitized Agent 365 correlation belongs to another mission_id"
        )
    if packet.tenant_id != sharepoint_observation.tenant_id:
        raise Agent365R0LiveLaunchError(
            "qualified Agent 365 packet belongs to another Microsoft tenant"
        )
    if correlation_bundle.tenant_id != sharepoint_observation.tenant_id:
        raise Agent365R0LiveLaunchError(
            "sanitized Agent 365 correlation belongs to another Microsoft tenant"
        )
    if packet.sharepoint_item_id != sharepoint_observation.source_item_id:
        raise Agent365R0LiveLaunchError(
            "qualified Agent 365 packet targets another SharePoint item"
        )
    if correlation_bundle.sharepoint_item_id != sharepoint_observation.source_item_id:
        raise Agent365R0LiveLaunchError(
            "sanitized Agent 365 correlation targets another SharePoint item"
        )

    return mission_id


__all__ = [
    "Agent365R0LiveLaunchError",
    "authorize_live_hardware_launch",
]
