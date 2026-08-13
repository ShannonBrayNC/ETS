from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ets.edge import upstream_demo


def _payload(event_hash: str = "a" * 64) -> dict[str, object]:
    return {
        "sync_schema": "ets.edge.sync.v1",
        "idempotency_key": "ets-edge-sync-v1:test-key",
        "tenant_id": "tenant_demo",
        "workspace_id": "workspace_alpha",
        "event_id": "evt_demo_001",
        "event_hash": event_hash,
        "tree_head": {
            "root_hash": "b" * 64,
            "tree_size": 1,
            "signature": "demo-signature",
        },
        "raw_payload_included": False,
    }


def test_upstream_replay_is_idempotent(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("ETS_EDGE_UPSTREAM_DB", str(tmp_path / "upstream.db"))
    client = TestClient(upstream_demo.app)

    first = client.post("/edge/v1/upstream/records", json=_payload())
    second = client.post("/edge/v1/upstream/records", json=_payload())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert client.get("/edge/v1/upstream/status").json()["accepted_records"] == 1


def test_upstream_conflicting_idempotency_key_fails_closed(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("ETS_EDGE_UPSTREAM_DB", str(tmp_path / "upstream.db"))
    client = TestClient(upstream_demo.app)

    assert client.post("/edge/v1/upstream/records", json=_payload()).status_code == 200
    conflict = client.post(
        "/edge/v1/upstream/records",
        json=_payload(event_hash="c" * 64),
    )

    assert conflict.status_code == 409
    assert client.get("/edge/v1/upstream/status").json()["accepted_records"] == 1


def test_upstream_refuses_raw_evidence_replication(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("ETS_EDGE_UPSTREAM_DB", str(tmp_path / "upstream.db"))
    client = TestClient(upstream_demo.app)
    payload = _payload()
    payload["raw_payload_included"] = True
    payload["raw_payload"] = {"secret": "must-not-cross-boundary"}

    response = client.post("/edge/v1/upstream/records", json=payload)

    assert response.status_code == 422
    assert client.get("/edge/v1/upstream/status").json()["accepted_records"] == 0
