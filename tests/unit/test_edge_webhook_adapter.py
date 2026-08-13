from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ets.edge import webhook_adapter


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 201) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeAsyncClient:
    captured_url: str | None = None
    captured_headers: dict[str, str] | None = None
    captured_json: dict[str, object | None] | None = None
    upstream_statuses: list[int] = []
    conflict_ack = False

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
        type(self).captured_url = url
        type(self).captured_headers = headers
        type(self).captured_json = json
        if url.endswith("/api/v1/events"):
            return _FakeResponse(
                {
                    "log_index": 7,
                    "event_hash": "b" * 64,
                    "tree_head": {
                        "log_id": "ets-edge-virtual-demo",
                        "tree_size": 8,
                        "root_hash": "c" * 64,
                        "timestamp_utc": "2026-08-13T00:00:00Z",
                        "signature": "demo-signature",
                        "signature_alg": "ed25519",
                        "key_id": "demo-key",
                    },
                }
            )

        response_status = 200
        if type(self).upstream_statuses:
            response_status = type(self).upstream_statuses.pop(0)
        if response_status >= 400:
            return _FakeResponse(
                {"detail": "synthetic upstream failure"},
                status_code=response_status,
            )

        tree_head = json["tree_head"]
        assert isinstance(tree_head, dict)
        checkpoint_root = tree_head["root_hash"]
        if type(self).conflict_ack:
            checkpoint_root = "d" * 64
        return _FakeResponse(
            {
                "status": "accepted",
                "logical_sequence": 1,
                "idempotency_key": json["idempotency_key"],
                "event_id": json["event_id"],
                "event_hash": json["event_hash"],
                "accepted_checkpoint_root": checkpoint_root,
                "accepted_checkpoint_size": tree_head["tree_size"],
            },
            status_code=200,
        )


def _client(monkeypatch: Any, tmp_path: Path) -> TestClient:
    _FakeAsyncClient.captured_url = None
    _FakeAsyncClient.captured_headers = None
    _FakeAsyncClient.captured_json = None
    _FakeAsyncClient.upstream_statuses = []
    _FakeAsyncClient.conflict_ack = False
    monkeypatch.setenv("ETS_EDGE_SYNC_DB", str(tmp_path / "sync.db"))
    monkeypatch.setenv("ETS_EDGE_SYNC_MAX_ITEMS", "100")
    monkeypatch.setenv("ETS_EDGE_SYNC_MAX_BYTES", str(16 * 1024 * 1024))
    monkeypatch.setattr(webhook_adapter.httpx, "AsyncClient", _FakeAsyncClient)
    webhook_adapter._SYNC_QUEUE = None
    return TestClient(webhook_adapter.app)


def _capture(client: TestClient, body: bytes) -> Any:
    return client.post(
        "/edge/v1/capture/webhook/github-demo",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-ETS-Tenant": "tenant_demo",
            "X-ETS-Workspace": "workspace_alpha",
            "X-Correlation-ID": "corr-webhook-001",
            "X-ETS-Actor": "demo-sender",
        },
    )


def test_webhook_hashes_exact_bytes_without_forwarding_raw_payload(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client = _client(monkeypatch, tmp_path)
    body = b'{"marker":"ETS_RAW_WEBHOOK_SECRET_9f31","sequence":1}'

    response = _capture(client, body)

    assert response.status_code == 201
    receipt = response.json()
    assert receipt["content_hash"] == hashlib.sha256(body).hexdigest()
    assert receipt["content_hash_alg"] == "sha256"
    assert receipt["byte_size"] == len(body)
    assert receipt["proof_url"].endswith(receipt["event_id"])
    assert receipt["sync_state"] == "pending"

    forwarded = _FakeAsyncClient.captured_json
    assert forwarded is not None
    assert forwarded["content_hash"] == hashlib.sha256(body).hexdigest()
    assert forwarded["schema_version"] == "ets.event.v1"
    assert forwarded["event_type"] == "evidence.captured.webhook"
    assert forwarded["correlation_id"] == "corr-webhook-001"
    assert forwarded["actor_id"] == "demo-sender"
    assert "ETS_RAW_WEBHOOK_SECRET_9f31" not in json.dumps(forwarded, sort_keys=True)

    metadata = forwarded["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["raw_payload_retained"] is False
    assert metadata["byte_size"] == len(body)

    sync_bytes = (tmp_path / "sync.db").read_bytes()
    assert b"ETS_RAW_WEBHOOK_SECRET_9f31" not in sync_bytes


def test_webhook_requires_tenant_and_workspace(monkeypatch: Any, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/edge/v1/capture/webhook/demo",
        content=b'{"ok":true}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert _FakeAsyncClient.captured_json is None


def test_webhook_rejects_unsupported_content_type(monkeypatch: Any, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/edge/v1/capture/webhook/demo",
        content=b"plain text",
        headers={
            "Content-Type": "text/plain",
            "X-ETS-Tenant": "tenant_demo",
            "X-ETS-Workspace": "workspace_alpha",
        },
    )

    assert response.status_code == 415
    assert _FakeAsyncClient.captured_json is None


def test_webhook_rejects_invalid_json(monkeypatch: Any, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/edge/v1/capture/webhook/demo",
        content=b'{"broken":',
        headers={
            "Content-Type": "application/json",
            "X-ETS-Tenant": "tenant_demo",
            "X-ETS-Workspace": "workspace_alpha",
        },
    )

    assert response.status_code == 422
    assert _FakeAsyncClient.captured_json is None


def test_webhook_rejects_body_over_one_mib(monkeypatch: Any, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    body = b'"' + (b"x" * webhook_adapter.MAX_WEBHOOK_BODY_BYTES) + b'"'

    response = client.post(
        "/edge/v1/capture/webhook/demo",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-ETS-Tenant": "tenant_demo",
            "X-ETS-Workspace": "workspace_alpha",
        },
    )

    assert response.status_code == 413
    assert _FakeAsyncClient.captured_json is None


def test_webhook_applies_sync_queue_backpressure(monkeypatch: Any, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    monkeypatch.setenv("ETS_EDGE_SYNC_MAX_BYTES", "1024")
    webhook_adapter._SYNC_QUEUE = None

    response = _capture(client, b'{"ok":true}')

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert _FakeAsyncClient.captured_json is None


def test_sync_run_synchronizes_queued_checkpoint(monkeypatch: Any, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = _capture(client, b'{"ok":true}')
    assert response.status_code == 201
    assert client.get("/edge/v1/sync/status").json()["queue_depth"] == 1

    sync = client.post("/edge/v1/sync/run")

    assert sync.status_code == 200
    assert sync.json()["synchronized"] == 1
    status_payload = client.get("/edge/v1/sync/status").json()
    assert status_payload["queue_depth"] == 0
    assert status_payload["synchronized"] == 1
    assert status_payload["upstream_status"] == "online"


def test_sync_partial_batch_failure_keeps_only_failed_record_pending(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client = _client(monkeypatch, tmp_path)
    assert _capture(client, b'{"sequence":1}').status_code == 201
    assert _capture(client, b'{"sequence":2}').status_code == 201
    _FakeAsyncClient.upstream_statuses = [200, 503]

    sync = client.post("/edge/v1/sync/run")

    assert sync.status_code == 200
    assert sync.json()["attempted"] == 2
    assert sync.json()["synchronized"] == 1
    assert sync.json()["retryable_failure"] == 1
    status_payload = client.get("/edge/v1/sync/status").json()
    assert status_payload["queue_depth"] == 1
    assert status_payload["retryable_failure"] == 1
    assert status_payload["synchronized"] == 1


def test_conflicting_upstream_acknowledgement_fails_closed(
    monkeypatch: Any, tmp_path: Path
) -> None:
    client = _client(monkeypatch, tmp_path)
    assert _capture(client, b'{"ok":true}').status_code == 201
    _FakeAsyncClient.conflict_ack = True

    sync = client.post("/edge/v1/sync/run")

    assert sync.status_code == 200
    assert sync.json()["synchronized"] == 0
    assert sync.json()["terminal_failure"] == 1
    assert sync.json()["upstream_status"] == "conflict"
    status_payload = client.get("/edge/v1/sync/status").json()
    assert status_payload["queue_depth"] == 1
    assert status_payload["terminal_failure"] == 1
