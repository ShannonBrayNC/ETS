from __future__ import annotations

import asyncio
import ipaddress
import secrets
import socket
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import Request

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.host import GatewayHostController, create_gateway_tls_context, load_gateway_tls_credentials
from ets.gateway.http import SourceAuthenticationError, create_gateway_app
from ets.gateway.ingress import GatewayIngressConfig, GatewayIngressService
from ets.gateway.server import create_gateway_https_server
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/orders"


class EphemeralCredentialResolver:
    def __init__(self, accepted: str, unregistered: str) -> None:
        self.accepted = accepted
        self.unregistered = unregistered

    def resolve(self, request: Request) -> str:
        value = request.headers.get("Authorization", "")
        if value == f"Bearer {self.accepted}":
            return PRINCIPAL
        if value == f"Bearer {self.unregistered}":
            return "spiffe://example.test/workload/unregistered"
        raise SourceAuthenticationError("test credential rejected")


def _certificate_files(tmp_path: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(minutes=10))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    certfile = tmp_path / "server-cert.pem"
    keyfile = tmp_path / "server-key.pem"
    certfile.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return certfile, keyfile


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
                    redacted_keys=frozenset({"secret"}),
                )
            ]
        ),
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "https-sync.db"),
        config=GatewayIngressConfig(max_body_bytes=4096),
    )
    return service, event_log


async def _wait_for_start(server: object, task: asyncio.Task[None]) -> None:
    for _ in range(500):
        if getattr(server, "started", False):
            return
        if task.done():
            await task
            raise AssertionError("server exited before startup")
        await asyncio.sleep(0.01)
    raise AssertionError("server did not start")


async def _exercise(tmp_path: Path) -> tuple[str, str, str]:
    accepted_credential = secrets.token_urlsafe(24)
    unregistered_credential = secrets.token_urlsafe(24)
    raw_marker = secrets.token_hex(24)

    certfile, keyfile = _certificate_files(tmp_path)
    server_tls = load_gateway_tls_credentials(
        create_gateway_tls_context(), certfile=certfile, keyfile=keyfile
    )
    client_tls = ssl.create_default_context(cafile=str(certfile))
    client_tls.minimum_version = ssl.TLSVersion.TLSv1_2
    client_tls.maximum_version = ssl.TLSVersion.TLSv1_3

    service, event_log = _service(tmp_path)
    host_controller = GatewayHostController()
    app = create_gateway_app(
        service,
        EphemeralCredentialResolver(accepted_credential, unregistered_credential),
        host_controller=host_controller,
    )

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    listener.setblocking(False)
    port = int(listener.getsockname()[1])

    server = create_gateway_https_server(
        app,
        server_tls,
        host_controller,
        host="127.0.0.1",
        port=port,
        graceful_shutdown_seconds=5,
    )
    server_task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        await _wait_for_start(server, server_task)

        _reader, writer = await asyncio.open_connection(
            "127.0.0.1",
            port,
            ssl=client_tls,
            server_hostname="127.0.0.1",
        )
        ssl_object = writer.get_extra_info("ssl_object")
        assert ssl_object is not None
        assert ssl_object.version() in {"TLSv1.2", "TLSv1.3"}
        writer.close()
        await writer.wait_closed()

        async with httpx.AsyncClient(
            base_url=f"https://127.0.0.1:{port}",
            verify=client_tls,
            trust_env=False,
            timeout=5.0,
        ) as client:
            accepted = await client.post(
                "/gateway/v1/webhooks",
                headers={
                    "Authorization": f"Bearer {accepted_credential}",
                    "Idempotency-Key": "scope-test",
                    "Content-Type": "application/json",
                    "X-ETS-Tenant": "caller_tenant",
                    "X-ETS-Workspace": "caller_workspace",
                },
                content=f'{{"order_id":"42","secret":"{raw_marker}"}}'.encode(),
            )
            assert accepted.status_code == 201
            event = event_log.get_by_event_id(accepted.json()["event_id"]).event
            assert event.tenant_id == "tenant_authoritative"
            assert event.workspace_id == "workspace_authoritative"
            assert event.metadata["source"]["transport_identity"] == PRINCIPAL
            assert raw_marker not in repr(event.metadata)

            unauthorized = await client.post(
                "/gateway/v1/webhooks",
                headers={
                    "Authorization": f"Bearer {unregistered_credential}",
                    "Idempotency-Key": "unregistered-test",
                    "Content-Type": "application/json",
                },
                content=b'{"order_id":"blocked"}',
            )
            assert unauthorized.status_code == 403
            assert len(event_log.list_entries()) == 1
    finally:
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=10.0)
        listener.close()

    assert host_controller.accepting is False
    assert host_controller.active_requests == 0
    assert server.drain_timed_out is False
    return accepted_credential, unregistered_credential, raw_marker


def test_gateway_deployed_loopback_https_boundary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    accepted, unregistered, raw_marker = asyncio.run(_exercise(tmp_path))
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert accepted not in output
    assert unregistered not in output
    assert raw_marker not in output
