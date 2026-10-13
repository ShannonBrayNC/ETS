from __future__ import annotations

import json
from datetime import UTC, datetime
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from ets.connectors.enterprise.microsoft_agent365_http import (
    MicrosoftAgent365AuthenticationError,
    MicrosoftAgent365AuthorizationError,
    MicrosoftAgent365HttpClient,
    MicrosoftAgent365LiveCollector,
    MicrosoftAgent365PaginationError,
    MicrosoftAgent365ResponseTooLargeError,
    MicrosoftAgent365RetryableError,
    MicrosoftAgent365TerminalError,
    MicrosoftAgent365ThrottleError,
    validate_agent365_inventory_url,
)

TENANT_ID = "11111111-2222-3333-4444-555555555555"
FIXED_TIME = datetime(2026, 9, 16, 16, 0, tzinfo=UTC)


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str | None = "application/json") -> None:
        self._body = body
        self.headers = Message()
        if content_type is not None:
            self.headers["Content-Type"] = content_type

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self._body
        return self._body[:size]


class _FakeOpener:
    def __init__(self, *results: _FakeResponse | BaseException) -> None:
        self._results = list(results)
        self.requests: list[Request] = []

    def open(self, request: Request, *, timeout: float) -> _FakeResponse:
        self.requests.append(request)
        if not self._results:
            raise AssertionError("unexpected request")
        result = self._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _client(*responses: _FakeResponse | BaseException, maximum_response_bytes: int = 1024 * 1024):
    client = MicrosoftAgent365HttpClient(
        b"test-token",
        maximum_response_bytes=maximum_response_bytes,
    )
    opener = _FakeOpener(*responses)
    client._opener = opener  # type: ignore[attr-defined]
    return client, opener


def _http_error(code: int, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages",
        code,
        "failure",
        headers,
        None,
    )


def test_inventory_url_accepts_source_next_link_without_rewriting() -> None:
    url = (
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages"
        "?$skiptoken=opaque%2Bvalue%3D"
    )
    assert validate_agent365_inventory_url(url, api_version="v1.0") == url


@pytest.mark.parametrize(
    "url",
    [
        "http://graph.microsoft.com/v1.0/copilot/admin/catalog/packages",
        "https://evil.example/v1.0/copilot/admin/catalog/packages",
        "https://graph.microsoft.com/beta/copilot/admin/catalog/packages",
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages/pkg-1",
        "https://user@graph.microsoft.com/v1.0/copilot/admin/catalog/packages",
        "https://graph.microsoft.com:444/v1.0/copilot/admin/catalog/packages",
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages#fragment",
    ],
)
def test_inventory_url_rejects_source_boundary_escape(url: str) -> None:
    with pytest.raises(MicrosoftAgent365PaginationError):
        validate_agent365_inventory_url(url, api_version="v1.0")


def test_fetch_inventory_is_read_only_and_preserves_exact_source_bytes() -> None:
    body = _json_bytes({"value": [{"id": "pkg-1", "displayName": "One"}]})
    client, opener = _client(_FakeResponse(body))

    response, page = client.fetch_inventory()

    assert response.body == body
    assert page.packages[0].package_id == "pkg-1"
    request = opener.requests[0]
    assert request.get_method() == "GET"
    assert request.data is None
    assert request.get_header("Authorization") == "Bearer test-token"
    assert request.get_header("Accept") == "application/json"


def test_fetch_inventory_rejects_untrusted_next_link_before_following_it() -> None:
    body = _json_bytes(
        {
            "value": [{"id": "pkg-1"}],
            "@odata.nextLink": "https://evil.example/v1.0/copilot/admin/catalog/packages?p=2",
        }
    )
    client, opener = _client(_FakeResponse(body))

    with pytest.raises(MicrosoftAgent365PaginationError):
        client.fetch_inventory()

    assert len(opener.requests) == 1


def test_fetch_detail_requires_response_id_to_match_requested_package() -> None:
    client, _ = _client(_FakeResponse(_json_bytes({"id": "pkg-other"})))

    with pytest.raises(MicrosoftAgent365TerminalError, match="does not match"):
        client.fetch_detail("pkg-1")


def test_live_snapshot_chains_inventory_pages_and_detail_fanout() -> None:
    next_link = (
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages?$skiptoken=page2"
    )
    page_one = _json_bytes(
        {
            "value": [{"id": "pkg-1", "displayName": "One"}],
            "@odata.nextLink": next_link,
        }
    )
    page_two = _json_bytes({"value": [{"id": "pkg-2", "displayName": "Two"}]})
    detail_one = _json_bytes({"id": "pkg-1", "displayName": "One", "longDescription": "A"})
    detail_two = _json_bytes({"id": "pkg-2", "displayName": "Two", "longDescription": "B"})
    client, opener = _client(
        _FakeResponse(page_one),
        _FakeResponse(page_two),
        _FakeResponse(detail_one),
        _FakeResponse(detail_two),
    )
    collector = MicrosoftAgent365LiveCollector(
        client,
        tenant_id=TENANT_ID,
        collector_identity="ets-agent365-q0-test",
        collector_version="1.0",
        clock=lambda: FIXED_TIME,
    )

    snapshot = collector.collect_snapshot()

    assert len(snapshot.inventory_pages) == 2
    assert len(snapshot.package_details) == 2
    acquisitions = (*snapshot.inventory_pages, *snapshot.package_details)
    assert [item.envelope.acquisition_sequence for item in acquisitions] == [0, 1, 2, 3]
    assert acquisitions[0].envelope.previous_envelope_hash is None
    for previous, current in zip(acquisitions[:-1], acquisitions[1:], strict=True):
        assert current.envelope.previous_envelope_hash == previous.envelope.envelope_hash
    assert snapshot.inventory_pages[0].envelope.raw_payload_utf8 == page_one.decode("utf-8")
    assert snapshot.package_details[1].detail.package.package_id == "pkg-2"
    assert [request.full_url for request in opener.requests] == [
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages",
        next_link,
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages/pkg-1",
        "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages/pkg-2",
    ]


def test_live_snapshot_detects_pagination_cycle() -> None:
    next_link = "https://graph.microsoft.com/v1.0/copilot/admin/catalog/packages?$skiptoken=same"
    page = _json_bytes({"value": [{"id": "pkg-1"}], "@odata.nextLink": next_link})
    client, _ = _client(_FakeResponse(page), _FakeResponse(page))
    collector = MicrosoftAgent365LiveCollector(
        client,
        tenant_id=TENANT_ID,
        collector_identity="collector",
        collector_version="1.0",
        clock=lambda: FIXED_TIME,
    )

    with pytest.raises(MicrosoftAgent365PaginationError, match="cycle"):
        collector.collect_snapshot(include_details=False)


def test_live_collector_digest_only_keeps_source_commitment_without_plaintext() -> None:
    body = _json_bytes({"value": [{"id": "pkg-1"}]})
    client, _ = _client(_FakeResponse(body))
    collector = MicrosoftAgent365LiveCollector(
        client,
        tenant_id=TENANT_ID,
        collector_identity="collector",
        collector_version="1.0",
        payload_retention="digest_only",
        clock=lambda: FIXED_TIME,
    )

    acquisition = collector.collect_inventory_page()

    assert acquisition.envelope.raw_payload_utf8 is None
    assert acquisition.envelope.raw_payload_sha256
    assert acquisition.response.body == body


def test_live_collector_requires_durable_store_for_protected_reference_mode() -> None:
    client, _ = _client()
    with pytest.raises(ValueError, match="durable protected-payload store"):
        MicrosoftAgent365LiveCollector(
            client,
            tenant_id=TENANT_ID,
            collector_identity="collector",
            collector_version="1.0",
            payload_retention="protected_reference",
        )


def test_client_repr_redacts_token_and_close_disables_reuse() -> None:
    client, _ = _client()
    assert "test-token" not in repr(client)
    assert "<redacted>" in repr(client)

    client.close()

    with pytest.raises(RuntimeError, match="closed"):
        client.fetch_inventory()


def test_response_size_limit_fails_closed() -> None:
    client, _ = _client(_FakeResponse(b"12345"), maximum_response_bytes=4)
    with pytest.raises(MicrosoftAgent365ResponseTooLargeError):
        client.fetch_inventory()


def test_non_json_content_type_is_retryable_source_failure() -> None:
    client, _ = _client(_FakeResponse(b"{}", content_type="text/html"))
    with pytest.raises(MicrosoftAgent365RetryableError, match="not JSON"):
        client.fetch_inventory()


@pytest.mark.parametrize(
    ("code", "exception_type"),
    [
        (401, MicrosoftAgent365AuthenticationError),
        (403, MicrosoftAgent365AuthorizationError),
        (500, MicrosoftAgent365RetryableError),
        (404, MicrosoftAgent365TerminalError),
    ],
)
def test_http_failures_are_classified_without_response_body(
    code: int,
    exception_type: type[Exception],
) -> None:
    client, _ = _client(_http_error(code))
    with pytest.raises(exception_type):
        client.fetch_inventory()


def test_throttle_exposes_bounded_retry_after() -> None:
    client, _ = _client(_http_error(429, retry_after="99999"))
    with pytest.raises(MicrosoftAgent365ThrottleError) as exc_info:
        client.fetch_inventory()
    assert exc_info.value.retry_after_seconds == 3600
