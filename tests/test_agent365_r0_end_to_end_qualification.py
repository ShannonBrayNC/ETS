from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ets.demos.agent365_r0_qualification import run_agent365_r0_reference_qualification
from ets.ranger.agent365_r0_mission_api import create_agent365_r0_mission_app
from ets.ranger.agent365_r0_mission_store import SQLiteRangerR0MissionBundleStore

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
T0 = datetime(2026, 9, 17, 20, 55, tzinfo=UTC)


def test_reference_mission_survives_restart_and_http_reconstruction(tmp_path) -> None:
    report = run_agent365_r0_reference_qualification(
        tmp_path,
        mission_id=MISSION_ID,
        started_at=T0,
    )

    assert report.mission_id == MISSION_ID
    assert report.stage_count == 7
    assert report.retained_mission_count_after_restart == 1
    assert report.chain_verified is True
    assert report.evidence_object_v2_verified is True
    assert report.physical_result_supported is True
    assert report.truth_claim_supported is False

    run_dir = tmp_path / MISSION_ID
    assert (run_dir / "gateway.db").exists()
    assert (run_dir / "ranger.db").exists()
    assert (run_dir / "mission-bundles.db").exists()
    assert (run_dir / "qualification-report.json").exists()

    # Simulate a separately started read service: reconstruct only from durable custody.
    store = SQLiteRangerR0MissionBundleStore(run_dir / "mission-bundles.db")
    try:
        app = create_agent365_r0_mission_app(store.build_index())
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}"
            )
    finally:
        store.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["mission_id"] == MISSION_ID
    assert payload["manifest"]["mission_id"] == MISSION_ID
    assert payload["manifest"]["scenario_id"] == report.scenario_id
    assert payload["manifest"]["decision_event_id"] == report.decision_event_id
    assert payload["manifest"]["decision_event_digest"] == report.decision_event_digest
    assert payload["manifest"]["evidence_object_v1_hash"] == report.evidence_object_v1_hash
    assert (
        payload["manifest"]["evidence_object_v2_identity_hash"]
        == report.evidence_object_v2_identity_hash
    )
    assert payload["verifier"]["chain_verified"] is True
    assert payload["verifier"]["evidence_object_v2_verified"] is True
    assert payload["verifier"]["physical_result_supported"] is True
    assert payload["verifier"]["truth_claim_supported"] is False


def test_reference_qualification_retains_distinct_missions_without_cross_splice(tmp_path) -> None:
    second_mission_id = "6b849951-c814-4dde-981f-68744f977731"

    first = run_agent365_r0_reference_qualification(
        tmp_path,
        mission_id=MISSION_ID,
        started_at=T0,
    )
    second = run_agent365_r0_reference_qualification(
        tmp_path,
        mission_id=second_mission_id,
        started_at=T0,
    )

    assert first.mission_id != second.mission_id
    assert first.decision_event_id != second.decision_event_id
    assert first.evidence_object_v1_hash != second.evidence_object_v1_hash
    assert first.evidence_object_v2_identity_hash != second.evidence_object_v2_identity_hash
