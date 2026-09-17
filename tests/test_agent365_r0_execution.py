from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    RangerR0GatewayCommandV1,
)
from ets.ranger.agent365_r0_execution import (
    RangerR0ExecutionError,
    RangerR0ExecutionPhase,
    RangerR0ExecutionSession,
    RangerR0StopObservationV1,
    RangerR0StopReason,
)
from ets.ranger.mobility import ClockQuality, RangerMobilityPolicy

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
OTHER_MISSION_ID = "88888888-8888-4888-8888-888888888888"
BASE_TIME = datetime(2026, 9, 17, 7, 30, tzinfo=UTC)


def _command() -> RangerR0GatewayCommandV1:
    return RangerR0GatewayCommandV1(
        mission_id=MISSION_ID,
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=FrozenR0CommandParameters(
            max_speed_mps=0.25,
            max_distance_m=2.0,
            max_duration_s=20,
            stop_distance_m=0.45,
        ),
        authorization_material_sha256="a" * 64,
        authorization_artifact_ref="sharepoint://ETS R0 Missions/items/42",
        gateway_decision_event_id="gateway:delivery-1:decision",
        delivery_id="delivery-1",
        issued_at=BASE_TIME,
    )


def _policy(*, max_speed: float = 0.25, allow_reverse: bool = False) -> RangerMobilityPolicy:
    return RangerMobilityPolicy(
        policy_id="ets.ranger.r0.forward-stop",
        policy_version="r0-forward-stop-policy.v1",
        max_linear_speed_mps=max_speed,
        max_yaw_rate_rad_s=0.05,
        max_command_queue_age_ms=500,
        watchdog_timeout_ms=1000,
        allow_reverse=allow_reverse,
    )


def _session() -> RangerR0ExecutionSession:
    return RangerR0ExecutionSession(
        command=_command(),
        expected_mission_id=MISSION_ID,
        vehicle_id="ets-ranger:r0-demo-001",
        controller_id="r0-controller",
        controller_session_id="r0-controller-session-001",
        boot_id="boot-r0-001",
        mobility_policy=_policy(),
        local_clock_quality=ClockQuality.SYNCHRONIZED,
    )


def _advance_to_motion_started(session: RangerR0ExecutionSession) -> list[object]:
    receipt = session.receive_command(
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=10_000_000,
    )
    mobility, authorization = session.authorize_motion(
        command_sequence=1,
        received_monotonic_ns=11_000_000,
        evaluated_monotonic_ns=12_000_000,
        evaluated_at=BASE_TIME + timedelta(milliseconds=12),
        hardware_estop_asserted=False,
    )
    started = session.observe_motion_started(
        observation_id="motion-start-1",
        sensor_id="motor-feedback-1",
        observed_at=BASE_TIME + timedelta(milliseconds=20),
        observed_monotonic_ns=20_000_000,
        observed_linear_speed_mps=0.20,
        observed_yaw_rate_rad_s=0.0,
    )
    return [receipt, mobility, authorization, started]


def _stop_observation(
    *,
    mission_id: str = MISSION_ID,
    obstacle_present: bool = True,
    stopping_point_reached: bool = False,
    estop: bool = False,
    policy_stop: bool = False,
) -> RangerR0StopObservationV1:
    return RangerR0StopObservationV1(
        mission_id=mission_id,
        observation_id="stop-observation-1",
        sensor_id="front-range-sensor-1",
        observed_at=BASE_TIME + timedelta(milliseconds=30),
        observed_monotonic_ns=30_000_000,
        obstacle_present=obstacle_present,
        obstacle_distance_m=0.40 if obstacle_present else None,
        stopping_point_reached=stopping_point_reached,
        hardware_estop_asserted=estop,
        policy_stop_asserted=policy_stop,
    )


def test_end_to_end_obstacle_stop_preserves_one_mission_id() -> None:
    session = _session()
    initial = _advance_to_motion_started(session)

    observed = session.observe_stop_condition(_stop_observation())
    decision = session.decide_stop(
        decided_at=BASE_TIME + timedelta(milliseconds=31),
        decided_monotonic_ns=31_000_000,
    )
    actuation = session.command_stop(
        actuation_id="stop-command-1",
        commanded_at=BASE_TIME + timedelta(milliseconds=32),
        commanded_monotonic_ns=32_000_000,
    )
    result = session.observe_resulting_state(
        observation_id="result-1",
        sensor_id="wheel-speed-1",
        observed_at=BASE_TIME + timedelta(milliseconds=50),
        observed_monotonic_ns=50_000_000,
        observed_linear_speed_mps=0.0,
    )

    records = [initial[0], initial[2], initial[3], observed, decision, actuation, result]
    assert all(record.envelope.mission_id == MISSION_ID for record in records)
    assert all(record.payload.mission_id == MISSION_ID for record in records)
    assert decision.payload.reason == RangerR0StopReason.OBSTACLE_PRESENT
    assert result.payload.stopped_confirmed is True
    assert session.phase is RangerR0ExecutionPhase.RESULT_OBSERVED


def test_execution_envelopes_form_one_digest_chain() -> None:
    session = _session()
    initial = _advance_to_motion_started(session)
    observed = session.observe_stop_condition(_stop_observation())
    decision = session.decide_stop(
        decided_at=BASE_TIME + timedelta(milliseconds=31),
        decided_monotonic_ns=31_000_000,
    )
    actuation = session.command_stop(
        actuation_id="stop-command-1",
        commanded_at=BASE_TIME + timedelta(milliseconds=32),
        commanded_monotonic_ns=32_000_000,
    )
    result = session.observe_resulting_state(
        observation_id="result-1",
        sensor_id="wheel-speed-1",
        observed_at=BASE_TIME + timedelta(milliseconds=50),
        observed_monotonic_ns=50_000_000,
        observed_linear_speed_mps=0.01,
    )

    chain = [initial[0], initial[2], initial[3], observed, decision, actuation, result]
    assert chain[0].envelope.parent_event_id is None
    assert chain[0].envelope.previous_event_digest is None
    for previous, current in zip(chain, chain[1:], strict=True):
        assert current.envelope.parent_event_id == previous.envelope.event_id
        assert current.envelope.previous_event_digest == previous.envelope.canonical_digest()


def test_receipt_commits_to_exact_gateway_command() -> None:
    command = _command()
    session = _session()

    receipt = session.receive_command(
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=10_000_000,
    )

    assert receipt.payload.gateway_command_sha256 == command.payload_sha256()
    assert receipt.payload.delivery_id == command.delivery_id
    assert receipt.payload.gateway_decision_event_id == command.gateway_decision_event_id


def test_runtime_rejects_gateway_command_for_another_mission() -> None:
    with pytest.raises(RangerR0ExecutionError, match="does not match") as raised:
        RangerR0ExecutionSession(
            command=_command(),
            expected_mission_id=OTHER_MISSION_ID,
            vehicle_id="ets-ranger:r0-demo-001",
            controller_id="r0-controller",
            controller_session_id="r0-controller-session-001",
            boot_id="boot-r0-001",
            mobility_policy=_policy(),
        )

    assert raised.value.code == "mission_id_mismatch"


def test_runtime_rejects_policy_broader_than_authorized_speed() -> None:
    with pytest.raises(RangerR0ExecutionError, match="exceeds") as raised:
        RangerR0ExecutionSession(
            command=_command(),
            expected_mission_id=MISSION_ID,
            vehicle_id="ets-ranger:r0-demo-001",
            controller_id="r0-controller",
            controller_session_id="r0-controller-session-001",
            boot_id="boot-r0-001",
            mobility_policy=_policy(max_speed=0.30),
        )

    assert raised.value.code == "mobility_policy_too_broad"


def test_runtime_rejects_reverse_capable_p0_policy() -> None:
    with pytest.raises(RangerR0ExecutionError, match="prohibit reverse") as raised:
        RangerR0ExecutionSession(
            command=_command(),
            expected_mission_id=MISSION_ID,
            vehicle_id="ets-ranger:r0-demo-001",
            controller_id="r0-controller",
            controller_session_id="r0-controller-session-001",
            boot_id="boot-r0-001",
            mobility_policy=_policy(allow_reverse=True),
        )

    assert raised.value.code == "reverse_not_frozen"


def test_hardware_estop_denies_motion_before_start() -> None:
    session = _session()
    session.receive_command(
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=10_000_000,
    )

    with pytest.raises(RangerR0ExecutionError, match="denied") as raised:
        session.authorize_motion(
            command_sequence=1,
            received_monotonic_ns=11_000_000,
            evaluated_monotonic_ns=12_000_000,
            evaluated_at=BASE_TIME + timedelta(milliseconds=12),
            hardware_estop_asserted=True,
        )

    assert raised.value.code == "motion_authorization_denied"
    assert session.phase is RangerR0ExecutionPhase.RECEIVED


def test_motion_start_cannot_exceed_authorized_speed() -> None:
    session = _session()
    session.receive_command(
        received_at=BASE_TIME + timedelta(milliseconds=10),
        received_monotonic_ns=10_000_000,
    )
    session.authorize_motion(
        command_sequence=1,
        received_monotonic_ns=11_000_000,
        evaluated_monotonic_ns=12_000_000,
        evaluated_at=BASE_TIME + timedelta(milliseconds=12),
        hardware_estop_asserted=False,
    )

    with pytest.raises(RangerR0ExecutionError, match="exceeds") as raised:
        session.observe_motion_started(
            observation_id="motion-start-1",
            sensor_id="motor-feedback-1",
            observed_at=BASE_TIME + timedelta(milliseconds=20),
            observed_monotonic_ns=20_000_000,
            observed_linear_speed_mps=0.26,
            observed_yaw_rate_rad_s=0.0,
        )

    assert raised.value.code == "observed_speed_exceeds_authorization"


def test_stop_observation_from_another_mission_fails_closed() -> None:
    session = _session()
    _advance_to_motion_started(session)

    with pytest.raises(RangerR0ExecutionError, match="does not match") as raised:
        session.observe_stop_condition(_stop_observation(mission_id=OTHER_MISSION_ID))

    assert raised.value.code == "mission_id_mismatch"


def test_no_stop_condition_cannot_generate_stop_decision() -> None:
    session = _session()
    _advance_to_motion_started(session)
    session.observe_stop_condition(
        _stop_observation(obstacle_present=False, stopping_point_reached=False)
    )

    with pytest.raises(RangerR0ExecutionError, match="requires obstacle") as raised:
        session.decide_stop(
            decided_at=BASE_TIME + timedelta(milliseconds=31),
            decided_monotonic_ns=31_000_000,
        )

    assert raised.value.code == "no_stop_condition"


def test_stop_reason_precedence_is_estop_policy_obstacle_stop_point() -> None:
    session = _session()
    _advance_to_motion_started(session)
    session.observe_stop_condition(
        _stop_observation(
            obstacle_present=True,
            stopping_point_reached=True,
            estop=True,
            policy_stop=True,
        )
    )

    decision = session.decide_stop(
        decided_at=BASE_TIME + timedelta(milliseconds=31),
        decided_monotonic_ns=31_000_000,
    )

    assert decision.payload.reason is RangerR0StopReason.HARDWARE_ESTOP


def test_stopping_point_is_valid_terminal_reason() -> None:
    session = _session()
    _advance_to_motion_started(session)
    session.observe_stop_condition(
        _stop_observation(obstacle_present=False, stopping_point_reached=True)
    )

    decision = session.decide_stop(
        decided_at=BASE_TIME + timedelta(milliseconds=31),
        decided_monotonic_ns=31_000_000,
    )

    assert decision.payload.reason is RangerR0StopReason.STOPPING_POINT_REACHED


def test_result_observation_can_prove_local_stop_failure_without_rewriting_history() -> None:
    session = _session()
    _advance_to_motion_started(session)
    session.observe_stop_condition(_stop_observation())
    session.decide_stop(
        decided_at=BASE_TIME + timedelta(milliseconds=31),
        decided_monotonic_ns=31_000_000,
    )
    session.command_stop(
        actuation_id="stop-command-1",
        commanded_at=BASE_TIME + timedelta(milliseconds=32),
        commanded_monotonic_ns=32_000_000,
    )

    result = session.observe_resulting_state(
        observation_id="result-1",
        sensor_id="wheel-speed-1",
        observed_at=BASE_TIME + timedelta(milliseconds=50),
        observed_monotonic_ns=50_000_000,
        observed_linear_speed_mps=0.03,
    )

    assert result.payload.stopped_confirmed is False
    assert result.payload.observed_linear_speed_mps == 0.03


def test_execution_order_is_fail_closed() -> None:
    session = _session()

    with pytest.raises(RangerR0ExecutionError, match="expected Ranger R0 phase") as raised:
        session.observe_motion_started(
            observation_id="too-early",
            sensor_id="motor-feedback-1",
            observed_at=BASE_TIME,
            observed_monotonic_ns=1,
            observed_linear_speed_mps=0.1,
            observed_yaw_rate_rad_s=0.0,
        )

    assert raised.value.code == "invalid_execution_phase"
