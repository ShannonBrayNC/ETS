from __future__ import annotations

import asyncio
import ipaddress
import ssl
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import GatewayIngressConfig, GatewayIngressService
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.gateway.syslog_host import GatewaySyslogHost, GatewaySyslogHostPolicy
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue

PRINCIPAL = "spiffe://example.test/workload/syslog-sender"


class FailSecondCapacityQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.capacity_checks = 0

    def ensure_capacity(self, additional_bytes: int) -> None:
        self.capacity_checks += 1
        if self.capacity_checks == 2:
            raise QueueCapacityError("simulated second-frame capacity failure")
        super().ensure_capacity(additional_bytes)


def _write_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def _credentials(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    now = datetime.now(UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ETS G1D Limits CA")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    ca_file = tmp_path / "limits-ca.pem"
    ca_file.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))

    def issue(
        stem: str,
        san: x509.SubjectAlternativeName,
    ) -> tuple[Path, Path]:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, stem)])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(minutes=30))
            .add_extension(san, critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        certfile = tmp_path / f"{stem}-cert.pem"
        keyfile = tmp_path / f"{stem}-key.pem"
        certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        _write_key(keyfile, key)
        return certfile, keyfile

    server_cert, server_key = issue(
        "limits-server",
        x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]
        ),
    )
    client_cert, client_key = issue(
        "limits-client",
        x509.SubjectAlternativeName([x509.UniformResourceIdentifier(PRINCIPAL)]),
    )
    return ca_file, server_cert, server_key, client_cert, client_key


def _tls_contexts(
    tmp_path: Path,
) -> tuple[ssl.SSLContext, ssl.SSLContext]:
    ca_file, server_cert, server_key, client_cert, client_key = _credentials(tmp_path)
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.minimum_version = ssl.TLSVersion.TLSv1_2
    server.maximum_version = ssl.TLSVersion.TLSv1_3
    server.options |= ssl.OP_NO_COMPRESSION
    server.load_cert_chain(certfile=str(server_cert), keyfile=str(server_key))
    server.load_verify_locations(cafile=str(ca_file))
    server.verify_mode = ssl.CERT_REQUIRED

    client = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(ca_file))
    client.minimum_version = ssl.TLSVersion.TLSv1_2
    client.maximum_version = ssl.TLSVersion.TLSv1_3
    client.check_hostname = False
    client.load_cert_chain(certfile=str(client_cert), keyfile=str(client_key))
    return server, client


def _registry() -> StaticSourceRegistry:
    return StaticSourceRegistry(
        [
            SourceRegistration(
                principal=PRINCIPAL,
                source_id="syslog-source-1",
                source_system="enterprise-syslog",
                tenant_id="tenant_authoritative",
                workspace_id="workspace_authoritative",
                adapter_id="gateway-syslog",
                event_type="evidence.captured.syslog",
            )
        ]
    )


def _frame(message: bytes) -> bytes:
    return str(len(message)).encode("ascii") + b" " + message


async def _open(
    port: int,
    client: ssl.SSLContext,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    return await asyncio.open_connection(
        "127.0.0.1",
        port,
        ssl=client,
        server_hostname="localhost",
    )


async def _wait_for_entries(event_log: InMemoryAppendOnlyLog, count: int) -> None:
    for _ in range(300):
        if len(event_log.list_entries()) >= count:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"expected {count} committed event(s)")


async def _saturation_and_idle(tmp_path: Path) -> None:
    server_tls, client_tls = _tls_contexts(tmp_path)
    registry = _registry()
    event_log = InMemoryAppendOnlyLog()
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "limits-sync.db"),
        config=GatewayIngressConfig(max_syslog_message_bytes=8192),
    )
    policy = GatewaySyslogHostPolicy(
        max_concurrent_connections=1,
        admission_timeout_seconds=0.03,
        read_idle_timeout_seconds=0.12,
        graceful_shutdown_seconds=1.0,
    )
    host = GatewaySyslogHost(
        service,
        registry,
        server_tls,
        policy=policy,
        host="127.0.0.1",
        port=0,
    )
    await host.start()
    port = host.bound_port
    assert port is not None

    first_reader, first_writer = await _open(port, client_tls)
    try:
        for _ in range(100):
            if host.active_connections >= 1:
                break
            await asyncio.sleep(0.005)
        assert host.active_connections >= 1

        second_reader, second_writer = await _open(port, client_tls)
        second_writer.write(_frame(b"<13>1 - second app p m - blocked"))
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await second_writer.drain()
        await asyncio.sleep(0.08)
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(second_reader.read(1), timeout=0.1)
        second_writer.close()
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await second_writer.wait_closed()
        assert event_log.list_entries() == []

        first_writer.write(_frame(b"<13>1 - first app p m - accepted"))
        await first_writer.drain()
        first_writer.close()
        await first_writer.wait_closed()
        await _wait_for_entries(event_log, 1)

        idle_reader, idle_writer = await _open(port, client_tls)
        data = await asyncio.wait_for(idle_reader.read(1), timeout=0.5)
        assert data == b""
        idle_writer.close()
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await idle_writer.wait_closed()
        assert len(event_log.list_entries()) == 1
    finally:
        first_writer.close()
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await first_writer.wait_closed()
        await host.shutdown()


async def _failure_ordering(tmp_path: Path) -> None:
    server_tls, client_tls = _tls_contexts(tmp_path)
    registry = _registry()
    event_log = InMemoryAppendOnlyLog()
    queue = FailSecondCapacityQueue(tmp_path / "failure-order-sync.db")
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=queue,
        config=GatewayIngressConfig(max_syslog_message_bytes=8192),
    )
    host = GatewaySyslogHost(
        service,
        registry,
        server_tls,
        host="127.0.0.1",
        port=0,
    )
    await host.start()
    port = host.bound_port
    assert port is not None

    _reader, writer = await _open(port, client_tls)
    combined = (
        _frame(b"<13>1 - first app p m - one")
        + _frame(b"<13>1 - second app p m - two")
        + _frame(b"<13>1 - third app p m - three")
    )
    try:
        writer.write(combined)
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await writer.drain()
        await asyncio.sleep(0.1)
        assert queue.capacity_checks == 2
        entries = event_log.list_entries()
        assert len(entries) == 1
        assert entries[0].event.metadata["source"]["declared_identity"] == "first"
    finally:
        writer.close()
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await writer.wait_closed()
        await host.shutdown()


async def _invalid_frames_create_no_evidence(tmp_path: Path) -> None:
    server_tls, client_tls = _tls_contexts(tmp_path)
    registry = _registry()
    event_log = InMemoryAppendOnlyLog()
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "invalid-frame-sync.db"),
        config=GatewayIngressConfig(max_syslog_message_bytes=8192),
    )
    host = GatewaySyslogHost(
        service,
        registry,
        server_tls,
        host="127.0.0.1",
        port=0,
    )
    await host.start()
    port = host.bound_port
    assert port is not None

    async def send_invalid(payload: bytes) -> None:
        _reader, writer = await _open(port, client_tls)
        try:
            writer.write(payload)
            with suppress(ConnectionError, OSError, ssl.SSLError):
                await writer.drain()
        finally:
            writer.close()
            with suppress(ConnectionError, OSError, ssl.SSLError):
                await writer.wait_closed()
        await asyncio.sleep(0.05)

    try:
        await send_invalid(b"x malformed")
        assert event_log.list_entries() == []

        await send_invalid(b"8193 ")
        assert event_log.list_entries() == []

        await send_invalid(b"10 abc")
        assert event_log.list_entries() == []
    finally:
        await host.shutdown()


async def _clean_shutdown_preserves_admitted_work(tmp_path: Path) -> None:
    server_tls, client_tls = _tls_contexts(tmp_path)
    registry = _registry()
    event_log = InMemoryAppendOnlyLog()
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "shutdown-sync.db"),
        config=GatewayIngressConfig(max_syslog_message_bytes=8192),
    )
    host = GatewaySyslogHost(
        service,
        registry,
        server_tls,
        policy=GatewaySyslogHostPolicy(graceful_shutdown_seconds=1.0),
        host="127.0.0.1",
        port=0,
    )
    await host.start()
    port = host.bound_port
    assert port is not None

    _reader, writer = await _open(port, client_tls)
    writer.write(_frame(b"<13>1 - admitted app p m - complete"))
    await writer.drain()
    await _wait_for_entries(event_log, 1)
    assert host.active_connections >= 1

    shutdown_task = asyncio.create_task(host.shutdown())
    try:
        for _ in range(100):
            if not host.accepting:
                break
            await asyncio.sleep(0.005)
        assert host.accepting is False

        try:
            _late_reader, late_writer = await _open(port, client_tls)
        except (ConnectionError, OSError, ssl.SSLError):
            pass
        else:
            late_writer.close()
            with suppress(ConnectionError, OSError, ssl.SSLError):
                await late_writer.wait_closed()
            raise AssertionError("new TLS connection was admitted after shutdown began")

        writer.close()
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await writer.wait_closed()
        await shutdown_task

        assert len(event_log.list_entries()) == 1
        assert host.active_connections == 0
        assert host.drain_timed_out is False
    finally:
        writer.close()
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await writer.wait_closed()
        if not shutdown_task.done():
            await shutdown_task


def test_gateway_syslog_connection_saturation_and_idle_timeout(tmp_path: Path) -> None:
    asyncio.run(_saturation_and_idle(tmp_path))


def test_gateway_syslog_stops_after_failed_frame_in_same_read(tmp_path: Path) -> None:
    asyncio.run(_failure_ordering(tmp_path))


def test_gateway_syslog_invalid_frames_create_no_partial_evidence(tmp_path: Path) -> None:
    asyncio.run(_invalid_frames_create_no_evidence(tmp_path))


def test_gateway_syslog_clean_shutdown_preserves_admitted_work(tmp_path: Path) -> None:
    asyncio.run(_clean_shutdown_preserves_admitted_work(tmp_path))
