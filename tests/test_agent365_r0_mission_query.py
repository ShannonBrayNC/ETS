from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest

import ets.ranger.agent365_r0_mission_query as mission_query
from ets.ranger.agent365_r0_evidence_v2 import (
    SCENARIO_ID,
    RangerR0EvidenceV2Bundle,
)
from ets.ranger.agent365_r0_mission_query import (
    AUTHORIZATION_ARTIFACT_ID,
    GATEWAY_ARTIFACT_IDS,
    RANGER_ARTIFACT_IDS,
    REQUIRED_SOURCE_ARTIFACT_IDS,
    RangerR0MissionQueryError,
    build_agent365_r0_mission_index,
    reconstruct_agent365_r0_mission,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
SECOND_MISSION_ID = "9f91831c-e420-4727-9158-c3a50521463b"


def _bundle(mission_id: str = MISSION_ID) -> RangerR0EvidenceV2Bundle:
    source_artifacts = {
        artifact_id: f"retained:{artifact_id}".encode()
        for artifact_id in REQUIRED_SOURCE_ARTIFACT_IDS
    }
    closure = SimpleNamespace(
        mission_id=mission_id,
        source_artifacts=source_artifacts,
        decision_event={
            "mission_id": mission_id,
            "event_id": "stored-ranger-event-id",
            "event_digest": f"sha256:{'1' * 64}",
        },
        evidence_object=SimpleNamespace(
            identity=SimpleNamespace(evidence_id="stored-v1-evidence-id")
        ),
        evidence_object_hash="2" * 64,
    )
    evidence_v2 = SimpleNamespace(
        identity=SimpleNamespace(object_id="stored-v2-object-id"),
        extensions={
            "lantern.demo": {
                "mission_id": mission_id,
                "scenario_id": SCENARIO_ID,
            }
        },
    )
    return RangerR0EvidenceV2Bundle(
        mission_id=mission_id,
        evidence_object=cast(Any, evidence_v2),
        evidence_object_identity_hash="3" * 64,
        source_closure=cast(Any, closure),
    )


def _install_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    def verified(bundle: RangerR0EvidenceV2Bundle) -> SimpleNamespace:
        return SimpleNamespace(
            valid=True,
            mission_id=bundle.mission_id,
            physical_result_supported=True,
        )

    monkeypatch.setattr(mission_query, "verify_agent365_r0_evidence_v2", verified)


def test_reconstruction_returns_exact_retained_chain_by_mission_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_verifier(monkeypatch)
    bundle = _bundle()

    result = reconstruct_agent365_r0_mission(MISSION_ID, [bundle])

    assert result.manifest.mission_id == MISSION_ID
    assert result.manifest.scenario_id == SCENARIO_ID
    assert result.manifest.authorization_artifact_id == AUTHORIZATION_ARTIFACT_ID
    assert result.manifest.gateway_artifact_ids == GATEWAY_ARTIFACT_IDS
    assert result.manifest.ranger_artifact_ids == RANGER_ARTIFACT_IDS
    assert result.manifest.decision_event_id == "stored-ranger-event-id"
    assert result.manifest.decision_event_digest == f"sha256:{'1' * 64}"
    assert result.manifest.evidence_object_v1_id == "stored-v1-evidence-id"
    assert result.manifest.evidence_object_v1_hash == "2" * 64
    assert result.manifest.evidence_object_v2_id == "stored-v2-object-id"
    assert result.manifest.evidence_object_v2_identity_hash == "3" * 64
    assert result.manifest.physical_result_supported is True
    assert result.manifest.truth_claim_supported is False
    assert set(result.source_artifacts) == set(REQUIRED_SOURCE_ARTIFACT_IDS)
    assert (
        result.source_artifacts[AUTHORIZATION_ARTIFACT_ID]
        == f"retained:{AUTHORIZATION_ARTIFACT_ID}".encode()
    )


def test_index_rejects_duplicate_authoritative_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_verifier(monkeypatch)
    bundle = _bundle()

    with pytest.raises(RangerR0MissionQueryError) as error:
        build_agent365_r0_mission_index([bundle, bundle])

    assert error.value.code == "duplicate_mission_id"


def test_query_rejects_unknown_mission(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_verifier(monkeypatch)
    index = build_agent365_r0_mission_index([_bundle()])

    with pytest.raises(RangerR0MissionQueryError) as error:
        index.reconstruct(SECOND_MISSION_ID)

    assert error.value.code == "mission_not_found"


def test_query_rejects_incomplete_retained_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_verifier(monkeypatch)
    bundle = _bundle()
    artifacts = dict(bundle.source_closure.source_artifacts)
    artifacts.pop("source:ranger-boundary:result_observed")
    incomplete_closure = SimpleNamespace(
        **{
            **bundle.source_closure.__dict__,
            "source_artifacts": artifacts,
        }
    )
    incomplete = replace(bundle, source_closure=cast(Any, incomplete_closure))
    index = build_agent365_r0_mission_index([incomplete])

    with pytest.raises(RangerR0MissionQueryError) as error:
        index.reconstruct(MISSION_ID)

    assert error.value.code == "incomplete_source_chain"


def test_query_rejects_cross_mission_decision_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_verifier(monkeypatch)
    bundle = _bundle()
    decision_event = dict(bundle.source_closure.decision_event)
    decision_event["mission_id"] = SECOND_MISSION_ID
    drifted_closure = SimpleNamespace(
        **{
            **bundle.source_closure.__dict__,
            "decision_event": decision_event,
        }
    )
    drifted = replace(bundle, source_closure=cast(Any, drifted_closure))
    index = build_agent365_r0_mission_index([drifted])

    with pytest.raises(RangerR0MissionQueryError) as error:
        index.reconstruct(MISSION_ID)

    assert error.value.code == "decision_event_mission_mismatch"
