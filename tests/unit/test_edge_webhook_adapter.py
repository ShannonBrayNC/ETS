from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi.testclient import TestClient

from ets.edge import webhook_adapter


class _FakeResponse:
    status_code = 201
    text = ""

    def json(self) -> dict[str, object]:
        return {"log_index": 7, "event_hash": "b" * 64}


class _FakeAsyncClient:
    captured_url: str | None = None
    captured_headers: dict[str, str] | None = None
    captured_json: dict[str, object | None] | None = None

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
        headers: dict[str, str],
        json: dict[str, object | None],
    ) -> _FakeResponse:
        type(self).captured_url = url
        type(self).captured_headers = headers
        type(self).captured_json = json
        return _FakeResponse()


def _client(monkeypatch: Any) -> TestClient:
    _FakeAsyncClient.captured_url = None
    _FakeAsyncClient.captured_headers = None
    _FakeAsyncClient.captured_json = None
    monkeypatch.setattr(webhook_adapter.httpx, "AsyncClient", _FakeAsyncClient)
    return TestClient(webhook_adapter.app)


def test_webhook_hashes_exact_bytes_without_forwarding_raw_payload(monkeypatch: Any) -> None:
    client = _client(monkeypatch)
    body = b'{"marker":"ETS_RAW_WEBHOOK_SECRET_9f31","sequence":1}'

    response = client.post(
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

    assert response.status_code == 201
    receipt = response.json()
    assert receipt["content_hash"] == hashlib.sha256(body).hexdigest()
    assert receipt["content_hash_alg"] == "sha256"
    assert receipt["byte_size"] == len(body)
    assert receipt["proof_url"].endswith(receipt["event_id"])

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


def test_webhook_requires_tenant_and_workspace(monkeypatch: Any) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/edge/v1/capture/webhook/demo",
        content=b'{"ok":true}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert _FakeAsyncClient.captured_json is None


def test_webhook_rejects_unsupported_content_type(monkeypatch: Any) -> None:
    client = _client(monkeypatch)

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


def test_webhook_rejects_invalid_json(monkeypatch: Any) -> None:
    client = _client(monkeypatch)

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


def test_webhook_rejects_body_over_one_mib(monkeypatch: Any) -> None:
    client = _client(monkeypatch)
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
