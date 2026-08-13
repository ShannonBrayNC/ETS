from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ets.edge import protected_ingress, webhook_adapter
from ets.edge.device_identity import build_device_identity, write_device_identity


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 201) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        del args

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, object | None],
    ) -> _FakeResponse:
        del url, headers, json
        return _FakeResponse(
            {
                "log_index": 0,
                "event_hash": "b" * 64,
                "tree_head": {
                    "log_id": "ets-edge-virtual-demo",
                    "tree_size": 1,
                    "root_hash": "c" * 64,
                    "timestamp_utc": "2026-08-13T01:00:00Z",
                    "signature": "demo-signature",
                    "signature_alg": "ed25519",
                    "key_id": "demo-key",
                },
            }
        )


def _client(monkeypatch: Any, tmp_path: Path) -> tuple[TestClient, str]:
    api_key = "K" * 32
    api_key_path = tmp_path / "edge-local-api-key"
    api_key_path.write_text(api_key + "\n", encoding="utf-8")

    identity_path = tmp_path / "edge-device-identity.json"
    identity = build_device_identity("11" * 32, "ets-edge-virtual-demo-key")
    write_device_identity(identity_path, identity)

    monkeypatch.setenv("ETS_EDGE_API_KEY_FILE", str(api_key_path))
    monkeypatch.setenv("ETS_EDGE_DEVICE_IDENTITY_FILE", str(identity_path))
    monkeypatch.setenv("ETS_EDGE_API_URL", "http://edge-api.test")
    monkeypatch.setenv("ETS_EDGE_SYNC_DB", str(tmp_path / "sync.db"))
    monkeypatch.setenv("ETS_EDGE_SYNC_MAX_ITEMS", "100")
    monkeypatch.setenv("ETS_EDGE_SYNC_MAX_BYTES", str(16 * 1024 * 1024))
    monkeypatch.delenv("ETS_EDGE_SYSLOG_ENABLED", raising=False)
    monkeypatch.setattr(webhook_adapter.httpx, "AsyncClient", _FakeAsyncClient)
    webhook_adapter._SYNC_QUEUE = None
    return TestClient(protected_ingress.app), api_key


def test_health_and_public_device_identity_do_not_require_secret(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client, _api_key = _client(monkeypatch, tmp_path)

    health = client.get("/health")
    identity = client.get("/edge/v1/device/identity")

    assert health.status_code == 200
    assert identity.status_code == 200
    payload = identity.json()
    assert payload["key_custody"] == "software_volume"
    assert payload["hardware_attested"] is False
    assert "private" not in json.dumps(payload).lower()
    assert "api_key" not in json.dumps(payload).lower()


def test_protected_ingress_rejects_missing_and_wrong_key(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client, _api_key = _client(monkeypatch, tmp_path)
    headers = {
        "Content-Type": "application/json",
        "X-ETS-Tenant": "tenant_demo",
        "X-ETS-Workspace": "workspace_alpha",
    }

    missing = client.post(
        "/edge/v1/capture/webhook/demo",
        content=b'{"ok":true}',
        headers=headers,
    )
    wrong = client.post(
        "/edge/v1/capture/webhook/demo",
        content=b'{"ok":true}',
        headers={**headers, "X-ETS-API-Key": "W" * 32},
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json()["error"]["code"] == "ETS_EDGE_AUTH_REQUIRED"


def test_correct_key_allows_webhook_and_operator_sync_status(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client, api_key = _client(monkeypatch, tmp_path)
    headers = {
        "Content-Type": "application/json",
        "X-ETS-Tenant": "tenant_demo",
        "X-ETS-Workspace": "workspace_alpha",
        "X-ETS-API-Key": api_key,
    }

    capture = client.post(
        "/edge/v1/capture/webhook/demo",
        content=b'{"ok":true}',
        headers=headers,
    )
    denied_status = client.get("/edge/v1/sync/status")
    allowed_status = client.get(
        "/edge/v1/sync/status",
        headers={"X-ETS-API-Key": api_key},
    )

    assert capture.status_code == 201
    assert capture.json()["sync_state"] == "pending"
    assert denied_status.status_code == 401
    assert allowed_status.status_code == 200
    assert allowed_status.json()["queue_depth"] == 1
