"""Credential-safe Microsoft Entra delta HTTP transport for G2E-C."""

from __future__ import annotations

from email.message import Message
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ets.connectors.enterprise.microsoft_entra_delta import (
    ENTRA_DEFAULT_MAXIMUM_BODY_BYTES,
    EntraDeltaRequestProfile,
    MicrosoftEntraDeltaPageV1,
    parse_entra_delta_page,
    validate_entra_delta_cursor_url,
)

ENTRA_DELTA_USER_AGENT = "ets-gateway-microsoft-entra-delta/1.0"
ENTRA_DELTA_MAXIMUM_TIMEOUT_SECONDS = 60.0


class MicrosoftEntraDeltaClientError(RuntimeError):
    """Base Entra delta source-client error without reusable credential material."""


class MicrosoftEntraDeltaAuthenticationError(MicrosoftEntraDeltaClientError):
    """Raised when Microsoft Graph rejects the access token."""


class MicrosoftEntraDeltaAuthorizationError(MicrosoftEntraDeltaClientError):
    """Raised when the token cannot access the configured directory collection."""


class MicrosoftEntraDeltaThrottleError(MicrosoftEntraDeltaClientError):
    """Raised when Microsoft Graph requests bounded retry behavior."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Microsoft Graph delta endpoint is rate limited")
        self.retry_after_seconds = max(1, retry_after_seconds)


class MicrosoftEntraDeltaRetryableError(MicrosoftEntraDeltaClientError):
    """Raised for bounded transient network/source failures."""


class MicrosoftEntraDeltaTerminalError(MicrosoftEntraDeltaClientError):
    """Raised for non-retryable source/transport failures."""


class MicrosoftEntraDeltaRedirectError(MicrosoftEntraDeltaTerminalError):
    """Raised when a credential-bearing Graph request attempts a redirect."""


class MicrosoftEntraDeltaResponseTooLargeError(MicrosoftEntraDeltaTerminalError):
    """Raised when a Graph response exceeds the configured byte bound."""


class MicrosoftEntraDeltaStateExpiredError(MicrosoftEntraDeltaClientError):
    """Raised when Graph invalidates delta state and an authorized resync is required."""

    resync_required = True


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
        raise MicrosoftEntraDeltaRedirectError(
            "Microsoft Graph redirects are disabled for credential-bearing delta requests"
        )


class MicrosoftEntraDeltaHttpClient:
    """Bounded Graph GET client that preserves source-provided delta URLs exactly."""

    def __init__(
        self,
        profile: EntraDeltaRequestProfile,
        credential_material: bytes,
        *,
        timeout_seconds: float = 30.0,
        maximum_response_bytes: int = ENTRA_DEFAULT_MAXIMUM_BODY_BYTES,
    ) -> None:
        if not credential_material:
            raise ValueError("Microsoft Graph credential material must not be empty")
        if not 0.1 <= timeout_seconds <= ENTRA_DELTA_MAXIMUM_TIMEOUT_SECONDS:
            raise ValueError("Microsoft Graph timeout_seconds must be between 0.1 and 60")
        if not 1 <= maximum_response_bytes <= 16 * 1024 * 1024:
            raise ValueError("Microsoft Graph maximum_response_bytes exceeds qualified bound")
        self._profile = profile
        self._credential = bytearray(credential_material)
        self._timeout_seconds = timeout_seconds
        self._maximum_response_bytes = maximum_response_bytes
        self._closed = False
        self._opener = build_opener(_RejectRedirects())

    def __repr__(self) -> str:
        return (
            "MicrosoftEntraDeltaHttpClient(credential=<redacted>, "
            f"collection={self._profile.collection!r})"
        )

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._credential)):
            self._credential[index] = 0
        self._closed = True

    def fetch(self, request_url: str | None = None) -> MicrosoftEntraDeltaPageV1:
        if self._closed:
            raise MicrosoftEntraDeltaClientError("Microsoft Graph delta client is closed")
        url = self._profile.initial_url if request_url is None else request_url
        url = validate_entra_delta_cursor_url(self._profile, url)
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._credential_text()}",
                "User-Agent": ENTRA_DELTA_USER_AGENT,
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                body = response.read(self._maximum_response_bytes + 1)
                if len(body) > self._maximum_response_bytes:
                    raise MicrosoftEntraDeltaResponseTooLargeError(
                        "Microsoft Graph delta response exceeds configured byte bound"
                    )
                _validate_json_content_type(response.headers.get("Content-Type"))
        except MicrosoftEntraDeltaClientError:
            raise
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise MicrosoftEntraDeltaRetryableError(
                "Microsoft Graph delta request failed"
            ) from exc

        try:
            return parse_entra_delta_page(
                body,
                profile=self._profile,
                request_url=url,
                maximum_body_bytes=self._maximum_response_bytes,
            )
        except ValueError as exc:
            raise MicrosoftEntraDeltaTerminalError(
                "Microsoft Graph delta response failed the qualified parser"
            ) from exc

    def _credential_text(self) -> str:
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise MicrosoftEntraDeltaAuthenticationError(
                "Microsoft Graph credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if 300 <= exc.code <= 399:
            raise MicrosoftEntraDeltaRedirectError(
                "Microsoft Graph redirects are disabled"
            ) from exc
        if exc.code == 401:
            raise MicrosoftEntraDeltaAuthenticationError(
                "Microsoft Graph access token was rejected"
            ) from exc
        if exc.code == 403:
            raise MicrosoftEntraDeltaAuthorizationError(
                "Microsoft Graph directory access was denied"
            ) from exc
        if exc.code == 410:
            raise MicrosoftEntraDeltaStateExpiredError(
                "Microsoft Graph delta state expired; authorized full resync is required"
            ) from exc
        if exc.code == 429:
            raise MicrosoftEntraDeltaThrottleError(
                _retry_after_seconds(exc.headers.get("Retry-After"))
            ) from exc
        if 500 <= exc.code <= 599:
            raise MicrosoftEntraDeltaRetryableError(
                "Microsoft Graph delta endpoint returned a server error"
            ) from exc
        raise MicrosoftEntraDeltaTerminalError(
            f"Microsoft Graph delta endpoint rejected request with HTTP {exc.code}"
        ) from exc


def _validate_json_content_type(value: str | None) -> None:
    if value is None:
        raise MicrosoftEntraDeltaRetryableError(
            "Microsoft Graph delta response omitted Content-Type"
        )
    media_type = value.partition(";")[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise MicrosoftEntraDeltaRetryableError(
            "Microsoft Graph delta response Content-Type is not JSON"
        )


def _retry_after_seconds(value: str | None) -> int:
    if value is None:
        return 1
    try:
        parsed = int(value)
    except ValueError:
        return 1
    return max(1, min(parsed, 3600))
