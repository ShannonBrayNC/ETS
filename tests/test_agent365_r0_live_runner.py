from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from ets.demos.agent365_r0_live_runner import (
    Agent365R0LiveLaunchError,
    authorize_live_hardware_launch,
)

MISSION_ID = "11111111-1111-4111-8111-111111111111"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
ITEM_ID = "42"


def _inputs() -> tuple[Any, Any, Any]:
    qualification = SimpleNamespace(
        packet=SimpleNamespace(
            qualification_state="qualified",
            live_attestation=object(),
            mission_id=MISSION_ID,
            tenant_id=TENANT_ID,
            sharepoint_item_id=ITEM_ID,
        )
    )
    sharepoint = SimpleNamespace(
        mission=SimpleNamespace(mission_id=MISSION_ID),
        source=SimpleNamespace(tenant_id=TENANT_ID),
        source_item_id=ITEM_ID,
    )
    correlation = SimpleNamespace(
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        sharepoint_item_id=ITEM_ID,
    )
    return qualification, sharepoint, correlation


def _authorize(
    qualification: Any,
    sharepoint: Any,
    correlation: Any,
    *,
    confirmed_mission_id: str = MISSION_ID,
    execute_live_mission: bool = True,
) -> str:
    return authorize_live_hardware_launch(
        qualification=cast(Any, qualification),
        sharepoint_observation=cast(Any, sharepoint),
        correlation_bundle=cast(Any, correlation),
        confirmed_mission_id=confirmed_mission_id,
        execute_live_mission=execute_live_mission,
    )


def test_live_launcher_requires_explicit_execution_flag() -> None:
    qualification, sharepoint, correlation = _inputs()

    with pytest.raises(Agent365R0LiveLaunchError, match="--execute-live-mission"):
        _authorize(
            qualification,
            sharepoint,
            correlation,
            execute_live_mission=False,
        )


def test_live_launcher_requires_exact_operator_mission_confirmation() -> None:
    qualification, sharepoint, correlation = _inputs()

    with pytest.raises(Agent365R0LiveLaunchError, match="operator confirmation"):
        _authorize(
            qualification,
            sharepoint,
            correlation,
            confirmed_mission_id="33333333-3333-4333-8333-333333333333",
        )


def test_live_launcher_rejects_unqualified_profile() -> None:
    qualification, sharepoint, correlation = _inputs()
    qualification.packet.qualification_state = "ready_for_live_qualification"

    with pytest.raises(Agent365R0LiveLaunchError, match="exactly qualified"):
        _authorize(qualification, sharepoint, correlation)


def test_live_launcher_rejects_cross_mission_correlation() -> None:
    qualification, sharepoint, correlation = _inputs()
    correlation.mission_id = "33333333-3333-4333-8333-333333333333"

    with pytest.raises(Agent365R0LiveLaunchError, match="correlation belongs to another"):
        _authorize(qualification, sharepoint, correlation)


def test_live_launcher_authorizes_only_the_exact_retained_mission() -> None:
    qualification, sharepoint, correlation = _inputs()

    assert _authorize(qualification, sharepoint, correlation) == MISSION_ID
