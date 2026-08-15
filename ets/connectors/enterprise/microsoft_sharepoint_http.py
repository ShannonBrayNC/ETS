"""Credential-safe Microsoft Graph SharePoint/OneDrive delta HTTP transport."""

from __future__ import annotations

from email.message import Message
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    SHAREPOINT_DELTA_DEFAULT_MAXIMUM_BODY_BYTES,
    MicrosoftSharePointDeltaPageV1,
    MicrosoftSharePointDeltaRequestProfile,
    parse_sharepoint_delta_page,
    validate_sharepoint_delta_url,
)

SHAREPOINT_DELTA_USER_AGENT = "ets-gateway-microsoft-sharepoint-delta/1.0"
SHAREPOINT_DELTA_MAXIMUM_TIMEOUT_SECONDS = 60.0
SHAREPOINT_DELTA_MAXIMUM_RESPONSE_BYTES = 16 * 1024 * 1024


class MicrosoftSharePointDeltaClientError(RuntimeError):
    """Base metadata-delta source client error without reusable credential material."""


class MicrosoftSharePointDeltaAuthenticationError(MicrosoftSharePointDeltaClientError):
    """Raised when Microsoft Graph rejects the access token."""


class MicrosoftSharePointDeltaAuthorizationError(MicrosoftSharePointDeltaClientError):
    """Raised when Graph denies the approved site/drive/list metadata scope."""


class MicrosoftSharePointDeltaThrottleError(MicrosoftSharePointDeltaClientError):
    """Raised when Graph requests bounded retry behavior."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Microsoft Graph SharePoint delta endpoint is rate limited")
        self.retry_after_seconds = max(1, retry_after_seconds)


class MicrosoftSharePointDeltaRetryableError(MicrosoftSharePointDeltaClientError):
    """Raised for bounded transient network/source failures."""


class MicrosoftSharePointDeltaTerminalError(MicrosoftSharePointDeltaClientError):
    """Raised for non-retryable source/transport failures."""


class MicrosoftSharePointDeltaRedirectError(MicrosoftSharePointDeltaTerminalError):
    """Raised when a credential-bearing Graph request attempts a redirect."""


class MicrosoftSharePointDeltaResponseTooLargeError(MicrosoftSharePointDeltaTerminalError):
    """Raised when a Graph response exceeds the configured byte bound."""


class MicrosoftSharePointDeltaStateExpiredError(MicrosoftSharePointDeltaClientError):
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
        raise MicrosoftSharePointDeltaRedirectError(
            "Microsoft Graph redirects are disabled for credential-bearing metadata requests"
        )


class MicrosoftSharePointDeltaHttpClient:
    """Bounded Graph GET client preserving source-provided continuation URLs exactly."""

    def __init__(
        self,
        profile: MicrosoftSharePointDeltaRequestProfile,
        credential_material: bytes,
        *,
        timeout_seconds: float = 30.0,
        maximum_response_bytes: int = SHAREPOINT_DELTA_DEFAULT_MAXIMUM_BODY_BYTES,
    ) -> None:
        if not credential_material:
            raise ValueError("Microsoft Graph credential material must not be empty")
        if not 0.1 <= timeout_seconds <= SHAREPOINT_DELTA_MAXIMUM_TIMEOUT_SECONDS:
            raise ValueError("Microsoft Graph timeout_seconds must be between 0.1 and 60")
        if not 1 <= maximum_response_bytes <= SHAREPOINT_DELTA_MAXIMUM_RESPONSE_BYTES:
            raise ValueError("Microsoft Graph maximum_response_bytes exceeds qualified bound")
        self._profile = profile
        self._credential = bytearray(credential_material)
        self._timeout_seconds = timeout_seconds
        self._maximum_response_bytes = maximum_response_bytes
        self._closed = False
        self._opener = build_opener(_RejectRedirects())

    def __repr__(self) -> str:
        return (
            "MicrosoftSharePointDeltaHttpClient(credential=<redacted>, "
            f"scope={self._profile.scope!r})"
        )

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._credential)):
            self._credential[index] = 0
        self._closed = True

    def fetch(self, request_url: str | None = None) -> MicrosoftSharePointDeltaPageV1:
        if self._closed:
            raise MicrosoftSharePointDeltaClientError(
                "Microsoft Graph SharePoint delta client is closed"
            )
        url = self._profile.initial_url if request_url is None else request_url
        url = validate_sharepoint_delta_url(self._profile, url)
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._credential_text()}",
                "User-Agent": SHAREPOINT_DELTA_USER_AGENT,
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                body = response.read(self._maximum_response_bytes + 1)
                if len(body) > self._maximum_response_bytes:
                    raise MicrosoftSharePointDeltaResponseTooLargeError(
                        "Microsoft Graph SharePoint delta response exceeds configured byte bound"
                    )
                _validate_json_content_type(response.headers.get("Content-Type"))
        except MicrosoftSharePointDeltaClientError:
            raise
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise MicrosoftSharePointDeltaRetryableError(
                "Microsoft Graph SharePoint delta request failed"
            ) from exc

        try:
            return parse_sharepoint_delta_page(
                body,
                self._profile,
                maximum_body_bytes=self._maximum_response_bytes,
            )
        except ValueError as exc:
            raise MicrosoftSharePointDeltaTerminalError(
                "Microsoft Graph SharePoint delta response failed the qualified parser"
            ) from exc

    def _credential_text(self) -> str:
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise MicrosoftSharePointDeltaAuthenticationError(
                "Microsoft Graph credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if 300 <= exc.code <= 399:
            raise MicrosoftSharePointDeltaRedirectError(
                "Microsoft Graph redirects are disabled"
            ) from exc
        if exc.code == 401:
            raise MicrosoftSharePointDeltaAuthenticationError(
                "Microsoft Graph access token was rejected"
            ) from exc
        if exc.code == 403:
            raise MicrosoftSharePointDeltaAuthorizationError(
                "Microsoft Graph SharePoint metadata access was denied"
            ) from exc
        if exc.code == 410:
            raise MicrosoftSharePointDeltaStateExpiredError(
                "Microsoft Graph SharePoint delta state expired; authorized resync is required"
            ) from exc
        if exc.code == 429:
            raise MicrosoftSharePointDeltaThrottleError(
                _retry_after_seconds(exc.headers.get("Retry-After"))
            ) from exc
        if 500 <= exc.code <= 599:
            raise MicrosoftSharePointDeltaRetryableError(
                "Microsoft Graph SharePoint delta endpoint returned a server error"
            ) from exc
        raise MicrosoftSharePointDeltaTerminalError(
            f"Microsoft Graph SharePoint delta endpoint rejected request with HTTP {exc.code}"
        ) from exc


def _validate_json_content_type(value: str | None) -> None:
    if value is None:
        raise MicrosoftSharePointDeltaRetryableError(
            "Microsoft Graph SharePoint delta response omitted Content-Type"
        )
    media_type = value.partition(";")[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise MicrosoftSharePointDeltaRetryableError(
            "Microsoft Graph SharePoint delta response Content-Type is not JSON"
        )


def _retry_after_seconds(value: str | None) -> int:
    if value is None:
        return 1
    try:
        parsed = int(value)
    except ValueError:
        return 1
    return max(1, min(parsed, 3600))
