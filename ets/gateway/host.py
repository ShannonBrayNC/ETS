"""Gateway HTTP host qualification policy for GATE-G1C-HOST."""

from __future__ import annotations

import asyncio
import ssl
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path


class GatewayHostLimitError(ValueError):
    """Raised when request metadata exceeds the qualified host policy."""


class GatewayHostSaturatedError(RuntimeError):
    """Raised when bounded host concurrency cannot admit a request."""


class UnsupportedContentEncodingError(GatewayHostLimitError):
    """Raised when a request uses an unqualified content encoding."""


@dataclass(frozen=True, slots=True)
class GatewayHostPolicy:
    """Qualified transport-host limits for Gateway webhook ingress."""

    max_header_count: int = 64
    max_header_bytes: int = 16 * 1024
    max_header_value_bytes: int = 4 * 1024
    max_concurrent_requests: int = 64
    admission_timeout_seconds: float = 0.05
    body_read_timeout_seconds: float = 10.0
    allowed_content_encodings: tuple[str, ...] = ("identity",)

    def __post_init__(self) -> None:
        numeric = (
            self.max_header_count,
            self.max_header_bytes,
            self.max_header_value_bytes,
            self.max_concurrent_requests,
        )
        if any(value < 1 for value in numeric):
            raise ValueError("Gateway host integer limits must be positive")
        if self.admission_timeout_seconds <= 0 or self.body_read_timeout_seconds <= 0:
            raise ValueError("Gateway host time limits must be positive")
        if not self.allowed_content_encodings:
            raise ValueError("at least one content encoding must be allowed")
        normalized = tuple(value.strip().lower() for value in self.allowed_content_encodings)
        if any(not value for value in normalized):
            raise ValueError("content encoding values cannot be empty")
        if normalized != self.allowed_content_encodings:
            raise ValueError("content encoding values must be normalized lowercase tokens")


class GatewayHostController:
    """Apply host metadata limits and bounded request admission."""

    def __init__(self, policy: GatewayHostPolicy | None = None) -> None:
        self.policy = policy or GatewayHostPolicy()
        self._semaphore = asyncio.Semaphore(self.policy.max_concurrent_requests)

    def validate_headers(self, headers: Iterable[tuple[bytes, bytes]]) -> None:
        """Reject excessive aggregate, count, or per-value HTTP headers."""

        count = 0
        total_bytes = 0
        for name, value in headers:
            count += 1
            total_bytes += len(name) + len(value)
            if len(value) > self.policy.max_header_value_bytes:
                raise GatewayHostLimitError("request header value exceeds configured limit")
            if count > self.policy.max_header_count:
                raise GatewayHostLimitError("request header count exceeds configured limit")
            if total_bytes > self.policy.max_header_bytes:
                raise GatewayHostLimitError("request headers exceed aggregate configured limit")

    def validate_content_encoding(self, value: str | None) -> None:
        """Reject compressed or otherwise unqualified request representations."""

        encoding = "identity" if value is None else value.strip().lower()
        if encoding not in self.policy.allowed_content_encodings:
            raise UnsupportedContentEncodingError("request content encoding is not qualified")

    @asynccontextmanager
    async def admission(self) -> AsyncIterator[None]:
        """Admit a request within the configured concurrency budget."""

        try:
            async with asyncio.timeout(self.policy.admission_timeout_seconds):
                await self._semaphore.acquire()
        except TimeoutError as exc:
            raise GatewayHostSaturatedError("Gateway host concurrency is saturated") from exc
        try:
            yield
        finally:
            self._semaphore.release()


def create_gateway_tls_context() -> ssl.SSLContext:
    """Create the qualified Gateway TLS server profile without loading credentials."""

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.options |= ssl.OP_NO_COMPRESSION
    return context


def load_gateway_tls_credentials(
    context: ssl.SSLContext,
    *,
    certfile: str | Path,
    keyfile: str | Path,
    client_ca_file: str | Path | None = None,
) -> ssl.SSLContext:
    """Load server credentials and optional client-certificate trust roots."""

    context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
    if client_ca_file is not None:
        context.load_verify_locations(cafile=str(client_ca_file))
        context.verify_mode = ssl.CERT_REQUIRED
    return context
