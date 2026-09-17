from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ets.demos.agent365_r0_mission import (
    MISSION_REQUESTED_ACTION,
    MISSION_SCENARIO_ID,
    MissionAuthorizationState,
    MissionStatus,
    SharePointMissionArtifactV1,
    assert_authorized_material_unchanged,
    authorize_mission,
    create_pending_mission,
    parse_sharepoint_fields,
    sharepoint_create_item_body,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
AUTHORIZED_AT = datetime(2026, 9, 17, 6, 45, tzinfo=UTC)
PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}


def _pending() -> SharePointMissionArtifactV1:
    return create_pending_mission(
        policy_version="r0-forward-stop-policy.v1",
        command_parameters=PARAMETERS,
        mission_id_factory=lambda: MISSION_ID,
    )


def _authorized() -> SharePointMissionArtifactV1:
    return authorize_mission(
        _pending(),
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=AUTHORIZED_AT,
    )


def test_pending_mission_generates_one_frozen_scenario_identifier() -> None:
    mission = _pending()

    assert mission.mission_id == MISSION_ID
    assert mission.scenario_id == MISSION_SCENARIO_ID
    assert mission.requested_action == MISSION_REQUESTED_ACTION
    assert mission.authorization_state == MissionAuthorizationState.PENDING
    assert mission.status == MissionStatus.CREATED


def test_mission_id_must_be_lowercase_canonical_uuidv4() -> None:
    with pytest.raises(ValidationError, match="UUIDv4"):
        SharePointMissionArtifactV1(
            mission_id="11111111-1111-1111-8111-111111111111",
            policy_version="policy.v1",
            command_parameters=PARAMETERS,
        )

    with pytest.raises(ValidationError, match="lowercase canonical UUIDv4"):
        SharePointMissionArtifactV1(
            mission_id=MISSION_ID.upper(),
            policy_version="policy.v1",
            command_parameters=PARAMETERS,
        )


def test_authorization_transition_preserves_mission_and_command_commitment() -> None:
    pending = _pending()
    pending_digest = pending.authorization_material_sha256()

    authorized = authorize_mission(
        pending,
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=AUTHORIZED_AT,
    )

    assert authorized.mission_id == pending.mission_id
    assert authorized.command_parameters == pending.command_parameters
    assert authorized.authorization_material_sha256() == pending_digest
    assert authorized.authorization_state == MissionAuthorizationState.AUTHORIZED
    assert authorized.status == MissionStatus.AUTHORIZED
    assert authorized.authorized_by_object_id == AUTHORIZER_ID
    assert authorized.authorized_at == AUTHORIZED_AT


def test_pending_mission_cannot_claim_authorization_metadata() -> None:
    with pytest.raises(ValidationError, match="PENDING mission cannot contain"):
        SharePointMissionArtifactV1(
            mission_id=MISSION_ID,
            policy_version="policy.v1",
            command_parameters=PARAMETERS,
            authorized_by_object_id=AUTHORIZER_ID,
            authorized_at=AUTHORIZED_AT,
        )


def test_graph_create_body_uses_frozen_field_names_and_canonical_json() -> None:
    authorized = _authorized()

    body = sharepoint_create_item_body(authorized)

    assert body == {
        "fields": {
            "Title": MISSION_ID,
            "MissionId": MISSION_ID,
            "ScenarioId": MISSION_SCENARIO_ID,
            "RequestedAction": MISSION_REQUESTED_ACTION,
            "AuthorizationState": "AUTHORIZED",
            "AuthorizedByObjectId": AUTHORIZER_ID,
            "AuthorizedAt": "2026-09-17T06:45:00.000000Z",
            "PolicyVersion": "r0-forward-stop-policy.v1",
            "CommandParameters": (
                '{"max_distance_m":2.0,"max_duration_s":20,'
                '"max_speed_mps":0.25,"stop_distance_m":0.45}'
            ),
            "Status": "AUTHORIZED",
        }
    }


def test_graph_fields_round_trip_preserves_authorized_material() -> None:
    authorized = _authorized()
    fields = sharepoint_create_item_body(authorized)["fields"]
    assert isinstance(fields, dict)

    observed = parse_sharepoint_fields(fields)

    assert observed == authorized
    assert_authorized_material_unchanged(authorized, observed)


def test_parse_rejects_scenario_or_action_scope_drift() -> None:
    body = sharepoint_create_item_body(_pending())
    fields = body["fields"]
    assert isinstance(fields, dict)

    changed_scenario = dict(fields)
    changed_scenario["ScenarioId"] = "agent365-r0-route-around-obstacle-v1"
    with pytest.raises(ValueError, match="frozen P0 scenario"):
        parse_sharepoint_fields(changed_scenario)

    changed_action = dict(fields)
    changed_action["RequestedAction"] = "TURN_AND_REROUTE"
    with pytest.raises(ValueError, match="frozen P0 action"):
        parse_sharepoint_fields(changed_action)


def test_material_change_after_authorization_fails_closed() -> None:
    authorized = _authorized()
    values = authorized.model_dump(mode="python")
    values["command_parameters"] = {**PARAMETERS, "max_distance_m": 3.0}
    changed = SharePointMissionArtifactV1.model_validate(values)

    with pytest.raises(ValueError, match="command material changed"):
        assert_authorized_material_unchanged(authorized, changed)


def test_mission_id_change_after_authorization_fails_closed() -> None:
    authorized = _authorized()
    values = authorized.model_dump(mode="python")
    values["mission_id"] = "88888888-8888-4888-8888-888888888888"
    changed = SharePointMissionArtifactV1.model_validate(values)

    with pytest.raises(ValueError, match="mission_id changed"):
        assert_authorized_material_unchanged(authorized, changed)


def test_parse_rejects_invalid_command_parameters_json() -> None:
    body = sharepoint_create_item_body(_pending())
    fields = body["fields"]
    assert isinstance(fields, dict)
    fields["CommandParameters"] = "not-json"

    with pytest.raises(ValueError, match="valid JSON"):
        parse_sharepoint_fields(fields)


def test_parse_rejects_non_string_optional_sharepoint_values() -> None:
    body = sharepoint_create_item_body(_pending())
    fields = body["fields"]
    assert isinstance(fields, dict)
    fields["EvidenceObjectId"] = {"unexpected": "shape"}

    with pytest.raises(ValueError, match="EvidenceObjectId must be a string"):
        parse_sharepoint_fields(fields)
