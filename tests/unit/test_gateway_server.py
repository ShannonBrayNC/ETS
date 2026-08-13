from __future__ import annotations

import ssl

from fastapi import FastAPI

from ets.gateway.host import GatewayHostController, create_gateway_tls_context
from ets.gateway.server import (
    DEFAULT_GATEWAY_GRACEFUL_SHUTDOWN_SECONDS,
    GatewayUvicornServer,
    create_gateway_https_server,
    create_gateway_uvicorn_config,
)


def test_gateway_uvicorn_config_matches_host_policy_and_tls_context() -> None:
    app = FastAPI()
    host_controller = GatewayHostController()
    tls_context = create_gateway_tls_context()

    config = create_gateway_uvicorn_config(app, tls_context, host_controller)

    assert config.host == "0.0.0.0"
    assert config.port == 8443
    assert config.workers == 1
    assert config.proxy_headers is False
    assert config.forwarded_allow_ips == []
    assert config.server_header is False
    assert config.access_log is False
    assert config.limit_concurrency == host_controller.policy.max_concurrent_requests
    assert config.timeout_graceful_shutdown == DEFAULT_GATEWAY_GRACEFUL_SHUTDOWN_SECONDS

    config.load()
    assert config.ssl is tls_context
    assert config.ssl.minimum_version == ssl.TLSVersion.TLSv1_2
    assert config.ssl.maximum_version == ssl.TLSVersion.TLSv1_3


def test_gateway_https_server_uses_same_controller_and_rejects_invalid_timeout() -> None:
    app = FastAPI()
    host_controller = GatewayHostController()
    tls_context = create_gateway_tls_context()

    server = create_gateway_https_server(app, tls_context, host_controller)

    assert isinstance(server, GatewayUvicornServer)
    assert server.host_controller is host_controller
    assert server.drain_timed_out is False

    try:
        create_gateway_https_server(
            app,
            tls_context,
            host_controller,
            graceful_shutdown_seconds=0,
        )
    except ValueError as exc:
        assert "graceful shutdown timeout" in str(exc)
    else:
        raise AssertionError("invalid graceful shutdown timeout was accepted")
