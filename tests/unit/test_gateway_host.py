from __future__ import annotations

import asyncio
import ssl
import time
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.host import (
    GatewayHostController,
    GatewayHostLimitError,
    GatewayHostPolicy,
    GatewayHostSaturatedError,
    UnsupportedContentEncodingError,
    create_gateway_tls_context,
)
from ets.gateway.http import SourceAuthenticationError, create_gateway_app
from ets.gateway.ingress import GatewayIngressConfig, GatewayIngressService
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/orders"


class TestPrincipalResolver:
    def resolve(self, request: Request) -> str:
        principal = request.headers.get("X-Test-Principal")
        if not principal:
            raise SourceAuthenticationError("test source identity missing")
        return principal


def make_client(
    tmp_path: Path,
    *,
    policy: GatewayHostPolicy,
) -> tuple[TestClient, InMemoryAppendOnlyLog, GatewayIngressService]:
    event_log = InMemoryAppendOnlyLog()
    service = GatewayIngressService(
        registry=StaticSourceRegistry(
            [
                SourceRegistration(
                    principal=PRINCIPAL,
                    source_id="orders-service",
                    source_system="orders",
                    tenant_id="tenant_authoritative",
                    workspace_id="workspace_authoritative",
                    adapter_id="gateway-json",
                    event_type="orders.received",
                )
            ]
        ),
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "sync.db"),
        config=GatewayIngressConfig(max_body_bytes=1024),
    )
    app = create_gateway_app(
        service,
        TestPrincipalResolver(),
        host_controller=GatewayHostController(policy),
    )
    return TestClient(app), event_log, service


def request_headers(key: str = "request-1") -> dict[str, str]:
    return {
        "X-Test-Principal": PRINCIPAL,
        "Idempotency-Key": key,
        "Content-Type": "application/json",
    }


def test_host_policy_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        GatewayHostPolicy(max_concurrent_requests=0)
    with pytest.raises(ValueError):
        GatewayHostPolicy(body_read_timeout_seconds=0)
    with pytest.raises(ValueError):
        GatewayHostPolicy(allowed_content_encodings=("GZIP",))


def test_host_header_count_aggregate_and_value_bounds() -> None:
    controller = GatewayHostController(
        GatewayHostPolicy(
            max_header_count=2,
            max_header_bytes=20,
            max_header_value_bytes=8,
        )
    )

    controller.validate_headers([(b"a", b"1"), (b"b", b"22")])
    with pytest.raises(GatewayHostLimitError):
        controller.validate_headers([(b"a", b"1"), (b"b", b"2"), (b"c", b"3")])
    with pytest.raises(GatewayHostLimitError):
        controller.validate_headers([(b"longname", b"12345678"), (b"b", b"22")])
    with pytest.raises(GatewayHostLimitError):
        controller.validate_headers([(b"a", b"123456789")])


def test_host_rejects_unqualified_content_encoding() -> None:
    controller = GatewayHostController()
    controller.validate_content_encoding(None)
    controller.validate_content_encoding("identity")
    with pytest.raises(UnsupportedContentEncodingError):
        controller.validate_content_encoding("gzip")


def test_host_admission_saturates_without_unbounded_wait() -> None:
    controller = GatewayHostController(
        GatewayHostPolicy(max_concurrent_requests=1, admission_timeout_seconds=0.001)
    )

    async def exercise() -> None:
        async with controller.admission():
            with pytest.raises(GatewayHostSaturatedError):
                async with controller.admission():
                    raise AssertionError("second request should not be admitted")

    asyncio.run(exercise())


def test_tls_profile_is_bounded_to_tls12_through_tls13() -> None:
    context = create_gateway_tls_context()

    assert context.minimum_version is ssl.TLSVersion.TLSv1_2
    assert context.maximum_version is ssl.TLSVersion.TLSv1_3
    assert context.options & ssl.OP_NO_COMPRESSION


def test_http_rejects_unqualified_content_encoding_before_append(tmp_path: Path) -> None:
    client, event_log, _ = make_client(tmp_path, policy=GatewayHostPolicy())
    headers = request_headers()
    headers["Content-Encoding"] = "gzip"

    response = client.post("/gateway/v1/webhooks", headers=headers, content=b"{}")

    assert response.status_code == 415
    assert event_log.list_entries() == []


def test_http_rejects_oversized_header_before_append(tmp_path: Path) -> None:
    policy = GatewayHostPolicy(max_header_value_bytes=64)
    client, event_log, _ = make_client(tmp_path, policy=policy)
    headers = request_headers()
    headers["X-Oversized"] = "x" * 65

    response = client.post("/gateway/v1/webhooks", headers=headers, content=b"{}")

    assert response.status_code == 431
    assert event_log.list_entries() == []


def test_body_read_timeout_occurs_before_authoritative_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = GatewayHostPolicy(body_read_timeout_seconds=0.001)
    client, event_log, _ = make_client(tmp_path, policy=policy)

    async def slow_read(_request: Request, _maximum: int) -> bytes:
        await asyncio.sleep(0.02)
        return b"{}"

    monkeypatch.setattr("ets.gateway.http._read_bounded_body", slow_read)
    response = client.post(
        "/gateway/v1/webhooks",
        headers=request_headers(),
        content=b"{}",
    )

    assert response.status_code == 408
    assert event_log.list_entries() == []


def test_body_read_deadline_does_not_wrap_authoritative_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = GatewayHostPolicy(body_read_timeout_seconds=0.005)
    client, event_log, service = make_client(tmp_path, policy=policy)
    original = service.ingest_json

    def slow_commit(principal: str, request: object):
        time.sleep(0.02)
        return original(principal, request)  # type: ignore[arg-type]

    monkeypatch.setattr(service, "ingest_json", slow_commit)
    response = client.post(
        "/gateway/v1/webhooks",
        headers=request_headers(),
        content=b"{}",
    )

    assert response.status_code == 201
    assert len(event_log.list_entries()) == 1
