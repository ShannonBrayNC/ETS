from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewContentDescriptorV1,
    purview_management_profile,
)
from ets.connectors.enterprise.microsoft_purview_http import (
    MicrosoftPurviewActivityHttpClient,
    MicrosoftPurviewAuthenticationError,
    MicrosoftPurviewAuthorizationError,
    MicrosoftPurviewRedirectError,
    MicrosoftPurviewResponseTooLargeError,
    MicrosoftPurviewThrottleError,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PUBLISHER_ID = "33333333-3333-3333-3333-333333333333"
TOKEN = b"fixture-purview-token"
CREATED = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)
EXPIRATION = CREATED + timedelta(days=7)


class FixtureResponse:
    def __init__(
        self,
        body: bytes,
        *,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.headers = Message()
        if content_type:
            self.headers["Content-Type"] = content_type
        for key, value in (headers or {}).items():
            self.headers[key] = value

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


def _tenant() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.tenant_profile.v1",
            "tenant_id": TENANT_ID,
            "application_id": APPLICATION_ID,
            "cloud": "global",
            "credential_ref": CredentialReferenceV1(
                schema_version="ets.connector.credential_ref.v1",
                ref="fixture://microsoft/purview",
            ).model_dump(mode="json"),
            "consent_state": "granted",
        }
    )


def _profile():
    return purview_management_profile(
        "purview-prod",
        _tenant(),
        plan="enterprise",
        publisher_identifier=PUBLISHER_ID,
    )


def _descriptor() -> MicrosoftPurviewContentDescriptorV1:
    return MicrosoftPurviewContentDescriptorV1(
        content_type="Audit.General",
        content_id="content-001",
        content_uri=(
            f"https://manage.office.com/api/v1.0/{TENANT_ID}/activity/feed/"
            "audit/content-001"
        ),
        content_created_utc=CREATED,
        content_expiration_utc=EXPIRATION,
        discovery_source="poll",
    )


def _audit_body() -> bytes:
    return json.dumps(
        [
            {
                "Id": "44444444-4444-4444-4444-444444444444",
                "RecordType": 1,
                "CreationTime": "2026-08-14T19:57:30Z",
                "Operation": "FileAccessed",
                "OrganizationId": TENANT_ID,
                "UserType": 0,
                "UserKey": "user-key-001",
                "Workload": "SharePoint",
                "UserId": "alice@example.test",
            }
        ]
    ).encode("utf-8")


def _http_error(url: str, code: int, *, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(url, code, "fixture error", headers, None)


def test_purview_subscription_start_and_stop_use_server_owned_root_and_redacted_token() -> None:
    start_body = json.dumps(
        {
            "contentType": "Audit.General",
            "status": "enabled",
            "webhook": {"status": "enabled"},
        }
    ).encode("utf-8")
    opener = FixtureOpener(
        [
            FixtureResponse(start_body),
            FixtureResponse(b"", content_type=""),
        ]
    )
    client = MicrosoftPurviewActivityHttpClient(_profile(), TOKEN)
    client._opener = opener

    state = client.start_subscription(
        "Audit.General",
        webhook_address="https://collector.example/purview",
        webhook_auth_id="server-auth-id",
    )
    client.stop_subscription("Audit.General")

    assert state.status == "enabled"
    assert state.webhook_status == "enabled"
    assert "/subscriptions/start?" in opener.requests[0].full_url
    assert "/subscriptions/stop?" in opener.requests[1].full_url
    assert f"PublisherIdentifier={PUBLISHER_ID}" in opener.requests[0].full_url
    assert opener.requests[0].get_header("Authorization") == f"Bearer {TOKEN.decode()}"
    assert TOKEN.decode() not in repr(client)


def test_purview_poll_replays_next_page_and_parses_discovery() -> None:
    profile = _profile()
    next_page = (
        f"{profile.management_root}/api/v1.0/{TENANT_ID}/activity/feed/"
        "subscriptions/content?contentType=Audit.General&PublisherIdentifier="
        f"{PUBLISHER_ID}&nextpage=opaque"
    )
    descriptor = {
        "contentType": "Audit.General",
        "contentId": "content-001",
        "contentUri": _descriptor().content_uri,
        "contentCreated": CREATED.isoformat().replace("+00:00", "Z"),
        "contentExpiration": EXPIRATION.isoformat().replace("+00:00", "Z"),
    }
    opener = FixtureOpener(
        [
            FixtureResponse(
                json.dumps([descriptor]).encode("utf-8"),
                headers={"NextPageUri": next_page},
            ),
            FixtureResponse(json.dumps([descriptor]).encode("utf-8")),
        ]
    )
    client = MicrosoftPurviewActivityHttpClient(profile, TOKEN)
    client._opener = opener

    first = client.list_content("Audit.General")
    second = client.list_content("Audit.General", next_page_uri=first.next_page_uri)

    assert first.next_page_uri == next_page
    assert len(first.descriptors) == 1
    assert opener.requests[1].full_url == next_page
    assert len(second.descriptors) == 1


def test_purview_content_uri_is_revalidated_before_credential_use_and_normalized() -> None:
    opener = FixtureOpener([FixtureResponse(_audit_body())])
    client = MicrosoftPurviewActivityHttpClient(_profile(), TOKEN)
    client._opener = opener

    content = client.retrieve_content(_descriptor())

    assert len(content.records) == 1
    assert content.records[0].operation == "FileAccessed"
    assert opener.requests[0].full_url == (
        f"{_descriptor().content_uri}?PublisherIdentifier={PUBLISHER_ID}"
    )

    bad = MicrosoftPurviewContentDescriptorV1(
        content_type="Audit.General",
        content_id="content-bad",
        content_uri=(
            f"https://evil.example/api/v1.0/{TENANT_ID}/activity/feed/audit/content-bad"
        ),
        content_created_utc=CREATED,
        content_expiration_utc=EXPIRATION,
        discovery_source="poll",
    )
    with pytest.raises(ValueError, match="management origin"):
        client.retrieve_content(bad)
    assert len(opener.requests) == 1


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (401, MicrosoftPurviewAuthenticationError),
        (403, MicrosoftPurviewAuthorizationError),
        (302, MicrosoftPurviewRedirectError),
    ],
)
def test_purview_http_maps_auth_and_redirect_failures(
    code: int,
    expected: type[Exception],
) -> None:
    profile = _profile()
    url = (
        f"{profile.management_root}/api/v1.0/{TENANT_ID}/activity/feed/"
        f"subscriptions/content?contentType=Audit.General&PublisherIdentifier={PUBLISHER_ID}"
    )
    opener = FixtureOpener([_http_error(url, code)])
    client = MicrosoftPurviewActivityHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(expected):
        client.list_content("Audit.General")


def test_purview_http_throttle_response_limit_and_close_fail_closed() -> None:
    profile = _profile()
    url = (
        f"{profile.management_root}/api/v1.0/{TENANT_ID}/activity/feed/"
        f"subscriptions/content?contentType=Audit.General&PublisherIdentifier={PUBLISHER_ID}"
    )
    opener = FixtureOpener([_http_error(url, 429, retry_after="120")])
    client = MicrosoftPurviewActivityHttpClient(profile, TOKEN)
    client._opener = opener

    with pytest.raises(MicrosoftPurviewThrottleError) as exc_info:
        client.list_content("Audit.General")
    assert exc_info.value.retry_after_seconds == 120

    oversized = FixtureOpener([FixtureResponse(b"[" + b"x" * 100 + b"]")])
    bounded = MicrosoftPurviewActivityHttpClient(
        profile,
        TOKEN,
        maximum_discovery_bytes=32,
    )
    bounded._opener = oversized
    with pytest.raises(MicrosoftPurviewResponseTooLargeError):
        bounded.list_content("Audit.General")

    bounded.close()
    assert bytes(bounded._credential) == b"\x00" * len(TOKEN)
    with pytest.raises(RuntimeError, match="client is closed"):
        bounded.list_content("Audit.General")
