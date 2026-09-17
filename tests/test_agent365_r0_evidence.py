from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ets.demos.agent365_r0_mission import (
    MissionStatus,
    SharePointMissionArtifactV1,
    authorize_mission,
    create_pending_mission,
)
from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    GatewayR0DispatchBundle,
    GatewayR0MissionGuard,
    GatewayR0MotionRequestV1,
    SqliteMissionDispatchLedger,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0BoundaryRecordV1,
    RangerR0MotionDirectiveV1,
    RangerR0MotionStartObservationV1,
    RangerR0ReceiptMotionBoundary,
    RangerR0ResultObservationV1,
    RangerR0StopDirectiveV1,
    RangerR0StopObservationV1,
    SqliteRangerR0ReceiptLedger,
)
from ets.ranger.agent365_r0_evidence import (
    RangerR0ConsequenceClosureBundle,
    RangerR0ConsequenceClosureError,
    build_agent365_r0_consequence_closure,
    complete_sharepoint_mission_from_closure,
    sharepoint_completion_patch_body,
    verify_agent365_r0_consequence_closure,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
T0 = datetime(2026, 9, 17, 8, 0, tzinfo=UTC)
PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}
ARTIFACT_REF = "sharepoint://ETS-R0-Missions/items/42"
VEHICLE_ID = "ets-ranger:r0-demo"
CONTROLLER_ID = "ranger-controller:r0"


def _authorized_mission() -> SharePointMissionArtifactV1:
    pending = create_pending_mission(
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=PARAMETERS,
        mission_id_factory=lambda: MISSION_ID,
    )
    return authorize_mission(
        pending,
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=T0,
    )


def _dispatch(tmp_path, mission: SharePointMissionArtifactV1) -> GatewayR0DispatchBundle:
    request = GatewayR0MotionRequestV1(
        mission_id=MISSION_ID,
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=FrozenR0CommandParameters.model_validate(PARAMETERS),
        authorization_material_sha256=mission.authorization_material_sha256(),
        authorization_artifact_ref=ARTIFACT_REF,
        delivery_id="delivery-1",
    )
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "gateway.db"))
    return guard.dispatch(request, mission, observed_at=T0)


def _run_physical_boundary(
    tmp_path,
    mission: SharePointMissionArtifactV1,
    dispatch: GatewayR0DispatchBundle,
) -> tuple[
    tuple[RangerR0BoundaryRecordV1, ...],
    RangerR0MotionDirectiveV1,
    RangerR0StopDirectiveV1,
]:
    boundary = RangerR0ReceiptMotionBoundary(
        SqliteRangerR0ReceiptLedger(tmp_path / "ranger.db"),
        vehicle_id=VEHICLE_ID,
        controller_id=CONTROLLER_ID,
    )
    receipt = boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=T0 + timedelta(milliseconds=10),
        observed_monotonic_ns=10_000_000,
    )
    authorized = boundary.authorize_motion(
        mission.mission_id,
        observed_at=T0 + timedelta(milliseconds=20),
        observed_monotonic_ns=20_000_000,
    )
    started = boundary.record_motion_started(
        RangerR0MotionStartObservationV1(
            mission_id=mission.mission_id,
            observer_id="sensor:encoder-fusion",
            observed_at=T0 + timedelta(milliseconds=30),
            observed_monotonic_ns=30_000_000,
            speed_mps=0.12,
            distance_travelled_m=0.01,
        )
    )
    stop_observed = boundary.observe_stop_condition(
        RangerR0StopObservationV1(
            mission_id=mission.mission_id,
            observer_id="sensor:forward-range",
            observed_at=T0 + timedelta(seconds=2),
            observed_monotonic_ns=2_000_000_000,
            distance_travelled_m=0.40,
            elapsed_s=1.98,
            obstacle_distance_m=0.40,
        )
    )
    assert stop_observed is not None
    stop_decided = boundary.decide_stop(
        mission.mission_id,
        observed_at=T0 + timedelta(seconds=2, milliseconds=5),
        observed_monotonic_ns=2_005_000_000,
    )
    stop_actuated = boundary.actuate_stop(
        mission.mission_id,
        observed_at=T0 + timedelta(seconds=2, milliseconds=10),
        observed_monotonic_ns=2_010_000_000,
    )
    result = boundary.record_result_observed(
        RangerR0ResultObservationV1(
            mission_id=mission.mission_id,
            observer_id="sensor:pose-witness",
            observed_at=T0 + timedelta(seconds=2, milliseconds=400),
            observed_monotonic_ns=2_400_000_000,
            speed_mps=0.0,
            distance_travelled_m=0.43,
            stationary_duration_ms=300,
        )
    )
    return (
        (
            receipt.receipt,
            authorized.record,
            started,
            stop_observed,
            stop_decided,
            stop_actuated.record,
            result,
        ),
        authorized.directive,
        stop_actuated.directive,
    )


def _closure(tmp_path) -> tuple[SharePointMissionArtifactV1, RangerR0ConsequenceClosureBundle]:
    mission = _authorized_mission()
    dispatch = _dispatch(tmp_path, mission)
    records, motion_directive, stop_directive = _run_physical_boundary(
        tmp_path,
        mission,
        dispatch,
    )
    closure = build_agent365_r0_consequence_closure(
        mission,
        dispatch,
        records,
        motion_directive=motion_directive,
        stop_directive=stop_directive,
    )
    return mission, closure


def test_closure_verifies_full_authority_dispatch_and_physical_result_chain(tmp_path) -> None:
    _, closure = _closure(tmp_path)

    result = verify_agent365_r0_consequence_closure(closure)

    assert result.valid is True
    assert result.mission_id == MISSION_ID
    assert result.stage_count == 7
    assert result.source_evidence_status == "VERIFIED"
    assert result.authorization_binding_valid is True
    assert result.gateway_chain_valid is True
    assert result.boundary_chain_valid is True
    assert result.directive_binding_valid is True
    assert result.independent_result_observation_supported is True
    assert result.physical_result_supported is True
    assert result.actuator_acknowledgement_observed is False
    assert result.actuator_response_observed is False
    assert result.truth_claim_supported is False


def test_closure_retains_all_authoritative_source_bytes(tmp_path) -> None:
    _, closure = _closure(tmp_path)

    # SharePoint authorization + 3 Gateway envelopes + robot command + 2 directives + 7 records.
    assert len(closure.source_artifacts) == 14
    assert closure.evidence_object.identity.evidence_id == (
        f"ranger-r0:{MISSION_ID}:consequence-closure"
    )
    assert closure.evidence_object_hash.startswith("sha256:")


def test_stop_command_remains_distinct_from_independent_result_proof(tmp_path) -> None:
    _, closure = _closure(tmp_path)

    result = verify_agent365_r0_consequence_closure(closure)

    # The generic consequence verifier remains conservative because P0 has no separate
    # actuator acknowledgement/response signal, while Step 4 still verifies the independent
    # RESULT_OBSERVED record as support for the stopped state.
    assert result.legacy_consequence_status == "NOT_OBSERVED"
    assert result.physical_result_supported is True
    assert result.actuator_acknowledgement_observed is False
    assert result.actuator_response_observed is False


def test_sharepoint_completion_links_verified_evidence_without_changing_authority(tmp_path) -> None:
    mission, closure = _closure(tmp_path)
    authorization_digest = mission.authorization_material_sha256()

    completed = complete_sharepoint_mission_from_closure(mission, closure)

    assert completed.status is MissionStatus.COMPLETED_OBSTACLE_STOP
    assert completed.evidence_object_id == closure.evidence_object.identity.evidence_id
    assert completed.evidence_bundle_ref == closure.evidence_bundle_ref
    assert completed.authorization_material_sha256() == authorization_digest
    assert sharepoint_completion_patch_body(completed) == {
        "fields": {
            "Status": "COMPLETED_OBSTACLE_STOP",
            "EvidenceObjectId": closure.evidence_object.identity.evidence_id,
            "EvidenceBundleRef": closure.evidence_bundle_ref,
        }
    }


def test_closure_rejects_missing_ranger_stage(tmp_path) -> None:
    mission = _authorized_mission()
    dispatch = _dispatch(tmp_path, mission)
    records, motion_directive, stop_directive = _run_physical_boundary(
        tmp_path,
        mission,
        dispatch,
    )

    with pytest.raises(RangerR0ConsequenceClosureError) as error:
        build_agent365_r0_consequence_closure(
            mission,
            dispatch,
            records[:-1],
            motion_directive=motion_directive,
            stop_directive=stop_directive,
        )

    assert error.value.code == "boundary_stage_count_mismatch"


def test_reverse_verifier_rejects_tampered_retained_source_bytes(tmp_path) -> None:
    _, closure = _closure(tmp_path)
    artifacts = dict(closure.source_artifacts)
    result_key = "source:ranger-boundary:result_observed"
    artifacts[result_key] = artifacts[result_key] + b" "
    tampered = replace(closure, source_artifacts=artifacts)

    with pytest.raises(RangerR0ConsequenceClosureError) as error:
        verify_agent365_r0_consequence_closure(tampered)

    assert error.value.code == "source_evidence_not_verified"
