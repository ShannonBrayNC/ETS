"""Retained qualification-campaign manifest for the Agent 365 -> physical R0 demo."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictCampaignModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class R0QualificationPhase(StrEnum):
    PREFLIGHT = "A_preflight"
    WHEELS_OFF_GROUND = "B_wheels_off_ground"
    LIVE_MISSION = "C_live_mission"
    CONTRADICTION_MATRIX = "D_contradiction_matrix"
    MULTI_HOUR_SOAK = "E_multi_hour_soak"
    SOAK_72H = "F_72h_soak"


class R0QualificationPhaseState(StrEnum):
    NOT_RUN = "not_run"
    PASS = "pass"
    FAIL = "fail"


class RetainedArtifactV1(StrictCampaignModel):
    schema_version: Literal["ets.demo.agent365-r0.retained-artifact.v1"] = (
        "ets.demo.agent365-r0.retained-artifact.v1"
    )
    relative_path: str = Field(min_length=1, max_length=4096)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class R0QualificationPhaseRecordV1(StrictCampaignModel):
    schema_version: Literal["ets.demo.agent365-r0.qualification-phase.v1"] = (
        "ets.demo.agent365-r0.qualification-phase.v1"
    )
    phase: R0QualificationPhase
    state: R0QualificationPhaseState
    recorded_at: datetime
    mission_ids: tuple[str, ...] = ()
    artifacts: tuple[RetainedArtifactV1, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("recorded_at")
    @classmethod
    def normalize_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("phase record time must be timezone-aware")
        return value.astimezone(UTC)


class R0QualificationCampaignV1(StrictCampaignModel):
    schema_version: Literal["ets.demo.agent365-r0.qualification-campaign.v1"] = (
        "ets.demo.agent365-r0.qualification-campaign.v1"
    )
    campaign_id: str = Field(min_length=1, max_length=256)
    code_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    hardware_profile: Literal["r0-bench-pi-drv8833-dual-vl53l0x.v1"] = (
        "r0-bench-pi-drv8833-dual-vl53l0x.v1"
    )
    phases: tuple[R0QualificationPhaseRecordV1, ...]
    claim_boundary: Literal[
        "bounded_developer_preview_qualification_not_general_autonomous_safety"
    ] = "bounded_developer_preview_qualification_not_general_autonomous_safety"

    @model_validator(mode="after")
    def validate_unique_phases(self) -> R0QualificationCampaignV1:
        phase_names = [item.phase for item in self.phases]
        if len(phase_names) != len(set(phase_names)):
            raise ValueError("qualification campaign contains duplicate phase records")
        return self

    def phase_state(self, phase: R0QualificationPhase) -> R0QualificationPhaseState:
        for item in self.phases:
            if item.phase is phase:
                return item.state
        return R0QualificationPhaseState.NOT_RUN

    def ready_for_multi_hour_soak(self) -> bool:
        required = (
            R0QualificationPhase.PREFLIGHT,
            R0QualificationPhase.WHEELS_OFF_GROUND,
            R0QualificationPhase.LIVE_MISSION,
            R0QualificationPhase.CONTRADICTION_MATRIX,
        )
        return all(self.phase_state(phase) is R0QualificationPhaseState.PASS for phase in required)

    def ready_for_72h_soak(self) -> bool:
        return (
            self.ready_for_multi_hour_soak()
            and self.phase_state(R0QualificationPhase.MULTI_HOUR_SOAK)
            is R0QualificationPhaseState.PASS
        )

    def qualified_developer_preview(self) -> bool:
        return (
            self.ready_for_72h_soak()
            and self.phase_state(R0QualificationPhase.SOAK_72H)
            is R0QualificationPhaseState.PASS
        )


def retain_artifacts(
    root: str | Path,
    paths: tuple[str | Path, ...],
) -> tuple[RetainedArtifactV1, ...]:
    """Hash selected retained artifacts using paths relative to the campaign root."""

    campaign_root = Path(root).resolve()
    retained: list[RetainedArtifactV1] = []
    for candidate in paths:
        path = Path(candidate).resolve()
        try:
            relative = path.relative_to(campaign_root)
        except ValueError as exc:
            raise ValueError("qualification artifacts must remain inside the campaign root") from exc
        if not path.is_file():
            raise ValueError(f"qualification artifact is not a file: {relative}")
        payload = path.read_bytes()
        retained.append(
            RetainedArtifactV1(
                relative_path=relative.as_posix(),
                sha256=hashlib.sha256(payload).hexdigest(),
                size_bytes=len(payload),
            )
        )
    return tuple(sorted(retained, key=lambda item: item.relative_path))


__all__ = [
    "R0QualificationCampaignV1",
    "R0QualificationPhase",
    "R0QualificationPhaseRecordV1",
    "R0QualificationPhaseState",
    "RetainedArtifactV1",
    "retain_artifacts",
]
