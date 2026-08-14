"""Credential-safe Microsoft Purview Management Activity HTTP transport for G2E-E."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewContentDescriptorV1,
    MicrosoftPurviewDiscoveryPageV1,
    MicrosoftPurviewManagementProfile,
    PurviewContentType,
    build_purview_content_list_url,
    parse_purview_discovery_page,
    validate_purview_next_page_uri,
)
from ets.connectors.enterprise.microsoft_purview_audit import (
    MicrosoftPurviewAuditContentV1,
    parse_purview_audit_content,
)

PURVIEW_HTTP_MAXIMUM_TIMEOUT_SECONDS = 60.0
PURVIEW_HTTP_MAXIMUM_DISCOVERY_BYTES = 2 * 1024 * 1024
PURVIEW_HTTP_MAXIMUM_CONTENT_BYTES = 16 * 1024 * 1024
PURVIEW_HTTP_USER_AGENT = "ets-gateway-microsoft-purview-activity/1.0"


class MicrosoftPurviewClientError(RuntimeError):
    """Base Purview transport error without reusable credential material."""


class MicrosoftPurviewAuthenticationError(MicrosoftPurviewClientError):
    """Raised when Microsoft rejects the access token."""


class MicrosoftPurviewAuthorizationError(MicrosoftPurviewClientError):
    """Raised when the token lacks Management Activity permission."""


class MicrosoftPurviewThrottleError(MicrosoftPurviewClientError):
    """Raised when the Management Activity API requests bounded retry behavior."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Microsoft Purview Management Activity API is rate limited")
        self.retry_after_seconds = max(1, retry_after_seconds)


class MicrosoftPurviewRetryableError(MicrosoftPurviewClientError):
    """Raised for bounded transient Management Activity failures."""


class MicrosoftPurviewTerminalError(MicrosoftPurviewClientError):
    """Raised for non-retryable Management Activity failures."""


class MicrosoftPurviewRedirectError(MicrosoftPurviewTerminalError):
    """Raised when a credential-bearing Purview request attempts a redirect."""


class MicrosoftPurviewResponseTooLargeError(MicrosoftPurviewTerminalError):
    """Raised when a Management Activity response exceeds its qualified bound."""


@dataclass(frozen=True, slots=True)
class MicrosoftPurviewSubscriptionStateV1:
    """Operational subscription state; never part of ETS canonical evidence."""

    content_type: PurviewContentType
    status: str
    webhook_status: str | None


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
        raise MicrosoftPurviewRedirectError(
            "Purview redirects are disabled for credential-bearing requests"
        )


class MicrosoftPurviewActivityHttpClient:
    """Bounded Management Activity client for one server-owned tenant/plan profile."""

    def __init__(
        self,
        profile: MicrosoftPurviewManagementProfile,
        credential_material: bytes,
        *,
        timeout_seconds: float = 30.0,
        maximum_discovery_bytes: int = PURVIEW_HTTP_MAXIMUM_DISCOVERY_BYTES,
        maximum_content_bytes: int = PURVIEW_HTTP_MAXIMUM_CONTENT_BYTES,
    ) -> None:
        if not credential_material:
            raise ValueError("Purview credential material must not be empty")
        if not 0.1 <= timeout_seconds <= PURVIEW_HTTP_MAXIMUM_TIMEOUT_SECONDS:
            raise ValueError("Purview timeout_seconds must be between 0.1 and 60")
        if not 1 <= maximum_discovery_bytes <= PURVIEW_HTTP_MAXIMUM_DISCOVERY_BYTES:
            raise ValueError("Purview maximum_discovery_bytes exceeds qualified bound")
        if not 1 <= maximum_content_bytes <= PURVIEW_HTTP_MAXIMUM_CONTENT_BYTES:
            raise ValueError("Purview maximum_content_bytes exceeds qualified bound")
        self._profile = profile
        self._credential = bytearray(credential_material)
        self._timeout_seconds = timeout_seconds
        self._maximum_discovery_bytes = maximum_discovery_bytes
        self._maximum_content_bytes = maximum_content_bytes
        self._closed = False
        self._opener = build_opener(_RejectRedirects())

    def __repr__(self) -> str:
        return (
            "MicrosoftPurviewActivityHttpClient(credential=<redacted>, "
            f"plan={self._profile.plan!r})"
        )

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._credential)):
            self._credential[index] = 0
        self._closed = True

    def start_subscription(
        self,
        content_type: PurviewContentType,
        *,
        webhook_address: str | None = None,
        webhook_auth_id: str | None = None,
        webhook_expiration_utc: datetime | None = None,
    ) -> MicrosoftPurviewSubscriptionStateV1:
        body: dict[str, object] | None = None
        if webhook_address is not None:
            if not webhook_address.startswith("https://") or len(webhook_address) > 2000:
                raise ValueError("Purview webhook address must be a bounded HTTPS URL")
            webhook: dict[str, object] = {"address": webhook_address}
            if webhook_auth_id is not None:
                if not 1 <= len(webhook_auth_id) <= 500:
                    raise ValueError("Purview webhook authId is outside the qualified bound")
                webhook["authId"] = webhook_auth_id
            if webhook_expiration_utc is not None:
                if (
                    webhook_expiration_utc.tzinfo is None
                    or webhook_expiration_utc.utcoffset() is None
                ):
                    raise ValueError("Purview webhook expiration must be timezone-aware")
                webhook["expiration"] = (
                    webhook_expiration_utc.isoformat().replace("+00:00", "Z")
                )
            body = {"webhook": webhook}
        elif webhook_auth_id is not None or webhook_expiration_utc is not None:
            raise ValueError("Purview webhook authId/expiration require a webhook address")

        raw = self._request_json(
            "POST",
            self._subscription_url("start", content_type),
            body=body,
            maximum_bytes=self._maximum_discovery_bytes,
        )
        if not isinstance(raw, dict):
            raise MicrosoftPurviewTerminalError(
                "Purview subscription start response must be a JSON object"
            )
        return _subscription_state(raw, content_type)

    def stop_subscription(self, content_type: PurviewContentType) -> None:
        raw = self._request_bytes(
            "POST",
            self._subscription_url("stop", content_type),
            body=None,
            maximum_bytes=self._maximum_discovery_bytes,
            accept_json=False,
        )
        if raw:
            raise MicrosoftPurviewTerminalError(
                "Purview subscription stop returned an unexpected response body"
            )

    def list_content(
        self,
        content_type: PurviewContentType,
        *,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        next_page_uri: str | None = None,
    ) -> MicrosoftPurviewDiscoveryPageV1:
        if next_page_uri is not None:
            if start_time_utc is not None or end_time_utc is not None:
                raise ValueError("Purview next-page replay must not rebuild the time window")
            url = validate_purview_next_page_uri(
                self._profile,
                content_type,
                next_page_uri,
            )
        else:
            url = build_purview_content_list_url(
                self._profile,
                content_type,
                start_time_utc=start_time_utc,
                end_time_utc=end_time_utc,
            )
        raw, headers = self._request_json_with_headers(
            "GET",
            url,
            body=None,
            maximum_bytes=self._maximum_discovery_bytes,
        )
        next_page = headers.get("NextPageUri")
        return parse_purview_discovery_page(
            raw,
            self._profile,
            content_type,
            discovery_source="poll",
            next_page_uri=next_page,
        )

    def retrieve_content(
        self,
        descriptor: MicrosoftPurviewContentDescriptorV1,
        *,
        service_specific_allowlist: frozenset[str] = frozenset(),
        include_client_ip: bool = False,
    ) -> MicrosoftPurviewAuditContentV1:
        from ets.connectors.enterprise.microsoft_purview_activity import (
            validate_purview_content_uri,
        )

        url = validate_purview_content_uri(self._profile, descriptor.content_uri)
        body = self._request_bytes(
            "GET",
            url,
            body=None,
            maximum_bytes=self._maximum_content_bytes,
            accept_json=True,
        )
        return parse_purview_audit_content(
            body,
            descriptor,
            self._profile,
            service_specific_allowlist=service_specific_allowlist,
            include_client_ip=include_client_ip,
            maximum_body_bytes=self._maximum_content_bytes,
        )

    def _subscription_url(self, operation: str, content_type: PurviewContentType) -> str:
        tenant_id = self._profile.tenant_profile.tenant_id
        root = (
            f"{self._profile.management_root}/api/v1.0/{tenant_id}/activity/feed/"
            f"subscriptions/{operation}"
        )
        query = urlencode(
            {
                "contentType": content_type,
                "PublisherIdentifier": self._profile.publisher_identifier,
            }
        )
        return f"{root}?{query}"

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, object] | None,
        maximum_bytes: int,
    ) -> object:
        decoded, _ = self._request_json_with_headers(
            method,
            url,
            body=body,
            maximum_bytes=maximum_bytes,
        )
        return decoded

    def _request_json_with_headers(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, object] | None,
        maximum_bytes: int,
    ) -> tuple[object, Message]:
        raw, headers = self._request(
            method,
            url,
            body=body,
            maximum_bytes=maximum_bytes,
            accept_json=True,
        )
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MicrosoftPurviewTerminalError(
                "Purview response is not valid UTF-8 JSON"
            ) from exc
        return decoded, headers

    def _request_bytes(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, object] | None,
        maximum_bytes: int,
        accept_json: bool,
    ) -> bytes:
        raw, _ = self._request(
            method,
            url,
            body=body,
            maximum_bytes=maximum_bytes,
            accept_json=accept_json,
        )
        return raw

    def _request(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, object] | None,
        maximum_bytes: int,
        accept_json: bool,
    ) -> tuple[bytes, Message]:
        if self._closed:
            raise MicrosoftPurviewClientError("Purview client is closed")
        data = (
            json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            if body is not None
            else None
        )
        request = Request(
            url,
            method=method,
            data=data,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._credential_text()}",
                "User-Agent": PURVIEW_HTTP_USER_AGENT,
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                raw = response.read(maximum_bytes + 1)
                if len(raw) > maximum_bytes:
                    raise MicrosoftPurviewResponseTooLargeError(
                        "Purview response exceeds configured byte bound"
                    )
                headers = response.headers
                if accept_json and raw:
                    _validate_json_content_type(headers.get("Content-Type"))
        except MicrosoftPurviewClientError:
            raise
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise MicrosoftPurviewRetryableError("Purview request failed") from exc
        return raw, headers

    def _credential_text(self) -> str:
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise MicrosoftPurviewAuthenticationError(
                "Purview credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if 300 <= exc.code <= 399:
            raise MicrosoftPurviewRedirectError(
                "Purview redirects are disabled"
            ) from exc
        if exc.code == 401:
            raise MicrosoftPurviewAuthenticationError(
                "Purview access token was rejected"
            ) from exc
        if exc.code == 403:
            raise MicrosoftPurviewAuthorizationError(
                "Purview Management Activity access was denied"
            ) from exc
        if exc.code == 429:
            raise MicrosoftPurviewThrottleError(
                _retry_after_seconds(exc.headers.get("Retry-After"))
            ) from exc
        if 500 <= exc.code <= 599:
            raise MicrosoftPurviewRetryableError(
                "Purview Management Activity endpoint returned a server error"
            ) from exc
        raise MicrosoftPurviewTerminalError(
            f"Purview Management Activity endpoint rejected request with HTTP {exc.code}"
        ) from exc


def _subscription_state(
    raw: dict[str, object],
    expected_content_type: PurviewContentType,
) -> MicrosoftPurviewSubscriptionStateV1:
    if raw.get("contentType") != expected_content_type:
        raise MicrosoftPurviewTerminalError(
            "Purview subscription response changed the requested content type"
        )
    status = raw.get("status")
    if not isinstance(status, str) or not status:
        raise MicrosoftPurviewTerminalError("Purview subscription response status is invalid")
    webhook_status: str | None = None
    webhook = raw.get("webhook")
    if webhook is not None:
        if not isinstance(webhook, dict):
            raise MicrosoftPurviewTerminalError(
                "Purview subscription response webhook state is invalid"
            )
        candidate = webhook.get("status")
        if candidate is not None:
            if not isinstance(candidate, str) or not candidate:
                raise MicrosoftPurviewTerminalError(
                    "Purview subscription webhook status is invalid"
                )
            webhook_status = candidate
    return MicrosoftPurviewSubscriptionStateV1(
        content_type=expected_content_type,
        status=status,
        webhook_status=webhook_status,
    )


def _validate_json_content_type(value: str | None) -> None:
    if value is None:
        raise MicrosoftPurviewRetryableError("Purview response omitted Content-Type")
    media_type = value.partition(";")[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise MicrosoftPurviewRetryableError("Purview response Content-Type is not JSON")


def _retry_after_seconds(value: str | None) -> int:
    if value is None:
        return 1
    try:
        parsed = int(value)
    except ValueError:
        return 1
    return max(1, min(parsed, 3600))
