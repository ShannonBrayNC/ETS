from __future__ import annotations

import json
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_sharepoint_delta import (
    sharepoint_drive_delta_request_profile,
)
from ets.connectors.enterprise.microsoft_sharepoint_http import (
    MicrosoftSharePointDeltaAuthenticationError,
    MicrosoftSharePointDeltaAuthorizationError,
    MicrosoftSharePointDeltaHttpClient,
    MicrosoftSharePointDeltaResponseTooLargeError,
    MicrosoftSharePointDeltaStateExpiredError,
    MicrosoftSharePointDeltaThrottleError,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
TOKEN = b"fixture-sharepoint-token"


class FixtureResponse:
    def __init__(self, body: bytes, *, content_type: str = "application/json") -> None:
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self, maximum: int) -> bytes:
        return self._body[:maximum]

    def __enter__(self) -> FixtureResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FixtureOpener:
    def __init__(self, responses: list[FixtureResponse | Exception]) -> None:
        self._responses = list(responses)
        self.requests: list[Request] = []

    def open(self, request: Request, *, timeout: float) -> FixtureResponse:
        self.requests.append(request)
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _tenant_profile() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": "global",
            "credential_ref": CredentialReferenceV1(
                schema_version="ets.connector.credential_ref.v1",
                ref="fixture://microsoft/sharepoint-token",
            ).model_dump(mode="json"),
            "consent_state": "granted",
        }
    )


def _payload(state_link: str, *, terminal: bool = False) -> bytes:
    payload: dict[str, object] = {
        "value": [
            {
                "id": "item-001",
                "name": "report.docx",
                "lastModifiedDateTime": "2026-08-14T20:30:00Z",
                "webUrl": "https://contoso.sharepoint.com/raw-location",
            }
        ]
    }
    payload["@odata.deltaLink" if terminal else "@odata.nextLink"] = state_link
    return json.dumps(payload).encode("utf-8")


def _http_error(url: str, code: int, *, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(url, code, "fixture error", headers, None)


def test_sharepoint_http_uses_server_owned_initial_url_and_bearer_token() -> None:
    profile = sharepoint_drive_delta_request_profile("prod", _tenant_profile(), "drive-001")
    next_link = profile.initial_url + "?$skiptoken=opaque-1"
    opener = FixtureOpener([FixtureResponse(_payload(next_link))])
    client = MicrosoftSharePointDeltaHttpClient(profile, TOKEN, timeout_seconds=5)
    client._opener = opener

    page = client.fetch()

    assert page.checkpoint_url == next_link
    assert opener.requests[0].full_url == profile.initial_url
    assert opener.requests[0].get_header("Authorization") == f"Bearer {TOKEN.decode()}"
    assert TOKEN.decode() not in repr(client)


def test_sharepoint_http_replays_exact_source_cursor() -> None:
    profile = sharepoint_drive_delta_request_profile("prod", _tenant_profile(), "drive-001")
    cursor = profile.initial_url + "?$skiptoken=opaque%2Bstate%3D%3D"
    terminal = profile.initial_url + "?$deltatoken=terminal%2Fstate"
    opener = FixtureOpener([FixtureResponse(_payload(terminal, terminal=True))])
    client = MicrosoftSharePointDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    page = client.fetch(cursor)

    assert opener.requests[0].full_url == cursor
    assert page.checkpoint_url == terminal
    assert page.cycle_complete is True


def test_sharepoint_http_410_requires_explicit_resync_without_initial_fallback() -> None:
    profile = sharepoint_drive_delta_request_profile("prod", _tenant_profile(), "drive-001")
    expired = profile.initial_url + "?$deltatoken=expired"
    opener = FixtureOpener([_http_error(expired, 410)])
    client = MicrosoftSharePointDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(MicrosoftSharePointDeltaStateExpiredError) as exc_info:
        client.fetch(expired)

    assert exc_info.value.resync_required is True
    assert [request.full_url for request in opener.requests] == [expired]


def test_sharepoint_http_rejects_foreign_origin_before_sending_credentials() -> None:
    profile = sharepoint_drive_delta_request_profile("prod", _tenant_profile(), "drive-001")
    opener = FixtureOpener([])
    client = MicrosoftSharePointDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(ValueError, match="server-owned Graph origin"):
        client.fetch("https://evil.example/v1.0/drives/drive-001/root/delta?$skiptoken=x")

    assert opener.requests == []


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (401, MicrosoftSharePointDeltaAuthenticationError),
        (403, MicrosoftSharePointDeltaAuthorizationError),
    ],
)
def test_sharepoint_http_maps_authentication_and_authorization_failures(
    code: int,
    expected: type[Exception],
) -> None:
    profile = sharepoint_drive_delta_request_profile("prod", _tenant_profile(), "drive-001")
    opener = FixtureOpener([_http_error(profile.initial_url, code)])
    client = MicrosoftSharePointDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(expected):
        client.fetch()


def test_sharepoint_http_preserves_bounded_retry_after() -> None:
    profile = sharepoint_drive_delta_request_profile("prod", _tenant_profile(), "drive-001")
    opener = FixtureOpener([_http_error(profile.initial_url, 429, retry_after="120")])
    client = MicrosoftSharePointDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(MicrosoftSharePointDeltaThrottleError) as exc_info:
        client.fetch()

    assert exc_info.value.retry_after_seconds == 120


def test_sharepoint_http_response_limit_and_close_fail_closed() -> None:
    profile = sharepoint_drive_delta_request_profile("prod", _tenant_profile(), "drive-001")
    opener = FixtureOpener([FixtureResponse(b"{" + b"x" * 100 + b"}")])
    client = MicrosoftSharePointDeltaHttpClient(
        profile,
        TOKEN,
        maximum_response_bytes=32,
    )
    client._opener = opener

    with pytest.raises(MicrosoftSharePointDeltaResponseTooLargeError):
        client.fetch()

    client.close()
    assert bytes(client._credential) == b"\x00" * len(TOKEN)
    with pytest.raises(RuntimeError, match="client is closed"):
        client.fetch()
