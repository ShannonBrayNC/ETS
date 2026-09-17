"""P0 Agent 365 + M365 + Ranger R0 SharePoint mission artifact boundary.

This module owns creation and validation of the frozen demonstration's Microsoft-side
mission/authorization artifact.  It deliberately does not perform HTTP I/O: Microsoft Graph
transport remains a separate boundary so generation of ``mission_id`` and authorization
material can be tested deterministically.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

MISSION_CONTRACT_ID: Final = "lantern.demo.agent365-r0.mission.v1"
MISSION_SCENARIO_ID: Final = "agent365-r0-forward-stop-v1"
MISSION_REQUESTED_ACTION: Final = "MOVE_FORWARD_UNTIL_STOP_CONDITION"
SHAREPOINT_MISSION_LIST_NAME: Final = "ETS R0 Missions"


class MissionAuthorizationState(StrEnum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class MissionStatus(StrEnum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"
    COMPLETED_STOP_POINT = "COMPLETED_STOP_POINT"
    COMPLETED_OBSTACLE_STOP = "COMPLETED_OBSTACLE_STOP"
    ABORTED_ESTOP = "ABORTED_ESTOP"
    ABORTED_POLICY = "ABORTED_POLICY"
    FAILED = "FAILED"


class SharePointMissionArtifactV1(BaseModel):
    """Normalized fields for the authoritative P0 SharePoint mission list item."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mission_id: str = Field(min_length=36, max_length=36)
    scenario_id: Literal["agent365-r0-forward-stop-v1"] = MISSION_SCENARIO_ID
    requested_action: Literal["MOVE_FORWARD_UNTIL_STOP_CONDITION"] = MISSION_REQUESTED_ACTION
    authorization_state: MissionAuthorizationState = MissionAuthorizationState.PENDING
    authorized_by_object_id: str | None = Field(default=None, min_length=36, max_length=36)
    authorized_at: datetime | None = None
    policy_version: str = Field(min_length=1, max_length=256)
    command_parameters: dict[str, JsonValue] = Field(min_length=1)
    status: MissionStatus = MissionStatus.CREATED
    evidence_object_id: str | None = Field(default=None, min_length=1, max_length=512)
    evidence_bundle_ref: str | None = Field(default=None, min_length=1, max_length=2048)

    @field_validator("mission_id")
    @classmethod
    def validate_mission_id(cls, value: str) -> str:
        try:
            parsed = UUID(value)
        except ValueError as exc:
            raise ValueError("mission_id must be a canonical UUIDv4 string") from exc
        if parsed.version != 4 or str(parsed) != value:
            raise ValueError("mission_id must be a lowercase canonical UUIDv4 string")
        return value

    @field_validator("authorized_by_object_id")
    @classmethod
    def validate_authorizer_object_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = UUID(value)
        except ValueError as exc:
            raise ValueError("authorized_by_object_id must be a canonical GUID") from exc
        if str(parsed) != value:
            raise ValueError("authorized_by_object_id must be a lowercase canonical GUID")
        return value

    @field_validator("authorized_at")
    @classmethod
    def normalize_authorized_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorized_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_authorization_shape(self) -> SharePointMissionArtifactV1:
        authorization_recorded = (
            self.authorized_by_object_id is not None and self.authorized_at is not None
        )
        if self.authorization_state == MissionAuthorizationState.PENDING:
            if self.authorized_by_object_id is not None or self.authorized_at is not None:
                raise ValueError("PENDING mission cannot contain authorization metadata")
            if self.status != MissionStatus.CREATED:
                raise ValueError("PENDING mission must remain in CREATED status")
        elif not authorization_recorded:
            raise ValueError("non-PENDING mission requires authorizer object ID and timestamp")

        if self.status == MissionStatus.AUTHORIZED:
            if self.authorization_state != MissionAuthorizationState.AUTHORIZED:
                raise ValueError("AUTHORIZED mission status requires AUTHORIZED authorization state")
        if self.status in {
            MissionStatus.DISPATCHED,
            MissionStatus.EXECUTING,
            MissionStatus.COMPLETED_STOP_POINT,
            MissionStatus.COMPLETED_OBSTACLE_STOP,
        } and self.authorization_state != MissionAuthorizationState.AUTHORIZED:
            raise ValueError("active/completed motion requires AUTHORIZED authorization state")
        return self

    def canonical_command_parameters(self) -> str:
        """Return stable JSON for the SharePoint text field and authorization commitment."""

        return _canonical_json(self.command_parameters)

    def authorization_material_sha256(self) -> str:
        """Commit to the immutable command material authorized for this mission."""

        material = {
            "contract_id": MISSION_CONTRACT_ID,
            "mission_id": self.mission_id,
            "scenario_id": self.scenario_id,
            "requested_action": self.requested_action,
            "policy_version": self.policy_version,
            "command_parameters": self.command_parameters,
        }
        return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def generate_mission_id() -> str:
    """Generate the P0 correlation identifier exactly once at mission creation."""

    return str(uuid4())


def create_pending_mission(
    *,
    policy_version: str,
    command_parameters: Mapping[str, JsonValue],
    mission_id_factory: Callable[[], str] = generate_mission_id,
) -> SharePointMissionArtifactV1:
    """Create a frozen-scenario mission before any SharePoint list item is written."""

    return SharePointMissionArtifactV1(
        mission_id=mission_id_factory(),
        policy_version=policy_version,
        command_parameters=dict(command_parameters),
    )


def authorize_mission(
    mission: SharePointMissionArtifactV1,
    *,
    authorized_by_object_id: str,
    authorized_at: datetime,
) -> SharePointMissionArtifactV1:
    """Return the immutable authorized form without changing command material or mission_id."""

    if mission.authorization_state != MissionAuthorizationState.PENDING:
        raise ValueError("only a PENDING mission can be authorized")
    if mission.status != MissionStatus.CREATED:
        raise ValueError("only a CREATED mission can be authorized")

    before_digest = mission.authorization_material_sha256()
    values = mission.model_dump(mode="python")
    values.update(
        authorization_state=MissionAuthorizationState.AUTHORIZED,
        authorized_by_object_id=authorized_by_object_id,
        authorized_at=authorized_at,
        status=MissionStatus.AUTHORIZED,
    )
    authorized = SharePointMissionArtifactV1.model_validate(values)
    if authorized.authorization_material_sha256() != before_digest:
        raise ValueError("authorization transition changed frozen command material")
    return authorized


def sharepoint_create_item_body(mission: SharePointMissionArtifactV1) -> dict[str, object]:
    """Build the Microsoft Graph listItem create body for ``ETS R0 Missions``.

    Graph v1.0 creates a generic SharePoint list item with a ``fields`` dictionary. Optional
    evidence references are omitted until they exist; authorization fields are omitted while the
    mission is PENDING.
    """

    fields: dict[str, object] = {
        "Title": mission.mission_id,
        "MissionId": mission.mission_id,
        "ScenarioId": mission.scenario_id,
        "RequestedAction": mission.requested_action,
        "AuthorizationState": mission.authorization_state.value,
        "PolicyVersion": mission.policy_version,
        "CommandParameters": mission.canonical_command_parameters(),
        "Status": mission.status.value,
    }
    if mission.authorized_by_object_id is not None:
        fields["AuthorizedByObjectId"] = mission.authorized_by_object_id
    if mission.authorized_at is not None:
        fields["AuthorizedAt"] = _format_utc(mission.authorized_at)
    if mission.evidence_object_id is not None:
        fields["EvidenceObjectId"] = mission.evidence_object_id
    if mission.evidence_bundle_ref is not None:
        fields["EvidenceBundleRef"] = mission.evidence_bundle_ref
    return {"fields": fields}


def parse_sharepoint_fields(fields: Mapping[str, object]) -> SharePointMissionArtifactV1:
    """Validate fields returned by Graph instead of trusting mutable SharePoint state."""

    command_parameters_text = _required_string(fields, "CommandParameters")
    try:
        command_parameters = json.loads(command_parameters_text)
    except json.JSONDecodeError as exc:
        raise ValueError("CommandParameters must contain valid JSON") from exc
    if not isinstance(command_parameters, dict) or not command_parameters:
        raise ValueError("CommandParameters must contain a non-empty JSON object")

    authorized_at_text = _optional_string(fields, "AuthorizedAt")
    authorized_at = None if authorized_at_text is None else _parse_datetime(authorized_at_text)

    return SharePointMissionArtifactV1(
        mission_id=_required_string(fields, "MissionId"),
        scenario_id=_required_string(fields, "ScenarioId"),
        requested_action=_required_string(fields, "RequestedAction"),
        authorization_state=MissionAuthorizationState(
            _required_string(fields, "AuthorizationState")
        ),
        authorized_by_object_id=_optional_string(fields, "AuthorizedByObjectId"),
        authorized_at=authorized_at,
        policy_version=_required_string(fields, "PolicyVersion"),
        command_parameters=command_parameters,
        status=MissionStatus(_required_string(fields, "Status")),
        evidence_object_id=_optional_string(fields, "EvidenceObjectId"),
        evidence_bundle_ref=_optional_string(fields, "EvidenceBundleRef"),
    )


def assert_authorized_material_unchanged(
    authorized: SharePointMissionArtifactV1,
    observed: SharePointMissionArtifactV1,
) -> None:
    """Fail closed if mutable SharePoint state changes the previously authorized command."""

    if authorized.authorization_state != MissionAuthorizationState.AUTHORIZED:
        raise ValueError("baseline mission is not AUTHORIZED")
    if authorized.mission_id != observed.mission_id:
        raise ValueError("mission_id changed after authorization")
    if authorized.authorization_material_sha256() != observed.authorization_material_sha256():
        raise ValueError("authorized mission command material changed")


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _format_utc(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError("AuthorizedAt must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("AuthorizedAt must be timezone-aware")
    return parsed.astimezone(UTC)


def _required_string(fields: Mapping[str, object], name: str) -> str:
    value = fields.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"SharePoint field {name} must be a non-empty string")
    return value


def _optional_string(fields: Mapping[str, object], name: str) -> str | None:
    value = fields.get(name)
    if value in {None, ""}:
        return None
    if not isinstance(value, str):
        raise ValueError(f"SharePoint field {name} must be a string when present")
    return value
