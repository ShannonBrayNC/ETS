"""Append-only operator recorder for the physical Agent 365 -> R0 qualification campaign."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from ets.demos.agent365_r0_qualification_campaign import (
    R0QualificationCampaignV1,
    R0QualificationPhase,
    R0QualificationPhaseRecordV1,
    R0QualificationPhaseState,
    retain_artifacts,
)

CAMPAIGN_FILENAME = "campaign.json"
CAMPAIGN_SHA256_FILENAME = "campaign.sha256"
HARDWARE_PROFILE = "r0-bench-pi-drv8833-dual-vl53l0x.v1"


class R0QualificationRecorderError(RuntimeError):
    """Raised when retained campaign state cannot safely advance."""


_PHASE_PREREQUISITES: dict[R0QualificationPhase, tuple[R0QualificationPhase, ...]] = {
    R0QualificationPhase.PREFLIGHT: (),
    R0QualificationPhase.WHEELS_OFF_GROUND: (R0QualificationPhase.PREFLIGHT,),
    R0QualificationPhase.LIVE_MISSION: (
        R0QualificationPhase.PREFLIGHT,
        R0QualificationPhase.WHEELS_OFF_GROUND,
    ),
    R0QualificationPhase.CONTRADICTION_MATRIX: (
        R0QualificationPhase.PREFLIGHT,
        R0QualificationPhase.WHEELS_OFF_GROUND,
        R0QualificationPhase.LIVE_MISSION,
    ),
    R0QualificationPhase.MULTI_HOUR_SOAK: (
        R0QualificationPhase.PREFLIGHT,
        R0QualificationPhase.WHEELS_OFF_GROUND,
        R0QualificationPhase.LIVE_MISSION,
        R0QualificationPhase.CONTRADICTION_MATRIX,
    ),
    R0QualificationPhase.SOAK_72H: (
        R0QualificationPhase.PREFLIGHT,
        R0QualificationPhase.WHEELS_OFF_GROUND,
        R0QualificationPhase.LIVE_MISSION,
        R0QualificationPhase.CONTRADICTION_MATRIX,
        R0QualificationPhase.MULTI_HOUR_SOAK,
    ),
}


def initialize_campaign(
    root: str | Path,
    *,
    campaign_id: str,
    code_sha: str,
) -> R0QualificationCampaignV1:
    campaign_root = Path(root)
    campaign_root.mkdir(parents=True, exist_ok=True)
    manifest_path = campaign_root / CAMPAIGN_FILENAME
    if manifest_path.exists():
        raise R0QualificationRecorderError("qualification campaign already exists")

    campaign = R0QualificationCampaignV1(
        campaign_id=campaign_id,
        code_sha=code_sha,
        phases=(),
    )
    _write_campaign(campaign_root, campaign)
    return campaign


def load_campaign(root: str | Path) -> R0QualificationCampaignV1:
    manifest_path = Path(root) / CAMPAIGN_FILENAME
    if not manifest_path.is_file():
        raise R0QualificationRecorderError("qualification campaign manifest is missing")
    return R0QualificationCampaignV1.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )


def append_phase(
    root: str | Path,
    *,
    phase: R0QualificationPhase,
    state: R0QualificationPhaseState,
    artifact_paths: tuple[str | Path, ...],
    notes: tuple[str, ...] = (),
    mission_ids: tuple[str, ...] = (),
    operator_observation: str | None = None,
    recorded_at: datetime | None = None,
) -> R0QualificationCampaignV1:
    campaign_root = Path(root)
    campaign = load_campaign(campaign_root)

    if any(item.phase is phase for item in campaign.phases):
        raise R0QualificationRecorderError(
            f"qualification phase {phase.value} is already retained and immutable"
        )

    if state is R0QualificationPhaseState.PASS:
        _require_prerequisites(campaign, phase)
        _validate_pass_artifacts(
            campaign_root,
            phase=phase,
            artifact_paths=artifact_paths,
            operator_observation=operator_observation,
        )

    retained = retain_artifacts(campaign_root, artifact_paths)
    phase_notes = notes
    if operator_observation is not None:
        phase_notes = (*phase_notes, f"operator_observation:{operator_observation}")

    record = R0QualificationPhaseRecordV1(
        phase=phase,
        state=state,
        recorded_at=recorded_at or datetime.now(UTC),
        mission_ids=mission_ids,
        artifacts=retained,
        notes=phase_notes,
    )
    updated = campaign.model_copy(update={"phases": (*campaign.phases, record)})
    _write_campaign(campaign_root, updated)
    return updated


def campaign_status(root: str | Path) -> dict[str, object]:
    campaign = load_campaign(root)
    return {
        "campaign_id": campaign.campaign_id,
        "code_sha": campaign.code_sha,
        "hardware_profile": campaign.hardware_profile,
        "phases": {
            phase.value: campaign.phase_state(phase).value for phase in R0QualificationPhase
        },
        "ready_for_phase_c_live_mission": (
            campaign.phase_state(R0QualificationPhase.PREFLIGHT)
            is R0QualificationPhaseState.PASS
            and campaign.phase_state(R0QualificationPhase.WHEELS_OFF_GROUND)
            is R0QualificationPhaseState.PASS
        ),
        "ready_for_multi_hour_soak": campaign.ready_for_multi_hour_soak(),
        "ready_for_72h_soak": campaign.ready_for_72h_soak(),
        "qualified_developer_preview": campaign.qualified_developer_preview(),
        "claim_boundary": campaign.claim_boundary,
    }


def _require_prerequisites(
    campaign: R0QualificationCampaignV1,
    phase: R0QualificationPhase,
) -> None:
    missing = [
        required.value
        for required in _PHASE_PREREQUISITES[phase]
        if campaign.phase_state(required) is not R0QualificationPhaseState.PASS
    ]
    if missing:
        raise R0QualificationRecorderError(
            f"cannot retain PASS for {phase.value}; prerequisite PASS missing: {', '.join(missing)}"
        )


def _validate_pass_artifacts(
    root: Path,
    *,
    phase: R0QualificationPhase,
    artifact_paths: tuple[str | Path, ...],
    operator_observation: str | None,
) -> None:
    if not artifact_paths:
        raise R0QualificationRecorderError("a PASS phase must retain at least one artifact")

    payloads = [_read_json_inside_root(root, path) for path in artifact_paths]
    if phase is R0QualificationPhase.PREFLIGHT:
        if not any(_valid_preflight_payload(payload) for payload in payloads):
            raise R0QualificationRecorderError(
                "Phase A PASS requires a successful no-motion preflight JSON artifact"
            )
    elif phase is R0QualificationPhase.WHEELS_OFF_GROUND:
        if not any(_valid_wheels_off_ground_payload(payload) for payload in payloads):
            raise R0QualificationRecorderError(
                "Phase B PASS requires a successful wheels-off-ground JSON artifact"
            )
        if operator_observation != "both_wheels_forward":
            raise R0QualificationRecorderError(
                "Phase B PASS requires explicit operator observation: both_wheels_forward"
            )


def _read_json_inside_root(root: Path, candidate: str | Path) -> dict[str, object]:
    campaign_root = root.resolve()
    path = Path(candidate).resolve()
    try:
        path.relative_to(campaign_root)
    except ValueError as exc:
        raise R0QualificationRecorderError(
            "qualification artifacts must remain inside the campaign root"
        ) from exc
    if path.suffix.lower() != ".json":
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _valid_preflight_payload(payload: dict[str, object]) -> bool:
    return (
        payload.get("profile") == HARDWARE_PROFILE
        and payload.get("motion_authorized") is False
        and payload.get("estop_circuit_closed") is True
        and payload.get("actuator_outputs_forced_stopped") is True
        and payload.get("claim_boundary")
        == "preflight_only_no_motor_motion_or_physical_mission_claim"
    )


def _valid_wheels_off_ground_payload(payload: dict[str, object]) -> bool:
    return (
        payload.get("profile") == HARDWARE_PROFILE
        and payload.get("gate") == R0QualificationPhase.WHEELS_OFF_GROUND.value
        and payload.get("automated_checks_passed") is True
        and payload.get("rear_translation_within_limit") is True
        and payload.get("estop_circuit_closed_before") is True
        and payload.get("estop_asserted_during_pulse") is False
        and payload.get("stop_command_completed_after") is True
        and payload.get("controller_acknowledgement_proves_translation") is False
        and payload.get("wheel_direction_inferred") is False
    )


def _write_campaign(root: Path, campaign: R0QualificationCampaignV1) -> None:
    payload = campaign.model_dump_json(indent=2).encode("utf-8") + b"\n"
    temp_path = root / f".{CAMPAIGN_FILENAME}.tmp"
    manifest_path = root / CAMPAIGN_FILENAME
    temp_path.write_bytes(payload)
    temp_path.replace(manifest_path)

    digest = hashlib.sha256(payload).hexdigest()
    (root / CAMPAIGN_SHA256_FILENAME).write_text(
        f"{digest}  {CAMPAIGN_FILENAME}\n",
        encoding="utf-8",
    )


__all__ = [
    "R0QualificationRecorderError",
    "append_phase",
    "campaign_status",
    "initialize_campaign",
    "load_campaign",
]
