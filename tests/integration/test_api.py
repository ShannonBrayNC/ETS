from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ets.api.app import create_app
from ets.core.models import EvidenceEvent


def make_event(event_id: str = "evt_001") -> dict:
    event = EvidenceEvent(
        event_id=event_id,
        tenant_id="tenant_a",
        workspace_id="workspace_a",
        evidence_id="evidence_001",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash="c" * 64,
        content_hash_alg="sha256",
        metadata={"case": "alpha"},
        created_at_utc=datetime(2026, 5, 18, 12, 30, tzinfo=UTC),
    )
    return event.model_dump(mode="json")


def make_client() -> TestClient:
    return TestClient(create_app())


def append_event(client: TestClient, event_id: str = "evt_001") -> dict:
    response = client.post("/api/v1/events", json=make_event(event_id))
    assert response.status_code == 201
    return response.json()


def test_health_and_ready_routes():
    client = make_client()

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready", "storage": "in_memory"}


def test_log_head_route_returns_unsigned_local_head():
    client = make_client()

    response = client.get("/api/v1/log/head")

    assert response.status_code == 200
    body = response.json()
    assert body["tree_size"] == 0
    assert body["log_id"] == "ets-local-dev"
    assert body["signature"] is None


def test_event_ingestion_updates_tree_and_returns_proof_url():
    client = make_client()

    body = append_event(client)

    assert body["event_id"] == "evt_001"
    assert body["log_index"] == 0
    assert len(body["event_hash"]) == 64
    assert body["tree_head"]["tree_size"] == 1
    assert body["inclusion_proof_url"] == "/api/v1/proofs/inclusion/evt_001"


def test_duplicate_event_returns_deterministic_conflict():
    client = make_client()
    append_event(client)

    response = client.post("/api/v1/events", json=make_event())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ETS_EVENT_DUPLICATE"


def test_event_can_be_retrieved_by_id_and_index():
    client = make_client()
    append_event(client)

    by_id = client.get("/api/v1/events/evt_001")
    by_index = client.get("/api/v1/events/by-index/0")

    assert by_id.status_code == 200
    assert by_index.status_code == 200
    assert by_id.json() == by_index.json()
    assert by_id.json()["event"]["event_id"] == "evt_001"


def test_missing_event_returns_404():
    client = make_client()

    response = client.get("/api/v1/events/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ETS_EVENT_NOT_FOUND"


def test_inclusion_proof_route_and_verify_route_accept_valid_proof():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")

    proof_response = client.get("/api/v1/proofs/inclusion/evt_002")
    assert proof_response.status_code == 200

    verify_response = client.post("/api/v1/verify/inclusion", json=proof_response.json())

    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True
    assert verify_response.json()["reason"] == "ok"


def test_verify_route_rejects_tampered_proof_without_hidden_state():
    client = make_client()
    append_event(client, "evt_001")
    append_event(client, "evt_002")
    proof = client.get("/api/v1/proofs/inclusion/evt_002").json()
    proof["root_hash"] = "0" * 64

    response = client.post("/api/v1/verify/inclusion", json=proof)

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_malformed_proof_returns_validation_error():
    client = make_client()

    response = client.post("/api/v1/verify/inclusion", json={"tree_size": "bad"})

    assert response.status_code == 422


def test_openapi_schema_is_generated_with_required_routes():
    client = make_client()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/events" in paths
    assert "/api/v1/verify/inclusion" in paths
