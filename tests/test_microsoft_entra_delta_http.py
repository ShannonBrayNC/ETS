from __future__ import annotations

import json
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_entra_delta import entra_delta_request_profile
from ets.connectors.enterprise.microsoft_entra_http import (
    MicrosoftEntraDeltaAuthenticationError,
    MicrosoftEntraDeltaAuthorizationError,
    MicrosoftEntraDeltaHttpClient,
    MicrosoftEntraDeltaResponseTooLargeError,
    MicrosoftEntraDeltaStateExpiredError,
    MicrosoftEntraDeltaThrottleError,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
TOKEN = b"fixture-graph-access-token"


class FixtureResponse:
    def __init__(
        self,
        body: bytes,
        *,
        content_type: str = "application/json",
    ) -> None:
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
        self.timeouts: list[float] = []

    def open(self, request: Request, *, timeout: float) -> FixtureResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _tenant_profile(*, cloud: str = "global") -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": cloud,
            "credential_ref": CredentialReferenceV1(
                schema_version="ets.connector.credential_ref.v1",
                ref="fixture://microsoft/entra-token",
            ).model_dump(mode="json"),
            "consent_state": "granted",
        }
    )


def _page_payload(
    *,
    state_link: str,
    terminal: bool = False,
) -> bytes:
    payload: dict[str, object] = {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
        "value": [
            {
                "id": "user-001",
                "accountEnabled": True,
                "userType": "Member",
                "displayName": "raw-name-must-not-survive",
            }
        ],
    }
    payload["@odata.deltaLink" if terminal else "@odata.nextLink"] = state_link
    return json.dumps(payload).encode("utf-8")


def _http_error(url: str, code: int, *, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(url, code, "fixture error", headers, None)


def test_entra_http_client_uses_server_owned_initial_url_and_bearer_token() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    next_link = f"{profile.initial_url}?$skiptoken=opaque-1"
    opener = FixtureOpener([FixtureResponse(_page_payload(state_link=next_link))])
    client = MicrosoftEntraDeltaHttpClient(profile, TOKEN, timeout_seconds=5)
    client._opener = opener

    page = client.fetch()

    assert page.next_link == next_link
    assert opener.requests[0].full_url == profile.initial_url
    assert opener.requests[0].get_header("Authorization") == f"Bearer {TOKEN.decode()}"
    assert opener.timeouts == [5]
    assert TOKEN.decode() not in repr(client)


def test_entra_http_client_replays_exact_source_cursor_without_rebuilding_query() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    cursor = f"{profile.initial_url}?$skiptoken=opaque%2Bstate%3D%3D"
    terminal = f"{profile.initial_url}?$deltatoken=terminal%2Fstate"
    opener = FixtureOpener(
        [FixtureResponse(_page_payload(state_link=terminal, terminal=True))]
    )
    client = MicrosoftEntraDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    page = client.fetch(cursor)

    assert opener.requests[0].full_url == cursor
    assert page.delta_link == terminal
    assert page.cycle_complete is True


def test_entra_http_410_requires_explicit_resync_and_never_falls_back_to_initial_url() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    expired_cursor = f"{profile.initial_url}?$deltatoken=expired-state"
    opener = FixtureOpener([_http_error(expired_cursor, 410)])
    client = MicrosoftEntraDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(MicrosoftEntraDeltaStateExpiredError) as exc_info:
        client.fetch(expired_cursor)

    assert exc_info.value.resync_required is True
    assert [request.full_url for request in opener.requests] == [expired_cursor]


def test_entra_http_rejects_cross_cloud_cursor_before_sending_credentials() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    opener = FixtureOpener([])
    client = MicrosoftEntraDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(ValueError, match="changed the qualified Graph origin"):
        client.fetch("https://graph.microsoft.us/v1.0/users/delta?$skiptoken=foreign")

    assert opener.requests == []


@pytest.mark.parametrize(
    ("code", "expected_error"),
    [
        (401, MicrosoftEntraDeltaAuthenticationError),
        (403, MicrosoftEntraDeltaAuthorizationError),
    ],
)
def test_entra_http_maps_authentication_and_authorization_failures(
    code: int,
    expected_error: type[Exception],
) -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    opener = FixtureOpener([_http_error(profile.initial_url, code)])
    client = MicrosoftEntraDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(expected_error):
        client.fetch()


def test_entra_http_preserves_bounded_retry_after_for_throttling() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    opener = FixtureOpener(
        [_http_error(profile.initial_url, 429, retry_after="120")]
    )
    client = MicrosoftEntraDeltaHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(MicrosoftEntraDeltaThrottleError) as exc_info:
        client.fetch()

    assert exc_info.value.retry_after_seconds == 120


def test_entra_http_response_limit_fails_before_delta_parser() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    body = b"{" + b"x" * 100 + b"}"
    opener = FixtureOpener([FixtureResponse(body)])
    client = MicrosoftEntraDeltaHttpClient(
        profile,
        TOKEN,
        maximum_response_bytes=32,
    )
    client._opener = opener

    with pytest.raises(MicrosoftEntraDeltaResponseTooLargeError):
        client.fetch()


def test_entra_http_client_close_zeroizes_runtime_token_and_prevents_reuse() -> None:
    profile = entra_delta_request_profile(_tenant_profile(), "users")
    client = MicrosoftEntraDeltaHttpClient(profile, TOKEN)

    client.close()

    assert bytes(client._credential) == b"\x00" * len(TOKEN)
    with pytest.raises(RuntimeError, match="client is closed"):
        client.fetch()
