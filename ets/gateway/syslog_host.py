"""Concrete bounded RFC 5425 TLS stream host for ETS Gateway G1D."""

from __future__ import annotations

import asyncio
import ssl
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from ets.capture import OctetCountingFramer, SyslogFramingError
from ets.gateway.host import create_gateway_tls_context, load_gateway_tls_credentials
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressError,
    GatewayIngressService,
    GatewayPartialCommitError,
)
from ets.gateway.source_registry import SourceAuthorizationError, StaticSourceRegistry
from ets.gateway.syslog_capture import GatewaySyslogCaptureError, GatewaySyslogCaptureRequest


class GatewaySyslogHostError(RuntimeError):
    """Base error for qualified Gateway syslog transport failures."""


class GatewaySyslogPeerIdentityError(GatewaySyslogHostError):
    """Raised when a TLS peer does not expose one qualified URI SAN principal."""


class GatewaySyslogHostSaturatedError(GatewaySyslogHostError):
    """Raised when the bounded connection admission window is exhausted."""


@dataclass(frozen=True, slots=True)
class GatewaySyslogHostPolicy:
    """Qualified limits for the RFC 5425 syslog TLS listener."""

    max_concurrent_connections: int = 64
    admission_timeout_seconds: float = 0.05
    tls_handshake_timeout_seconds: float = 10.0
    read_idle_timeout_seconds: float = 30.0
    read_chunk_bytes: int = 4096
    max_prefix_bytes: int = 10
    max_message_bytes: int = 8192
    max_buffer_bytes: int = 8203
    graceful_shutdown_seconds: float = 30.0

    def __post_init__(self) -> None:
        integer_limits = (
            self.max_concurrent_connections,
            self.read_chunk_bytes,
            self.max_prefix_bytes,
            self.max_message_bytes,
            self.max_buffer_bytes,
        )
        if any(value < 1 for value in integer_limits):
            raise ValueError("Gateway syslog host integer limits must be positive")
        time_limits = (
            self.admission_timeout_seconds,
            self.tls_handshake_timeout_seconds,
            self.read_idle_timeout_seconds,
            self.graceful_shutdown_seconds,
        )
        if any(value <= 0 for value in time_limits):
            raise ValueError("Gateway syslog host time limits must be positive")
        if self.max_buffer_bytes < self.max_message_bytes + 2:
            raise ValueError(
                "max_buffer_bytes must accommodate the qualified message and framing state"
            )


def extract_uri_san_principal(peer_certificate: object) -> str:
    """Extract exactly one bounded URI SAN principal from a validated peer certificate."""

    if not isinstance(peer_certificate, dict):
        raise GatewaySyslogPeerIdentityError("validated peer certificate metadata is unavailable")
    subject_alt_name = peer_certificate.get("subjectAltName", ())
    if not isinstance(subject_alt_name, (tuple, list)):
        raise GatewaySyslogPeerIdentityError("validated peer certificate SAN metadata is invalid")

    uri_values: list[str] = []
    for entry in subject_alt_name:
        if not isinstance(entry, tuple) or len(entry) != 2:
            continue
        kind, value = entry
        if kind == "URI" and isinstance(value, str):
            uri_values.append(value)

    if len(uri_values) != 1:
        raise GatewaySyslogPeerIdentityError(
            "validated peer certificate must contain exactly one URI SAN"
        )
    principal = uri_values[0]
    if not 1 <= len(principal) <= 500:
        raise GatewaySyslogPeerIdentityError("validated peer URI SAN is outside configured bounds")
    return principal


def create_gateway_syslog_tls_context(
    *,
    certfile: str | Path,
    keyfile: str | Path,
    client_ca_file: str | Path,
) -> ssl.SSLContext:
    """Create the qualified mTLS context for RFC 5425 syslog transport."""

    context = load_gateway_tls_credentials(
        create_gateway_tls_context(),
        certfile=certfile,
        keyfile=keyfile,
        client_ca_file=client_ca_file,
    )
    # RFC 9662 forbids TLS 1.3 early data for secure syslog. Python's ssl layer
    # does not expose early-data APIs; disabling TLS 1.3 session tickets makes
    # the profile explicit and prevents ticket-based resumption from becoming
    # an accidental path to 0-RTT if runtime support changes later.
    context.num_tickets = 0
    return context


class GatewaySyslogHost:
    """Bounded asyncio TLS stream host that delegates complete frames to Gateway ingress."""

    def __init__(
        self,
        service: GatewayIngressService,
        registry: StaticSourceRegistry,
        tls_context: ssl.SSLContext,
        *,
        policy: GatewaySyslogHostPolicy | None = None,
        host: str = "0.0.0.0",
        port: int = 6514,
    ) -> None:
        resolved_policy = policy or GatewaySyslogHostPolicy(
            max_message_bytes=service.max_syslog_message_bytes,
            max_buffer_bytes=service.max_syslog_message_bytes + 11,
        )
        if resolved_policy.max_message_bytes != service.max_syslog_message_bytes:
            raise ValueError(
                "Gateway syslog host message limit must match Gateway ingress configuration"
            )
        if tls_context.verify_mode != ssl.CERT_REQUIRED:
            raise ValueError("Gateway syslog TLS host requires client certificates")
        if tls_context.minimum_version < ssl.TLSVersion.TLSv1_2:
            raise ValueError("Gateway syslog TLS host requires TLS 1.2 or newer")
        if ssl.HAS_TLSv1_3 and tls_context.maximum_version < ssl.TLSVersion.TLSv1_3:
            raise ValueError("Gateway syslog TLS host must support TLS 1.3 when available")
        if tls_context.num_tickets != 0:
            raise ValueError("Gateway syslog TLS host requires TLS 1.3 session tickets disabled")
        if not tls_context.options & ssl.OP_NO_COMPRESSION:
            raise ValueError("Gateway syslog TLS host requires TLS compression to be disabled")
        if not 0 <= port <= 65535:
            raise ValueError("Gateway syslog host port must be between 0 and 65535")

        self.service = service
        self.registry = registry
        self.tls_context = tls_context
        self.policy = resolved_policy
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None
        self._accepting = True
        self._semaphore = asyncio.Semaphore(self.policy.max_concurrent_connections)
        self._connection_tasks: set[asyncio.Task[None]] = set()
        self._drained = asyncio.Event()
        self._drained.set()
        self.drain_timed_out = False

    @property
    def accepting(self) -> bool:
        """Return whether new application connections may still be admitted."""

        return self._accepting

    @property
    def active_connections(self) -> int:
        """Return the number of currently tracked TLS connection tasks."""

        return len(self._connection_tasks)

    @property
    def bound_port(self) -> int | None:
        """Return the first bound TCP port after startup."""

        if self._server is None or not self._server.sockets:
            return None
        return int(self._server.sockets[0].getsockname()[1])

    async def start(self) -> None:
        """Start accepting qualified RFC 5425 TLS connections."""

        if self._server is not None:
            raise RuntimeError("Gateway syslog host is already started")
        self._accepting = True
        self.drain_timed_out = False
        self._server = await asyncio.start_server(
            self._client_connected,
            self.host,
            self.port,
            ssl=self.tls_context,
            ssl_handshake_timeout=self.policy.tls_handshake_timeout_seconds,
            ssl_shutdown_timeout=self.policy.graceful_shutdown_seconds,
            start_serving=True,
        )

    async def serve_forever(self) -> None:
        """Serve until the underlying asyncio server is closed."""

        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def shutdown(self) -> None:
        """Stop accepts, drain admitted connections, then cancel transport work on timeout."""

        self._accepting = False
        server = self._server
        if server is not None:
            server.close()
            await server.wait_closed()

        if self._connection_tasks:
            try:
                async with asyncio.timeout(self.policy.graceful_shutdown_seconds):
                    await self._drained.wait()
            except TimeoutError:
                self.drain_timed_out = True
                for task in tuple(self._connection_tasks):
                    task.cancel()
                await asyncio.gather(*tuple(self._connection_tasks), return_exceptions=True)
        self._server = None

    def _client_connected(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        if not self._accepting:
            writer.close()
            return
        task = asyncio.create_task(self._handle_connection(reader, writer))
        if not self._connection_tasks:
            self._drained.clear()
        self._connection_tasks.add(task)
        task.add_done_callback(self._connection_finished)

    def _connection_finished(self, task: asyncio.Task[None]) -> None:
        self._connection_tasks.discard(task)
        with suppress(asyncio.CancelledError):
            task.exception()
        if not self._connection_tasks:
            self._drained.set()

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        acquired = False
        try:
            try:
                async with asyncio.timeout(self.policy.admission_timeout_seconds):
                    await self._semaphore.acquire()
                acquired = True
            except TimeoutError as exc:
                raise GatewaySyslogHostSaturatedError(
                    "Gateway syslog connection concurrency is saturated"
                ) from exc

            if not self._accepting:
                return

            ssl_object = cast(
                ssl.SSLObject | ssl.SSLSocket | None,
                writer.get_extra_info("ssl_object"),
            )
            if ssl_object is None:
                raise GatewaySyslogPeerIdentityError(
                    "qualified syslog listener requires an authenticated TLS connection"
                )
            if ssl_object.compression() is not None:
                raise GatewaySyslogHostError("TLS compression is not qualified")

            principal = extract_uri_san_principal(ssl_object.getpeercert())
            self.registry.resolve(principal)
            session_id = uuid4().hex
            frame_sequence = 0
            framer = OctetCountingFramer(
                maximum_message_bytes=self.policy.max_message_bytes,
                maximum_prefix_bytes=self.policy.max_prefix_bytes,
                maximum_buffer_bytes=self.policy.max_buffer_bytes,
            )

            while self._accepting:
                try:
                    async with asyncio.timeout(self.policy.read_idle_timeout_seconds):
                        data = await reader.read(self.policy.read_chunk_bytes)
                except TimeoutError as exc:
                    raise GatewaySyslogHostError(
                        "Gateway syslog connection read timed out"
                    ) from exc

                if not data:
                    framer.finish()
                    break

                frames = framer.feed(data)
                for frame in frames:
                    frame_sequence += 1
                    request = GatewaySyslogCaptureRequest(
                        message=frame,
                        delivery_id=f"{session_id}:{frame_sequence}",
                        sequence=frame_sequence,
                        received_at_utc=datetime.now(UTC),
                    )
                    self.service.ingest_syslog(principal, request)
        except (
            GatewayBackpressureError,
            GatewayConflictError,
            GatewayIngressError,
            GatewayPartialCommitError,
            GatewaySyslogCaptureError,
            GatewaySyslogHostError,
            SourceAuthorizationError,
            SyslogFramingError,
        ):
            # Fail closed without echoing raw MSG / STRUCTURED-DATA into operational output.
            pass
        finally:
            if acquired:
                self._semaphore.release()
            writer.close()
            with suppress(ConnectionError, OSError, ssl.SSLError):
                await writer.wait_closed()
