"""Bounded credential-safe HTTPS transport for the Generic REST connector."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from email.message import Message
from typing import Final, NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

GENERIC_REST_USER_AGENT: Final = "ets-gateway-generic-rest/1.0"
GENERIC_REST_MAX_TIMEOUT_SECONDS: Final = 60.0
GENERIC_REST_MAX_RESPONSE_BYTES: Final = 16 * 1024 * 1024
GENERIC_REST_MAX_HEADERS: Final = 64
GENERIC_REST_MAX_QUERY_ITEMS: Final = 64
GENERIC_REST_MAX_NAME_LENGTH: Final = 128
GENERIC_REST_MAX_VALUE_LENGTH: Final = 2048

_SENSITIVE_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "credential",
        "password",
        "private_key",
        "proxy_authorization",
        "secret",
        "token",
        "x_api_key",
    }
)
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class GenericRestClientError(RuntimeError):
    """Base Generic REST source-client error without reusable credential material."""


class GenericRestAuthenticationError(GenericRestClientError):
    """Raised when the source rejects supplied authentication material."""


class GenericRestAuthorizationError(GenericRestClientError):
    """Raised when the authenticated principal cannot access the requested source."""


class GenericRestThrottleError(GenericRestClientError):
    """Raised when the source instructs the connector to retry later."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Generic REST source is rate limited")
        self.retry_after_seconds = max(1, retry_after_seconds)


class GenericRestRetryableError(GenericRestClientError):
    """Raised for bounded transient transport/source failures."""


class GenericRestTerminalError(GenericRestClientError):
    """Raised when the source rejects a request in a non-retryable way."""


class GenericRestResponseTooLargeError(GenericRestTerminalError):
    """Raised when the source response exceeds the configured byte bound."""


class GenericRestRedirectError(GenericRestTerminalError):
    """Raised when a source attempts an HTTP redirect."""


@dataclass(frozen=True, slots=True)
class GenericRestHostPolicy:
    """Server-owned exact-host allow-list for credential-bearing source requests."""

    allowed_hosts: frozenset[str]

    def __post_init__(self) -> None:
        if not self.allowed_hosts:
            raise ValueError("Generic REST trusted-host policy must not be empty")
        normalized: set[str] = set()
        for host in self.allowed_hosts:
            value = host.strip().lower().rstrip(".")
            if not value or ":" in value or "/" in value or "@" in value:
                raise ValueError("Generic REST trusted hosts must be bare DNS hostnames")
            normalized.add(value)
        object.__setattr__(self, "allowed_hosts", frozenset(normalized))

    def authorize(self, endpoint_url: str) -> str:
        parts = urlsplit(endpoint_url)
        if parts.scheme != "https":
            raise ValueError("Generic REST endpoints must use HTTPS")
        if parts.username is not None or parts.password is not None:
            raise ValueError("Generic REST endpoint URLs must not contain user information")
        if parts.fragment:
            raise ValueError("Generic REST endpoint URLs must not contain fragments")
        if parts.query:
            raise ValueError("Generic REST endpoint query belongs in the bounded query profile")
        host = (parts.hostname or "").lower().rstrip(".")
        if not host or host not in self.allowed_hosts:
            raise ValueError("Generic REST endpoint host is not authorized by server policy")
        if parts.port not in {None, 443}:
            raise ValueError("Generic REST reference profile requires HTTPS port 443")
        return host


@dataclass(frozen=True, slots=True)
class GenericRestRequestProfile:
    """One bounded GET request profile with non-sensitive customer metadata only."""

    endpoint_url: str
    timeout_seconds: float = 30.0
    max_response_bytes: int = 1024 * 1024
    headers: Mapping[str, str] | None = None
    query: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not 0.1 <= self.timeout_seconds <= GENERIC_REST_MAX_TIMEOUT_SECONDS:
            raise ValueError("Generic REST timeout_seconds must be between 0.1 and 60")
        if not 1 <= self.max_response_bytes <= GENERIC_REST_MAX_RESPONSE_BYTES:
            raise ValueError("Generic REST max_response_bytes exceeds the qualified bound")
        _validate_key_values(self.headers or {}, kind="header", maximum=GENERIC_REST_MAX_HEADERS)
        _validate_key_values(self.query or {}, kind="query", maximum=GENERIC_REST_MAX_QUERY_ITEMS)


@dataclass(frozen=True, slots=True)
class GenericRestResponse:
    """Bounded response bytes plus a minimized response-header view."""

    body: bytes
    content_type: str | None
    etag: str | None
    last_modified: str | None


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> NoReturn:
        raise GenericRestRedirectError("Generic REST redirects are disabled")


class GenericRestHttpClient:
    """Reference HTTPS GET transport with bounded credential lifetime and no redirects."""

    def __init__(
        self,
        profile: GenericRestRequestProfile,
        host_policy: GenericRestHostPolicy,
        *,
        credential_material: bytes | None = None,
    ) -> None:
        host_policy.authorize(profile.endpoint_url)
        if credential_material is not None and not credential_material:
            raise ValueError("Generic REST credential material must not be empty")
        self._profile = profile
        self._credential = (
            bytearray(credential_material) if credential_material is not None else None
        )
        self._closed = False
        self._opener = build_opener(_RejectRedirects())

    def __repr__(self) -> str:
        return "GenericRestHttpClient(credential=<redacted>)"

    def close(self) -> None:
        if self._closed:
            return
        if self._credential is not None:
            for index in range(len(self._credential)):
                self._credential[index] = 0
        self._closed = True

    def get(self) -> GenericRestResponse:
        if self._closed:
            raise GenericRestClientError("Generic REST client is closed")
        request = Request(
            _request_url(self._profile),
            method="GET",
            headers=self._request_headers(),
        )
        try:
            with self._opener.open(
                request,
                timeout=self._profile.timeout_seconds,
            ) as response:
                body = response.read(self._profile.max_response_bytes + 1)
                if len(body) > self._profile.max_response_bytes:
                    raise GenericRestResponseTooLargeError(
                        "Generic REST response exceeds configured byte bound"
                    )
                return GenericRestResponse(
                    body=body,
                    content_type=response.headers.get("Content-Type"),
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                )
        except GenericRestClientError:
            raise
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise GenericRestRetryableError("Generic REST source request failed") from exc

    def _request_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": GENERIC_REST_USER_AGENT}
        headers.update(self._profile.headers or {})
        if self._credential is not None:
            headers["Authorization"] = f"Bearer {self._credential_text()}"
        return headers

    def _credential_text(self) -> str:
        assert self._credential is not None
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise GenericRestAuthenticationError(
                "Generic REST credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if 300 <= exc.code <= 399:
            raise GenericRestRedirectError("Generic REST redirects are disabled") from exc
        if exc.code == 401:
            raise GenericRestAuthenticationError(
                "Generic REST source authentication failed"
            ) from exc
        if exc.code == 403:
            raise GenericRestAuthorizationError(
                "Generic REST source authorization failed"
            ) from exc
        if exc.code == 429:
            raise GenericRestThrottleError(_retry_after_seconds(exc.headers)) from exc
        if 500 <= exc.code <= 599:
            raise GenericRestRetryableError("Generic REST source server error") from exc
        raise GenericRestTerminalError(
            f"Generic REST source rejected request with HTTP {exc.code}"
        ) from exc


def _request_url(profile: GenericRestRequestProfile) -> str:
    parts = urlsplit(profile.endpoint_url)
    query = urlencode(sorted((profile.query or {}).items()))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", query, ""))


def _validate_key_values(values: Mapping[str, str], *, kind: str, maximum: int) -> None:
    if len(values) > maximum:
        raise ValueError(f"Generic REST {kind} count exceeds the qualified bound")
    for name, value in values.items():
        if not _NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Generic REST {kind} name is invalid")
        normalized = name.casefold().replace("-", "_").replace(".", "_")
        if normalized in _SENSITIVE_NAMES:
            raise ValueError(
                f"Generic REST {kind} {name!r} must use a credential reference instead"
            )
        if len(value) > GENERIC_REST_MAX_VALUE_LENGTH:
            raise ValueError(f"Generic REST {kind} value exceeds the qualified bound")


def _retry_after_seconds(headers: Message) -> int:
    value = headers.get("Retry-After")
    if value is None:
        return 60
    try:
        parsed = int(value)
    except ValueError:
        return 60
    return min(max(parsed, 1), 3600)
