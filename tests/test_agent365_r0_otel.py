from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ets.capture.otlp import OtlpObservationV1
from ets.demos.agent365_r0_correlation import (
    Agent365ApiMaturity,
    Agent365RetainedSourceRefV1,
)
from ets.demos.agent365_r0_otel import (
    Agent365OtlpAttributeProfileV1,
    Agent365R0OtlpMappingError,
    project_agent365_otlp,
    runtime_observation_from_otlp,
    tool_observation_from_otlp,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
AUTH_DIGEST = "a" * 64
T0 = datetime(2026, 9, 17, 22, 30, tzinfo=UTC)


def _profile() -> Agent365OtlpAttributeProfileV1:
    return Agent365OtlpAttributeProfileV1(
        profile_id="agent365-demo-explicit-v1",
        package_id_key="demo.package.id",
        agent_identity_id_key="demo.agent.identity.id",
        invocation_id_key="demo.invocation.id",
        session_id_key="demo.session.id",
        mission_id_key="ets.mission_id",
        tool_call_id_key="demo.tool.call.id",
        tool_name_key="demo.tool.name",
        tool_status_key="demo.tool.status",
        sharepoint_item_id_key="demo.sharepoint.item.id",
        sharepoint_authorization_material_sha256_key="ets.authorization.sha256",
    )


def _source(family: str, suffix: str) -> Agent365RetainedSourceRefV1:
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


def _attribute(key: str, value: str) -> dict[str, object]:
    return {"key": key, "value": {"string_value": value}}


def _trace(
    *,
    ordinal: int,
    attributes: list[dict[str, object]],
    trace_id: str = "trace-1",
    span_id: str = "span-1",
    parent_span_id: str | None = None,
    resource_attributes: list[dict[str, object]] | None = None,
) -> OtlpObservationV1:
    record: dict[str, object] = {
        "trace_id": trace_id,
        "span_id": span_id,
        "name": "opaque-span-name-not-used-for-classification",
        "attributes": attributes,
    }
    if parent_span_id is not None:
        record["parent_span_id"] = parent_span_id
    resource: dict[str, object] = {}
    if resource_attributes is not None:
        resource["attributes"] = resource_attributes
    return OtlpObservationV1(
        schema_version="ets.otlp.observation.v1",
        signal_class="traces",
        record_ordinal=ordinal,
        source_timestamp_utc=T0,
        decoder_profile="ets.gateway.otlp.protobuf.v1",
        transformation_profile="ets.gateway.otlp.protobuf-to-semantic.v1",
        resource_metadata=resource,
        scope_metadata={},
        record_metadata=record,
    )


def _runtime_trace(*, mission_id: str = MISSION_ID) -> OtlpObservationV1:
    return _trace(
        ordinal=0,
        span_id="runtime-span",
        attributes=[
            _attribute("demo.package.id", "pkg-1"),
            _attribute("demo.agent.identity.id", "agent-1"),
            _attribute("demo.invocation.id", "invocation-1"),
            _attribute("demo.session.id", "session-1"),
            _attribute("ets.mission_id", mission_id),
        ],
    )


def _tool_trace(*, mission_id: str = MISSION_ID) -> OtlpObservationV1:
    return _trace(
        ordinal=1,
        span_id="tool-span",
        parent_span_id="runtime-span",
        attributes=[
            _attribute("demo.package.id", "pkg-1"),
            _attribute("demo.agent.identity.id", "agent-1"),
            _attribute("demo.tool.call.id", "tool-call-1"),
            _attribute("demo.tool.name", "sharepoint.create_or_update_mission"),
            _attribute("demo.tool.status", "succeeded"),
            _attribute("ets.mission_id", mission_id),
            _attribute("demo.sharepoint.item.id", "42"),
            _attribute("ets.authorization.sha256", AUTH_DIGEST),
        ],
    )


def test_runtime_projection_uses_only_explicit_attribute_profile() -> None:
    result = runtime_observation_from_otlp(
        _runtime_trace(),
        _source("agent365.runtime.otel", "1"),
        _profile(),
    )

    assert result.application_mission_id == MISSION_ID
    assert result.package_id == "pkg-1"
    assert result.agent_identity_id == "agent-1"
    assert result.invocation_id == "invocation-1"
    assert result.trace_id == "trace-1"
    assert result.span_id == "runtime-span"


def test_tool_projection_preserves_trace_parent_and_sharepoint_commitment() -> None:
    result = tool_observation_from_otlp(
        _tool_trace(),
        _source("agent365.tool.otel", "2"),
        _profile(),
    )

    assert result.application_mission_id == MISSION_ID
    assert result.parent_span_id == "runtime-span"
    assert result.tool_call_id == "tool-call-1"
    assert result.sharepoint_item_id == "42"
    assert result.sharepoint_authorization_material_sha256 == AUTH_DIGEST


def test_projection_does_not_infer_role_from_span_name() -> None:
    trace = _runtime_trace()
    wrong_source = _source("agent365.tool.otel", "3")

    with pytest.raises(Agent365R0OtlpMappingError, match="runtime projection requires"):
        runtime_observation_from_otlp(trace, wrong_source, _profile())


def test_missing_configured_attribute_fails_closed() -> None:
    trace = _trace(
        ordinal=0,
        attributes=[_attribute("ets.mission_id", MISSION_ID)],
    )
    with pytest.raises(Agent365R0OtlpMappingError, match="invocation"):
        runtime_observation_from_otlp(
            trace,
            _source("agent365.runtime.otel", "4"),
            _profile(),
        )


def test_conflicting_record_and_resource_attribute_fails_closed() -> None:
    trace = _trace(
        ordinal=0,
        attributes=[
            _attribute("demo.invocation.id", "record-invocation"),
            _attribute("ets.mission_id", MISSION_ID),
        ],
        resource_attributes=[
            _attribute("demo.invocation.id", "resource-invocation"),
        ],
    )
    with pytest.raises(Agent365R0OtlpMappingError, match="conflicts"):
        runtime_observation_from_otlp(
            trace,
            _source("agent365.runtime.otel", "5"),
            _profile(),
        )


def test_non_trace_signal_is_rejected() -> None:
    trace = _runtime_trace()
    invalid = trace.model_copy(update={"signal_class": "logs"})
    with pytest.raises(Agent365R0OtlpMappingError, match="requires OTLP traces"):
        runtime_observation_from_otlp(
            invalid,
            _source("agent365.runtime.otel", "6"),
            _profile(),
        )


def test_unknown_tool_status_is_not_promoted_to_success() -> None:
    trace = _trace(
        ordinal=1,
        span_id="tool-span",
        attributes=[
            _attribute("demo.tool.call.id", "tool-call-1"),
            _attribute("demo.tool.name", "sharepoint"),
            _attribute("demo.tool.status", "microsoft-new-status"),
        ],
    )
    with pytest.raises(Agent365R0OtlpMappingError, match="status vocabulary"):
        tool_observation_from_otlp(
            trace,
            _source("agent365.tool.otel", "7"),
            _profile(),
        )


def test_batch_projection_accepts_explicitly_classified_runtime_and_tool_spans() -> None:
    projection = project_agent365_otlp(
        runtime_spans=((_runtime_trace(), _source("agent365.runtime.otel", "8")),),
        tool_spans=((_tool_trace(), _source("agent365.tool.otel", "9")),),
        profile=_profile(),
    )

    assert len(projection.runtime_observations) == 1
    assert len(projection.tool_observations) == 1
    assert projection.source_record_ordinals == (0, 1)
    assert projection.claim_boundary == "configured_semantic_projection_of_retained_otlp_only"
