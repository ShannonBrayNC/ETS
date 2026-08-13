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
from ets.gateway.syslog_host import GatewaySyslogHost, create_gateway_syslog_tls_context
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/syslog-sender"


def _write_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def _make_ca(tmp_path: Path, stem: str) -> tuple[x509.Certificate, rsa.RSAPrivateKey, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"{stem} CA")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=2))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    path = tmp_path / f"{stem}-ca.pem"
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert, key, path


def _issue(
    tmp_path: Path,
    stem: str,
    *,
    issuer_cert: x509.Certificate,
    issuer_key: rsa.RSAPrivateKey,
    san: x509.SubjectAlternativeName,
    not_before: datetime,
    not_after: datetime,
) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, stem)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(san, critical=False)
        .sign(issuer_key, hashes.SHA256())
    )
    certfile = tmp_path / f"{stem}-cert.pem"
    keyfile = tmp_path / f"{stem}-key.pem"
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    _write_key(keyfile, key)
    return certfile, keyfile


def _service(
    tmp_path: Path,
) -> tuple[GatewayIngressService, StaticSourceRegistry, InMemoryAppendOnlyLog]:
    registry = StaticSourceRegistry(
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
    event_log = InMemoryAppendOnlyLog()
    service = GatewayIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=SyncQueue(tmp_path / "negative-syslog.db"),
        config=GatewayIngressConfig(max_syslog_message_bytes=8192),
    )
    return service, registry, event_log


def _client_context(
    ca_file: Path,
    certfile: Path | None = None,
    keyfile: Path | None = None,
) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(ca_file))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = False
    if certfile is not None and keyfile is not None:
        context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
    return context


def _frame(message: bytes) -> bytes:
    return str(len(message)).encode("ascii") + b" " + message


async def _try_tls_send(port: int, context: ssl.SSLContext, payload: bytes) -> None:
    try:
        _reader, writer = await asyncio.open_connection(
            "127.0.0.1",
            port,
            ssl=context,
            server_hostname="localhost",
        )
    except (ConnectionError, OSError, ssl.SSLError):
        return
    try:
        writer.write(payload)
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await writer.drain()
        await asyncio.sleep(0.05)
    finally:
        writer.close()
        with suppress(ConnectionError, OSError, ssl.SSLError):
            await writer.wait_closed()


async def _exercise_negative_tls(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    trusted_ca, trusted_key, trusted_ca_file = _make_ca(tmp_path, "trusted")
    untrusted_ca, untrusted_key, _untrusted_ca_file = _make_ca(tmp_path, "untrusted")

    server_cert, server_key = _issue(
        tmp_path,
        "server",
        issuer_cert=trusted_ca,
        issuer_key=trusted_key,
        san=x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]
        ),
        not_before=now - timedelta(minutes=1),
        not_after=now + timedelta(minutes=30),
    )
    valid_cert, valid_key = _issue(
        tmp_path,
        "valid",
        issuer_cert=trusted_ca,
        issuer_key=trusted_key,
        san=x509.SubjectAlternativeName([x509.UniformResourceIdentifier(PRINCIPAL)]),
        not_before=now - timedelta(minutes=1),
        not_after=now + timedelta(minutes=30),
    )
    missing_uri_cert, missing_uri_key = _issue(
        tmp_path,
        "missing-uri",
        issuer_cert=trusted_ca,
        issuer_key=trusted_key,
        san=x509.SubjectAlternativeName([x509.DNSName("client.example.test")]),
        not_before=now - timedelta(minutes=1),
        not_after=now + timedelta(minutes=30),
    )
    ambiguous_cert, ambiguous_key = _issue(
        tmp_path,
        "ambiguous-uri",
        issuer_cert=trusted_ca,
        issuer_key=trusted_key,
        san=x509.SubjectAlternativeName(
            [
                x509.UniformResourceIdentifier(PRINCIPAL),
                x509.UniformResourceIdentifier("spiffe://example.test/workload/other"),
            ]
        ),
        not_before=now - timedelta(minutes=1),
        not_after=now + timedelta(minutes=30),
    )
    untrusted_cert, untrusted_cert_key = _issue(
        tmp_path,
        "untrusted-client",
        issuer_cert=untrusted_ca,
        issuer_key=untrusted_key,
        san=x509.SubjectAlternativeName([x509.UniformResourceIdentifier(PRINCIPAL)]),
        not_before=now - timedelta(minutes=1),
        not_after=now + timedelta(minutes=30),
    )
    expired_cert, expired_key = _issue(
        tmp_path,
        "expired-client",
        issuer_cert=trusted_ca,
        issuer_key=trusted_key,
        san=x509.SubjectAlternativeName([x509.UniformResourceIdentifier(PRINCIPAL)]),
        not_before=now - timedelta(minutes=30),
        not_after=now - timedelta(minutes=1),
    )
    future_cert, future_key = _issue(
        tmp_path,
        "future-client",
        issuer_cert=trusted_ca,
        issuer_key=trusted_key,
        san=x509.SubjectAlternativeName([x509.UniformResourceIdentifier(PRINCIPAL)]),
        not_before=now + timedelta(minutes=5),
        not_after=now + timedelta(minutes=30),
    )

    service, registry, event_log = _service(tmp_path)
    server_tls = create_gateway_syslog_tls_context(
        certfile=server_cert,
        keyfile=server_key,
        client_ca_file=trusted_ca_file,
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
    payload = _frame(b"<13>1 - claimed app p m - secret-marker")

    try:
        # Baseline: the trusted, registered URI-SAN client can commit.
        await _try_tls_send(
            port,
            _client_context(trusted_ca_file, valid_cert, valid_key),
            payload,
        )
        for _ in range(200):
            if len(event_log.list_entries()) == 1:
                break
            await asyncio.sleep(0.01)
        assert len(event_log.list_entries()) == 1

        # No client certificate.
        await _try_tls_send(port, _client_context(trusted_ca_file), payload)

        # Certificate from an untrusted CA.
        await _try_tls_send(
            port,
            _client_context(trusted_ca_file, untrusted_cert, untrusted_cert_key),
            payload,
        )

        # Expired and not-yet-valid certificates.
        await _try_tls_send(
            port,
            _client_context(trusted_ca_file, expired_cert, expired_key),
            payload,
        )
        await _try_tls_send(
            port,
            _client_context(trusted_ca_file, future_cert, future_key),
            payload,
        )

        # TLS-valid peers with missing or ambiguous URI SAN identity.
        await _try_tls_send(
            port,
            _client_context(trusted_ca_file, missing_uri_cert, missing_uri_key),
            payload,
        )
        await _try_tls_send(
            port,
            _client_context(trusted_ca_file, ambiguous_cert, ambiguous_key),
            payload,
        )

        # Plaintext to the TLS port never reaches the application boundary.
        try:
            _reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(payload)
            with suppress(ConnectionError, OSError):
                await writer.drain()
            await asyncio.sleep(0.05)
            writer.close()
            with suppress(ConnectionError, OSError):
                await writer.wait_closed()
        except (ConnectionError, OSError):
            pass

        await asyncio.sleep(0.1)
        assert len(event_log.list_entries()) == 1
    finally:
        await host.shutdown()


def test_gateway_syslog_tls_negative_identity_and_handshake_cases(tmp_path: Path) -> None:
    asyncio.run(_exercise_negative_tls(tmp_path))
