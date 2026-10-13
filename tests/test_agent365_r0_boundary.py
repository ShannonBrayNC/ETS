from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.demos.agent365_r0_mission import (
    SharePointMissionArtifactV1,
    authorize_mission,
    create_pending_mission,
)
from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    GatewayR0DispatchBundle,
    GatewayR0MissionGuard,
    GatewayR0MotionRequestV1,
    MissionCorrelationEnvelopeV1,
    SqliteMissionDispatchLedger,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0BoundaryError,
    RangerR0MotionStartObservationV1,
    RangerR0ReceiptMotionBoundary,
    RangerR0ResultObservationV1,
    RangerR0Stage,
    RangerR0StopObservationV1,
    RangerR0StopReason,
    SqliteRangerR0ReceiptLedger,
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


def _dispatch(
    tmp_path,
    *,
    delivery_id: str = "delivery-1",
    retry_of_delivery_id: str | None = None,
    observed_at: datetime = T0,
) -> GatewayR0DispatchBundle:
    mission = _authorized_mission()
    request = GatewayR0MotionRequestV1(
        mission_id=MISSION_ID,
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=FrozenR0CommandParameters.model_validate(PARAMETERS),
        authorization_material_sha256=mission.authorization_material_sha256(),
        authorization_artifact_ref=ARTIFACT_REF,
        delivery_id=delivery_id,
        retry_of_delivery_id=retry_of_delivery_id,
    )
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "gateway.db"))
    return guard.dispatch(request, mission, observed_at=observed_at)


def _boundary(tmp_path) -> RangerR0ReceiptMotionBoundary:
    return RangerR0ReceiptMotionBoundary(
        SqliteRangerR0ReceiptLedger(tmp_path / "ranger.db"),
        vehicle_id=VEHICLE_ID,
        controller_id=CONTROLLER_ID,
    )


def _receive_and_authorize(
    tmp_path,
) -> tuple[RangerR0ReceiptMotionBoundary, GatewayR0DispatchBundle]:
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    receipt = boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=T0 + timedelta(milliseconds=10),
        observed_monotonic_ns=10_000_000,
    )
    assert receipt.execution_allowed is True
    boundary.authorize_motion(
        MISSION_ID,
        observed_at=T0 + timedelta(milliseconds=20),
        observed_monotonic_ns=20_000_000,
    )
    return boundary, dispatch


def _record_started(boundary: RangerR0ReceiptMotionBoundary) -> None:
    boundary.record_motion_started(
        RangerR0MotionStartObservationV1(
            mission_id=MISSION_ID,
            observer_id="sensor:encoder-fusion",
            observed_at=T0 + timedelta(milliseconds=30),
            observed_monotonic_ns=30_000_000,
            speed_mps=0.12,
            distance_travelled_m=0.01,
        )
    )


def test_first_receipt_binds_gateway_egress_and_preserves_mission_id(tmp_path) -> None:
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)

    result = boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=T0 + timedelta(milliseconds=10),
        observed_monotonic_ns=10_000_000,
    )

    assert result.first_delivery is True
    assert result.execution_allowed is True
    assert result.current_stage is RangerR0Stage.RECEIVED
    assert result.receipt.envelope.mission_id == MISSION_ID
    assert result.receipt.envelope.parent_event_id == dispatch.egress_event.event_id
    assert (
        result.receipt.envelope.previous_event_digest
        == dispatch.egress_event.canonical_digest()
    )


def test_receipt_rejects_tampered_gateway_payload_commitment(tmp_path) -> None:
    dispatch = _dispatch(tmp_path)
    values = dispatch.egress_event.model_dump(mode="python")
    values["payload_sha256"] = "0" * 64
    tampered = MissionCorrelationEnvelopeV1.model_validate(values)
    boundary = _boundary(tmp_path)

    with pytest.raises(RangerR0BoundaryError) as error:
        boundary.receive(
            dispatch.robot_command,
            tampered,
            observed_at=T0 + timedelta(milliseconds=10),
            observed_monotonic_ns=10_000_000,
        )

    assert error.value.code == "gateway_payload_mismatch"


def test_gateway_transport_retry_is_receipted_but_cannot_reexecute(tmp_path) -> None:
    first = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    boundary.receive(
        first.robot_command,
        first.egress_event,
        observed_at=T0 + timedelta(milliseconds=10),
        observed_monotonic_ns=10_000_000,
    )

    retry = _dispatch(
        tmp_path,
        delivery_id="delivery-2",
        retry_of_delivery_id="delivery-1",
        observed_at=T0 + timedelta(seconds=1),
    )
    receipt = boundary.receive(
        retry.robot_command,
        retry.egress_event,
        observed_at=T0 + timedelta(seconds=1, milliseconds=10),
        observed_monotonic_ns=1_010_000_000,
    )

    assert receipt.first_delivery is False
    assert receipt.execution_allowed is False
    assert receipt.receipt.envelope.event_type == "ranger.command.retry.received"
    assert boundary.stage(MISSION_ID) is RangerR0Stage.RECEIVED


def test_motion_authorization_fails_closed_on_hardware_estop(tmp_path) -> None:
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=T0 + timedelta(milliseconds=10),
        observed_monotonic_ns=10_000_000,
    )

    with pytest.raises(RangerR0BoundaryError) as error:
        boundary.authorize_motion(
            MISSION_ID,
            observed_at=T0 + timedelta(milliseconds=20),
            observed_monotonic_ns=20_000_000,
            hardware_estop_asserted=True,
        )

    assert error.value.code == "hardware_estop_asserted"
    assert boundary.stage(MISSION_ID) is RangerR0Stage.RECEIVED


def test_full_receipt_motion_stop_result_chain(tmp_path) -> None:
    boundary, _ = _receive_and_authorize(tmp_path)
    _record_started(boundary)

    stop_observation = boundary.observe_stop_condition(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            observer_id="sensor:forward-range",
            observed_at=T0 + timedelta(seconds=2),
            observed_monotonic_ns=2_000_000_000,
            distance_travelled_m=0.40,
            elapsed_s=1.98,
            obstacle_distance_m=0.40,
        )
    )
    assert stop_observation is not None
    assert stop_observation.stage is RangerR0Stage.STOP_CONDITION_OBSERVED
    assert (
        stop_observation.payload["trigger_reasons"]
        == [RangerR0StopReason.OBSTACLE_WITHIN_STOP_DISTANCE.value]
    )

    decision = boundary.decide_stop(
        MISSION_ID,
        observed_at=T0 + timedelta(seconds=2, milliseconds=5),
        observed_monotonic_ns=2_005_000_000,
    )
    assert decision.stage is RangerR0Stage.STOP_DECIDED

    actuation = boundary.actuate_stop(
        MISSION_ID,
        observed_at=T0 + timedelta(seconds=2, milliseconds=10),
        observed_monotonic_ns=2_010_000_000,
    )
    assert actuation.record.stage is RangerR0Stage.STOP_ACTUATED
    assert actuation.directive.linear_speed_mps == 0.0
    assert (
        actuation.directive.claim_boundary
        == "stop_actuation_command_not_proof_chassis_stopped"
    )

    result = boundary.record_result_observed(
        RangerR0ResultObservationV1(
            mission_id=MISSION_ID,
            observer_id="sensor:pose-witness",
            observed_at=T0 + timedelta(seconds=2, milliseconds=400),
            observed_monotonic_ns=2_400_000_000,
            speed_mps=0.0,
            distance_travelled_m=0.43,
            stationary_duration_ms=300,
        )
    )
    assert result.stage is RangerR0Stage.RESULT_OBSERVED
    assert result.payload["outcome"] == "STOP_CONFIRMED"
    assert boundary.stage(MISSION_ID) is RangerR0Stage.RESULT_OBSERVED


def test_stop_actuation_is_not_accepted_as_proof_that_chassis_stopped(tmp_path) -> None:
    boundary, _ = _receive_and_authorize(tmp_path)
    _record_started(boundary)
    observed = boundary.observe_stop_condition(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            observer_id="sensor:forward-range",
            observed_at=T0 + timedelta(seconds=2),
            observed_monotonic_ns=2_000_000_000,
            distance_travelled_m=0.4,
            elapsed_s=1.9,
            obstacle_distance_m=0.4,
        )
    )
    assert observed is not None
    boundary.decide_stop(
        MISSION_ID,
        observed_at=T0 + timedelta(seconds=2, milliseconds=5),
        observed_monotonic_ns=2_005_000_000,
    )
    boundary.actuate_stop(
        MISSION_ID,
        observed_at=T0 + timedelta(seconds=2, milliseconds=10),
        observed_monotonic_ns=2_010_000_000,
    )

    with pytest.raises(RangerR0BoundaryError) as error:
        boundary.record_result_observed(
            RangerR0ResultObservationV1(
                mission_id=MISSION_ID,
                observer_id="sensor:pose-witness",
                observed_at=T0 + timedelta(seconds=2, milliseconds=100),
                observed_monotonic_ns=2_100_000_000,
                speed_mps=0.08,
                distance_travelled_m=0.44,
                stationary_duration_ms=0,
            )
        )

    assert error.value.code == "result_not_stopped"
    assert boundary.stage(MISSION_ID) is RangerR0Stage.STOP_ACTUATED


def test_non_triggering_sensor_observation_does_not_advance_stop_state(tmp_path) -> None:
    boundary, _ = _receive_and_authorize(tmp_path)
    _record_started(boundary)

    record = boundary.observe_stop_condition(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            observer_id="sensor:forward-range",
            observed_at=T0 + timedelta(seconds=1),
            observed_monotonic_ns=1_000_000_000,
            distance_travelled_m=0.2,
            elapsed_s=0.9,
            obstacle_distance_m=1.0,
        )
    )

    assert record is None
    assert boundary.stage(MISSION_ID) is RangerR0Stage.MOTION_STARTED


def test_max_distance_is_a_stop_condition(tmp_path) -> None:
    boundary, _ = _receive_and_authorize(tmp_path)
    _record_started(boundary)

    record = boundary.observe_stop_condition(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            observer_id="sensor:odometry",
            observed_at=T0 + timedelta(seconds=10),
            observed_monotonic_ns=10_000_000_000,
            distance_travelled_m=2.0,
            elapsed_s=9.9,
        )
    )

    assert record is not None
    assert record.payload["trigger_reasons"] == [
        RangerR0StopReason.MAX_DISTANCE_REACHED.value
    ]


def test_result_observer_must_be_distinct_from_motion_controller(tmp_path) -> None:
    boundary, _ = _receive_and_authorize(tmp_path)
    _record_started(boundary)
    observed = boundary.observe_stop_condition(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            observer_id="sensor:forward-range",
            observed_at=T0 + timedelta(seconds=2),
            observed_monotonic_ns=2_000_000_000,
            distance_travelled_m=0.4,
            elapsed_s=1.9,
            obstacle_distance_m=0.4,
        )
    )
    assert observed is not None
    boundary.decide_stop(
        MISSION_ID,
        observed_at=T0 + timedelta(seconds=2, milliseconds=5),
        observed_monotonic_ns=2_005_000_000,
    )
    boundary.actuate_stop(
        MISSION_ID,
        observed_at=T0 + timedelta(seconds=2, milliseconds=10),
        observed_monotonic_ns=2_010_000_000,
    )

    with pytest.raises(RangerR0BoundaryError) as error:
        boundary.record_result_observed(
            RangerR0ResultObservationV1(
                mission_id=MISSION_ID,
                observer_id=CONTROLLER_ID,
                observed_at=T0 + timedelta(seconds=2, milliseconds=400),
                observed_monotonic_ns=2_400_000_000,
                speed_mps=0.0,
                distance_travelled_m=0.43,
                stationary_duration_ms=300,
            )
        )

    assert error.value.code == "observer_not_independent"


def test_out_of_order_transition_fails_closed(tmp_path) -> None:
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=T0 + timedelta(milliseconds=10),
        observed_monotonic_ns=10_000_000,
    )

    with pytest.raises(RangerR0BoundaryError) as error:
        boundary.decide_stop(
            MISSION_ID,
            observed_at=T0 + timedelta(milliseconds=20),
            observed_monotonic_ns=20_000_000,
        )

    assert error.value.code == "invalid_stage_transition"
