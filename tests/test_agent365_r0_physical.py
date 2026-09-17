from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ets.demos.agent365_r0_mission import authorize_mission, create_pending_mission
from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    GatewayR0MissionGuard,
    GatewayR0MotionRequestV1,
    SqliteMissionDispatchLedger,
)
from ets.ranger.agent365_r0_boundary import (
    RangerR0BoundaryError,
    RangerR0MotionStartObservationV1,
    RangerR0ReceiptMotionBoundary,
    RangerR0ResultObservationV1,
    RangerR0StopObservationV1,
    SqliteRangerR0ReceiptLedger,
)
from ets.ranger.agent365_r0_physical import (
    RangerR0ActuatorReceiptV1,
    RangerR0PhysicalExecutionError,
    execute_physical_r0_mission,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
VEHICLE_ID = "ets-ranger:r0-demo"
CONTROLLER_ID = "controller:r0-physical"
ACTUATOR_ID = "actuator:motor-controller"
T0 = datetime(2026, 9, 17, 22, 0, tzinfo=UTC)
PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}


class ScriptClock:
    def __init__(self, monotonic_values: list[int]) -> None:
        self._values = iter(monotonic_values)
        self._offset = 0

    def now_utc(self) -> datetime:
        self._offset += 1
        return T0 + timedelta(milliseconds=self._offset)

    def monotonic_ns(self) -> int:
        return next(self._values)


class ScriptActuator:
    actuator_id = ACTUATOR_ID

    def __init__(self) -> None:
        self.motion_calls = 0
        self.stop_calls = 0
        self.fail_safe_calls: list[str] = []

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
        self.fail_safe_calls.append(reason)
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
    def __init__(self, *, estop: bool = False, never_stop: bool = False) -> None:
        self.estop = estop
        self.never_stop = never_stop
        self.stop_samples = 0

    def hardware_estop_asserted(self) -> bool:
        return self.estop

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
        self.stop_samples += 1
        return RangerR0StopObservationV1(
            mission_id=mission_id,
            observer_id="sensor:forward-range",
            observed_at=T0 + timedelta(milliseconds=30 + self.stop_samples),
            observed_monotonic_ns=30 + self.stop_samples,
            distance_travelled_m=0.40,
            elapsed_s=1.0,
            obstacle_distance_m=0.80 if self.never_stop else 0.40,
        )

    def observe_result(self, mission_id, stop_directive):
        return RangerR0ResultObservationV1(
            mission_id=mission_id,
            observer_id="sensor:pose-witness",
            observed_at=T0 + timedelta(milliseconds=60),
            observed_monotonic_ns=60,
            speed_mps=0.0,
            distance_travelled_m=0.43,
            stationary_duration_ms=300,
        )


def _received_boundary(tmp_path) -> RangerR0ReceiptMotionBoundary:
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
    request = GatewayR0MotionRequestV1(
        mission_id=MISSION_ID,
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=FrozenR0CommandParameters.model_validate(PARAMETERS),
        authorization_material_sha256=mission.authorization_material_sha256(),
        authorization_artifact_ref="sharepoint://ETS-R0-Missions/items/42",
        delivery_id="delivery-physical-1",
    )
    gateway = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "gateway.db"))
    dispatch = gateway.dispatch(request, mission, observed_at=T0)
    boundary = RangerR0ReceiptMotionBoundary(
        SqliteRangerR0ReceiptLedger(tmp_path / "ranger.db"),
        vehicle_id=VEHICLE_ID,
        controller_id=CONTROLLER_ID,
    )
    boundary.receive(
        dispatch.robot_command,
        dispatch.egress_event,
        observed_at=T0 + timedelta(microseconds=1),
        observed_monotonic_ns=1,
    )
    return boundary


def test_physical_adapter_preserves_distinct_actuation_and_sensor_evidence(tmp_path) -> None:
    boundary = _received_boundary(tmp_path)
    actuator = ScriptActuator()
    sensors = ScriptSensors()

    result = execute_physical_r0_mission(
        boundary,
        MISSION_ID,
        actuator=actuator,
        sensors=sensors,
        clock=ScriptClock([10, 40, 50]),
    )

    assert result.independent_physical_result_observed is True
    assert result.motion_actuator_receipt.claim_boundary == (
        "controller_acknowledgement_not_physical_observation"
    )
    assert result.stop_actuator_receipt.claim_boundary == (
        "controller_acknowledgement_not_physical_observation"
    )
    assert actuator.motion_calls == 1
    assert actuator.stop_calls == 1
    assert actuator.fail_safe_calls == []
    assert [record.stage.value for record in result.boundary_records] == [
        "AUTHORIZED",
        "MOTION_STARTED",
        "STOP_CONDITION_OBSERVED",
        "STOP_DECIDED",
        "STOP_ACTUATED",
        "RESULT_OBSERVED",
    ]


def test_asserted_estop_prevents_motion_actuation(tmp_path) -> None:
    boundary = _received_boundary(tmp_path)
    actuator = ScriptActuator()

    with pytest.raises(RangerR0PhysicalExecutionError) as exc_info:
        execute_physical_r0_mission(
            boundary,
            MISSION_ID,
            actuator=actuator,
            sensors=ScriptSensors(estop=True),
            clock=ScriptClock([10]),
        )

    assert exc_info.value.code == "hardware_estop_asserted"
    assert actuator.motion_calls == 0
    assert actuator.stop_calls == 0


def test_missing_stop_observation_fails_safe_without_result_claim(tmp_path) -> None:
    boundary = _received_boundary(tmp_path)
    actuator = ScriptActuator()

    with pytest.raises(RangerR0PhysicalExecutionError) as exc_info:
        execute_physical_r0_mission(
            boundary,
            MISSION_ID,
            actuator=actuator,
            sensors=ScriptSensors(never_stop=True),
            clock=ScriptClock([10]),
            maximum_stop_observations=2,
        )

    assert exc_info.value.code == "stop_observation_budget_exhausted"
    assert actuator.motion_calls == 1
    assert actuator.stop_calls == 0
    assert actuator.fail_safe_calls


def test_controller_identity_cannot_be_used_as_independent_motion_observer(tmp_path) -> None:
    boundary = _received_boundary(tmp_path)
    boundary.authorize_motion(
        MISSION_ID,
        observed_at=T0 + timedelta(milliseconds=1),
        observed_monotonic_ns=10,
    )

    with pytest.raises(RangerR0BoundaryError) as exc_info:
        boundary.record_motion_started(
            RangerR0MotionStartObservationV1(
                mission_id=MISSION_ID,
                observer_id=CONTROLLER_ID,
                observed_at=T0 + timedelta(milliseconds=2),
                observed_monotonic_ns=20,
                speed_mps=0.12,
                distance_travelled_m=0.01,
            )
        )

    assert exc_info.value.code == "observer_not_independent"
