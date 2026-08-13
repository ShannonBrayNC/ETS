"""Concrete Uvicorn HTTPS assembly for the qualified ETS Gateway host."""

from __future__ import annotations

import socket
import ssl
from collections.abc import Callable
from types import FrameType

import uvicorn
from fastapi import FastAPI

from ets.gateway.host import GatewayHostController

DEFAULT_GATEWAY_GRACEFUL_SHUTDOWN_SECONDS = 30


def _ssl_context_factory(
    context: ssl.SSLContext,
) -> Callable[[uvicorn.Config, Callable[[], ssl.SSLContext]], ssl.SSLContext]:
    def factory(
        _config: uvicorn.Config,
        _default_factory: Callable[[], ssl.SSLContext],
    ) -> ssl.SSLContext:
        return context

    return factory


def create_gateway_uvicorn_config(
    app: FastAPI,
    tls_context: ssl.SSLContext,
    host_controller: GatewayHostController,
    *,
    host: str = "0.0.0.0",
    port: int = 8443,
    graceful_shutdown_seconds: int = DEFAULT_GATEWAY_GRACEFUL_SHUTDOWN_SECONDS,
) -> uvicorn.Config:
    """Create the production-like Gateway HTTPS server configuration."""

    if graceful_shutdown_seconds < 1:
        raise ValueError("graceful shutdown timeout must be positive")

    return uvicorn.Config(
        app,
        host=host,
        port=port,
        workers=1,
        loop="asyncio",
        proxy_headers=False,
        forwarded_allow_ips=[],
        server_header=False,
        access_log=False,
        limit_concurrency=host_controller.policy.max_concurrent_requests,
        timeout_graceful_shutdown=graceful_shutdown_seconds,
        ssl_context_factory=_ssl_context_factory(tls_context),
    )


class GatewayUvicornServer(uvicorn.Server):
    """Uvicorn server that begins Gateway drain before transport shutdown."""

    def __init__(
        self,
        config: uvicorn.Config,
        host_controller: GatewayHostController,
        *,
        drain_timeout_seconds: float = DEFAULT_GATEWAY_GRACEFUL_SHUTDOWN_SECONDS,
    ) -> None:
        if drain_timeout_seconds <= 0:
            raise ValueError("drain timeout must be positive")
        super().__init__(config)
        self.host_controller = host_controller
        self.drain_timeout_seconds = drain_timeout_seconds
        self.drain_timed_out = False

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        """Reject new application admission as soon as process shutdown is requested."""

        self.host_controller.begin_shutdown()
        super().handle_exit(sig, frame)

    async def shutdown(self, sockets: list[socket.socket] | None = None) -> None:
        """Drain admitted Gateway work before delegating transport shutdown to Uvicorn."""

        self.host_controller.begin_shutdown()
        try:
            await self.host_controller.wait_drained(self.drain_timeout_seconds)
        except TimeoutError:
            self.drain_timed_out = True
        await super().shutdown(sockets=sockets)


def create_gateway_https_server(
    app: FastAPI,
    tls_context: ssl.SSLContext,
    host_controller: GatewayHostController,
    *,
    host: str = "0.0.0.0",
    port: int = 8443,
    graceful_shutdown_seconds: int = DEFAULT_GATEWAY_GRACEFUL_SHUTDOWN_SECONDS,
) -> GatewayUvicornServer:
    """Assemble one qualified Gateway HTTPS server around an already-authenticated app."""

    config = create_gateway_uvicorn_config(
        app,
        tls_context,
        host_controller,
        host=host,
        port=port,
        graceful_shutdown_seconds=graceful_shutdown_seconds,
    )
    return GatewayUvicornServer(
        config,
        host_controller,
        drain_timeout_seconds=float(graceful_shutdown_seconds),
    )
