from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.host import (
    GatewayHostController,
    GatewayHostDrainingError,
    GatewayHostLimitError,
    GatewayHostPolicy,
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


def _service(tmp_path: Path) -> tuple[GatewayIngressService, InMemoryAppendOnlyLog]:
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
    return service, event_log


def _headers() -> dict[str, str]:
    return {
        "X-Test-Principal": PRINCIPAL,
        "Idempotency-Key": "request-1",
        "Content-Type": "application/json",
    }


def test_critical_header_specific_bounds() -> None:
    policy = GatewayHostPolicy()
    controller = GatewayHostController(policy)

    controller.validate_headers(
        [
            (b"content-type", b"x" * policy.max_content_type_bytes),
            (b"x-ets-observed-at", b"x" * policy.max_observed_at_bytes),
        ]
    )
    with pytest.raises(GatewayHostLimitError):
        controller.validate_headers(
            [(b"content-type", b"x" * (policy.max_content_type_bytes + 1))]
        )
    with pytest.raises(GatewayHostLimitError):
        controller.validate_headers(
            [(b"x-ets-observed-at", b"x" * (policy.max_observed_at_bytes + 1))]
        )


def test_shutdown_drains_admitted_work_rejects_waiter_and_restart_is_fresh() -> None:
    policy = GatewayHostPolicy(max_concurrent_requests=1, admission_timeout_seconds=0.1)
    controller = GatewayHostController(policy)

    async def exercise() -> None:
        async def waiting_request() -> str:
            try:
                async with controller.admission():
                    return "admitted"
            except GatewayHostDrainingError:
                return "draining"

        async with controller.admission():
            assert controller.active_requests == 1
            waiter = asyncio.create_task(waiting_request())
            await asyncio.sleep(0)
            controller.begin_shutdown()
            assert controller.accepting is False
            assert controller.active_requests == 1

        assert await waiter == "draining"
        assert controller.active_requests == 0

        restarted = GatewayHostController(policy)
        assert restarted.accepting is True
        async with restarted.admission():
            assert restarted.active_requests == 1
        assert restarted.active_requests == 0

    asyncio.run(exercise())


def test_http_draining_host_returns_backpressure_before_append(tmp_path: Path) -> None:
    service, event_log = _service(tmp_path)
    controller = GatewayHostController()
    app = create_gateway_app(
        service,
        TestPrincipalResolver(),
        host_controller=controller,
    )
    client = TestClient(app)
    controller.begin_shutdown()

    response = client.post(
        "/gateway/v1/webhooks",
        headers=_headers(),
        content=b"{}",
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    assert event_log.list_entries() == []


def test_http_observed_at_header_limit_precedes_timestamp_parse(tmp_path: Path) -> None:
    service, event_log = _service(tmp_path)
    policy = GatewayHostPolicy(max_observed_at_bytes=32)
    app = create_gateway_app(
        service,
        TestPrincipalResolver(),
        host_controller=GatewayHostController(policy),
    )
    client = TestClient(app)
    headers = _headers()
    headers["X-ETS-Observed-At"] = "2" * 33

    response = client.post(
        "/gateway/v1/webhooks",
        headers=headers,
        content=b"{}",
    )

    assert response.status_code == 431
    assert event_log.list_entries() == []
