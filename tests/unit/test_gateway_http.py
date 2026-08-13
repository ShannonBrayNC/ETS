from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient

from ets.core.api import InMemoryAppendOnlyLog
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


def registration(*, enabled: bool = True) -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="orders-service",
        source_system="orders",
        tenant_id="tenant_authoritative",
        workspace_id="workspace_authoritative",
        adapter_id="gateway-json",
        event_type="orders.received",
        redacted_keys=frozenset({"secret"}),
        enabled=enabled,
    )


def client_for(
    tmp_path: Path,
    *,
    max_body_bytes: int = 1024,
    enabled: bool = True,
) -> tuple[TestClient, InMemoryAppendOnlyLog]:
    event_log = InMemoryAppendOnlyLog()
    service = GatewayIngressService(
        registry=StaticSourceRegistry([registration(enabled=enabled)]),
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "sync.db"),
        config=GatewayIngressConfig(max_body_bytes=max_body_bytes),
    )
    app = create_gateway_app(service, TestPrincipalResolver())
    return TestClient(app), event_log


def headers(key: str = "request-1") -> dict[str, str]:
    return {
        "X-Test-Principal": PRINCIPAL,
        "Idempotency-Key": key,
        "Content-Type": "application/json",
    }


def test_http_scope_is_server_authorized_not_request_authorized(tmp_path: Path) -> None:
    client, event_log = client_for(tmp_path)
    request_headers = headers()
    request_headers["X-ETS-Tenant"] = "tenant_attacker"
    request_headers["X-ETS-Workspace"] = "workspace_attacker"
    request_headers["X-ETS-Declared-Identity"] = "payload-claimed-orders"

    response = client.post(
        "/gateway/v1/webhooks",
        headers=request_headers,
        content=b'{"order_id":"42","secret":"remove-me"}',
    )

    assert response.status_code == 201
    event = event_log.get_by_event_id(response.json()["event_id"]).event
    assert event.tenant_id == "tenant_authoritative"
    assert event.workspace_id == "workspace_authoritative"
    assert event.metadata["source"]["transport_identity"] == PRINCIPAL
    assert event.metadata["source"]["declared_identity"] == "payload-claimed-orders"


def test_http_duplicate_returns_existing_event(tmp_path: Path) -> None:
    client, event_log = client_for(tmp_path)
    first = client.post(
        "/gateway/v1/webhooks",
        headers=headers(),
        content=b'{"order_id":"42"}',
    )
    second = client.post(
        "/gateway/v1/webhooks",
        headers=headers(),
        content=b'{"order_id":"42"}',
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["event_id"] == second.json()["event_id"]
    assert second.json()["duplicate"] is True
    assert len(event_log.list_entries()) == 1


def test_http_conflicting_retry_returns_409(tmp_path: Path) -> None:
    client, event_log = client_for(tmp_path)
    client.post(
        "/gateway/v1/webhooks",
        headers=headers(),
        content=b'{"order_id":"42"}',
    )
    response = client.post(
        "/gateway/v1/webhooks",
        headers=headers(),
        content=b'{"order_id":"43"}',
    )

    assert response.status_code == 409
    assert len(event_log.list_entries()) == 1


def test_http_missing_authenticated_principal_returns_401(tmp_path: Path) -> None:
    client, event_log = client_for(tmp_path)
    response = client.post(
        "/gateway/v1/webhooks",
        headers={"Idempotency-Key": "request-1", "Content-Type": "application/json"},
        content=b"{}",
    )

    assert response.status_code == 401
    assert event_log.list_entries() == []


def test_http_disabled_source_returns_403(tmp_path: Path) -> None:
    client, event_log = client_for(tmp_path, enabled=False)
    response = client.post(
        "/gateway/v1/webhooks",
        headers=headers(),
        content=b"{}",
    )

    assert response.status_code == 403
    assert event_log.list_entries() == []


def test_http_stream_body_exact_and_plus_one(tmp_path: Path) -> None:
    client, event_log = client_for(tmp_path, max_body_bytes=12)
    exact = b'     {"a":1}'
    plus_one = b'      {"a":1}'

    accepted = client.post(
        "/gateway/v1/webhooks",
        headers=headers("exact"),
        content=exact,
    )
    rejected = client.post(
        "/gateway/v1/webhooks",
        headers=headers("plus"),
        content=plus_one,
    )

    assert accepted.status_code == 201
    assert rejected.status_code == 413
    assert len(event_log.list_entries()) == 1


def test_http_invalid_observed_time_and_content_type_fail_before_append(tmp_path: Path) -> None:
    client, event_log = client_for(tmp_path)
    invalid_time = headers("time")
    invalid_time["X-ETS-Observed-At"] = "not-a-time"

    bad_time = client.post(
        "/gateway/v1/webhooks",
        headers=invalid_time,
        content=b"{}",
    )
    bad_type = client.post(
        "/gateway/v1/webhooks",
        headers={
            "X-Test-Principal": PRINCIPAL,
            "Idempotency-Key": "type",
            "Content-Type": "application/octet-stream",
        },
        content=b"{}",
    )

    assert bad_time.status_code == 400
    assert bad_type.status_code == 400
    assert event_log.list_entries() == []
