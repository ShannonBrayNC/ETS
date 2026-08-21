from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import grpc
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2_grpc
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import GatewayIngressService
from ets.gateway.otlp_grpc import (
    GatewayOtlpGrpcHost,
    MtlsUriSanPrincipalResolver,
    create_otlp_grpc_mtls_credentials,
)
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/otlp-grpc-mtls"
UNAUTHORIZED_PRINCIPAL = "spiffe://example.test/workload/unauthorized"
NOW = datetime(2026, 8, 14, 4, 30, tzinfo=UTC)
SOURCE_TIME_NS = 1_786_660_800_123_456_000


def _registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="otlp-grpc-mtls",
        source_system="opentelemetry",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        adapter_id="gateway-otlp-grpc",
        adapter_version="1.0",
        event_type="telemetry.observed",
        classification="internal",
        redaction_profile="otlp-redaction-v1",
        minimization_profile="otlp-metadata-v1",
        redacted_keys=frozenset({"secret"}),
        clock_quality="synchronized",
    )


def _request() -> ExportLogsServiceRequest:
    request = ExportLogsServiceRequest()
    resource_logs = request.resource_logs.add()
    scope_logs = resource_logs.scope_logs.add()
    record = scope_logs.log_records.add()
    record.time_unix_nano = SOURCE_TIME_NS
    record.body.string_value = "mTLS body"
    return request


def _key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem_key(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _pem_cert(certificate: x509.Certificate) -> bytes:
    return certificate.public_bytes(serialization.Encoding.PEM)


def _ca() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    key = _key()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ETS Test CA")])
    certificate_now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before((certificate_now - timedelta(days=1)).replace(tzinfo=None))
        .not_valid_after((certificate_now + timedelta(days=30)).replace(tzinfo=None))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256())
    )
    return key, certificate


def _leaf(
    *,
    ca_key: rsa.RSAPrivateKey,
    ca_certificate: x509.Certificate,
    common_name: str,
    server: bool,
    uri_sans: tuple[str, ...] = (),
) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    key = _key()
    san_values: list[x509.GeneralName] = [x509.UniformResourceIdentifier(uri) for uri in uri_sans]
    if server:
        san_values.append(x509.DNSName("localhost"))
    eku = ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH
    certificate_now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .issuer_name(ca_certificate.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before((certificate_now - timedelta(days=1)).replace(tzinfo=None))
        .not_valid_after((certificate_now + timedelta(days=7)).replace(tzinfo=None))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(san_values), critical=False)
        .add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return key, certificate


def _service(
    tmp_path: Path,
) -> tuple[GatewayIngressService, InMemoryAppendOnlyLog, SyncQueue]:
    event_log = InMemoryAppendOnlyLog()
    sync_queue = SyncQueue(tmp_path / "mtls-sync.db")
    service = GatewayIngressService(
        registry=StaticSourceRegistry([_registration()]),
        event_log=event_log,
        sync_queue=sync_queue,
        now=lambda: NOW,
    )
    return service, event_log, sync_queue


def _secure_channel(
    port: int,
    *,
    ca_pem: bytes,
    client_key: bytes | None,
    client_certificate: bytes | None,
) -> grpc.Channel:
    credentials = grpc.ssl_channel_credentials(
        root_certificates=ca_pem,
        private_key=client_key,
        certificate_chain=client_certificate,
    )
    return grpc.secure_channel(
        f"127.0.0.1:{port}",
        credentials,
        options=(
            ("grpc.ssl_target_name_override", "localhost"),
            ("grpc.default_authority", "localhost"),
        ),
    )


def test_mtls_uri_san_is_authoritative_gateway_principal(tmp_path: Path) -> None:
    ca_key, ca_certificate = _ca()
    server_key, server_certificate = _leaf(
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        common_name="localhost",
        server=True,
    )
    client_key, client_certificate = _leaf(
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        common_name="otlp-client",
        server=False,
        uri_sans=(PRINCIPAL,),
    )
    ca_pem = _pem_cert(ca_certificate)
    service, event_log, sync_queue = _service(tmp_path)
    host = GatewayOtlpGrpcHost(
        service,
        MtlsUriSanPrincipalResolver(),
        host="127.0.0.1",
        port=0,
        server_credentials=create_otlp_grpc_mtls_credentials(
            private_key=_pem_key(server_key),
            certificate_chain=_pem_cert(server_certificate),
            client_ca=ca_pem,
        ),
    )
    host.start()
    channel = _secure_channel(
        host.bound_port,
        ca_pem=ca_pem,
        client_key=_pem_key(client_key),
        client_certificate=_pem_cert(client_certificate),
    )
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        stub.Export(
            _request(),
            metadata=(("idempotency-key", "mtls-qualified"),),
            timeout=5,
        )

        entries = event_log.list_entries()
        assert len(entries) == 1
        assert entries[0].event.tenant_id == "tenant-a"
        assert entries[0].event.workspace_id == "workspace-a"
        assert sync_queue.status().queue_depth == 1
        assert host.transport_profile == "mtls"
    finally:
        channel.close()
        host.shutdown()


def test_mtls_unregistered_uri_san_is_permission_denied(tmp_path: Path) -> None:
    ca_key, ca_certificate = _ca()
    server_key, server_certificate = _leaf(
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        common_name="localhost",
        server=True,
    )
    client_key, client_certificate = _leaf(
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        common_name="unauthorized-client",
        server=False,
        uri_sans=(UNAUTHORIZED_PRINCIPAL,),
    )
    ca_pem = _pem_cert(ca_certificate)
    service, event_log, _ = _service(tmp_path)
    host = GatewayOtlpGrpcHost(
        service,
        MtlsUriSanPrincipalResolver(),
        host="127.0.0.1",
        port=0,
        server_credentials=create_otlp_grpc_mtls_credentials(
            private_key=_pem_key(server_key),
            certificate_chain=_pem_cert(server_certificate),
            client_ca=ca_pem,
        ),
    )
    host.start()
    channel = _secure_channel(
        host.bound_port,
        ca_pem=ca_pem,
        client_key=_pem_key(client_key),
        client_certificate=_pem_cert(client_certificate),
    )
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        with pytest.raises(grpc.RpcError) as exc_info:
            stub.Export(
                _request(),
                metadata=(("idempotency-key", "unauthorized"),),
                timeout=5,
            )
        assert exc_info.value.code() == grpc.StatusCode.PERMISSION_DENIED
        assert event_log.list_entries() == []
    finally:
        channel.close()
        host.shutdown()


def test_mtls_requires_client_certificate(tmp_path: Path) -> None:
    ca_key, ca_certificate = _ca()
    server_key, server_certificate = _leaf(
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        common_name="localhost",
        server=True,
    )
    ca_pem = _pem_cert(ca_certificate)
    service, event_log, _ = _service(tmp_path)
    host = GatewayOtlpGrpcHost(
        service,
        MtlsUriSanPrincipalResolver(),
        host="127.0.0.1",
        port=0,
        server_credentials=create_otlp_grpc_mtls_credentials(
            private_key=_pem_key(server_key),
            certificate_chain=_pem_cert(server_certificate),
            client_ca=ca_pem,
        ),
    )
    host.start()
    channel = _secure_channel(
        host.bound_port,
        ca_pem=ca_pem,
        client_key=None,
        client_certificate=None,
    )
    try:
        stub = logs_service_pb2_grpc.LogsServiceStub(channel)
        with pytest.raises(grpc.RpcError):
            stub.Export(
                _request(),
                metadata=(("idempotency-key", "missing-client-cert"),),
                timeout=2,
            )
        assert event_log.list_entries() == []
    finally:
        channel.close()
        host.shutdown()
