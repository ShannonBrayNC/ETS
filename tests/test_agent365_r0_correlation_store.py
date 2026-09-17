from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ets.demos.agent365_r0_correlation import (
    Agent365ApiMaturity,
    Agent365IdentityObservationV1,
    Agent365R0CorrelationBundleV1,
    Agent365RetainedSourceRefV1,
    Agent365RuntimeObservationV1,
    Agent365ToolObservationV1,
    Agent365ToolStatus,
)
from ets.ranger.agent365_r0_correlation_store import (
    Agent365R0CorrelationStoreError,
    SQLiteAgent365R0CorrelationStore,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
T0 = datetime(2026, 9, 17, 23, 0, tzinfo=UTC)


def _source(family: str, suffix: str) -> Agent365RetainedSourceRefV1:
    return Agent365RetainedSourceRefV1(
        tenant_id=TENANT_ID,
        source_family=family,  # type: ignore[arg-type]
        api_maturity=Agent365ApiMaturity.DOCUMENTED_PREVIEW,
        acquisition_time=T0,
        microsoft_event_time=T0,
        payload_ref=f"ets://agent365/source/{suffix}",
        raw_payload_sha256=suffix * 64,
        source_envelope_sha256=suffix * 64,
        collector_identity="ets.agent365-store-test",
        collector_version="1.0",
    )


def _bundle() -> Agent365R0CorrelationBundleV1:
    identity = Agent365IdentityObservationV1(
        observation_id="identity-1",
        source=_source("agent365.catalog", "1"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
    )
    runtime = Agent365RuntimeObservationV1(
        observation_id="runtime-1",
        source=_source("agent365.runtime.otel", "2"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
        invocation_id="invocation-1",
        session_id="session-1",
        trace_id="trace-1",
        span_id="runtime-span",
        application_mission_id=MISSION_ID,
    )
    tool = Agent365ToolObservationV1(
        observation_id="tool-1",
        source=_source("agent365.tool.otel", "3"),
        package_id="pkg-1",
        agent_identity_id="agent-1",
        trace_id="trace-1",
        span_id="tool-span",
        parent_span_id="runtime-span",
        tool_call_id="tool-call-1",
        tool_name="sharepoint.create_or_update_mission",
        status=Agent365ToolStatus.SUCCEEDED,
        application_mission_id=MISSION_ID,
        sharepoint_item_id="42",
        sharepoint_authorization_material_sha256="4" * 64,
    )
    return Agent365R0CorrelationBundleV1(
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        sharepoint_item_id="42",
        sharepoint_authorization_material_sha256="4" * 64,
        sharepoint_source_payload_sha256="5" * 64,
        identity_observations=(identity,),
        runtime_observations=(runtime,),
        tool_observations=(tool,),
        correlation_bases=("application_mission_id",),
    )


def test_store_reopens_and_returns_same_sanitized_bundle(tmp_path) -> None:
    path = tmp_path / "agent365-correlation.db"
    bundle = _bundle()
    store = SQLiteAgent365R0CorrelationStore(path)
    store.save(bundle)
    store.close()

    reopened = SQLiteAgent365R0CorrelationStore(path)
    try:
        assert reopened.contains(MISSION_ID) is True
        assert reopened.mission_ids() == (MISSION_ID,)
        assert reopened.load(MISSION_ID) == bundle
    finally:
        reopened.close()


def test_identical_replay_is_idempotent(tmp_path) -> None:
    store = SQLiteAgent365R0CorrelationStore(tmp_path / "agent365-correlation.db")
    try:
        bundle = _bundle()
        store.save(bundle)
        store.save(bundle)
        assert store.mission_ids() == (MISSION_ID,)
    finally:
        store.close()


def test_conflicting_same_mission_fails_closed(tmp_path) -> None:
    store = SQLiteAgent365R0CorrelationStore(tmp_path / "agent365-correlation.db")
    try:
        bundle = _bundle()
        store.save(bundle)
        changed = bundle.model_copy(update={"sharepoint_source_payload_sha256": "9" * 64})
        with pytest.raises(Agent365R0CorrelationStoreError, match="different retained"):
            store.save(changed)
    finally:
        store.close()


def test_corrupted_stored_json_hash_fails_closed(tmp_path) -> None:
    path = tmp_path / "agent365-correlation.db"
    store = SQLiteAgent365R0CorrelationStore(path)
    store.save(_bundle())
    store.close()

    import sqlite3

    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            UPDATE agent365_r0_correlation_bundles
            SET bundle_json = bundle_json || ' '
            WHERE mission_id = ?
            """,
            (MISSION_ID,),
        )
        connection.commit()
    finally:
        connection.close()

    reopened = SQLiteAgent365R0CorrelationStore(path)
    try:
        with pytest.raises(Agent365R0CorrelationStoreError, match="SHA-256"):
            reopened.load(MISSION_ID)
    finally:
        reopened.close()


def test_missing_mission_is_explicit(tmp_path) -> None:
    store = SQLiteAgent365R0CorrelationStore(tmp_path / "agent365-correlation.db")
    try:
        with pytest.raises(Agent365R0CorrelationStoreError) as exc_info:
            store.load(MISSION_ID)
        assert exc_info.value.code == "mission_not_found"
    finally:
        store.close()
