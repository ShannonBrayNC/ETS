from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import pytest

from ets.demos.agent365_r0_correlation import (
    Agent365ApiMaturity,
    Agent365IdentityObservationV1,
    Agent365R0CorrelationError,
    Agent365RetainedSourceRefV1,
    Agent365RuntimeObservationV1,
    Agent365ToolObservationV1,
    Agent365ToolStatus,
    SharePointMissionCorrelationAnchorV1,
    correlate_agent365_to_r0_mission,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
OTHER_MISSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
AUTH_DIGEST = "1" * 64
SOURCE_DIGEST = "2" * 64
T0 = datetime(2026, 9, 17, 22, 0, tzinfo=UTC)

SourceFamily = Literal[
    "agent365.catalog",
    "agent365.runtime.otel",
    "agent365.tool.otel",
]


def _source(
    family: SourceFamily,
    *,
    suffix: str,
) -> Agent365RetainedSourceRefV1:
    return Agent365RetainedSourceRefV1(
        tenant_id=TENANT_ID,
        source_family=family,
        api_maturity=Agent365ApiMaturity.DOCUMENTED_PREVIEW,
        acquisition_time=T0,
        microsoft_event_time=T0,
        payload_ref=f"ets://agent365/source/{suffix}",
        raw_payload_sha256=suffix * 64,
        source_envelope_sha256=suffix * 64,
        collector_identity="ets.agent365-test",
        collector_version="1.0",
    )


def _anchor() -> SharePointMissionCorrelationAnchorV1:
    return SharePointMissionCorrelationAnchorV1(
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        item_id="42",
        authorization_material_sha256=AUTH_DIGEST,
        source_payload_sha256=SOURCE_DIGEST,
        source_payload_ref="ets://microsoft/sharepoint/mission-source/sha256/source",
        acquired_at=T0,
    )


def _identity() -> Agent365IdentityObservationV1:
    return Agent365IdentityObservationV1(
        observation_id="identity:pkg-1",
        source=_source("agent365.catalog", suffix="3"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
        blueprint_id="blueprint-1",
    )


def _runtime(
    *,
    mission_id: str | None = MISSION_ID,
    trace_id: str = "trace-1",
    span_id: str = "span-runtime",
) -> Agent365RuntimeObservationV1:
    return Agent365RuntimeObservationV1(
        observation_id=f"runtime:{trace_id}:{span_id}:{mission_id}",
        source=_source("agent365.runtime.otel", suffix="4"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
        invocation_id="invocation-1",
        session_id="session-1",
        trace_id=trace_id,
        span_id=span_id,
        application_mission_id=mission_id,
    )


def _tool(
    *,
    mission_id: str | None = MISSION_ID,
    item_id: str | None = "42",
    trace_id: str = "trace-1",
    parent_span_id: str | None = "span-runtime",
    authorization_digest: str | None = AUTH_DIGEST,
) -> Agent365ToolObservationV1:
    return Agent365ToolObservationV1(
        observation_id=f"tool:{trace_id}:{mission_id}:{item_id}",
        source=_source("agent365.tool.otel", suffix="5"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
        trace_id=trace_id,
        span_id="span-tool",
        parent_span_id=parent_span_id,
        tool_call_id="tool-call-1",
        tool_name="sharepoint.create_or_update_mission",
        status=Agent365ToolStatus.SUCCEEDED,
        application_mission_id=mission_id,
        sharepoint_item_id=item_id,
        sharepoint_authorization_material_sha256=authorization_digest,
    )


def test_direct_mission_id_correlation_keeps_propositions_distinct() -> None:
    bundle = correlate_agent365_to_r0_mission(
        _anchor(),
        identities=(_identity(),),
        runtime=(_runtime(),),
        tools=(_tool(),),
    )

    assert bundle.mission_id == MISSION_ID
    assert bundle.correlation_bases == ("application_mission_id",)
    assert len(bundle.identity_observations) == 1
    assert len(bundle.runtime_observations) == 1
    assert len(bundle.tool_observations) == 1
    assert bundle.tool_execution_success_proves_sharepoint_state is False
    assert bundle.agent365_observation_proves_physical_result is False


def test_missing_native_mission_id_can_join_by_item_then_trace_parentage() -> None:
    bundle = correlate_agent365_to_r0_mission(
        _anchor(),
        identities=(_identity(),),
        runtime=(_runtime(mission_id=None),),
        tools=(_tool(mission_id=None),),
    )

    assert bundle.correlation_bases == ("sharepoint_item_id", "trace_parentage")
    assert bundle.tool_observations[0].application_mission_id is None
    assert bundle.runtime_observations[0].application_mission_id is None


def test_duplicate_identical_observations_are_idempotent() -> None:
    identity = _identity()
    runtime = _runtime()
    tool = _tool()
    bundle = correlate_agent365_to_r0_mission(
        _anchor(),
        identities=(identity, identity),
        runtime=(runtime, runtime),
        tools=(tool, tool),
    )

    assert len(bundle.identity_observations) == 1
    assert len(bundle.runtime_observations) == 1
    assert len(bundle.tool_observations) == 1


def test_wrong_mission_tool_fails_closed() -> None:
    with pytest.raises(Agent365R0CorrelationError, match="different application mission_id"):
        correlate_agent365_to_r0_mission(
            _anchor(),
            identities=(_identity(),),
            runtime=(_runtime(),),
            tools=(_tool(mission_id=OTHER_MISSION_ID),),
        )


def test_cross_mission_runtime_cannot_contaminate_bound_trace() -> None:
    with pytest.raises(Agent365R0CorrelationError, match="cross-mission"):
        correlate_agent365_to_r0_mission(
            _anchor(),
            identities=(_identity(),),
            runtime=(_runtime(mission_id=OTHER_MISSION_ID),),
            tools=(_tool(),),
        )


def test_tool_success_does_not_override_sharepoint_authorization_disagreement() -> None:
    with pytest.raises(Agent365R0CorrelationError, match="disagrees with live SharePoint"):
        correlate_agent365_to_r0_mission(
            _anchor(),
            identities=(_identity(),),
            runtime=(_runtime(),),
            tools=(_tool(authorization_digest="9" * 64),),
        )


def test_wrong_sharepoint_item_fails_for_directly_bound_tool() -> None:
    with pytest.raises(Agent365R0CorrelationError, match="another SharePoint item"):
        correlate_agent365_to_r0_mission(
            _anchor(),
            identities=(_identity(),),
            runtime=(_runtime(),),
            tools=(_tool(item_id="43"),),
        )


def test_tool_parent_span_must_exist_in_bound_runtime() -> None:
    with pytest.raises(Agent365R0CorrelationError, match="parent_span_id"):
        correlate_agent365_to_r0_mission(
            _anchor(),
            identities=(_identity(),),
            runtime=(_runtime(),),
            tools=(_tool(parent_span_id="missing-span"),),
        )


def test_identity_context_must_match_runtime_or_tool_participant() -> None:
    unrelated = Agent365IdentityObservationV1(
        observation_id="identity:other",
        source=_source("agent365.catalog", suffix="6"),
        package_id="pkg-other",
        agent_identity_id="agent-other",
    )
    with pytest.raises(Agent365R0CorrelationError, match="identity observation matches"):
        correlate_agent365_to_r0_mission(
            _anchor(),
            identities=(unrelated,),
            runtime=(_runtime(),),
            tools=(_tool(),),
        )
