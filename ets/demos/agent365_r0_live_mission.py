"""First fully live Agent 365 -> SharePoint -> Gateway -> Ranger R0 mission boundary.

This orchestrator intentionally refuses to turn software readiness into a live claim.  It
requires an already ``qualified`` controlled-tenant Agent 365 profile, a source-attributable
SharePoint mission observation, the exact sanitized Agent 365 correlation bundle, and an
operator attestation for the physical hardware run.  Controller acknowledgements remain
separate from independent physical observations and from Microsoft-side telemetry.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.demos.agent365_r0_correlation import (
    Agent365R0CorrelationBundleV1,
    sharepoint_correlation_anchor,
)
from ets.demos.agent365_r0_profile_qualification import (
    Agent365ProfileQualificationResultV1,
)
from ets.demos.agent365_r0_sharepoint_live import SharePointMissionLiveObservationV1
from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    GatewayR0MissionGuard,
    GatewayR0MotionRequestV1,
    SqliteMissionDispatchLedger,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0ReceiptMotionBoundary,
    SqliteRangerR0ReceiptLedger,
)
from ets.ranger.agent365_r0_correlation_store import SQLiteAgent365R0CorrelationStore
from ets.ranger.agent365_r0_evidence import build_agent365_r0_consequence_closure
from ets.ranger.agent365_r0_evidence_v2 import (
    SCENARIO_ID,
    promote_agent365_r0_closure_to_v2,
    verify_agent365_r0_evidence_v2,
)
from ets.ranger.agent365_r0_mission_store import SQLiteRangerR0MissionBundleStore
from ets.ranger.agent365_r0_physical import (
    RangerR0ActuatorReceiptV1,
    RangerR0PhysicalActuator,
    RangerR0PhysicalClock,
    RangerR0PhysicalSensors,
    SystemRangerR0PhysicalClock,
    execute_physical_r0_mission,
)

DEFAULT_VEHICLE_ID = "ets-ranger:r0-demo"
DEFAULT_CONTROLLER_ID = "ranger-controller:r0"


class Agent365R0LiveMissionError(RuntimeError):
    """Raised when the first live mission cannot satisfy every evidence boundary."""


class StrictLiveMissionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RangerR0HardwareRunAttestationV1(StrictLiveMissionModel):
    """Operator assertion that injected actuator/sensor implementations address real hardware."""

    schema_version: Literal["ets.demo.agent365-r0.hardware-run-attestation.v1"] = (
        "ets.demo.agent365-r0.hardware-run-attestation.v1"
    )
    run_id: str = Field(min_length=1, max_length=256)
    mission_id: str = Field(min_length=36, max_length=36)
    actuator_id: str = Field(min_length=1, max_length=256)
    result_observer_id: str = Field(min_length=1, max_length=256)
    operator_subject: str = Field(min_length=1, max_length=256)
    attested_at: datetime
    physical_hardware_present: Literal[True] = True
    independent_result_observer_present: Literal[True] = True
    hardware_estop_available: Literal[True] = True

    @field_validator("attested_at")
    @classmethod
    def normalize_attested_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("hardware attestation time must be timezone-aware")
        return value.astimezone(UTC)


class Agent365R0LiveMissionReportV1(StrictLiveMissionModel):
    """Sanitized report emitted only after durable Microsoft + physical reconstruction."""

    schema_version: Literal["ets.demo.agent365-r0.live-mission-report.v1"] = (
        "ets.demo.agent365-r0.live-mission-report.v1"
    )
    mission_id: str = Field(min_length=36, max_length=36)
    scenario_id: str
    execution_state: Literal["operator_attested_hardware_run"] = (
        "operator_attested_hardware_run"
    )
    agent365_profile_id: str
    agent365_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    agent365_qualification_packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    agent365_live_attestation_present: Literal[True] = True
    microsoft_tenant_id: str = Field(min_length=36, max_length=36)
    sharepoint_item_id: str
    sharepoint_source_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sharepoint_authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gateway_ingress_event_id: str
    gateway_decision_event_id: str
    gateway_egress_event_id: str
    gateway_command_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ranger_receive_event_id: str
    motion_actuator_id: str
    motion_actuator_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stop_actuator_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hardware_run_attestation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    independent_result_observer_id: str
    independent_result_event_id: str
    evidence_object_v1_id: str
    evidence_object_v1_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_object_v2_id: str
    evidence_object_v2_identity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_result_supported: Literal[True] = True
    physical_store_reopened: Literal[True] = True
    agent365_correlation_store_reopened: Literal[True] = True
    sanitized_api_reconstruction_ready: Literal[True] = True
    controller_acknowledgement_proves_motion: Literal[False] = False
    agent365_tool_success_proves_sharepoint_state: Literal[False] = False
    agent365_observation_proves_physical_result: Literal[False] = False
    truth_claim_supported: Literal[False] = False
    claim_boundary: str = (
        "report_binds_operator_attested_hardware_execution_and_independent_result_observation_"
        "to_qualified_microsoft_sources_without_converting_any_single_observer_into_truth"
    )


class Agent365R0LiveMissionResultV1(StrictLiveMissionModel):
    schema_version: Literal["ets.demo.agent365-r0.live-mission-result.v1"] = (
        "ets.demo.agent365-r0.live-mission-result.v1"
    )
    report: Agent365R0LiveMissionReportV1
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def run_agent365_r0_live_mission(
    workdir: str | Path,
    *,
    qualification: Agent365ProfileQualificationResultV1,
    sharepoint_observation: SharePointMissionLiveObservationV1,
    correlation_bundle: Agent365R0CorrelationBundleV1,
    actuator: RangerR0PhysicalActuator,
    sensors: RangerR0PhysicalSensors,
    hardware_attestation: RangerR0HardwareRunAttestationV1,
    clock: RangerR0PhysicalClock | None = None,
    vehicle_id: str = DEFAULT_VEHICLE_ID,
    controller_id: str = DEFAULT_CONTROLLER_ID,
    delivery_id: str | None = None,
    maximum_stop_observations: int = 10_000,
) -> Agent365R0LiveMissionResultV1:
    """Execute one qualified, source-bound mission through the physical R0 boundary.

    Every Microsoft/correlation mismatch is checked before Gateway dispatch.  Once motion is
    attempted the existing physical adapter remains responsible for fail-safe stop behavior.
    """

    packet = qualification.packet
    _validate_qualified_inputs(
        qualification=qualification,
        sharepoint_observation=sharepoint_observation,
        correlation_bundle=correlation_bundle,
    )

    mission = sharepoint_observation.mission
    mission_id = mission.mission_id
    run_dir = Path(workdir) / mission_id
    run_dir.mkdir(parents=True, exist_ok=True)
    local_clock = clock or SystemRangerR0PhysicalClock()

    command_parameters = FrozenR0CommandParameters.model_validate(mission.command_parameters)
    actual_delivery_id = delivery_id or f"live:{mission_id}"
    request = GatewayR0MotionRequestV1(
        mission_id=mission_id,
        policy_version=mission.policy_version,  # type: ignore[arg-type]
        command_parameters=command_parameters,
        authorization_material_sha256=sharepoint_observation.authorization_material_sha256,
        authorization_artifact_ref=sharepoint_observation.source.payload_ref,
        delivery_id=actual_delivery_id,
    )
    gateway = GatewayR0MissionGuard(SqliteMissionDispatchLedger(run_dir / "gateway.db"))
    dispatch = gateway.dispatch(
        request,
        mission,
        observed_at=local_clock.now_utc(),
    )

    boundary = RangerR0ReceiptMotionBoundary(
        SqliteRangerR0ReceiptLedger(run_dir / "ranger.db"),
        vehicle_id=vehicle_id,
        controller_id=controller_id,
    )
    receipt = boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=local_clock.now_utc(),
        observed_monotonic_ns=local_clock.monotonic_ns(),
    )
    if not receipt.execution_allowed or not receipt.first_delivery:
        raise Agent365R0LiveMissionError(
            "first live mission did not produce a first-delivery robot receipt"
        )

    physical = execute_physical_r0_mission(
        boundary,
        mission_id,
        actuator=actuator,
        sensors=sensors,
        clock=local_clock,
        maximum_stop_observations=maximum_stop_observations,
    )
    records = (receipt.receipt, *physical.boundary_records)
    result_record = records[-1]
    result_observer_id = result_record.payload.get("observer_id")
    if not isinstance(result_observer_id, str) or not result_observer_id:
        raise Agent365R0LiveMissionError(
            "independent result record did not retain a result observer identifier"
        )
    _validate_hardware_attestation(
        hardware_attestation,
        mission_id=mission_id,
        actuator_id=actuator.actuator_id,
        result_observer_id=result_observer_id,
    )

    physical_source_dir = run_dir / "physical-source"
    motion_receipt_sha256 = _retain_model(
        physical_source_dir / "motion-actuator-receipt.json",
        physical.motion_actuator_receipt,
    )
    stop_receipt_sha256 = _retain_model(
        physical_source_dir / "stop-actuator-receipt.json",
        physical.stop_actuator_receipt,
    )
    hardware_attestation_sha256 = _retain_model(
        physical_source_dir / "hardware-run-attestation.json",
        hardware_attestation,
    )

    closure = build_agent365_r0_consequence_closure(
        mission,
        dispatch,
        records,
        motion_directive=physical.motion_directive,
        stop_directive=physical.stop_directive,
    )
    bundle = promote_agent365_r0_closure_to_v2(closure)
    verification = verify_agent365_r0_evidence_v2(bundle)
    if not verification.valid or not verification.physical_result_supported:
        raise Agent365R0LiveMissionError(
            "live physical Evidence Object v2 did not verify with an independent stopped result"
        )

    physical_store_path = run_dir / "mission-bundles.db"
    physical_store = SQLiteRangerR0MissionBundleStore(physical_store_path)
    try:
        physical_store.save(bundle)
    finally:
        physical_store.close()

    correlation_store_path = run_dir / "agent365-correlation.db"
    correlation_store = SQLiteAgent365R0CorrelationStore(correlation_store_path)
    try:
        correlation_store.save(correlation_bundle)
    finally:
        correlation_store.close()

    reopened_physical = SQLiteRangerR0MissionBundleStore(physical_store_path)
    try:
        reconstruction = reopened_physical.build_index().reconstruct(mission_id)
    finally:
        reopened_physical.close()
    if not reconstruction.manifest.physical_result_supported:
        raise Agent365R0LiveMissionError(
            "reopened physical mission no longer supports the independent stopped result"
        )

    reopened_correlation = SQLiteAgent365R0CorrelationStore(correlation_store_path)
    try:
        loaded_correlation = reopened_correlation.load(mission_id)
    finally:
        reopened_correlation.close()
    if loaded_correlation != correlation_bundle:
        raise Agent365R0LiveMissionError(
            "reopened Agent 365 correlation differs from the qualified mission correlation"
        )

    _retain_model(run_dir / "agent365-profile-qualification.json", qualification)
    manifest = reconstruction.manifest
    report = Agent365R0LiveMissionReportV1(
        mission_id=mission_id,
        scenario_id=SCENARIO_ID,
        agent365_profile_id=packet.profile.profile_id,
        agent365_profile_sha256=packet.profile_sha256,
        agent365_qualification_packet_sha256=qualification.packet_sha256,
        microsoft_tenant_id=packet.tenant_id,
        sharepoint_item_id=sharepoint_observation.source_item_id,
        sharepoint_source_payload_sha256=sharepoint_observation.source.raw_payload_sha256,
        sharepoint_authorization_material_sha256=(
            sharepoint_observation.authorization_material_sha256
        ),
        gateway_ingress_event_id=dispatch.ingress_event.event_id,
        gateway_decision_event_id=dispatch.decision_event.event_id,
        gateway_egress_event_id=dispatch.egress_event.event_id,
        gateway_command_payload_sha256=dispatch.robot_command.payload_sha256(),
        ranger_receive_event_id=receipt.receipt.envelope.event_id,
        motion_actuator_id=actuator.actuator_id,
        motion_actuator_receipt_sha256=motion_receipt_sha256,
        stop_actuator_receipt_sha256=stop_receipt_sha256,
        hardware_run_attestation_sha256=hardware_attestation_sha256,
        independent_result_observer_id=result_observer_id,
        independent_result_event_id=result_record.envelope.event_id,
        evidence_object_v1_id=manifest.evidence_object_v1_id,
        evidence_object_v1_hash=manifest.evidence_object_v1_hash,
        evidence_object_v2_id=manifest.evidence_object_v2_id,
        evidence_object_v2_identity_hash=manifest.evidence_object_v2_identity_hash,
    )
    report_sha256 = _retain_model(run_dir / "live-mission-report.json", report)
    return Agent365R0LiveMissionResultV1(report=report, report_sha256=report_sha256)


def _validate_qualified_inputs(
    *,
    qualification: Agent365ProfileQualificationResultV1,
    sharepoint_observation: SharePointMissionLiveObservationV1,
    correlation_bundle: Agent365R0CorrelationBundleV1,
) -> None:
    packet = qualification.packet
    if packet.qualification_state != "qualified" or packet.live_attestation is None:
        raise Agent365R0LiveMissionError(
            "live physical dispatch requires a qualified controlled-tenant Agent 365 profile"
        )
    expected_packet_sha256 = _model_sha256(packet)
    if qualification.packet_sha256 != expected_packet_sha256:
        raise Agent365R0LiveMissionError(
            "Agent 365 qualification packet digest does not match the supplied packet"
        )

    anchor = sharepoint_correlation_anchor(sharepoint_observation)
    if packet.mission_id != anchor.mission_id:
        raise Agent365R0LiveMissionError("qualified Agent 365 packet belongs to another mission")
    if packet.tenant_id != anchor.tenant_id:
        raise Agent365R0LiveMissionError("qualified Agent 365 packet belongs to another tenant")
    if packet.sharepoint_item_id != anchor.item_id:
        raise Agent365R0LiveMissionError(
            "qualified Agent 365 packet targets another SharePoint item"
        )
    if packet.sharepoint_authorization_material_sha256 != anchor.authorization_material_sha256:
        raise Agent365R0LiveMissionError(
            "qualified Agent 365 packet disagrees with live SharePoint authorization"
        )
    if packet.sharepoint_source_payload_sha256 != anchor.source_payload_sha256:
        raise Agent365R0LiveMissionError(
            "qualified Agent 365 packet is not bound to the supplied SharePoint source"
        )

    if correlation_bundle.mission_id != packet.mission_id:
        raise Agent365R0LiveMissionError("Agent 365 correlation belongs to another mission")
    if correlation_bundle.tenant_id != packet.tenant_id:
        raise Agent365R0LiveMissionError("Agent 365 correlation belongs to another tenant")
    if correlation_bundle.sharepoint_item_id != packet.sharepoint_item_id:
        raise Agent365R0LiveMissionError(
            "Agent 365 correlation targets another SharePoint item"
        )
    if (
        correlation_bundle.sharepoint_authorization_material_sha256
        != packet.sharepoint_authorization_material_sha256
    ):
        raise Agent365R0LiveMissionError(
            "Agent 365 correlation disagrees with the qualified authorization commitment"
        )
    if correlation_bundle.sharepoint_source_payload_sha256 != packet.sharepoint_source_payload_sha256:
        raise Agent365R0LiveMissionError(
            "Agent 365 correlation is not bound to the qualified SharePoint source"
        )
    if correlation_bundle.correlation_bases != packet.correlation_bases:
        raise Agent365R0LiveMissionError(
            "Agent 365 correlation bases differ from the qualified profile packet"
        )

    identity_ids = tuple(sorted(item.observation_id for item in correlation_bundle.identity_observations))
    runtime_ids = tuple(sorted(item.observation_id for item in correlation_bundle.runtime_observations))
    tool_ids = tuple(sorted(item.observation_id for item in correlation_bundle.tool_observations))
    if identity_ids != packet.identity_observation_ids:
        raise Agent365R0LiveMissionError("qualified identity observation set changed")
    if runtime_ids != packet.runtime_observation_ids:
        raise Agent365R0LiveMissionError("qualified runtime observation set changed")
    if tool_ids != packet.tool_observation_ids:
        raise Agent365R0LiveMissionError("qualified tool observation set changed")

    source_envelopes = {
        observation.source.source_envelope_sha256
        for observation in (
            *correlation_bundle.identity_observations,
            *correlation_bundle.runtime_observations,
            *correlation_bundle.tool_observations,
        )
    }
    if tuple(sorted(source_envelopes)) != packet.source_envelope_sha256s:
        raise Agent365R0LiveMissionError(
            "Agent 365 retained source commitments changed after profile qualification"
        )


def _validate_hardware_attestation(
    attestation: RangerR0HardwareRunAttestationV1,
    *,
    mission_id: str,
    actuator_id: str,
    result_observer_id: str,
) -> None:
    if attestation.mission_id != mission_id:
        raise Agent365R0LiveMissionError("hardware attestation belongs to another mission")
    if attestation.actuator_id != actuator_id:
        raise Agent365R0LiveMissionError("hardware attestation names another actuator")
    if attestation.result_observer_id != result_observer_id:
        raise Agent365R0LiveMissionError(
            "hardware attestation names another independent result observer"
        )


def _retain_model(path: Path, model: BaseModel) -> str:
    raw = _canonical_json(model.model_dump(mode="json")).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise Agent365R0LiveMissionError(
                f"retained live-mission artifact already contains different bytes: {path.name}"
            )
    else:
        path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _model_sha256(model: BaseModel) -> str:
    raw = _canonical_json(model.model_dump(mode="json")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


__all__ = [
    "Agent365R0LiveMissionError",
    "Agent365R0LiveMissionReportV1",
    "Agent365R0LiveMissionResultV1",
    "RangerR0HardwareRunAttestationV1",
    "run_agent365_r0_live_mission",
]
