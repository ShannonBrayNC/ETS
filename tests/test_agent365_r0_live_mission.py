from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from ets.api.auth import LocalAPIKeyAuthPolicy
from ets.demos.agent365_r0_correlation import (
    Agent365ApiMaturity,
    Agent365IdentityObservationV1,
    Agent365R0CorrelationBundleV1,
    Agent365RetainedSourceRefV1,
    Agent365RuntimeObservationV1,
    Agent365ToolObservationV1,
    Agent365ToolStatus,
)
from ets.demos.agent365_r0_live_mission import (
    Agent365R0LiveMissionError,
    RangerR0HardwareRunAttestationV1,
    run_agent365_r0_live_mission,
)
from ets.demos.agent365_r0_mission import authorize_mission, create_pending_mission
from ets.demos.agent365_r0_otel import Agent365OtlpAttributeProfileV1
from ets.demos.agent365_r0_profile_qualification import (
    Agent365ControlledTenantAttestationV1,
    Agent365ObservedAttributeKeysV1,
    Agent365ProfileQualificationPacketV1,
    Agent365ProfileQualificationResultV1,
)
from ets.demos.agent365_r0_sharepoint_live import (
    SharePointMissionLiveObservationV1,
    SharePointMissionSourceEnvelopeV1,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0MotionStartObservationV1,
    RangerR0ResultObservationV1,
    RangerR0StopObservationV1,
)
from ets.ranger.agent365_r0_correlation_store import SQLiteAgent365R0CorrelationStore
from ets.ranger.agent365_r0_mission_api import create_agent365_r0_mission_app
from ets.ranger.agent365_r0_mission_store import SQLiteRangerR0MissionBundleStore
from ets.ranger.agent365_r0_physical import RangerR0ActuatorReceiptV1

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
ACTUATOR_ID = "actuator:motor-controller"
RESULT_OBSERVER_ID = "sensor:pose-witness"
T0 = datetime(2026, 9, 17, 22, 30, tzinfo=UTC)
PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}


class ScriptClock:
    def __init__(self) -> None:
        self._times = iter([1, 2, 10, 40, 50])
        self._monotonic = iter([2, 10, 40, 50])

    def now_utc(self) -> datetime:
        return T0 + timedelta(milliseconds=next(self._times))

    def monotonic_ns(self) -> int:
        return next(self._monotonic)


class ScriptActuator:
    actuator_id = ACTUATOR_ID

    def __init__(self) -> None:
        self.motion_calls = 0
        self.stop_calls = 0
        self.fail_safe_calls = 0

    def apply_motion(self, directive):
        self.motion_calls += 1
        return RangerR0ActuatorReceiptV1(
            mission_id=directive.mission_id,
            actuator_id=self.actuator_id,
            command_kind="motion",
            accepted=True,
            observed_at=T0 + timedelta(milliseconds=11),
            observed_monotonic_ns=11,
        )

    def apply_stop(self, directive):
        self.stop_calls += 1
        return RangerR0ActuatorReceiptV1(
            mission_id=directive.mission_id,
            actuator_id=self.actuator_id,
            command_kind="stop",
            accepted=True,
            observed_at=T0 + timedelta(milliseconds=51),
            observed_monotonic_ns=51,
        )

    def fail_safe_stop(self, mission_id: str, *, reason: str):
        self.fail_safe_calls += 1
        return RangerR0ActuatorReceiptV1(
            mission_id=mission_id,
            actuator_id=self.actuator_id,
            command_kind="fail_safe_stop",
            accepted=True,
            observed_at=T0 + timedelta(milliseconds=99),
            observed_monotonic_ns=99,
            reason=reason,
        )


class ScriptSensors:
    def hardware_estop_asserted(self) -> bool:
        return False

    def observe_motion_start(self, mission_id, directive):
        return RangerR0MotionStartObservationV1(
            mission_id=mission_id,
            observer_id="sensor:wheel-encoder",
            observed_at=T0 + timedelta(milliseconds=20),
            observed_monotonic_ns=20,
            speed_mps=0.12,
            distance_travelled_m=0.01,
        )

    def observe_stop_condition(self, mission_id, directive):
        return RangerR0StopObservationV1(
            mission_id=mission_id,
            observer_id="sensor:forward-range",
            observed_at=T0 + timedelta(milliseconds=30),
            observed_monotonic_ns=30,
            distance_travelled_m=0.40,
            elapsed_s=1.0,
            obstacle_distance_m=0.40,
        )

    def observe_result(self, mission_id, stop_directive):
        return RangerR0ResultObservationV1(
            mission_id=mission_id,
            observer_id=RESULT_OBSERVER_ID,
            observed_at=T0 + timedelta(milliseconds=60),
            observed_monotonic_ns=60,
            speed_mps=0.0,
            distance_travelled_m=0.43,
            stationary_duration_ms=300,
        )


def _canonical_sha(value: dict[str, object]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _source(family: str, digit: str) -> Agent365RetainedSourceRefV1:
    return Agent365RetainedSourceRefV1(
        tenant_id=TENANT_ID,
        source_family=family,  # type: ignore[arg-type]
        api_maturity=Agent365ApiMaturity.DOCUMENTED_PREVIEW,
        acquisition_time=T0,
        microsoft_event_time=T0,
        payload_ref=f"ets://agent365/retained/{digit}",
        raw_payload_sha256=digit * 64,
        source_envelope_sha256=digit * 64,
        collector_identity="ets.agent365-live-test",
        collector_version="1.0",
    )


def _sharepoint_observation() -> SharePointMissionLiveObservationV1:
    pending = create_pending_mission(
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=PARAMETERS,
        mission_id_factory=lambda: MISSION_ID,
    )
    mission = authorize_mission(
        pending,
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=T0,
    )
    envelope = SharePointMissionSourceEnvelopeV1(
        requested_mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        site_id="site-1",
        list_id="list-1",
        item_id="42",
        acquired_at=T0,
        request_path="/v1.0/sites/site-1/lists/list-1/items/42?expand=fields",
        raw_payload_sha256="4" * 64,
        raw_payload_size=512,
        payload_ref="ets://microsoft/sharepoint/mission-source/sha256/" + ("4" * 64),
        retained_filename="raw/sha256-" + ("4" * 64) + ".json",
        content_type="application/json",
        etag='"etag-1"',
        collector_identity="ets.microsoft-sharepoint-mission-collector",
        collector_version="1.0",
    )
    return SharePointMissionLiveObservationV1(
        mission=mission,
        source=envelope,
        source_item_id="42",
        body_etag='"etag-1"',
        authorization_material_sha256=mission.authorization_material_sha256(),
    )


def _correlation(observation: SharePointMissionLiveObservationV1) -> Agent365R0CorrelationBundleV1:
    identity = Agent365IdentityObservationV1(
        observation_id="identity:pkg-1",
        source=_source("agent365.catalog", "1"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
    )
    runtime = Agent365RuntimeObservationV1(
        observation_id="runtime:trace-1:runtime-span",
        source=_source("agent365.runtime.otel", "2"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
        invocation_id="invocation-1",
        session_id="session-1",
        trace_id="trace-1",
        span_id="runtime-span",
        application_mission_id=MISSION_ID,
    )
    tool = Agent365ToolObservationV1(
        observation_id="tool:trace-1:tool-span",
        source=_source("agent365.tool.otel", "3"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
        trace_id="trace-1",
        span_id="tool-span",
        parent_span_id="runtime-span",
        tool_call_id="tool-call-1",
        tool_name="sharepoint.create_or_update_mission",
        status=Agent365ToolStatus.SUCCEEDED,
        application_mission_id=MISSION_ID,
        sharepoint_item_id="42",
        sharepoint_authorization_material_sha256=(
            observation.authorization_material_sha256
        ),
    )
    return Agent365R0CorrelationBundleV1(
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        sharepoint_item_id="42",
        sharepoint_authorization_material_sha256=(
            observation.authorization_material_sha256
        ),
        sharepoint_source_payload_sha256=observation.source.raw_payload_sha256,
        identity_observations=(identity,),
        runtime_observations=(runtime,),
        tool_observations=(tool,),
        correlation_bases=("application_mission_id",),
    )


def _qualification(
    observation: SharePointMissionLiveObservationV1,
    correlation: Agent365R0CorrelationBundleV1,
) -> Agent365ProfileQualificationResultV1:
    profile = Agent365OtlpAttributeProfileV1(
        profile_id="controlled-tenant-live-v1",
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
    profile_sha256 = _canonical_sha(profile.model_dump(mode="json"))
    source_envelopes = tuple(
        sorted(
            {
                item.source.source_envelope_sha256
                for item in (
                    *correlation.identity_observations,
                    *correlation.runtime_observations,
                    *correlation.tool_observations,
                )
            }
        )
    )
    live_attestation = Agent365ControlledTenantAttestationV1(
        run_id="agent365-controlled-live-001",
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        profile_id=profile.profile_id,
        profile_sha256=profile_sha256,
        source_envelope_sha256s=source_envelopes,
        operator_subject="operator:test",
        captured_at=T0,
    )
    packet = Agent365ProfileQualificationPacketV1(
        qualification_state="qualified",
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        profile=profile,
        profile_sha256=profile_sha256,
        observed_attribute_keys=Agent365ObservedAttributeKeysV1(
            runtime_record_keys=("invocation.id", "ets.mission_id"),
            runtime_resource_keys=("agent.identity.id", "package.id"),
            tool_record_keys=("tool.call.id", "tool.name", "tool.status"),
            tool_resource_keys=("sharepoint.item.id", "authorization.sha256"),
        ),
        source_envelope_sha256s=source_envelopes,
        source_record_refs=("2" * 64 + ":0", "3" * 64 + ":1"),
        identity_observation_ids=tuple(
            item.observation_id for item in correlation.identity_observations
        ),
        runtime_observation_ids=tuple(
            item.observation_id for item in correlation.runtime_observations
        ),
        tool_observation_ids=tuple(
            item.observation_id for item in correlation.tool_observations
        ),
        sharepoint_item_id="42",
        sharepoint_authorization_material_sha256=(
            observation.authorization_material_sha256
        ),
        sharepoint_source_payload_sha256=observation.source.raw_payload_sha256,
        correlation_bases=correlation.correlation_bases,
        live_attestation=live_attestation,
    )
    return Agent365ProfileQualificationResultV1(
        packet=packet,
        packet_sha256=_canonical_sha(packet.model_dump(mode="json")),
    )


def _hardware_attestation() -> RangerR0HardwareRunAttestationV1:
    return RangerR0HardwareRunAttestationV1(
        run_id="r0-hardware-live-001",
        mission_id=MISSION_ID,
        actuator_id=ACTUATOR_ID,
        result_observer_id=RESULT_OBSERVER_ID,
        operator_subject="operator:test",
        attested_at=T0,
    )


def _inputs():
    observation = _sharepoint_observation()
    correlation = _correlation(observation)
    qualification = _qualification(observation, correlation)
    return observation, correlation, qualification


def _api_key() -> str:
    return "local-" + ("x" * 24)


def test_live_orchestrator_persists_both_planes_and_api_reconstructs(tmp_path) -> None:
    observation, correlation, qualification = _inputs()
    actuator = ScriptActuator()

    result = run_agent365_r0_live_mission(
        tmp_path,
        qualification=qualification,
        sharepoint_observation=observation,
        correlation_bundle=correlation,
        actuator=actuator,
        sensors=ScriptSensors(),
        hardware_attestation=_hardware_attestation(),
        clock=ScriptClock(),
    )

    report = result.report
    assert report.execution_state == "operator_attested_hardware_run"
    assert report.mission_id == MISSION_ID
    assert report.physical_result_supported is True
    assert report.controller_acknowledgement_proves_motion is False
    assert report.agent365_tool_success_proves_sharepoint_state is False
    assert report.agent365_observation_proves_physical_result is False
    assert actuator.motion_calls == 1
    assert actuator.stop_calls == 1
    assert actuator.fail_safe_calls == 0

    run_dir = tmp_path / MISSION_ID
    physical_store = SQLiteRangerR0MissionBundleStore(run_dir / "mission-bundles.db")
    correlation_store = SQLiteAgent365R0CorrelationStore(run_dir / "agent365-correlation.db")
    try:
        app = create_agent365_r0_mission_app(
            physical_store.build_index(),
            auth_policy=LocalAPIKeyAuthPolicy(_api_key()),
            correlation_store=correlation_store,
        )
        client = TestClient(app)
        response = client.get(
            f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}",
            headers={"X-ETS-API-Key": _api_key()},
        )
    finally:
        correlation_store.close()
        physical_store.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["verifier"]["physical_result_supported"] is True
    assert payload["agent365_correlation"]["state"] == "observed"
    assert payload["agent365_correlation"]["bundle"]["mission_id"] == MISSION_ID
    assert payload["agent365_correlation"]["agent365_observation_proves_physical_result"] is False


def test_unqualified_profile_fails_before_gateway_or_motion(tmp_path) -> None:
    observation, correlation, qualification = _inputs()
    packet = qualification.packet.model_copy(
        update={"qualification_state": "ready_for_live_qualification", "live_attestation": None}
    )
    unqualified = Agent365ProfileQualificationResultV1(
        packet=packet,
        packet_sha256=_canonical_sha(packet.model_dump(mode="json")),
    )
    actuator = ScriptActuator()

    with pytest.raises(Agent365R0LiveMissionError, match="requires a qualified"):
        run_agent365_r0_live_mission(
            tmp_path,
            qualification=unqualified,
            sharepoint_observation=observation,
            correlation_bundle=correlation,
            actuator=actuator,
            sensors=ScriptSensors(),
            hardware_attestation=_hardware_attestation(),
            clock=ScriptClock(),
        )

    assert actuator.motion_calls == 0
    assert not (tmp_path / MISSION_ID / "gateway.db").exists()


def test_changed_sharepoint_source_fails_before_physical_execution(tmp_path) -> None:
    observation, correlation, qualification = _inputs()
    changed_source = observation.source.model_copy(update={"raw_payload_sha256": "9" * 64})
    changed_observation = observation.model_copy(update={"source": changed_source})
    actuator = ScriptActuator()

    with pytest.raises(Agent365R0LiveMissionError, match="not bound to the supplied SharePoint"):
        run_agent365_r0_live_mission(
            tmp_path,
            qualification=qualification,
            sharepoint_observation=changed_observation,
            correlation_bundle=correlation,
            actuator=actuator,
            sensors=ScriptSensors(),
            hardware_attestation=_hardware_attestation(),
            clock=ScriptClock(),
        )

    assert actuator.motion_calls == 0


def test_changed_correlation_observation_set_fails_before_motion(tmp_path) -> None:
    observation, correlation, qualification = _inputs()
    changed_runtime = correlation.runtime_observations[0].model_copy(
        update={"observation_id": "runtime:changed"}
    )
    changed_correlation = correlation.model_copy(\n        update={"runtime_observations": (changed_runtime,)}\n    )
    actuator = ScriptActuator()

    with pytest.raises(Agent365R0LiveMissionError, match="runtime observation set changed"):
        run_agent365_r0_live_mission(
            tmp_path,
            qualification=qualification,
            sharepoint_observation=observation,
            correlation_bundle=changed_correlation,
            actuator=actuator,
            sensors=ScriptSensors(),
            hardware_attestation=_hardware_attestation(),
            clock=ScriptClock(),
        )

    assert actuator.motion_calls == 0
