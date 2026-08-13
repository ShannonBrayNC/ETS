from __future__ import annotations

import asyncio
import ipaddress
import json
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import GatewayIngressConfig, GatewayIngressService
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.gateway.syslog_host import GatewaySyslogHost, create_gateway_syslog_tls_context
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/syslog-sender"
UNREGISTERED = "spiffe://example.test/workload/unregistered-syslog"


def _write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def _credential_files(tmp_path: Path) -> dict[str, Path]:
    now = datetime.now(UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ETS G1D Test CA")])
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

    ca_file = tmp_path / "ca.pem"
    ca_file.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))

    def issue(
        stem: str,
        *,
        common_name: str,
        san: x509.SubjectAlternativeName,
    ) -> tuple[Path, Path]:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        certificate = (
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
        certfile.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        _write_private_key(keyfile, key)
        return certfile, keyfile

    server_cert, server_key = issue(
        "server",
        common_name="localhost",
        san=x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]
        ),
    )
    client_cert, client_key = issue(
        "client",
        common_name="registered-client",
        san=x509.SubjectAlternativeName([x509.UniformResourceIdentifier(PRINCIPAL)]),
    )
    unregistered_cert, unregistered_key = issue(
        "unregistered",
        common_name="unregistered-client",
        san=x509.SubjectAlternativeName([x509.UniformResourceIdentifier(UNREGISTERED)]),
    )
    return {
        "ca": ca_file,
        "server_cert": server_cert,
        "server_key": server_key,
        "client_cert": client_cert,
        "client_key": client_key,
        "unregistered_cert": unregistered_cert,
        "unregistered_key": unregistered_key,
    }


def _client_context(
    credentials: dict[str, Path],
    *,
    cert_key: tuple[str, str],
) -> ssl.SSLContext:
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=str(credentials["ca"]),
    )
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = False
    context.load_cert_chain(
        certfile=str(credentials[cert_key[0]]),
        keyfile=str(credentials[cert_key[1]]),
    )
    return context


def _service(
    tmp_path: Path,
) -> tuple[GatewayIngressService, StaticSourceRegistry, InMemoryAppendOnlyLog, SyncQueue]:
    registry = StaticSourceRegistry(
        [
            SourceRegistration(
                principal=PRINCIPAL,
                source_id="syslog-source-1",
                source_system="enterprise-syslog",
                tenant_id="tenant_authoritative",
                workspace_id="workspace_authoritative",
                adapter_id="gateway-syslog",
                adapter_version="1.0",
                event_type="evidence.captured.syslog",
                classification="internal",
                redaction_profile="syslog-header-only-v1",
                minimization_profile="syslog-header-only-v1",
                clock_quality="synchronized",
            )
        ]
    )
    event_log = InMemoryAppendOnlyLog()
    sync_queue = SyncQueue(tmp_path / "syslog-tls-sync.db")
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=sync_queue,
        config=GatewayIngressConfig(max_syslog_message_bytes=8192),
    )
    return service, registry, event_log, sync_queue


def _frame(message: bytes) -> bytes:
    return str(len(message)).encode("ascii") + b" " + message


async def _wait_for_entries(event_log: InMemoryAppendOnlyLog, count: int) -> None:
    for _ in range(500):
        if len(event_log.list_entries()) >= count:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"expected at least {count} committed events")


async def _send(
    port: int,
    context: ssl.SSLContext,
    chunks: list[bytes],
) -> tuple[str, str | None]:
    _reader, writer = await asyncio.open_connection(
        "127.0.0.1",
        port,
        ssl=context,
        server_hostname="localhost",
    )
    ssl_object = writer.get_extra_info("ssl_object")
    assert ssl_object is not None
    version = ssl_object.version()
    compression = ssl_object.compression()
    for chunk in chunks:
        writer.write(chunk)
        await writer.drain()
    writer.close()
    await writer.wait_closed()
    return version or "", compression


async def _exercise(tmp_path: Path) -> tuple[list[object], str]:
    credentials = _credential_files(tmp_path)
    service, registry, event_log, sync_queue = _service(tmp_path)
    server_tls = create_gateway_syslog_tls_context(
        certfile=credentials["server_cert"],
        keyfile=credentials["server_key"],
        client_ca_file=credentials["ca"],
    )
    registered_tls = _client_context(
        credentials,
        cert_key=("client_cert", "client_key"),
    )
    unregistered_tls = _client_context(
        credentials,
        cert_key=("unregistered_cert", "unregistered_key"),
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

    raw_marker = "ETS_G1D_RAW_SECRET_74f2"
    first = (
        b"<34>1 2026-08-13T22:40:00Z claimed-host app 123 ID47 - "
        + raw_marker.encode()
    )
    second = b"<13>1 - another-host app p m - second-secret"
    encoded_first = _frame(first)

    try:
        version, compression = await _send(
            port,
            registered_tls,
            [encoded_first[:3], encoded_first[3:-2], encoded_first[-2:] + _frame(second)],
        )
        assert version in {"TLSv1.2", "TLSv1.3"}
        assert compression is None
        await _wait_for_entries(event_log, 2)

        entries = event_log.list_entries()
        first_event = entries[0].event
        assert first_event.tenant_id == "tenant_authoritative"
        assert first_event.workspace_id == "workspace_authoritative"
        assert first_event.metadata["source"]["transport_identity"] == PRINCIPAL
        assert first_event.metadata["source"]["declared_identity"] == "claimed-host"
        assert first_event.metadata["privacy"]["contains_raw_evidence"] is False
        assert raw_marker not in json.dumps(first_event.model_dump(mode="json"))

        claimed = sync_queue.claim_batch(10)
        assert len(claimed) == 2
        assert raw_marker not in json.dumps([record.payload for record in claimed])

        await _send(port, registered_tls, [_frame(first)])
        await _wait_for_entries(event_log, 3)
        replay_entries = event_log.list_entries()
        assert replay_entries[0].event.event_id != replay_entries[2].event.event_id
        assert replay_entries[0].event.content_hash == replay_entries[2].event.content_hash

        await _send(port, unregistered_tls, [_frame(first)])
        await asyncio.sleep(0.05)
        assert len(event_log.list_entries()) == 3
    finally:
        await host.shutdown()

    assert host.accepting is False
    assert host.active_connections == 0
    assert host.drain_timed_out is False
    return list(event_log.list_entries()), raw_marker


def test_gateway_deployed_syslog_tls_boundary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    entries, raw_marker = asyncio.run(_exercise(tmp_path))
    assert len(entries) == 3
    captured = capsys.readouterr()
    assert raw_marker not in captured.out
    assert raw_marker not in captured.err
