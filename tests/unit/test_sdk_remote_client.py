import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest

from ets.sdk import AsyncETSClient, ETSApplicationError, ETSClient


def _event() -> dict[str, object]:
    return {
        "event_id": "evt_sdk_remote_001",
        "tenant_id": "tenant_dev",
        "workspace_id": "workspace_dev",
        "evidence_id": "evidence_sdk_remote_001",
        "event_type": "sdk.remote.test",
        "subject_ref": "subject-1",
        "content_hash": "a" * 64,
        "content_hash_alg": "sha256",
        "metadata": {"source": "unit-test"},
        "created_at_utc": datetime(2026, 9, 25, 15, 0, tzinfo=UTC),
        "schema_version": "ets.event.v1",
        "source_system": "sdk-tests",
        "actor_id": None,
        "correlation_id": None,
        "external_refs": None,
        "redaction_profile": None,
    }


def _tree_head() -> dict[str, object]:
    return {
        "tree_size": 1,
        "root_hash": "b" * 64,
        "created_at_utc": "2026-09-25T15:01:00Z",
        "log_id": "ets-sdk-dev",
        "signature_alg": None,
        "signature": None,
        "public_key_id": None,
    }


def _append_response() -> dict[str, object]:
    return {
        "event_id": "evt_sdk_remote_001",
        "log_index": 0,
        "event_hash": "c" * 64,
        "tree_head": _tree_head(),
        "inclusion_proof_url": "/api/v1/proofs/inclusion/evt_sdk_remote_001",
    }


def _event_record() -> dict[str, object]:
    event = _event()
    event["created_at_utc"] = "2026-09-25T15:00:00Z"
    return {
        "log_index": 0,
        "event_hash": "c" * 64,
        "leaf_hash": "b" * 64,
        "event": event,
    }


def test_sync_client_capture_headers_receipt_and_compatibility():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/version":
            return httpx.Response(
                200,
                json={
                    "name": "Evidence Transparency System",
                    "version": "0.1.0",
                    "api_version": "v1",
                },
            )
        if request.url.path == "/api/v1/events" and request.method == "POST":
            body = json.loads(request.content)
            assert body["event_id"] == "evt_sdk_remote_001"
            return httpx.Response(201, json=_append_response())
        if request.url.path == "/api/v1/events/evt_sdk_remote_001":
            return httpx.Response(200, json=_event_record())
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with ETSClient(
        "https://ets.example",
        api_key="local-development-key",
        tenant_id="tenant_dev",
        workspace_id="workspace_dev",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.check_compatibility().api_version == "v1"
        receipt = client.capture(_event(), correlation_id="corr-001")
        record = client.get_event("evt_sdk_remote_001")

    assert receipt.commitment_state == "committed_local"
    assert receipt.event_hash == "c" * 64
    assert record.event.event_id == "evt_sdk_remote_001"
    capture_request = next(request for request in requests if request.method == "POST")
    assert capture_request.headers["X-ETS-API-Key"] == "local-development-key"
    assert capture_request.headers["X-ETS-Tenant"] == "tenant_dev"
    assert capture_request.headers["X-ETS-Workspace"] == "workspace_dev"
    assert capture_request.headers["X-Correlation-ID"] == "corr-001"
    assert capture_request.headers["X-ETS-SDK-Contract"] == "ets.application.sdk.v1"


def test_bearer_client_rejects_caller_controlled_scope_headers():
    with pytest.raises(ETSApplicationError) as exc_info:
        ETSClient(
            "https://ets.example",
            bearer_token="header.payload.signature",
            tenant_id="tenant_dev",
            workspace_id="workspace_dev",
        )

    assert exc_info.value.code == "unsafe_configuration"


def test_insecure_http_is_loopback_only_and_explicit():
    with pytest.raises(ETSApplicationError):
        ETSClient("http://ets.example", allow_insecure_http=True)

    client = ETSClient(
        "http://127.0.0.1:8000",
        tenant_id="tenant_dev",
        workspace_id="workspace_dev",
        allow_insecure_http=True,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"status": "ok", "version": "0.1.0"})
        ),
    )
    try:
        assert client.health().status == "ok"
    finally:
        client.close()


def test_api_error_is_normalized_without_exposing_auth_material():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "code": "ETS_AUTH_FORBIDDEN",
                    "message": "authenticated principal lacks evidence.create capability",
                    "correlation_id": "corr-denied",
                }
            },
        )

    client = ETSClient(
        "https://ets.example",
        bearer_token="secret-token-value",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(ETSApplicationError) as exc_info:
            client.capture(_event())
    finally:
        client.close()

    assert exc_info.value.code == "authorization_failed"
    assert exc_info.value.api_code == "ETS_AUTH_FORBIDDEN"
    assert exc_info.value.correlation_id == "corr-denied"
    assert "secret-token-value" not in str(exc_info.value)


def test_async_client_uses_same_contract():
    async def run() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/v1/events":
                return httpx.Response(201, json=_append_response())
            if request.url.path == "/api/v1/events/evt_sdk_remote_001":
                return httpx.Response(200, json=_event_record())
            raise AssertionError(f"unexpected request: {request.method} {request.url}")

        async with AsyncETSClient(
            "https://ets.example",
            api_key="local-development-key",
            tenant_id="tenant_dev",
            workspace_id="workspace_dev",
            transport=httpx.MockTransport(handler),
        ) as client:
            receipt = await client.capture(_event())
            record = await client.get_event("evt_sdk_remote_001")
            assert receipt.commitment_state == "committed_local"
            assert record.event.event_type == "sdk.remote.test"

    asyncio.run(run())
