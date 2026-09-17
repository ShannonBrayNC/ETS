from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.demos.agent365_r0_mission import authorize_mission, create_pending_mission
from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    GatewayR0MissionGuard,
    GatewayR0MotionRequestV1,
    MissionCorrelationEnvelopeV1,
    SqliteMissionDispatchLedger,
)
from ets.ranger.agent365_r0_motion import (
    RangerR0MotionBoundary,
    RangerR0MotionBoundaryError,
    RangerR0MotionState,
    RangerR0ResultObservationV1,
    RangerR0StopCondition,
    RangerR0StopObservationV1,
    SqliteRangerR0ReceiptLedger,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
OTHER_MISSION_ID = "88888888-8888-4888-8888-888888888888"
AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
BASE_TIME = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
ARTIFACT_REF = "sharepoint://ETS-R0-Missions/items/42"
VEHICLE_ID = "ets-ranger:r0-demo-001"
BOOT_ID = "boot-r0-demo-001"
PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}


def _dispatch(
    tmp_path,
    *,
    delivery_id: str = "delivery-1",
    retry_of_delivery_id: str | None = None,
    dispatch_ledger: SqliteMissionDispatchLedger | None = None,
):
    mission = authorize_mission(
        create_pending_mission(
            policy_version="r0-forward-stop-policy.v1",
            command_parameters=PARAMETERS,
            mission_id_factory=lambda: MISSION_ID,
        ),
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=BASE_TIME,
    )
    request = GatewayR0MotionRequestV1(
        mission_id=MISSION_ID,
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=FrozenR0CommandParameters.model_validate(PARAMETERS),
        authorization_material_sha256=mission.authorization_material_sha256(),
        authorization_artifact_ref=ARTIFACT_REF,
        delivery_id=delivery_id,
        retry_of_delivery_id=retry_of_delivery_id,
    )
    ledger = dispatch_ledger or SqliteMissionDispatchLedger(tmp_path / "gateway.db")
    return GatewayR0MissionGuard(ledger).dispatch(
        request,
        mission,
        observed_at=BASE_TIME,
    )


def _boundary(tmp_path, ledger: SqliteRangerR0ReceiptLedger | None = None):
    return RangerR0MotionBoundary(
        vehicle_id=VEHICLE_ID,
        boot_id=BOOT_ID,
        receipt_ledger=ledger or SqliteRangerR0ReceiptLedger(tmp_path / "ranger.db"),
    )


def _receive_authorize_start(tmp_path):
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    receipt = boundary.receive_gateway_command(
        dispatch.robot_command,
        dispatch.egress_event,
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=1,
    )
    assert receipt.execute is True
    boundary.authorize_motion(
        hardware_estop_asserted=False,
        local_motion_ready=True,
        evaluated_at=BASE_TIME + timedelta(milliseconds=20),
        evaluated_monotonic_ns=2,
    )
    boundary.record_motion_start(
        actuator_id="motor-controller:r0",
        actuator_command_id="motor-command:start-1",
        commanded_linear_speed_mps=0.20,
        controller_acknowledged=True,
        acknowledged_at=BASE_TIME + timedelta(milliseconds=30),
        acknowledged_monotonic_ns=3,
    )
    return dispatch, boundary


def _complete_stop(boundary, *, condition: RangerR0StopCondition) -> None:
    kwargs: dict[str, object] = {}
    if condition is RangerR0StopCondition.MARKED_STOP_POINT:
        kwargs["marked_stop_detected"] = True
    elif condition is RangerR0StopCondition.OBSTACLE:
        kwargs["obstacle_distance_m"] = 0.30
    elif condition is RangerR0StopCondition.ESTOP:
        kwargs["hardware_estop_asserted"] = True
    else:
        kwargs["policy_reason"] = "maximum mission duration reached"

    boundary.record_stop_observation(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            delivery_id="delivery-1",
            observation_id="stop-observation-1",
            sensor_id="sensor:r0-stop",
            condition=condition,
            observed_at=BASE_TIME + timedelta(milliseconds=40),
            observed_monotonic_ns=4,
            **kwargs,
        )
    )
    boundary.record_stop_decision(
        decided_at=BASE_TIME + timedelta(milliseconds=50),
        decided_monotonic_ns=5,
    )
    boundary.record_stop_actuation(
        actuator_id="motor-controller:r0",
        actuator_command_id="motor-command:stop-1",
        controller_acknowledged=True,
        acknowledged_at=BASE_TIME + timedelta(milliseconds=60),
        acknowledged_monotonic_ns=6,
    )
    boundary.record_result_observation(
        RangerR0ResultObservationV1(
            mission_id=MISSION_ID,
            delivery_id="delivery-1",
            observation_id="result-observation-1",
            observer_id="wheel-encoder:r0-independent-read",
            observer_independent_of_actuator=True,
            measured_linear_speed_mps=0.0,
            measured_yaw_rate_rad_s=0.0,
            observed_at=BASE_TIME + timedelta(milliseconds=70),
            observed_monotonic_ns=7,
        )
    )


def test_obstacle_stop_preserves_mission_across_complete_robot_chain(tmp_path) -> None:
    dispatch, boundary = _receive_authorize_start(tmp_path)
    _complete_stop(boundary, condition=RangerR0StopCondition.OBSTACLE)

    transcript = boundary.transcript()

    assert transcript.state is RangerR0MotionState.RESULT_OBSERVED
    assert transcript.stop_condition is RangerR0StopCondition.OBSTACLE
    assert len(transcript.events) == 7
    assert all(event.mission_id == MISSION_ID for event in transcript.events)
    assert transcript.events[0].previous_event_digest == dispatch.egress_event.canonical_digest()
    for previous, current in zip(transcript.events, transcript.events[1:], strict=False):
        assert current.parent_event_id == previous.event_id
        assert current.previous_event_digest == previous.canonical_digest()
    assert transcript.events[-1].event_type == "ranger.result.stationary.observed"


def test_marked_stop_uses_same_frozen_motion_boundary(tmp_path) -> None:
    _, boundary = _receive_authorize_start(tmp_path)
    _complete_stop(boundary, condition=RangerR0StopCondition.MARKED_STOP_POINT)

    transcript = boundary.transcript()

    assert transcript.state is RangerR0MotionState.RESULT_OBSERVED
    assert transcript.stop_condition is RangerR0StopCondition.MARKED_STOP_POINT


def test_hardware_estop_prevents_motion_authorization(tmp_path) -> None:
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    boundary.receive_gateway_command(
        dispatch.robot_command,
        dispatch.egress_event,
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=1,
    )

    event = boundary.authorize_motion(
        hardware_estop_asserted=True,
        local_motion_ready=True,
        evaluated_at=BASE_TIME + timedelta(milliseconds=20),
        evaluated_monotonic_ns=2,
    )

    assert boundary.state is RangerR0MotionState.REJECTED_AUTHORITY
    assert event.event_type == "ranger.motion.authorization.denied"
    with pytest.raises(RangerR0MotionBoundaryError) as error:
        boundary.record_motion_start(
            actuator_id="motor-controller:r0",
            actuator_command_id="must-not-run",
            commanded_linear_speed_mps=0.10,
            controller_acknowledged=True,
            acknowledged_at=BASE_TIME + timedelta(milliseconds=30),
            acknowledged_monotonic_ns=3,
        )
    assert error.value.code == "invalid_state_transition"


def test_stop_actuation_is_not_treated_as_stopped_result(tmp_path) -> None:
    _, boundary = _receive_authorize_start(tmp_path)
    boundary.record_stop_observation(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            delivery_id="delivery-1",
            observation_id="obstacle-1",
            sensor_id="range:r0",
            condition=RangerR0StopCondition.OBSTACLE,
            obstacle_distance_m=0.30,
            observed_at=BASE_TIME + timedelta(milliseconds=40),
            observed_monotonic_ns=4,
        )
    )
    boundary.record_stop_decision(
        decided_at=BASE_TIME + timedelta(milliseconds=50),
        decided_monotonic_ns=5,
    )
    event = boundary.record_stop_actuation(
        actuator_id="motor-controller:r0",
        actuator_command_id="stop-1",
        controller_acknowledged=True,
        acknowledged_at=BASE_TIME + timedelta(milliseconds=60),
        acknowledged_monotonic_ns=6,
    )

    assert boundary.state is RangerR0MotionState.STOP_ACTUATED
    assert event.event_type == "ranger.stop.actuation.acknowledged"
    assert not any(
        item.event_type == "ranger.result.stationary.observed"
        for item in boundary.transcript().events
    )


def test_moving_result_is_retained_as_failed_observation(tmp_path) -> None:
    _, boundary = _receive_authorize_start(tmp_path)
    boundary.record_stop_observation(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            delivery_id="delivery-1",
            observation_id="obstacle-1",
            sensor_id="range:r0",
            condition=RangerR0StopCondition.OBSTACLE,
            obstacle_distance_m=0.30,
            observed_at=BASE_TIME + timedelta(milliseconds=40),
            observed_monotonic_ns=4,
        )
    )
    boundary.record_stop_decision(
        decided_at=BASE_TIME + timedelta(milliseconds=50),
        decided_monotonic_ns=5,
    )
    boundary.record_stop_actuation(
        actuator_id="motor-controller:r0",
        actuator_command_id="stop-1",
        controller_acknowledged=True,
        acknowledged_at=BASE_TIME + timedelta(milliseconds=60),
        acknowledged_monotonic_ns=6,
    )

    event = boundary.record_result_observation(
        RangerR0ResultObservationV1(
            mission_id=MISSION_ID,
            delivery_id="delivery-1",
            observation_id="result-moving-1",
            observer_id="wheel-encoder:r0-independent-read",
            observer_independent_of_actuator=True,
            measured_linear_speed_mps=0.08,
            measured_yaw_rate_rad_s=0.0,
            observed_at=BASE_TIME + timedelta(milliseconds=70),
            observed_monotonic_ns=7,
        )
    )

    assert boundary.state is RangerR0MotionState.FAILED_OBSERVATION
    assert event.event_type == "ranger.result.stop.not_established"


def test_result_observer_cannot_be_the_actuator_identity(tmp_path) -> None:
    _, boundary = _receive_authorize_start(tmp_path)
    boundary.record_stop_observation(
        RangerR0StopObservationV1(
            mission_id=MISSION_ID,
            delivery_id="delivery-1",
            observation_id="obstacle-1",
            sensor_id="range:r0",
            condition=RangerR0StopCondition.OBSTACLE,
            obstacle_distance_m=0.30,
            observed_at=BASE_TIME + timedelta(milliseconds=40),
            observed_monotonic_ns=4,
        )
    )
    boundary.record_stop_decision(
        decided_at=BASE_TIME + timedelta(milliseconds=50),
        decided_monotonic_ns=5,
    )
    boundary.record_stop_actuation(
        actuator_id="motor-controller:r0",
        actuator_command_id="stop-1",
        controller_acknowledged=True,
        acknowledged_at=BASE_TIME + timedelta(milliseconds=60),
        acknowledged_monotonic_ns=6,
    )

    with pytest.raises(RangerR0MotionBoundaryError) as error:
        boundary.record_result_observation(
            RangerR0ResultObservationV1(
                mission_id=MISSION_ID,
                delivery_id="delivery-1",
                observation_id="self-attest-1",
                observer_id="motor-controller:r0",
                observer_independent_of_actuator=False,
                measured_linear_speed_mps=0.0,
                measured_yaw_rate_rad_s=0.0,
                observed_at=BASE_TIME + timedelta(milliseconds=70),
                observed_monotonic_ns=7,
            )
        )

    assert error.value.code == "actuator_cannot_self_attest_result"


def test_stop_decision_cannot_precede_stop_observation(tmp_path) -> None:
    _, boundary = _receive_authorize_start(tmp_path)

    with pytest.raises(RangerR0MotionBoundaryError) as error:
        boundary.record_stop_decision(
            decided_at=BASE_TIME + timedelta(milliseconds=40),
            decided_monotonic_ns=4,
        )

    assert error.value.code == "invalid_state_transition"


def test_stop_observation_must_match_mission_and_delivery(tmp_path) -> None:
    _, boundary = _receive_authorize_start(tmp_path)

    with pytest.raises(RangerR0MotionBoundaryError) as error:
        boundary.record_stop_observation(
            RangerR0StopObservationV1(
                mission_id=OTHER_MISSION_ID,
                delivery_id="delivery-1",
                observation_id="wrong-mission",
                sensor_id="range:r0",
                condition=RangerR0StopCondition.OBSTACLE,
                obstacle_distance_m=0.30,
                observed_at=BASE_TIME + timedelta(milliseconds=40),
                observed_monotonic_ns=4,
            )
        )

    assert error.value.code == "mission_id_mismatch"


def test_obstacle_outside_authorized_threshold_cannot_trigger_demo_stop(tmp_path) -> None:
    _, boundary = _receive_authorize_start(tmp_path)

    with pytest.raises(RangerR0MotionBoundaryError) as error:
        boundary.record_stop_observation(
            RangerR0StopObservationV1(
                mission_id=MISSION_ID,
                delivery_id="delivery-1",
                observation_id="far-obstacle",
                sensor_id="range:r0",
                condition=RangerR0StopCondition.OBSTACLE,
                obstacle_distance_m=0.80,
                observed_at=BASE_TIME + timedelta(milliseconds=40),
                observed_monotonic_ns=4,
            )
        )

    assert error.value.code == "obstacle_outside_stop_threshold"


def test_gateway_egress_commitment_must_match_received_command(tmp_path) -> None:
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    values = dispatch.egress_event.model_dump(mode="python")
    values["payload_sha256"] = "0" * 64
    tampered = MissionCorrelationEnvelopeV1.model_validate(values)

    with pytest.raises(RangerR0MotionBoundaryError) as error:
        boundary.receive_gateway_command(
            dispatch.robot_command,
            tampered,
            received_at=BASE_TIME + timedelta(milliseconds=10),
            received_monotonic_ns=1,
        )

    assert error.value.code == "gateway_payload_mismatch"


def test_gateway_retry_is_deduplicated_across_ranger_process_restart(tmp_path) -> None:
    gateway_ledger = SqliteMissionDispatchLedger(tmp_path / "gateway.db")
    ranger_ledger = SqliteRangerR0ReceiptLedger(tmp_path / "ranger.db")
    first = _dispatch(tmp_path, dispatch_ledger=gateway_ledger)
    first_boundary = _boundary(tmp_path, ranger_ledger)
    first_result = first_boundary.receive_gateway_command(
        first.robot_command,
        first.egress_event,
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=1,
    )
    assert first_result.execute is True

    retry = _dispatch(
        tmp_path,
        delivery_id="delivery-2",
        retry_of_delivery_id="delivery-1",
        dispatch_ledger=gateway_ledger,
    )
    restarted_boundary = _boundary(tmp_path, ranger_ledger)
    retry_result = restarted_boundary.receive_gateway_command(
        retry.robot_command,
        retry.egress_event,
        received_at=BASE_TIME + timedelta(milliseconds=20),
        received_monotonic_ns=1,
    )

    assert retry_result.transport_retry is True
    assert retry_result.execute is False
    assert retry_result.event.mission_id == MISSION_ID
    assert retry_result.event.event_type == "ranger.command.retry.deduplicated"


def test_non_monotonic_robot_event_time_fails_closed(tmp_path) -> None:
    dispatch = _dispatch(tmp_path)
    boundary = _boundary(tmp_path)
    boundary.receive_gateway_command(
        dispatch.robot_command,
        dispatch.egress_event,
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=10,
    )

    with pytest.raises(RangerR0MotionBoundaryError) as error:
        boundary.authorize_motion(
            hardware_estop_asserted=False,
            local_motion_ready=True,
            evaluated_at=BASE_TIME + timedelta(milliseconds=20),
            evaluated_monotonic_ns=10,
        )

    assert error.value.code == "non_monotonic_event_time"
