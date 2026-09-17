from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

import ets.ranger.agent365_r0_mission_query as mission_query
from ets.api.auth import AuthContext, AuthPolicy, LocalAPIKeyAuthPolicy
from ets.ranger.agent365_r0_evidence_v2 import (
    SCENARIO_ID,
    RangerR0EvidenceV2Bundle,
)
from ets.ranger.agent365_r0_mission_api import create_agent365_r0_mission_app
from ets.ranger.agent365_r0_mission_query import (
    REQUIRED_SOURCE_ARTIFACT_IDS,
    build_agent365_r0_mission_index,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
UNKNOWN_MISSION_ID = "9f91831c-e420-4727-9158-c3a50521463b"


def _local_test_credential() -> str:
    """Return a deterministic non-secret credential without storing a secret-like literal."""

    return "local-" + ("x" * 24)


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


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _install_verifier(monkeypatch)
    index = build_agent365_r0_mission_index([_bundle()])
    app = create_agent365_r0_mission_app(
        index,
        auth_policy=LocalAPIKeyAuthPolicy(_local_test_credential()),
    )
    return TestClient(app)


def _headers() -> dict[str, str]:
    return {"X-ETS-API-Key": _local_test_credential()}


def test_mission_api_returns_manifest_and_verifier_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)

    response = client.get(
        f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}",
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mission_id"] == MISSION_ID
    assert payload["manifest"]["mission_id"] == MISSION_ID
    assert payload["manifest"]["decision_event_id"] == "stored-ranger-event-id"
    assert payload["manifest"]["physical_result_supported"] is True
    assert payload["verifier"]["chain_verified"] is True
    assert payload["verifier"]["evidence_object_v2_verified"] is True
    assert payload["verifier"]["physical_result_supported"] is True
    assert payload["verifier"]["truth_claim_supported"] is False
    assert "source_artifacts" not in payload
    assert "bundle" not in payload


def test_mission_api_requires_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)

    response = client.get(f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "ETS_AUTH_REQUIRED"


def test_mission_api_returns_not_found_for_unknown_mission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)

    response = client.get(
        f"/api/v1/demos/agent365-r0/missions/{UNKNOWN_MISSION_ID}",
        headers=_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "mission_not_found"


class _NoEvidenceReadPolicy(AuthPolicy):
    def authenticate(self, request: Request) -> AuthContext:
        del request
        return AuthContext(
            subject="no-evidence-reader",
            roles=(),
            capabilities=(),
            authorization_profile="production",
        )


def test_mission_api_requires_evidence_read_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_verifier(monkeypatch)
    index = build_agent365_r0_mission_index([_bundle()])
    app = create_agent365_r0_mission_app(index, auth_policy=_NoEvidenceReadPolicy())
    client = TestClient(app)

    response = client.get(f"/api/v1/demos/agent365-r0/missions/{MISSION_ID}")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ETS_EVIDENCE_READ_FORBIDDEN"
