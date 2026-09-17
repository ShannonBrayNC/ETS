from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from fastapi.testclient import TestClient

from ets.api.auth import LocalAPIKeyAuthPolicy
from ets.demos.agent365_r0_correlation import (
    Agent365ApiMaturity,
    Agent365IdentityObservationV1,
    Agent365R0CorrelationBundleV1,
    Agent365RetainedSourceRefV1,
    Agent365RuntimeObservationV1,
    Agent365ToolObservationV1,
    Agent365ToolStatus,
)
from ets.ranger.agent365_r0_correlation_store import SQLiteAgent365R0CorrelationStore
from ets.ranger.agent365_r0_mission_api import create_agent365_r0_mission_app
from ets.ranger.agent365_r0_mission_query import RangerR0MissionChainManifest

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
T0 = datetime(2026, 9, 17, 23, 15, tzinfo=UTC)


def _credential() -> str:
    return "local-" + ("x" * 24)


def _source(family: str, suffix: str) -> Agent365RetainedSourceRefV1:
    return Agent365RetainedSourceRefV1(
        tenant_id=TENANT_ID,
        source_family=family,  # type: ignore[arg-type]
        api_maturity=Agent365ApiMaturity.DOCUMENTED_PREVIEW,
        acquisition_time=T0,
        microsoft_event_time=T0,
        payload_ref=f"ets://agent365/protected/{suffix}",
        raw_payload_sha256=suffix * 64,
        source_envelope_sha256=suffix * 64,
        collector_identity="ets.agent365-api-test",
        collector_version="1.0",
    )


def _correlation_bundle() -> Agent365R0CorrelationBundleV1:
    return Agent365R0CorrelationBundleV1(
        mission_id=MISSION_ID,
        tenant_id=TENANT_ID,
        sharepoint_item_id="42",
        sharepoint_authorization_material_sha256="4" * 64,
        sharepoint_source_payload_sha256="5" * 64,
        identity_observations=(
            Agent365IdentityObservationV1(
                observation_id="identity-1",
                source=_source("agent365.catalog", "1"),
                package_id="pkg-1",
                agent_identity_id="agent-1",
            ),
        ),
        runtime_observations=(
            Agent365RuntimeObservationV1(
                observation_id="runtime-1",
                source=_source("agent365.runtime.otel", "2"),
                package_id="pkg-1",
                agent_identity_id="agent-1",
                invocation_id="invocation-1",
                session_id="session-1",
                trace_id="trace-1",
                span_id="runtime-span",
                application_mission_id=MISSION_ID,
            ),
        ),
        tool_observations=(
            Agent365ToolObservationV1(
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
            ),
        ),
        correlation_bases=("application_mission_id",),
    )


def _manifest() -> RangerR0MissionChainManifest:
    return RangerR0MissionChainManifest(
        mission_id=MISSION_ID,
        scenario_id="agent365-ranger-r0-forward-stop.v1",
        authorization_artifact_id="source:sharepoint-authorization",
        gateway_artifact_ids=("gateway",),
        ranger_artifact_ids=("ranger",),
        retained_source_artifact_ids=("source",),
        decision_event_id="decision-1",
        decision_event_digest="sha256:" + ("1" * 64),
        evidence_object_v1_id="evidence-v1",
        evidence_object_v1_hash="2" * 64,
        evidence_object_v2_id="evidence-v2",
        evidence_object_v2_identity_hash="3" * 64,
        physical_result_supported=True,
    )


class _MissionIndex:
    def reconstruct(self, mission_id: str) -> SimpleNamespace:
        assert mission_id == MISSION_ID
        return SimpleNamespace(manifest=_manifest())


def _client(store: SQLiteAgent365R0CorrelationStore | None) -> TestClient:
    app = create_agent365_r0_mission_app(
        cast(Any, _MissionIndex()),
        auth_policy=LocalAPIKeyAuthPolicy(_credential()),
        correlation_store=store,
    )
    return TestClient(app)


def _headers() -> dict[str, str]:
    return {"X-ETS-API-Key": _credential()}


def test_api_returns_sanitized_agent365_correlation_without_raw_payloads(tmp_path) -> None:
    store = SQLiteAgent365R0CorrelationStore(tmp_path / "agent365-correlation.db")
    try:
        store.save(_correlation_bundle())
        response = _client(store).get(
            f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}",
            headers=_headers(),
        )
    finally:
        store.close()

    assert response.status_code == 200
    payload = response.json()
    correlation = payload["agent365_correlation"]
    assert correlation["state"] == "observed"
    assert correlation["raw_source_payloads_returned"] is False
    assert correlation["tool_execution_success_proves_sharepoint_state"] is False
    assert correlation["agent365_observation_proves_physical_result"] is False
    assert correlation["bundle"]["mission_id"] == MISSION_ID
    assert correlation["bundle"]["tool_observations"][0]["trace_id"] == "trace-1"
    assert "raw_payload_utf8" not in response.text
    assert "source_artifacts" not in payload
    assert payload["verifier"]["physical_result_supported"] is True


def test_api_represents_missing_agent365_runtime_as_not_observed(tmp_path) -> None:
    store = SQLiteAgent365R0CorrelationStore(tmp_path / "agent365-correlation.db")
    try:
        response = _client(store).get(
            f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}",
            headers=_headers(),
        )
    finally:
        store.close()

    assert response.status_code == 200
    correlation = response.json()["agent365_correlation"]
    assert correlation["state"] == "not_observed"
    assert "bundle" not in correlation
    assert response.json()["verifier"]["physical_result_supported"] is True


def test_api_without_correlation_store_preserves_existing_response_shape() -> None:
    response = _client(None).get(
        f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}",
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "agent365_correlation" not in payload
    assert payload["mission_id"] == MISSION_ID
