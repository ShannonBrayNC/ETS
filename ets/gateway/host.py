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


class GatewayHostDrainingError(GatewayHostSaturatedError):
    """Raised when a draining host no longer accepts new requests."""


class UnsupportedContentEncodingError(GatewayHostLimitError):
    """Raised when a request uses an unqualified content encoding."""


@dataclass(frozen=True, slots=True)
class GatewayHostPolicy:
    """Qualified transport-host limits for Gateway webhook ingress."""

    max_header_count: int = 64
    max_header_bytes: int = 16 * 1024
    max_header_value_bytes: int = 4 * 1024
    max_content_type_bytes: int = 200
    max_observed_at_bytes: int = 64
    max_idempotency_key_bytes: int = 200
    max_declared_identity_bytes: int = 500
    max_correlation_id_bytes: int = 200
    max_content_encoding_bytes: int = 64
    max_authorization_bytes: int = 4 * 1024
    max_content_length_bytes: int = 32
    max_concurrent_requests: int = 64
    admission_timeout_seconds: float = 0.05
    body_read_timeout_seconds: float = 10.0
    allowed_content_encodings: tuple[str, ...] = ("identity",)

    def __post_init__(self) -> None:
        numeric = (
            self.max_header_count,
            self.max_header_bytes,
            self.max_header_value_bytes,
            self.max_content_type_bytes,
            self.max_observed_at_bytes,
            self.max_idempotency_key_bytes,
            self.max_declared_identity_bytes,
            self.max_correlation_id_bytes,
            self.max_content_encoding_bytes,
            self.max_authorization_bytes,
            self.max_content_length_bytes,
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
        self._accepting = True
        self._active_requests = 0
        self._drained = asyncio.Event()
        self._drained.set()

    @property
    def accepting(self) -> bool:
        """Return whether the host accepts new requests."""

        return self._accepting

    @property
    def active_requests(self) -> int:
        """Return the number of requests currently admitted by this controller."""

        return self._active_requests

    def begin_shutdown(self) -> None:
        """Stop new admission while allowing already-admitted requests to complete."""

        self._accepting = False

    async def wait_drained(self, timeout_seconds: float | None = None) -> None:
        """Wait until all already-admitted work has exited the host controller."""

        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("drain timeout must be positive")
        if timeout_seconds is None:
            await self._drained.wait()
            return
        try:
            async with asyncio.timeout(timeout_seconds):
                await self._drained.wait()
        except TimeoutError as exc:
            raise TimeoutError("Gateway host did not drain before timeout") from exc

    def validate_headers(self, headers: Iterable[tuple[bytes, bytes]]) -> None:
        """Reject excessive, duplicate, or overlong security-relevant HTTP headers."""

        critical_limits = {
            b"content-type": self.policy.max_content_type_bytes,
            b"x-ets-observed-at": self.policy.max_observed_at_bytes,
            b"idempotency-key": self.policy.max_idempotency_key_bytes,
            b"x-ets-declared-identity": self.policy.max_declared_identity_bytes,
            b"x-correlation-id": self.policy.max_correlation_id_bytes,
            b"content-encoding": self.policy.max_content_encoding_bytes,
            b"authorization": self.policy.max_authorization_bytes,
            b"content-length": self.policy.max_content_length_bytes,
        }
        seen_critical: set[bytes] = set()
        count = 0
        total_bytes = 0
        for name, value in headers:
            normalized_name = name.lower()
            count += 1
            total_bytes += len(name) + len(value)
            if len(value) > self.policy.max_header_value_bytes:
                raise GatewayHostLimitError("request header value exceeds configured limit")
            critical_limit = critical_limits.get(normalized_name)
            if critical_limit is not None:
                if normalized_name in seen_critical:
                    raise GatewayHostLimitError("duplicate security-relevant request header")
                seen_critical.add(normalized_name)
                if len(value) > critical_limit:
                    raise GatewayHostLimitError("critical request header exceeds configured limit")
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
        """Admit a request within concurrency and host-drain boundaries."""

        if not self._accepting:
            raise GatewayHostDrainingError("Gateway host is draining")

        acquired = False
        try:
            try:
                async with asyncio.timeout(self.policy.admission_timeout_seconds):
                    await self._semaphore.acquire()
                acquired = True
            except TimeoutError as exc:
                raise GatewayHostSaturatedError("Gateway host concurrency is saturated") from exc

            if not self._accepting:
                raise GatewayHostDrainingError("Gateway host is draining")

            if self._active_requests == 0:
                self._drained.clear()
            self._active_requests += 1
            try:
                yield
            finally:
                self._active_requests -= 1
                if self._active_requests == 0:
                    self._drained.set()
        finally:
            if acquired:
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
