from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ets.capture.otlp import OtlpObservationV1
from ets.demos.agent365_r0_correlation import (
    Agent365ApiMaturity,
    Agent365IdentityObservationV1,
    Agent365RetainedSourceRefV1,
    SharePointMissionCorrelationAnchorV1,
)
from ets.demos.agent365_r0_otel import Agent365OtlpAttributeProfileV1
from ets.demos.agent365_r0_profile_qualification import (
    Agent365ControlledTenantAttestationV1,
    Agent365ProfileQualificationError,
    qualify_agent365_otlp_profile,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
AUTH_DIGEST = "a" * 64
T0 = datetime(2026, 9, 17, 22, 45, tzinfo=UTC)
SENSITIVE_VALUE = "DO_NOT_LEAK_CONTROLLED_PROMPT"


def _attribute(key: str, value: str) -> dict[str, object]:
    return {"key": key, "value": {"string_value": value}}


def _trace(
    ordinal: int,
    span_id: str,
    attributes: list[dict[str, object]],
    *,
    parent_span_id: str | None = None,
    resource_attributes: list[dict[str, object]] | None = None,
) -> OtlpObservationV1:
    record: dict[str, object] = {
        "trace_id": "trace-1",
        "span_id": span_id,
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


def _source(
    family: str,
    suffix: str,
    *,
    tenant_id: str = TENANT_ID,
) -> Agent365RetainedSourceRefV1:
    return Agent365RetainedSourceRefV1(
        tenant_id=tenant_id,
        source_family=family,  # type: ignore[arg-type]
        api_maturity=Agent365ApiMaturity.DOCUMENTED_PREVIEW,
        acquisition_time=T0,
        microsoft_event_time=T0,
        payload_ref=f"ets://agent365/retained/{suffix}",
        raw_payload_sha256=suffix * 64,
        source_envelope_sha256=suffix * 64,
        collector_identity="ets.agent365-profile-test",
        collector_version="1.0",
    )


def _profile() -> Agent365OtlpAttributeProfileV1:
    return Agent365OtlpAttributeProfileV1(
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


def _inputs(
    *,
    tool_tenant_id: str = TENANT_ID,
) -> tuple[
    tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    tuple[tuple[OtlpObservationV1, Agent365RetainedSourceRefV1], ...],
    tuple[Agent365IdentityObservationV1, ...],
    SharePointMissionCorrelationAnchorV1,
]:
    runtime = _trace(
        0,
        "runtime-span",
        [
            _attribute("package.id", "pkg-1"),
            _attribute("agent.identity.id", "agent-1"),
            _attribute("invocation.id", "invocation-1"),
            _attribute("session.id", "session-1"),
            _attribute("ets.mission_id", MISSION_ID),
            _attribute("prompt.text", SENSITIVE_VALUE),
        ],
        resource_attributes=[_attribute("service.name", "controlled-agent")],
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
    identity = Agent365IdentityObservationV1(
        observation_id="identity:pkg-1",
        source=_source("agent365.catalog", "3"),
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
    return (
        ((runtime, _source("agent365.runtime.otel", "1")),),
        ((tool, _source("agent365.tool.otel", "2", tenant_id=tool_tenant_id)),),
        (identity,),
        anchor,
    )


def test_synthetic_qualification_is_deterministic_but_not_live_qualified() -> None:
    runtime_spans, tool_spans, identities, anchor = _inputs()

    first = qualify_agent365_otlp_profile(
        profile=_profile(),
        runtime_spans=runtime_spans,
        tool_spans=tool_spans,
        identities=identities,
        anchor=anchor,
    )
    second = qualify_agent365_otlp_profile(
        profile=_profile(),
        runtime_spans=runtime_spans,
        tool_spans=tool_spans,
        identities=identities,
        anchor=anchor,
    )

    assert first == second
    assert first.packet.qualification_state == "ready_for_live_qualification"
    assert first.packet.live_attestation is None
    assert first.packet.observed_attribute_keys.attribute_values_included is False
    assert "prompt.text" in first.packet.observed_attribute_keys.runtime_record_keys
    assert "service.name" in first.packet.observed_attribute_keys.runtime_resource_keys
    assert SENSITIVE_VALUE not in first.packet.model_dump_json()
    assert first.packet.raw_otlp_payloads_included is False
    assert first.packet.tool_execution_success_proves_sharepoint_state is False
    assert first.packet.agent365_observation_proves_physical_result is False


def test_exact_controlled_tenant_attestation_promotes_profile_to_qualified() -> None:
    runtime_spans, tool_spans, identities, anchor = _inputs()
    ready = qualify_agent365_otlp_profile(
        profile=_profile(),
        runtime_spans=runtime_spans,
        tool_spans=tool_spans,
        identities=identities,
        anchor=anchor,
    )
    attestation = Agent365ControlledTenantAttestationV1(
        run_id="agent365-r0-controlled-run-001",
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        profile_id=_profile().profile_id,
        profile_sha256=ready.packet.profile_sha256,
        source_envelope_sha256s=ready.packet.source_envelope_sha256s,
        operator_subject="controlled-tenant-operator",
        captured_at=T0,
    )

    qualified = qualify_agent365_otlp_profile(
        profile=_profile(),
        runtime_spans=runtime_spans,
        tool_spans=tool_spans,
        identities=identities,
        anchor=anchor,
        live_attestation=attestation,
    )

    assert qualified.packet.qualification_state == "qualified"
    assert qualified.packet.live_attestation == attestation
    assert qualified.packet.mission_id == MISSION_ID
    assert qualified.packet.correlation_bases == ("application_mission_id",)


def test_profile_drift_invalidates_controlled_tenant_attestation() -> None:
    runtime_spans, tool_spans, identities, anchor = _inputs()
    ready = qualify_agent365_otlp_profile(
        profile=_profile(),
        runtime_spans=runtime_spans,
        tool_spans=tool_spans,
        identities=identities,
        anchor=anchor,
    )
    attestation = Agent365ControlledTenantAttestationV1(
        run_id="agent365-r0-controlled-run-001",
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        profile_id=_profile().profile_id,
        profile_sha256="f" * 64,
        source_envelope_sha256s=ready.packet.source_envelope_sha256s,
        operator_subject="controlled-tenant-operator",
        captured_at=T0,
    )

    with pytest.raises(Agent365ProfileQualificationError, match="profile digest"):
        qualify_agent365_otlp_profile(
            profile=_profile(),
            runtime_spans=runtime_spans,
            tool_spans=tool_spans,
            identities=identities,
            anchor=anchor,
            live_attestation=attestation,
        )


def test_cross_tenant_otlp_source_fails_closed() -> None:
    other_tenant = "33333333-3333-4333-8333-333333333333"
    runtime_spans, tool_spans, identities, anchor = _inputs(tool_tenant_id=other_tenant)

    with pytest.raises(ValueError, match="tenant differs"):
        qualify_agent365_otlp_profile(
            profile=_profile(),
            runtime_spans=runtime_spans,
            tool_spans=tool_spans,
            identities=identities,
            anchor=anchor,
        )
