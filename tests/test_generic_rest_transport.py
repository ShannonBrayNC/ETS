from __future__ import annotations

from email.message import Message
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from ets.connectors.generic.rest import (
    GenericRestAuthenticationError,
    GenericRestAuthorizationError,
    GenericRestHostPolicy,
    GenericRestHttpClient,
    GenericRestRedirectError,
    GenericRestRequestProfile,
    GenericRestResponseTooLargeError,
    GenericRestRetryableError,
    GenericRestTerminalError,
    GenericRestThrottleError,
)


class FixtureResponse:
    def __init__(self, body: bytes, *, headers: dict[str, str] | None = None) -> None:
        self.body = body
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def read(self, amount: int = -1) -> bytes:
        return self.body if amount < 0 else self.body[:amount]

    def __enter__(self) -> FixtureResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FixtureOpener:
    def __init__(self, response: FixtureResponse | Exception) -> None:
        self.response = response
        self.requests: list[Request] = []
        self.timeouts: list[float] = []

    def open(self, request: Request, *, timeout: float) -> FixtureResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _policy() -> GenericRestHostPolicy:
    return GenericRestHostPolicy(frozenset({"api.example.test"}))


def _profile(**overrides: Any) -> GenericRestRequestProfile:
    values: dict[str, Any] = {
        "endpoint_url": "https://api.example.test/v1/events",
        "timeout_seconds": 12.5,
        "max_response_bytes": 1024,
        "headers": {"X-Source-Profile": "audit"},
        "query": {"limit": "100"},
    }
    values.update(overrides)
    return GenericRestRequestProfile(**values)


def _client(
    response: FixtureResponse | Exception,
    *,
    profile: GenericRestRequestProfile | None = None,
    credential: bytes | None = b"fixture-token",
) -> tuple[GenericRestHttpClient, FixtureOpener]:
    client = GenericRestHttpClient(
        profile or _profile(),
        _policy(),
        credential_material=credential,
    )
    opener = FixtureOpener(response)
    client._opener = opener  # type: ignore[assignment]
    return client, opener


def _http_error(code: int, *, headers: dict[str, str] | None = None) -> HTTPError:
    message = Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return HTTPError(
        "https://api.example.test/v1/events",
        code,
        "fixture",
        message,
        None,
    )


def test_server_host_policy_requires_exact_https_host() -> None:
    policy = _policy()

    assert policy.authorize("https://api.example.test/v1/events") == "api.example.test"

    with pytest.raises(ValueError, match="HTTPS"):
        policy.authorize("http://api.example.test/v1/events")
    with pytest.raises(ValueError, match="not authorized"):
        policy.authorize("https://attacker.invalid/v1/events")
    with pytest.raises(ValueError, match="user information"):
        policy.authorize("https://user@api.example.test/v1/events")
    with pytest.raises(ValueError, match="query belongs"):
        policy.authorize("https://api.example.test/v1/events?token=inline")
    with pytest.raises(ValueError, match="port 443"):
        policy.authorize("https://api.example.test:8443/v1/events")


def test_profile_rejects_sensitive_static_headers_and_query_values() -> None:
    with pytest.raises(ValueError, match="credential reference"):
        _profile(headers={"Authorization": "Bearer inline"})
    with pytest.raises(ValueError, match="credential reference"):
        _profile(query={"api_key": "inline"})


def test_profile_enforces_bounded_timeout_response_and_metadata_counts() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        _profile(timeout_seconds=61)
    with pytest.raises(ValueError, match="max_response_bytes"):
        _profile(max_response_bytes=20 * 1024 * 1024)
    with pytest.raises(ValueError, match="header count"):
        _profile(headers={f"X-{index}": "v" for index in range(65)})


def test_get_uses_bounded_query_headers_timeout_and_credential_authorization() -> None:
    client, opener = _client(
        FixtureResponse(
            b'{"items":[]}',
            headers={"Content-Type": "application/json", "ETag": '"abc"'},
        )
    )

    response = client.get()

    assert response.body == b'{"items":[]}'
    assert response.content_type == "application/json"
    assert response.etag == '"abc"'
    assert opener.timeouts == [12.5]
    request = opener.requests[0]
    assert request.full_url == "https://api.example.test/v1/events?limit=100"
    assert request.get_header("Authorization") == "Bearer fixture-token"
    assert request.get_header("X-source-profile") == "audit"


def test_unauthenticated_profile_never_invents_authorization_header() -> None:
    client, opener = _client(FixtureResponse(b"{}"), credential=None)

    client.get()

    assert opener.requests[0].get_header("Authorization") is None


def test_response_byte_bound_reads_plus_one_and_fails_closed() -> None:
    client, _ = _client(
        FixtureResponse(b"12345"),
        profile=_profile(max_response_bytes=4),
    )

    with pytest.raises(GenericRestResponseTooLargeError):
        client.get()


def test_http_statuses_map_without_advancing_source_semantics() -> None:
    cases = (
        (401, {}, GenericRestAuthenticationError),
        (403, {}, GenericRestAuthorizationError),
        (302, {"Location": "https://attacker.invalid"}, GenericRestRedirectError),
        (500, {}, GenericRestRetryableError),
        (418, {}, GenericRestTerminalError),
    )
    for code, headers, expected in cases:
        client, _ = _client(_http_error(code, headers=headers))
        with pytest.raises(expected):
            client.get()


def test_rate_limit_retry_after_is_bounded() -> None:
    client, _ = _client(_http_error(429, headers={"Retry-After": "9000"}))

    with pytest.raises(GenericRestThrottleError) as exc_info:
        client.get()

    assert exc_info.value.retry_after_seconds == 3600


def test_client_representation_redacts_and_close_zeroizes_credential_copy() -> None:
    client, _ = _client(FixtureResponse(b"{}"))

    assert "fixture-token" not in repr(client)
    credential = client._credential
    assert credential is not None
    assert bytes(credential) == b"fixture-token"

    client.close()

    assert bytes(credential) == b"\x00" * len(b"fixture-token")
    with pytest.raises(RuntimeError, match="closed"):
        client.get()
