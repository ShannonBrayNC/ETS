from __future__ import annotations

import ssl
from pathlib import Path

import pytest

from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.ingress import GatewayIngressConfig, GatewayIngressService
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.gateway.syslog_host import (
    GatewaySyslogHost,
    GatewaySyslogHostPolicy,
    GatewaySyslogPeerIdentityError,
    extract_uri_san_principal,
)
from ets.runtime.sync_queue import SyncQueue

PRINCIPAL = "spiffe://example.test/workload/syslog-sender"


def _registry() -> StaticSourceRegistry:
    return StaticSourceRegistry(
        [
            SourceRegistration(
                principal=PRINCIPAL,
                source_id="syslog-source",
                source_system="enterprise-syslog",
                tenant_id="tenant_authoritative",
                workspace_id="workspace_authoritative",
                adapter_id="gateway-syslog",
                event_type="evidence.captured.syslog",
            )
        ]
    )


def _service(tmp_path: Path, *, max_message_bytes: int = 8192) -> GatewayIngressService:
    return GatewayIngressService(
        registry=_registry(),
        event_log=InMemoryAppendOnlyLog(),
        sync_queue=SyncQueue(tmp_path / "syslog-host-unit.db"),
        config=GatewayIngressConfig(max_syslog_message_bytes=max_message_bytes),
    )


def _qualified_context() -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.options |= ssl.OP_NO_COMPRESSION
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def test_extract_uri_san_principal_accepts_one_uri_and_ignores_other_san_types() -> None:
    certificate = {
        "subjectAltName": (
            ("DNS", "sender.example.test"),
            ("URI", PRINCIPAL),
        )
    }

    assert extract_uri_san_principal(certificate) == PRINCIPAL


@pytest.mark.parametrize(
    "certificate",
    [
        {},
        {"subjectAltName": (("DNS", "sender.example.test"),)},
        {"subjectAltName": (("URI", PRINCIPAL), ("URI", "spiffe://other"))},
    ],
)
def test_extract_uri_san_principal_rejects_missing_or_ambiguous_uri(
    certificate: dict[str, object],
) -> None:
    with pytest.raises(GatewaySyslogPeerIdentityError):
        extract_uri_san_principal(certificate)


def test_syslog_host_policy_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="integer limits"):
        GatewaySyslogHostPolicy(max_concurrent_connections=0)
    with pytest.raises(ValueError, match="time limits"):
        GatewaySyslogHostPolicy(read_idle_timeout_seconds=0)
    with pytest.raises(ValueError, match="max_buffer_bytes"):
        GatewaySyslogHostPolicy(max_message_bytes=100, max_buffer_bytes=101)


def test_syslog_host_requires_mutual_tls(tmp_path: Path) -> None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.options |= ssl.OP_NO_COMPRESSION

    with pytest.raises(ValueError, match="client certificates"):
        GatewaySyslogHost(_service(tmp_path), _registry(), context, port=0)


def test_syslog_host_requires_ingress_and_transport_message_bounds_to_match(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="message limit"):
        GatewaySyslogHost(
            _service(tmp_path, max_message_bytes=4096),
            _registry(),
            _qualified_context(),
            policy=GatewaySyslogHostPolicy(max_message_bytes=8192),
            port=0,
        )


def test_syslog_host_accepts_ephemeral_port_and_qualified_context(tmp_path: Path) -> None:
    host = GatewaySyslogHost(
        _service(tmp_path),
        _registry(),
        _qualified_context(),
        port=0,
    )

    assert host.accepting is True
    assert host.active_connections == 0
    assert host.bound_port is None
