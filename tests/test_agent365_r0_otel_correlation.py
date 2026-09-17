from __future__ import annotations

from datetime import UTC, datetime

from ets.capture.otlp import OtlpObservationV1
from ets.demos.agent365_r0_correlation import (
    Agent365ApiMaturity,
    Agent365IdentityObservationV1,
    Agent365RetainedSourceRefV1,
    SharePointMissionCorrelationAnchorV1,
    correlate_agent365_to_r0_mission,
)
from ets.demos.agent365_r0_otel import (
    Agent365OtlpAttributeProfileV1,
    project_agent365_otlp,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
AUTH_DIGEST = "a" * 64
T0 = datetime(2026, 9, 17, 22, 45, tzinfo=UTC)


def _attribute(key: str, value: str) -> dict[str, object]:
    return {"key": key, "value": {"string_value": value}}


def _trace(
    ordinal: int,
    span_id: str,
    attributes: list[dict[str, object]],
    *,
    parent_span_id: str | None = None,
) -> OtlpObservationV1:
    record: dict[str, object] = {
        "trace_id": "trace-1",
        "span_id": span_id,
        "attributes": attributes,
    }
    if parent_span_id is not None:
        record["parent_span_id"] = parent_span_id
    return OtlpObservationV1(
        schema_version="ets.otlp.observation.v1",
        signal_class="traces",
        record_ordinal=ordinal,
        source_timestamp_utc=T0,
        decoder_profile="ets.gateway.otlp.protobuf.v1",
        transformation_profile="ets.gateway.otlp.protobuf-to-semantic.v1",
        resource_metadata={},
        scope_metadata={},
        record_metadata=record,
    )


def _source(
    family: str,
    suffix: str,
) -> Agent365RetainedSourceRefV1:
    return Agent365RetainedSourceRefV1(
        tenant_id=TENANT_ID,
        source_family=family,  # type: ignore[arg-type]
        api_maturity=Agent365ApiMaturity.DOCUMENTED_PREVIEW,
        acquisition_time=T0,
        microsoft_event_time=T0,
        payload_ref=f"ets://agent365/otel/{suffix}",
        raw_payload_sha256=suffix * 64,
        source_envelope_sha256=suffix * 64,
        collector_identity="ets.agent365-otel-test",
        collector_version="1.0",
    )


def test_projected_otlp_runtime_and_tool_observations_enter_mission_correlation() -> None:
    profile = Agent365OtlpAttributeProfileV1(
        profile_id="controlled-tenant-fixture-v1",
        package_id_key="package.id",
        agent_identity_id_key="agent.identity.id",
        invocation_id_key="invocation.id",
        session_id_key="session.id",
        mission_id_key="ets.mission_id",
        tool_call_id_key="tool.call.id",
        tool_name_key="tool.name",
        tool_status_key="tool.status",
        sharepoint_item_id_key="sharepoint.item.id",
        sharepoint_authorization_material_sha256_key="authorization.sha256",
    )
    runtime = _trace(
        0,
        "runtime-span",
        [
            _attribute("package.id", "pkg-1"),
            _attribute("agent.identity.id", "agent-1"),
            _attribute("invocation.id", "invocation-1"),
            _attribute("session.id", "session-1"),
            _attribute("ets.mission_id", MISSION_ID),
        ],
    )
    tool = _trace(
        1,
        "tool-span",
        [
            _attribute("package.id", "pkg-1"),
            _attribute("agent.identity.id", "agent-1"),
            _attribute("tool.call.id", "tool-call-1"),
            _attribute("tool.name", "sharepoint.create_or_update_mission"),
            _attribute("tool.status", "succeeded"),
            _attribute("ets.mission_id", MISSION_ID),
            _attribute("sharepoint.item.id", "42"),
            _attribute("authorization.sha256", AUTH_DIGEST),
        ],
        parent_span_id="runtime-span",
    )
    projection = project_agent365_otlp(
        runtime_spans=((runtime, _source("agent365.runtime.otel", "1")),),
        tool_spans=((tool, _source("agent365.tool.otel", "2")),),
        profile=profile,
    )
    identity_source = Agent365RetainedSourceRefV1(
        tenant_id=TENANT_ID,
        source_family="agent365.catalog",
        api_maturity=Agent365ApiMaturity.DOCUMENTED_PREVIEW,
        acquisition_time=T0,
        microsoft_event_time=T0,
        payload_ref="ets://agent365/catalog/identity-1",
        raw_payload_sha256="3" * 64,
        source_envelope_sha256="3" * 64,
        collector_identity="ets.agent365-catalog-test",
        collector_version="1.0",
    )
    identity = Agent365IdentityObservationV1(
        observation_id="identity:pkg-1",
        source=identity_source,
        package_id="pkg-1",
        agent_identity_id="agent-1",
    )
    anchor = SharePointMissionCorrelationAnchorV1(
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        item_id="42",
        authorization_material_sha256=AUTH_DIGEST,
        source_payload_sha256="4" * 64,
        source_payload_ref="ets://microsoft/sharepoint/mission-source/4",
        acquired_at=T0,
    )

    bundle = correlate_agent365_to_r0_mission(
        anchor,
        identities=(identity,),
        runtime=projection.runtime_observations,
        tools=projection.tool_observations,
    )

    assert bundle.mission_id == MISSION_ID
    assert bundle.correlation_bases == ("application_mission_id",)
    assert bundle.runtime_observations[0].trace_id == "trace-1"
    assert bundle.tool_observations[0].parent_span_id == "runtime-span"
    assert bundle.tool_execution_success_proves_sharepoint_state is False
    assert bundle.agent365_observation_proves_physical_result is False
