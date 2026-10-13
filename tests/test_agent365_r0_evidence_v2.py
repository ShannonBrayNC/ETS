from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ets.demos.agent365_r0_mission import (
    SharePointMissionArtifactV1,
    authorize_mission,
    create_pending_mission,
)
from ets.evidence_object import DigestRef, identity_hash
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
    build_agent365_r0_consequence_closure,
)
from ets.ranger.agent365_r0_evidence_v2 import (
    EVIDENCE_OBJECT_V1_CONTRACT_ID,
    MISSION_CONTRACT_ID,
    SCENARIO_ID,
    RangerR0EvidenceV2Error,
    promote_agent365_r0_closure_to_v2,
    verify_agent365_r0_evidence_v2,
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


def _closure(tmp_path) -> RangerR0ConsequenceClosureBundle:
    mission = _authorized_mission()
    dispatch = _dispatch(tmp_path, mission)
    records, motion_directive, stop_directive = _run_physical_boundary(
        tmp_path,
        mission,
        dispatch,
    )
    return build_agent365_r0_consequence_closure(
        mission,
        dispatch,
        records,
        motion_directive=motion_directive,
        stop_directive=stop_directive,
    )


def test_v2_promotion_binds_mission_context_extension_and_v1_source(tmp_path) -> None:
    closure = _closure(tmp_path)

    bundle = promote_agent365_r0_closure_to_v2(closure)
    result = verify_agent365_r0_evidence_v2(bundle)

    assert result.valid is True
    assert result.mission_id == MISSION_ID
    assert result.mission_context_binding_valid is True
    assert result.mission_extension_valid is True
    assert result.v1_provenance_binding_valid is True
    assert result.ranger_event_binding_valid is True
    assert result.attached_v1_proof_valid is True
    assert result.source_closure_valid is True
    assert result.physical_result_supported is True
    assert result.truth_claim_supported is False
    assert len(bundle.evidence_object_identity_hash) == 64

    context = next(
        item
        for item in bundle.evidence_object.bindings
        if item.binding_type == "context"
    )
    assert context.contract_id == MISSION_CONTRACT_ID
    assert context.subject_ref == f"mission:{MISSION_ID}"
    assert bundle.evidence_object.extensions["lantern.demo"] == {
        "mission_id": MISSION_ID,
        "scenario_id": SCENARIO_ID,
    }

    provenance = next(
        item
        for item in bundle.evidence_object.bindings
        if item.binding_type == "provenance"
    )
    assert provenance.contract_id == EVIDENCE_OBJECT_V1_CONTRACT_ID
    assert provenance.commitment is not None
    assert provenance.commitment.digest == closure.evidence_object_hash


def test_v2_identity_excludes_proof_attachment_but_verifier_detects_tamper(tmp_path) -> None:
    closure = _closure(tmp_path)
    bundle = promote_agent365_r0_closure_to_v2(closure)
    proof = bundle.evidence_object.proof_material[0]
    tampered_proof = proof.model_copy(
        update={"material": {"evidence_object": {"tampered": True}}}
    )
    tampered_object = bundle.evidence_object.model_copy(
        update={"proof_material": (tampered_proof,)}
    )

    # Evidence Object v2 deliberately excludes proof_material from canonical identity.
    assert identity_hash(tampered_object) == bundle.evidence_object_identity_hash

    tampered_bundle = replace(bundle, evidence_object=tampered_object)
    with pytest.raises(RangerR0EvidenceV2Error) as error:
        verify_agent365_r0_evidence_v2(tampered_bundle)

    assert error.value.code == "invalid_v1_proof_material"


def test_v2_verifier_rejects_mission_extension_drift(tmp_path) -> None:
    bundle = promote_agent365_r0_closure_to_v2(_closure(tmp_path))
    extensions = dict(bundle.evidence_object.extensions)
    extensions["lantern.demo"] = {
        "mission_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "scenario_id": SCENARIO_ID,
    }
    drifted_object = bundle.evidence_object.model_copy(update={"extensions": extensions})
    drifted_bundle = replace(
        bundle,
        evidence_object=drifted_object,
        evidence_object_identity_hash=identity_hash(drifted_object),
    )

    with pytest.raises(RangerR0EvidenceV2Error) as error:
        verify_agent365_r0_evidence_v2(drifted_bundle)

    assert error.value.code == "mission_extension_mismatch"


def test_v2_verifier_rejects_changed_v1_commitment(tmp_path) -> None:
    bundle = promote_agent365_r0_closure_to_v2(_closure(tmp_path))
    bindings = list(bundle.evidence_object.bindings)
    index = next(
        i for i, item in enumerate(bindings) if item.binding_type == "provenance"
    )
    bindings[index] = bindings[index].model_copy(
        update={"commitment": DigestRef(digest="0" * 64)}
    )
    drifted_object = bundle.evidence_object.model_copy(update={"bindings": tuple(bindings)})
    drifted_bundle = replace(
        bundle,
        evidence_object=drifted_object,
        evidence_object_identity_hash=identity_hash(drifted_object),
    )

    with pytest.raises(RangerR0EvidenceV2Error) as error:
        verify_agent365_r0_evidence_v2(drifted_bundle)

    assert error.value.code == "v1_provenance_commitment_mismatch"
