from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.demos.agent365_r0_mission import (
    MissionAuthorizationState,
    MissionStatus,
    SharePointMissionArtifactV1,
    authorize_mission,
    create_pending_mission,
)
from ets.gateway.agent365_r0_mission import (
    FrozenR0CommandParameters,
    GatewayMissionEnforcementError,
    GatewayR0MissionGuard,
    GatewayR0MotionRequestV1,
    MissionCorrelationEnvelopeV1,
    SqliteMissionDispatchLedger,
    build_correlation_envelope,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
OTHER_MISSION_ID = "88888888-8888-4888-8888-888888888888"
AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
OBSERVED_AT = datetime(2026, 9, 17, 7, 0, tzinfo=UTC)
PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}
ARTIFACT_REF = "sharepoint://ETS-R0-Missions/items/42"


def _authorized_mission() -> SharePointMissionArtifactV1:
    pending = create_pending_mission(
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=PARAMETERS,
        mission_id_factory=lambda: MISSION_ID,
    )
    return authorize_mission(
        pending,
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=OBSERVED_AT,
    )


def _request(
    mission: SharePointMissionArtifactV1,
    *,
    delivery_id: str = "delivery-1",
    retry_of_delivery_id: str | None = None,
    command_parameters: dict[str, float | int] | None = None,
    mission_id: str = MISSION_ID,
) -> GatewayR0MotionRequestV1:
    return GatewayR0MotionRequestV1(
        mission_id=mission_id,
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=FrozenR0CommandParameters.model_validate(
            command_parameters or PARAMETERS
        ),
        authorization_material_sha256=mission.authorization_material_sha256(),
        authorization_artifact_ref=ARTIFACT_REF,
        delivery_id=delivery_id,
        retry_of_delivery_id=retry_of_delivery_id,
    )


def test_correlation_envelope_hashes_source_without_mutating_it() -> None:
    raw = b'{"native":"microsoft-payload"}'

    envelope = build_correlation_envelope(
        mission_id=MISSION_ID,
        event_id="collector:event-1",
        event_type="microsoft.observation.correlated",
        source_domain="ets.microsoft-collector",
        observed_at=OBSERVED_AT,
        payload=raw,
        correlation_basis="authorization_artifact",
    )

    assert envelope.mission_id == MISSION_ID
    assert envelope.payload_sha256 == hashlib.sha256(raw).hexdigest()
    assert envelope.schema_version == "ets.demo.agent365-r0.mission-event.v1"
    assert raw == b'{"native":"microsoft-payload"}'


def test_envelope_rejects_non_uuid4_mission_id() -> None:
    with pytest.raises(ValidationError, match="UUIDv4"):
        MissionCorrelationEnvelopeV1(
            mission_id="11111111-1111-1111-8111-111111111111",
            event_id="event-1",
            event_type="gateway.command.received",
            source_domain="ets.gateway",
            observed_at=OBSERVED_AT,
            payload_sha256="0" * 64,
        )


def test_first_dispatch_propagates_one_mission_id_across_gateway(tmp_path) -> None:
    mission = _authorized_mission()
    ledger = SqliteMissionDispatchLedger(tmp_path / "dispatch.db")
    guard = GatewayR0MissionGuard(ledger)

    result = guard.dispatch(_request(mission), mission, observed_at=OBSERVED_AT)

    assert result.transport_retry is False
    assert result.ingress_event.mission_id == MISSION_ID
    assert result.decision_event.mission_id == MISSION_ID
    assert result.egress_event.mission_id == MISSION_ID
    assert result.robot_command.mission_id == MISSION_ID
    assert result.ingress_event.event_id != result.decision_event.event_id
    assert result.decision_event.event_id != result.egress_event.event_id
    assert result.robot_command.gateway_decision_event_id == result.decision_event.event_id
    assert result.egress_event.payload_sha256 == result.robot_command.payload_sha256()
    assert result.decision_event.previous_event_digest == result.ingress_event.canonical_digest()
    assert result.egress_event.previous_event_digest == result.decision_event.canonical_digest()


def test_gateway_rejects_mission_id_mismatch_before_dispatch(tmp_path) -> None:
    mission = _authorized_mission()
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(
            _request(mission, mission_id=OTHER_MISSION_ID),
            mission,
            observed_at=OBSERVED_AT,
        )

    assert error.value.code == "mission_id_mismatch"


def test_gateway_rejects_non_authorized_sharepoint_state(tmp_path) -> None:
    pending = create_pending_mission(
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=PARAMETERS,
        mission_id_factory=lambda: MISSION_ID,
    )
    request_values = {
        "mission_id": MISSION_ID,
        "policy_version": "r0-forward-stop-policy.v1",
        "command_parameters": FrozenR0CommandParameters.model_validate(PARAMETERS),
        "authorization_material_sha256": pending.authorization_material_sha256(),
        "authorization_artifact_ref": ARTIFACT_REF,
        "delivery_id": "delivery-1",
    }
    request = GatewayR0MotionRequestV1.model_validate(request_values)
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(request, pending, observed_at=OBSERVED_AT)

    assert error.value.code == "mission_not_authorized"


def test_gateway_rejects_terminal_mission(tmp_path) -> None:
    mission = _authorized_mission()
    values = mission.model_dump(mode="python")
    values["status"] = MissionStatus.COMPLETED_STOP_POINT
    terminal = SharePointMissionArtifactV1.model_validate(values)
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(_request(terminal), terminal, observed_at=OBSERVED_AT)

    assert error.value.code == "mission_terminal"


def test_request_rejects_command_beyond_frozen_speed_profile() -> None:
    mission = _authorized_mission()

    with pytest.raises(ValidationError):
        GatewayR0MotionRequestV1(
            mission_id=MISSION_ID,
            policy_version="r0-forward-stop-policy.v1",
            command_parameters=FrozenR0CommandParameters(
                max_speed_mps=0.5,
                max_distance_m=2.0,
                max_duration_s=20,
                stop_distance_m=0.45,
            ),
            authorization_material_sha256=mission.authorization_material_sha256(),
            authorization_artifact_ref=ARTIFACT_REF,
            delivery_id="delivery-1",
        )


def test_gateway_rejects_parameters_different_from_authorized_command(tmp_path) -> None:
    mission = _authorized_mission()
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))
    safer_but_different = {
        "max_speed_mps": 0.2,
        "max_distance_m": 2.0,
        "max_duration_s": 20,
        "stop_distance_m": 0.45,
    }

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(
            _request(mission, command_parameters=safer_but_different),
            mission,
            observed_at=OBSERVED_AT,
        )

    assert error.value.code == "command_parameters_mismatch"


def test_gateway_rejects_wrong_authorization_commitment(tmp_path) -> None:
    mission = _authorized_mission()
    values = _request(mission).model_dump(mode="python")
    values["authorization_material_sha256"] = "0" * 64
    request = GatewayR0MotionRequestV1.model_validate(values)
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(request, mission, observed_at=OBSERVED_AT)

    assert error.value.code == "authorization_digest_mismatch"


def test_second_dispatch_requires_explicit_retry_link(tmp_path) -> None:
    mission = _authorized_mission()
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))
    guard.dispatch(_request(mission), mission, observed_at=OBSERVED_AT)

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(
            _request(mission, delivery_id="delivery-2"),
            mission,
            observed_at=OBSERVED_AT,
        )

    assert error.value.code == "authorization_already_consumed"


def test_explicit_same_command_transport_retry_is_accepted(tmp_path) -> None:
    mission = _authorized_mission()
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))
    guard.dispatch(_request(mission), mission, observed_at=OBSERVED_AT)

    retry = guard.dispatch(
        _request(
            mission,
            delivery_id="delivery-2",
            retry_of_delivery_id="delivery-1",
        ),
        mission,
        observed_at=OBSERVED_AT,
    )

    assert retry.transport_retry is True
    assert retry.robot_command.mission_id == MISSION_ID
    assert retry.robot_command.retry_of_delivery_id == "delivery-1"
    assert retry.ingress_event.event_type == "gateway.command.retry.received"
    assert retry.egress_event.event_type == "gateway.command.retry.accepted"


def test_retry_parent_must_belong_to_same_mission(tmp_path) -> None:
    mission = _authorized_mission()
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))
    guard.dispatch(_request(mission), mission, observed_at=OBSERVED_AT)

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(
            _request(
                mission,
                delivery_id="delivery-2",
                retry_of_delivery_id="missing-delivery",
            ),
            mission,
            observed_at=OBSERVED_AT,
        )

    assert error.value.code == "invalid_retry_parent"


def test_duplicate_delivery_id_is_rejected(tmp_path) -> None:
    mission = _authorized_mission()
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))
    guard.dispatch(_request(mission), mission, observed_at=OBSERVED_AT)

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(
            _request(
                mission,
                delivery_id="delivery-1",
                retry_of_delivery_id="delivery-1",
            ),
            mission,
            observed_at=OBSERVED_AT,
        )

    assert error.value.code == "duplicate_delivery_id"


def test_authorized_artifact_outside_safety_profile_fails_closed(tmp_path) -> None:
    pending = create_pending_mission(
        policy_version="r0-forward-stop-policy.v1",
        command_parameters={
            "max_speed_mps": 0.5,
            "max_distance_m": 2.0,
            "max_duration_s": 20,
            "stop_distance_m": 0.45,
        },
        mission_id_factory=lambda: MISSION_ID,
    )
    mission = authorize_mission(
        pending,
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=OBSERVED_AT,
    )
    request = GatewayR0MotionRequestV1(
        mission_id=MISSION_ID,
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=FrozenR0CommandParameters.model_validate(PARAMETERS),
        authorization_material_sha256=mission.authorization_material_sha256(),
        authorization_artifact_ref=ARTIFACT_REF,
        delivery_id="delivery-1",
    )
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(request, mission, observed_at=OBSERVED_AT)

    assert error.value.code == "authorized_parameters_outside_safety_profile"


def test_revoked_authorization_is_rejected(tmp_path) -> None:
    mission = _authorized_mission()
    values = mission.model_dump(mode="python")
    values["authorization_state"] = MissionAuthorizationState.REVOKED
    values["status"] = MissionStatus.ABORTED_POLICY
    revoked = SharePointMissionArtifactV1.model_validate(values)
    guard = GatewayR0MissionGuard(SqliteMissionDispatchLedger(tmp_path / "dispatch.db"))

    with pytest.raises(GatewayMissionEnforcementError) as error:
        guard.dispatch(_request(revoked), revoked, observed_at=OBSERVED_AT)

    assert error.value.code == "mission_not_authorized"
