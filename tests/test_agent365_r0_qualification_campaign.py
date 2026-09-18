from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ets.demos.agent365_r0_qualification_campaign import (
    R0QualificationCampaignV1,
    R0QualificationPhase,
    R0QualificationPhaseRecordV1,
    R0QualificationPhaseState,
    retain_artifacts,
)


def _phase(
    phase: R0QualificationPhase,
    state: R0QualificationPhaseState,
) -> R0QualificationPhaseRecordV1:
    return R0QualificationPhaseRecordV1(
        phase=phase,
        state=state,
        recorded_at=datetime(2026, 9, 17, tzinfo=UTC),
    )


def _campaign(*phases: R0QualificationPhaseRecordV1) -> R0QualificationCampaignV1:
    return R0QualificationCampaignV1(
        campaign_id="agent365-r0-demo-qualification",
        code_sha="a" * 40,
        phases=tuple(phases),
    )


def test_campaign_is_not_soak_ready_until_a_through_d_pass() -> None:
    campaign = _campaign(
        _phase(R0QualificationPhase.PREFLIGHT, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.WHEELS_OFF_GROUND, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.LIVE_MISSION, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.CONTRADICTION_MATRIX, R0QualificationPhaseState.FAIL),
    )

    assert campaign.ready_for_multi_hour_soak() is False
    assert campaign.ready_for_72h_soak() is False
    assert campaign.qualified_developer_preview() is False


def test_campaign_enters_72h_only_after_multi_hour_pass() -> None:
    campaign = _campaign(
        _phase(R0QualificationPhase.PREFLIGHT, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.WHEELS_OFF_GROUND, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.LIVE_MISSION, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.CONTRADICTION_MATRIX, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.MULTI_HOUR_SOAK, R0QualificationPhaseState.PASS),
    )

    assert campaign.ready_for_multi_hour_soak() is True
    assert campaign.ready_for_72h_soak() is True
    assert campaign.qualified_developer_preview() is False


def test_campaign_requires_72h_pass_for_developer_preview_qualification() -> None:
    campaign = _campaign(
        _phase(R0QualificationPhase.PREFLIGHT, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.WHEELS_OFF_GROUND, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.LIVE_MISSION, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.CONTRADICTION_MATRIX, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.MULTI_HOUR_SOAK, R0QualificationPhaseState.PASS),
        _phase(R0QualificationPhase.SOAK_72H, R0QualificationPhaseState.PASS),
    )

    assert campaign.qualified_developer_preview() is True


def test_campaign_rejects_duplicate_phase_records() -> None:
    with pytest.raises(ValueError, match="duplicate phase"):
        _campaign(
            _phase(R0QualificationPhase.PREFLIGHT, R0QualificationPhaseState.PASS),
            _phase(R0QualificationPhase.PREFLIGHT, R0QualificationPhaseState.PASS),
        )


def test_retain_artifacts_hashes_only_files_inside_campaign_root(tmp_path) -> None:
    retained_file = tmp_path / "phase-a" / "preflight.json"
    retained_file.parent.mkdir()
    retained_file.write_text('{"motion_authorized": false}\n', encoding="utf-8")

    artifacts = retain_artifacts(tmp_path, (retained_file,))

    assert len(artifacts) == 1
    assert artifacts[0].relative_path == "phase-a/preflight.json"
    assert artifacts[0].size_bytes == retained_file.stat().st_size
    assert len(artifacts[0].sha256) == 64


def test_retain_artifacts_rejects_paths_outside_campaign_root(tmp_path) -> None:
    root = tmp_path / "campaign"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the campaign root"):
        retain_artifacts(root, (outside,))
