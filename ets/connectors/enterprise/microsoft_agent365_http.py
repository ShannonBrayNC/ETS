"""Credential-safe Microsoft Agent 365 live acquisition for A365-Q0."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from typing import Literal, NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ets.connectors.enterprise.microsoft_agent365 import (
    AGENT365_DEFAULT_MAXIMUM_BODY_BYTES,
    Agent365ApiMaturity,
    Agent365PayloadRetention,
    MicrosoftAgent365InventoryPageV1,
    MicrosoftAgent365PackageDetailV1,
    MicrosoftSourceEnvelopeV1,
    agent365_package_detail_url,
    agent365_packages_url,
    build_source_envelope,
    parse_agent365_inventory_response,
    parse_agent365_package_detail,
)

AGENT365_USER_AGENT = "ets-gateway-microsoft-agent365/1.0"
AGENT365_MAXIMUM_TIMEOUT_SECONDS = 60.0
AGENT365_MAXIMUM_NEXT_LINK_CHARACTERS = 4096
AGENT365_MAXIMUM_PAGES = 1000
AGENT365_MAXIMUM_PACKAGES = 100_000


class MicrosoftAgent365ClientError(RuntimeError):
    """Base Agent 365 collector error without reusable credential material."""


class MicrosoftAgent365AuthenticationError(MicrosoftAgent365ClientError):
    """Raised when Microsoft Graph rejects the access token."""


class MicrosoftAgent365AuthorizationError(MicrosoftAgent365ClientError):
    """Raised when the token cannot read the Agent 365 package catalog."""


class MicrosoftAgent365ThrottleError(MicrosoftAgent365ClientError):
    """Raised when Microsoft Graph requests bounded retry behavior."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Microsoft Agent 365 package endpoint is rate limited")
        self.retry_after_seconds = max(1, retry_after_seconds)


class MicrosoftAgent365RetryableError(MicrosoftAgent365ClientError):
    """Raised for bounded transient source/network failures."""


class MicrosoftAgent365TerminalError(MicrosoftAgent365ClientError):
    """Raised for non-retryable source/transport failures."""


class MicrosoftAgent365RedirectError(MicrosoftAgent365TerminalError):
    """Raised when a credential-bearing Graph request attempts a redirect."""


class MicrosoftAgent365ResponseTooLargeError(MicrosoftAgent365TerminalError):
    """Raised when a Graph response exceeds the configured byte bound."""


class MicrosoftAgent365PaginationError(MicrosoftAgent365TerminalError):
    """Raised when a source-provided nextLink escapes the qualified boundary."""


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
        raise MicrosoftAgent365RedirectError(
            "Microsoft Graph redirects are disabled for credential-bearing Agent 365 requests"
        )


@dataclass(frozen=True, slots=True)
class MicrosoftAgent365HttpResponse:
    """Ephemeral exact response bytes plus source request metadata."""

    request_url: str
    body: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class MicrosoftAgent365InventoryAcquisition:
    response: MicrosoftAgent365HttpResponse
    envelope: MicrosoftSourceEnvelopeV1
    page: MicrosoftAgent365InventoryPageV1


@dataclass(frozen=True, slots=True)
class MicrosoftAgent365DetailAcquisition:
    response: MicrosoftAgent365HttpResponse
    envelope: MicrosoftSourceEnvelopeV1
    detail: MicrosoftAgent365PackageDetailV1


@dataclass(frozen=True, slots=True)
class MicrosoftAgent365InventorySnapshot:
    inventory_pages: tuple[MicrosoftAgent365InventoryAcquisition, ...]
    package_details: tuple[MicrosoftAgent365DetailAcquisition, ...]


class MicrosoftAgent365HttpClient:
    """Bounded read-only Graph client for Agent 365 package inventory and details."""

    def __init__(
        self,
        credential_material: bytes,
        *,
        api_version: Literal["v1.0", "beta"] = "v1.0",
        timeout_seconds: float = 30.0,
        maximum_response_bytes: int = AGENT365_DEFAULT_MAXIMUM_BODY_BYTES,
    ) -> None:
        if not credential_material:
            raise ValueError("Microsoft Graph credential material must not be empty")
        if not 0.1 <= timeout_seconds <= AGENT365_MAXIMUM_TIMEOUT_SECONDS:
            raise ValueError("timeout_seconds must be between 0.1 and 60")
        if not 1 <= maximum_response_bytes <= 64 * 1024 * 1024:
            raise ValueError("maximum_response_bytes exceeds the qualified Agent 365 bound")
        self._credential = bytearray(credential_material)
        self._api_version = api_version
        self._timeout_seconds = timeout_seconds
        self._maximum_response_bytes = maximum_response_bytes
        self._closed = False
        self._opener = build_opener(_RejectRedirects())

    @property
    def api_version(self) -> Literal["v1.0", "beta"]:
        return self._api_version

    def __repr__(self) -> str:
        return (
            "MicrosoftAgent365HttpClient(credential=<redacted>, "
            f"api_version={self._api_version!r})"
        )

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._credential)):
            self._credential[index] = 0
        self._closed = True

    def fetch_inventory(
        self,
        request_url: str | None = None,
    ) -> tuple[MicrosoftAgent365HttpResponse, MicrosoftAgent365InventoryPageV1]:
        if self._closed:
            raise MicrosoftAgent365ClientError("Microsoft Agent 365 client is closed")
        url = (
            agent365_packages_url(api_version=self._api_version)
            if request_url is None
            else validate_agent365_inventory_url(request_url, api_version=self._api_version)
        )
        response = self._fetch(url)
        try:
            page = parse_agent365_inventory_response(
                response.body,
                maximum_body_bytes=self._maximum_response_bytes,
            )
        except ValueError as exc:
            raise MicrosoftAgent365TerminalError(
                "Microsoft Agent 365 inventory response failed the qualified parser"
            ) from exc
        if page.next_link is not None:
            validate_agent365_inventory_url(page.next_link, api_version=self._api_version)
        return response, page

    def fetch_detail(
        self,
        package_id: str,
    ) -> tuple[MicrosoftAgent365HttpResponse, MicrosoftAgent365PackageDetailV1]:
        if self._closed:
            raise MicrosoftAgent365ClientError("Microsoft Agent 365 client is closed")
        url = agent365_package_detail_url(package_id, api_version=self._api_version)
        response = self._fetch(url)
        try:
            detail = parse_agent365_package_detail(
                response.body,
                maximum_body_bytes=self._maximum_response_bytes,
            )
        except ValueError as exc:
            raise MicrosoftAgent365TerminalError(
                "Microsoft Agent 365 package detail failed the qualified parser"
            ) from exc
        if detail.package.package_id != package_id:
            raise MicrosoftAgent365TerminalError(
                "Microsoft Agent 365 detail response package id does not match the request"
            )
        return response, detail

    def _fetch(self, url: str) -> MicrosoftAgent365HttpResponse:
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._credential_text()}",
                "User-Agent": AGENT365_USER_AGENT,
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as source_response:
                body = source_response.read(self._maximum_response_bytes + 1)
                if len(body) > self._maximum_response_bytes:
                    raise MicrosoftAgent365ResponseTooLargeError(
                        "Microsoft Agent 365 response exceeds configured byte bound"
                    )
                content_type = source_response.headers.get("Content-Type")
                _validate_json_content_type(content_type)
        except MicrosoftAgent365ClientError:
            raise
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise MicrosoftAgent365RetryableError(
                "Microsoft Agent 365 package request failed"
            ) from exc
        if content_type is None:  # pragma: no cover - guarded by validator
            raise MicrosoftAgent365RetryableError("Microsoft Graph omitted Content-Type")
        return MicrosoftAgent365HttpResponse(
            request_url=url,
            body=body,
            content_type=content_type,
        )

    def _credential_text(self) -> str:
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise MicrosoftAgent365AuthenticationError(
                "Microsoft Graph credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if 300 <= exc.code <= 399:
            raise MicrosoftAgent365RedirectError(
                "Microsoft Graph redirects are disabled"
            ) from exc
        if exc.code == 401:
            raise MicrosoftAgent365AuthenticationError(
                "Microsoft Graph access token was rejected"
            ) from exc
        if exc.code == 403:
            raise MicrosoftAgent365AuthorizationError(
                "Microsoft Graph denied Agent 365 package access"
            ) from exc
        if exc.code == 429:
            raise MicrosoftAgent365ThrottleError(
                _retry_after_seconds(exc.headers.get("Retry-After"))
            ) from exc
        if 500 <= exc.code <= 599:
            raise MicrosoftAgent365RetryableError(
                "Microsoft Agent 365 package endpoint returned a server error"
            ) from exc
        raise MicrosoftAgent365TerminalError(
            f"Microsoft Agent 365 package endpoint rejected request with HTTP {exc.code}"
        ) from exc


class MicrosoftAgent365LiveCollector:
    """Source-preserving in-memory acquisition chain; durable custody is a later Q0 gate."""

    def __init__(
        self,
        client: MicrosoftAgent365HttpClient,
        *,
        tenant_id: str,
        collector_identity: str,
        collector_version: str,
        payload_retention: Agent365PayloadRetention = "inline",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if payload_retention == "protected_reference":
            raise ValueError(
                "protected_reference retention requires a durable protected-payload store"
            )
        self._client = client
        self._tenant_id = tenant_id
        self._collector_identity = collector_identity
        self._collector_version = collector_version
        self._payload_retention = payload_retention
        self._clock = clock or _utc_now
        self._sequence = 0
        self._previous_envelope_hash: str | None = None

    def collect_inventory_page(
        self,
        request_url: str | None = None,
    ) -> MicrosoftAgent365InventoryAcquisition:
        response, page = self._client.fetch_inventory(request_url)
        envelope = self._envelope(
            response,
            source_type="agent365.package_inventory",
        )
        return MicrosoftAgent365InventoryAcquisition(
            response=response,
            envelope=envelope,
            page=page,
        )

    def collect_detail(self, package_id: str) -> MicrosoftAgent365DetailAcquisition:
        response, detail = self._client.fetch_detail(package_id)
        envelope = self._envelope(
            response,
            source_type="agent365.package_detail",
        )
        return MicrosoftAgent365DetailAcquisition(
            response=response,
            envelope=envelope,
            detail=detail,
        )

    def collect_snapshot(
        self,
        *,
        include_details: bool = True,
        maximum_pages: int = 100,
        maximum_packages: int = 10_000,
    ) -> MicrosoftAgent365InventorySnapshot:
        if not 1 <= maximum_pages <= AGENT365_MAXIMUM_PAGES:
            raise ValueError("maximum_pages is outside the qualified Agent 365 bound")
        if not 1 <= maximum_packages <= AGENT365_MAXIMUM_PACKAGES:
            raise ValueError("maximum_packages is outside the qualified Agent 365 bound")

        pages: list[MicrosoftAgent365InventoryAcquisition] = []
        package_ids: list[str] = []
        seen_package_ids: set[str] = set()
        seen_urls: set[str] = set()
        request_url: str | None = None

        while True:
            if len(pages) >= maximum_pages:
                raise MicrosoftAgent365PaginationError(
                    "Agent 365 inventory exceeded the configured page limit"
                )
            acquisition = self.collect_inventory_page(request_url)
            pages.append(acquisition)
            for package in acquisition.page.packages:
                if package.package_id not in seen_package_ids:
                    seen_package_ids.add(package.package_id)
                    package_ids.append(package.package_id)
                    if len(package_ids) > maximum_packages:
                        raise MicrosoftAgent365PaginationError(
                            "Agent 365 inventory exceeded the configured package limit"
                        )

            next_link = acquisition.page.next_link
            if next_link is None:
                break
            validated_next = validate_agent365_inventory_url(
                next_link,
                api_version=self._client.api_version,
            )
            if validated_next in seen_urls:
                raise MicrosoftAgent365PaginationError(
                    "Agent 365 inventory pagination contains a cycle"
                )
            seen_urls.add(validated_next)
            request_url = validated_next

        details: list[MicrosoftAgent365DetailAcquisition] = []
        if include_details:
            for package_id in package_ids:
                details.append(self.collect_detail(package_id))

        return MicrosoftAgent365InventorySnapshot(
            inventory_pages=tuple(pages),
            package_details=tuple(details),
        )

    def _envelope(
        self,
        response: MicrosoftAgent365HttpResponse,
        *,
        source_type: Literal["agent365.package_inventory", "agent365.package_detail"],
    ) -> MicrosoftSourceEnvelopeV1:
        maturity: Agent365ApiMaturity = (
            "stable" if self._client.api_version == "v1.0" else "beta"
        )
        envelope = build_source_envelope(
            response.body,
            source_type=source_type,
            tenant_id=self._tenant_id,
            acquisition_time=self._clock(),
            api_version=self._client.api_version,
            api_maturity=maturity,
            request_path=_request_path(response.request_url),
            collector_identity=self._collector_identity,
            collector_version=self._collector_version,
            acquisition_sequence=self._sequence,
            previous_envelope_hash=self._previous_envelope_hash,
            payload_retention=self._payload_retention,
        )
        self._sequence += 1
        self._previous_envelope_hash = envelope.envelope_hash
        return envelope


def validate_agent365_inventory_url(
    value: str,
    *,
    api_version: Literal["v1.0", "beta"],
) -> str:
    """Validate a source-provided inventory URL without rewriting it."""

    if not 1 <= len(value) <= AGENT365_MAXIMUM_NEXT_LINK_CHARACTERS:
        raise MicrosoftAgent365PaginationError(
            "Agent 365 inventory URL is outside the qualified length bound"
        )
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise MicrosoftAgent365PaginationError("Agent 365 inventory URL must use HTTPS")
    if parsed.hostname != "graph.microsoft.com":
        raise MicrosoftAgent365PaginationError(
            "Agent 365 inventory URL escaped the Microsoft Graph host"
        )
    if parsed.username is not None or parsed.password is not None:
        raise MicrosoftAgent365PaginationError(
            "Agent 365 inventory URL cannot contain user information"
        )
    if parsed.port not in {None, 443}:
        raise MicrosoftAgent365PaginationError(
            "Agent 365 inventory URL uses an unsupported port"
        )
    if parsed.fragment:
        raise MicrosoftAgent365PaginationError(
            "Agent 365 inventory URL cannot contain a fragment"
        )
    expected_path = f"/{api_version}/copilot/admin/catalog/packages"
    if parsed.path != expected_path:
        raise MicrosoftAgent365PaginationError(
            "Agent 365 inventory URL escaped the qualified collection path"
        )
    return value


def _validate_json_content_type(value: str | None) -> None:
    if value is None:
        raise MicrosoftAgent365RetryableError(
            "Microsoft Agent 365 response omitted Content-Type"
        )
    media_type = value.partition(";")[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise MicrosoftAgent365RetryableError(
            "Microsoft Agent 365 response Content-Type is not JSON"
        )


def _retry_after_seconds(value: str | None) -> int:
    if value is None:
        return 1
    try:
        parsed = int(value)
    except ValueError:
        return 1
    return max(1, min(parsed, 3600))


def _request_path(value: str) -> str:
    parsed = urlsplit(value)
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")


def _utc_now() -> datetime:
    return datetime.now(UTC)