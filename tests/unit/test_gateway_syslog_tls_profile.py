from __future__ import annotations

import ssl
from pathlib import Path

import pytest

import ets.gateway.syslog_host as syslog_host


def test_qualified_syslog_tls_factory_disables_tls13_session_tickets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.num_tickets = 2

    def fake_create() -> ssl.SSLContext:
        return context

    def fake_load(
        supplied: ssl.SSLContext,
        *,
        certfile: str | Path,
        keyfile: str | Path,
        client_ca_file: str | Path | None = None,
    ) -> ssl.SSLContext:
        assert certfile == "server.pem"
        assert keyfile == "server-key.pem"
        assert client_ca_file == "ca.pem"
        return supplied

    monkeypatch.setattr(syslog_host, "create_gateway_tls_context", fake_create)
    monkeypatch.setattr(syslog_host, "load_gateway_tls_credentials", fake_load)

    result = syslog_host.create_gateway_syslog_tls_context(
        certfile="server.pem",
        keyfile="server-key.pem",
        client_ca_file="ca.pem",
    )

    assert result is context
    assert result.num_tickets == 0


def test_python_ssl_early_data_support_change_requires_profile_review() -> None:
    # Python 3.12 does not expose TLS 1.3 early-data APIs. If that changes,
    # qualification must fail until the syslog profile explicitly disables them.
    assert not hasattr(ssl.SSLContext, "maximum_early_data")
