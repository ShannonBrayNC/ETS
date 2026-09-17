from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import ets.ranger.agent365_r0_mission_store as mission_store
from ets.evidence_object import (
    ContractBinding,
    EvidenceIdentity,
    EvidenceIdentityV2,
    EvidenceObject,
    EvidenceObjectV2,
)
from ets.ranger.agent365_r0_evidence import RangerR0ConsequenceClosureBundle
from ets.ranger.agent365_r0_evidence_v2 import RangerR0EvidenceV2Bundle
from ets.ranger.agent365_r0_mission_store import (
    RangerR0MissionStoreError,
    SQLiteRangerR0MissionBundleStore,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"


def _bundle(*, source_value: bytes = b"retained-source-bytes") -> RangerR0EvidenceV2Bundle:
    created_at = datetime(2026, 9, 17, 20, 30, tzinfo=UTC)
    evidence_v1 = EvidenceObject(
        identity=EvidenceIdentity(
            evidence_id="evidence-v1:test",
            version=1,
            namespace="lantern.demo",
            evidence_type="test-r0-closure",
        ),
        created_at=created_at,
    )
    evidence_v2 = EvidenceObjectV2(
        identity=EvidenceIdentityV2(
            object_id="evidence-v2:test",
            namespace="lantern.demo",
            object_type="test-r0-closure",
            version=1,
        ),
        created_at=created_at,
        bindings=(
            ContractBinding(
                binding_type="context",
                contract_id="lantern.demo.test",
                subject_ref=f"mission:{MISSION_ID}",
            ),
        ),
    )
    closure = RangerR0ConsequenceClosureBundle(
        mission_id=MISSION_ID,
        decision_event={"mission_id": MISSION_ID, "event_id": "event:test"},
        evidence_object=evidence_v1,
        evidence_object_hash="a" * 64,
        evidence_bundle_ref=f"ets://mission/{MISSION_ID}/bundle/test",
        source_artifacts={"source:test": source_value},
    )
    return RangerR0EvidenceV2Bundle(
        mission_id=MISSION_ID,
        evidence_object=evidence_v2,
        evidence_object_identity_hash="b" * 64,
        source_closure=closure,
    )


def _accept_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    def verified(bundle: RangerR0EvidenceV2Bundle) -> SimpleNamespace:
        return SimpleNamespace(valid=True, mission_id=bundle.mission_id)

    monkeypatch.setattr(mission_store, "verify_agent365_r0_evidence_v2", verified)


def test_durable_store_round_trips_exact_source_bytes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_verification(monkeypatch)
    store = SQLiteRangerR0MissionBundleStore(tmp_path / "missions.db")
    original = _bundle(source_value=b"\x00binary\xffsource")

    store.save(original)
    loaded = store.load(MISSION_ID)

    assert loaded.mission_id == MISSION_ID
    assert loaded.evidence_object.identity.object_id == "evidence-v2:test"
    assert loaded.source_closure.evidence_object.identity.evidence_id == "evidence-v1:test"
    assert loaded.source_closure.source_artifacts["source:test"] == b"\x00binary\xffsource"
    assert store.mission_ids() == (MISSION_ID,)
    store.close()


def test_durable_store_exact_replay_is_idempotent(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_verification(monkeypatch)
    store = SQLiteRangerR0MissionBundleStore(tmp_path / "missions.db")
    bundle = _bundle()

    store.save(bundle)
    store.save(bundle)

    assert store.mission_ids() == (MISSION_ID,)
    store.close()


def test_durable_store_rejects_conflicting_history(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_verification(monkeypatch)
    store = SQLiteRangerR0MissionBundleStore(tmp_path / "missions.db")
    store.save(_bundle(source_value=b"first"))

    with pytest.raises(RangerR0MissionStoreError) as exc_info:
        store.save(_bundle(source_value=b"different"))

    assert exc_info.value.code == "duplicate_mission_conflict"
    store.close()


def test_durable_store_detects_retained_envelope_tampering(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _accept_verification(monkeypatch)
    path = tmp_path / "missions.db"
    store = SQLiteRangerR0MissionBundleStore(path)
    store.save(_bundle())
    store.close()

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE agent365_r0_mission_bundles
            SET bundle_json = bundle_json || ' '
            WHERE mission_id = ?
            """,
            (MISSION_ID,),
        )
        connection.commit()

    reopened = SQLiteRangerR0MissionBundleStore(path)
    with pytest.raises(RangerR0MissionStoreError) as exc_info:
        reopened.load(MISSION_ID)

    assert exc_info.value.code == "stored_bundle_hash_mismatch"
    reopened.close()
