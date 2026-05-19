from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

import ets.explorer.app as explorer_app


def test_explorer_health_starts_without_static_directory() -> None:
    client = TestClient(explorer_app.app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_explorer_index_fetches_v1_tree_head(monkeypatch) -> None:
    requested_paths: list[str] = []

    async def fake_api_get(path: str) -> dict[str, Any]:
        requested_paths.append(path)
        return {
            "tree_size": 0,
            "root_hash": "0" * 64,
            "created_at_utc": "2026-05-19T00:00:00Z",
            "log_id": "ets-local-dev",
            "signature_alg": None,
            "signature": None,
            "public_key_id": None,
        }

    monkeypatch.setattr(explorer_app, "api_get", fake_api_get)
    client = TestClient(explorer_app.app)

    response = client.get("/")

    assert response.status_code == 200
    assert requested_paths == ["/api/v1/log/head"]
