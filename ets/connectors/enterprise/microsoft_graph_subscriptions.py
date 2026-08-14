"""Microsoft Graph subscription lifecycle client for G2E-B.

This module manages source operational state only. Subscription creation, renewal,
reauthorization, and deletion do not create ETS evidence or prove observation
continuity.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from email.message import Message
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_graph import (
    GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS,
    GRAPH_MAXIMUM_RESOURCE_CHARACTERS,
    MicrosoftGraphSubscriptionStateV1,
    hash_graph_client_state,
)

GRAPH_SUBSCRIPTION_MAXIMUM_RESPONSE_BYTES = 256 * 1024
GRAPH_SUBSCRIPTION_MAXIMUM_TIMEOUT_SECONDS = 60.0
GRAPH_SUBSCRIPTION_USER_AGENT = "ets-gateway-microsoft-graph-subscriptions/1.0"


class MicrosoftGraphSubscriptionClientError(RuntimeError):
    """Base subscription-management error without reusable credential material."""


class MicrosoftGraphSubscriptionAuthenticationError(MicrosoftGraphSubscriptionClientError):
    """Raised when Microsoft Graph rejects the access token."""


class MicrosoftGraphSubscriptionAuthorizationError(MicrosoftGraphSubscriptionClientError):
    """Raised when the token lacks subscription-management permission."""


class MicrosoftGraphSubscriptionThrottleError(MicrosoftGraphSubscriptionClientError):
    """Raised when Microsoft Graph requests bounded retry behavior."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Microsoft Graph subscription endpoint is rate limited")
        self.retry_after_seconds = max(1, retry_after_seconds)


class MicrosoftGraphSubscriptionRetryableError(MicrosoftGraphSubscriptionClientError):
    """Raised for bounded transient network/source failures."""


class MicrosoftGraphSubscriptionTerminalError(MicrosoftGraphSubscriptionClientError):
    """Raised for non-retryable subscription-management failures."""


class MicrosoftGraphSubscriptionRedirectError(MicrosoftGraphSubscriptionTerminalError):
    """Raised when a credential-bearing Graph request attempts a redirect."""


class MicrosoftGraphSubscriptionResponseTooLargeError(
    MicrosoftGraphSubscriptionTerminalError
):
    """Raised when a Graph subscription response exceeds the qualified byte bound."""


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
        raise MicrosoftGraphSubscriptionRedirectError(
            "Microsoft Graph redirects are disabled for credential-bearing subscription requests"
        )


class MicrosoftGraphSubscriptionHttpClient:
    """Bounded v1.0 subscription-management client for one qualified Microsoft cloud."""

    def __init__(
        self,
        tenant_profile: MicrosoftTenantProfileV1,
        credential_material: bytes,
        *,
        notification_url: str,
        lifecycle_notification_url: str | None = None,
        timeout_seconds: float = 30.0,
        maximum_response_bytes: int = GRAPH_SUBSCRIPTION_MAXIMUM_RESPONSE_BYTES,
    ) -> None:
        if not credential_material:
            raise ValueError("Microsoft Graph credential material must not be empty")
        if not 0.1 <= timeout_seconds <= GRAPH_SUBSCRIPTION_MAXIMUM_TIMEOUT_SECONDS:
            raise ValueError("Microsoft Graph timeout_seconds must be between 0.1 and 60")
        if not 1 <= maximum_response_bytes <= GRAPH_SUBSCRIPTION_MAXIMUM_RESPONSE_BYTES:
            raise ValueError(
                "Microsoft Graph maximum_response_bytes exceeds the qualified bound"
            )
        self._tenant_profile = tenant_profile
        self._graph_root = tenant_profile.endpoints.graph_root
        self._notification_url = _validate_webhook_url(notification_url)
        self._lifecycle_notification_url = (
            _validate_webhook_url(lifecycle_notification_url)
            if lifecycle_notification_url is not None
            else None
        )
        self._credential = bytearray(credential_material)
        self._timeout_seconds = timeout_seconds
        self._maximum_response_bytes = maximum_response_bytes
        self._closed = False
        self._opener = build_opener(_RejectRedirects())

    def __repr__(self) -> str:
        return (
            "MicrosoftGraphSubscriptionHttpClient(credential=<redacted>, "
            f"cloud={self._tenant_profile.cloud!r})"
        )

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._credential)):
            self._credential[index] = 0
        self._closed = True

    def create(
        self,
        *,
        resource: str,
        change_type: str,
        expiration_date_time: datetime,
        client_state: str,
    ) -> MicrosoftGraphSubscriptionStateV1:
        resource = _validate_resource(resource)
        change_type = _validate_change_type(change_type)
        expiration = _normalize_expiration(expiration_date_time)
        client_state_hash = hash_graph_client_state(client_state)
        body: dict[str, object] = {
            "changeType": change_type,
            "notificationUrl": self._notification_url,
            "resource": resource,
            "expirationDateTime": _format_utc(expiration),
            "clientState": client_state,
            "latestSupportedTlsVersion": "v1_2",
        }
        if self._lifecycle_notification_url is not None:
            body["lifecycleNotificationUrl"] = self._lifecycle_notification_url
        response_body = self._request_json(
            "POST",
            self._subscriptions_url,
            body=body,
            expected_status=201,
        )
        return _subscription_state_from_response(
            response_body,
            tenant_profile=self._tenant_profile,
            expected_resource=resource,
            expected_client_state_sha256=client_state_hash,
            status="active",
            gap_state="none",
        )

    def renew(
        self,
        subscription: MicrosoftGraphSubscriptionStateV1,
        *,
        expiration_date_time: datetime,
    ) -> MicrosoftGraphSubscriptionStateV1:
        self._validate_state(subscription)
        expiration = _normalize_expiration(expiration_date_time)
        response_body = self._request_json(
            "PATCH",
            self._subscription_url(subscription.subscription_id),
            body={"expirationDateTime": _format_utc(expiration)},
            expected_status=200,
        )
        updated = _subscription_state_from_response(
            response_body,
            tenant_profile=self._tenant_profile,
            expected_resource=subscription.resource,
            expected_client_state_sha256=subscription.client_state_sha256,
            status="active",
            gap_state=subscription.gap_state,
        )
        if updated.subscription_id != subscription.subscription_id:
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph renewal changed subscription identity"
            )
        return updated

    def reauthorize(
        self,
        subscription: MicrosoftGraphSubscriptionStateV1,
    ) -> MicrosoftGraphSubscriptionStateV1:
        self._validate_state(subscription)
        self._request_no_content(
            "POST",
            self._subscription_url(subscription.subscription_id) + "/reauthorize",
        )
        return subscription.model_copy(update={"status": "active"})

    def delete(self, subscription: MicrosoftGraphSubscriptionStateV1) -> None:
        self._validate_state(subscription)
        self._request_no_content(
            "DELETE",
            self._subscription_url(subscription.subscription_id),
        )

    def _validate_state(self, subscription: MicrosoftGraphSubscriptionStateV1) -> None:
        if subscription.tenant_id.casefold() != self._tenant_profile.tenant_id.casefold():
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription tenant does not match configured tenant"
            )
        if subscription.cloud != self._tenant_profile.cloud:
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription cloud does not match configured cloud"
            )

    @property
    def _subscriptions_url(self) -> str:
        return f"{self._graph_root}/v1.0/subscriptions"

    def _subscription_url(self, subscription_id: str) -> str:
        if not 1 <= len(subscription_id) <= 200:
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription identifier is invalid"
            )
        return f"{self._subscriptions_url}/{quote(subscription_id, safe='')}"

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, object],
        expected_status: int,
    ) -> dict[str, object]:
        response_body = self._request(
            method,
            url,
            body=body,
            expected_status=expected_status,
            expect_json=True,
        )
        if response_body is None:  # pragma: no cover - guarded by expect_json
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription response body is missing"
            )
        return response_body

    def _request_no_content(self, method: str, url: str) -> None:
        self._request(
            method,
            url,
            body=None,
            expected_status=204,
            expect_json=False,
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, object] | None,
        expected_status: int,
        expect_json: bool,
    ) -> dict[str, object] | None:
        if self._closed:
            raise MicrosoftGraphSubscriptionClientError(
                "Microsoft Graph subscription client is closed"
            )
        _validate_graph_management_url(self._graph_root, url)
        data = (
            json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
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
                "User-Agent": GRAPH_SUBSCRIPTION_USER_AGENT,
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                status_code = response.getcode()
                if status_code != expected_status:
                    raise MicrosoftGraphSubscriptionTerminalError(
                        "Microsoft Graph subscription endpoint returned an unexpected success code"
                    )
                raw = response.read(self._maximum_response_bytes + 1)
                if len(raw) > self._maximum_response_bytes:
                    raise MicrosoftGraphSubscriptionResponseTooLargeError(
                        "Microsoft Graph subscription response exceeds configured byte bound"
                    )
                if not expect_json:
                    if raw:
                        raise MicrosoftGraphSubscriptionTerminalError(
                            "Microsoft Graph no-content operation returned an unexpected body"
                        )
                    return None
                _validate_json_content_type(response.headers.get("Content-Type"))
        except MicrosoftGraphSubscriptionClientError:
            raise
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise MicrosoftGraphSubscriptionRetryableError(
                "Microsoft Graph subscription request failed"
            ) from exc

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription response is not valid JSON"
            ) from exc
        if not isinstance(decoded, dict):
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription response must be an object"
            )
        return decoded

    def _credential_text(self) -> str:
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise MicrosoftGraphSubscriptionAuthenticationError(
                "Microsoft Graph credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if 300 <= exc.code <= 399:
            raise MicrosoftGraphSubscriptionRedirectError(
                "Microsoft Graph redirects are disabled"
            ) from exc
        if exc.code == 401:
            raise MicrosoftGraphSubscriptionAuthenticationError(
                "Microsoft Graph access token was rejected"
            ) from exc
        if exc.code == 403:
            raise MicrosoftGraphSubscriptionAuthorizationError(
                "Microsoft Graph subscription access was denied"
            ) from exc
        if exc.code == 404:
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription does not exist"
            ) from exc
        if exc.code == 429:
            raise MicrosoftGraphSubscriptionThrottleError(
                _retry_after_seconds(exc.headers.get("Retry-After"))
            ) from exc
        if 500 <= exc.code <= 599:
            raise MicrosoftGraphSubscriptionRetryableError(
                "Microsoft Graph subscription endpoint returned a server error"
            ) from exc
        raise MicrosoftGraphSubscriptionTerminalError(
            f"Microsoft Graph subscription endpoint rejected request with HTTP {exc.code}"
        ) from exc


def _subscription_state_from_response(
    raw: dict[str, object],
    *,
    tenant_profile: MicrosoftTenantProfileV1,
    expected_resource: str,
    expected_client_state_sha256: str,
    status: str,
    gap_state: str,
) -> MicrosoftGraphSubscriptionStateV1:
    subscription_id = _required_string(raw, "id", 200)
    resource = _required_string(raw, "resource", GRAPH_MAXIMUM_RESOURCE_CHARACTERS)
    if resource != expected_resource:
        raise MicrosoftGraphSubscriptionTerminalError(
            "Microsoft Graph subscription response changed the configured resource"
        )
    client_state = raw.get("clientState")
    if client_state is not None:
        if (
            not isinstance(client_state, str)
            or not 1 <= len(client_state) <= GRAPH_MAXIMUM_CLIENT_STATE_CHARACTERS
            or hash_graph_client_state(client_state) != expected_client_state_sha256
        ):
            raise MicrosoftGraphSubscriptionTerminalError(
                "Microsoft Graph subscription response clientState does not match"
            )
    expiration = _parse_datetime(
        _required_string(raw, "expirationDateTime", 100),
        "expirationDateTime",
    )
    return MicrosoftGraphSubscriptionStateV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_subscription_state.v1",
            "subscription_id": subscription_id,
            "tenant_id": tenant_profile.tenant_id,
            "cloud": tenant_profile.cloud,
            "resource": resource,
            "client_state_sha256": expected_client_state_sha256,
            "expiration_date_time": expiration,
            "status": status,
            "gap_state": gap_state,
        }
    )


def _validate_graph_management_url(graph_root: str, value: str) -> None:
    root = urlsplit(graph_root)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != root.hostname:
        raise MicrosoftGraphSubscriptionTerminalError(
            "Microsoft Graph management request changed the qualified Graph origin"
        )
    if parsed.port not in {None, 443}:
        raise MicrosoftGraphSubscriptionTerminalError(
            "Microsoft Graph management request changed the qualified Graph port"
        )
    if not parsed.path.startswith("/v1.0/subscriptions"):
        raise MicrosoftGraphSubscriptionTerminalError(
            "Microsoft Graph management request changed the qualified subscription path"
        )
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise MicrosoftGraphSubscriptionTerminalError(
            "Microsoft Graph management request contains unsupported URL components"
        )


def _validate_webhook_url(value: str) -> str:
    if not 1 <= len(value) <= 2000:
        raise ValueError("Microsoft Graph webhook URL length is invalid")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Microsoft Graph webhook URL must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise ValueError("Microsoft Graph webhook URL contains unsupported components")
    return value


def _validate_resource(value: str) -> str:
    if not 1 <= len(value) <= GRAPH_MAXIMUM_RESOURCE_CHARACTERS:
        raise ValueError("Microsoft Graph subscription resource length is invalid")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError("Microsoft Graph subscription resource contains control data")
    return value


def _validate_change_type(value: str) -> str:
    parts = [part.strip() for part in value.split(",")]
    if not parts or any(part not in {"created", "updated", "deleted"} for part in parts):
        raise ValueError("Microsoft Graph subscription changeType is invalid")
    if len(set(parts)) != len(parts):
        raise ValueError("Microsoft Graph subscription changeType contains duplicates")
    return ",".join(parts)


def _normalize_expiration(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Microsoft Graph subscription expiration must be timezone-aware")
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str, field_name: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MicrosoftGraphSubscriptionTerminalError(
            f"Microsoft Graph subscription {field_name} is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MicrosoftGraphSubscriptionTerminalError(
            f"Microsoft Graph subscription {field_name} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def _required_string(raw: dict[str, object], key: str, maximum: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise MicrosoftGraphSubscriptionTerminalError(
            f"Microsoft Graph subscription response {key} is invalid"
        )
    return value


def _validate_json_content_type(value: str | None) -> None:
    if value is None:
        raise MicrosoftGraphSubscriptionRetryableError(
            "Microsoft Graph subscription response omitted Content-Type"
        )
    media_type = value.partition(";")[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise MicrosoftGraphSubscriptionRetryableError(
            "Microsoft Graph subscription response Content-Type is not JSON"
        )


def _retry_after_seconds(value: str | None) -> int:
    if value is None:
        return 1
    try:
        parsed = int(value)
    except ValueError:
        return 1
    return max(1, min(parsed, 3600))
