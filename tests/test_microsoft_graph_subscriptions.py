from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_graph import (
    MicrosoftGraphSubscriptionStateV1,
    hash_graph_client_state,
)
from ets.connectors.enterprise.microsoft_graph_subscriptions import (
    MicrosoftGraphSubscriptionAuthenticationError,
    MicrosoftGraphSubscriptionAuthorizationError,
    MicrosoftGraphSubscriptionHttpClient,
    MicrosoftGraphSubscriptionTerminalError,
    MicrosoftGraphSubscriptionThrottleError,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
TOKEN = b"fixture-graph-subscription-token"
CLIENT_STATE = "server-owned-client-state"
NOTIFICATION_URL = "https://gateway.example.test/gateway/v1/microsoft/graph"
LIFECYCLE_URL = "https://gateway.example.test/gateway/v1/microsoft/graph"
NOW = datetime(2026, 8, 14, 14, 0, tzinfo=UTC)
EXPIRATION = NOW + timedelta(hours=2)


class FixtureResponse:
    def __init__(
        self,
        status_code: int,
        body: bytes = b"",
        *,
        content_type: str | None = "application/json",
    ) -> None:
        self._status_code = status_code
        self._body = body
        self.headers = Message()
        if content_type is not None:
            self.headers["Content-Type"] = content_type

    def getcode(self) -> int:
        return self._status_code

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
                ref="fixture://microsoft/graph-subscriptions",
            ).model_dump(mode="json"),
            "consent_state": "granted",
        }
    )


def _subscription_response(
    *,
    subscription_id: str = "subscription-001",
    resource: str = "users",
    client_state: str = CLIENT_STATE,
    expiration: datetime = EXPIRATION,
) -> bytes:
    return json.dumps(
        {
            "id": subscription_id,
            "resource": resource,
            "clientState": client_state,
            "expirationDateTime": expiration.isoformat().replace("+00:00", "Z"),
            "changeType": "updated,deleted",
            "notificationUrl": NOTIFICATION_URL,
        }
    ).encode("utf-8")


def _state(
    *,
    status: str = "active",
    gap_state: str = "none",
    cloud: str = "global",
) -> MicrosoftGraphSubscriptionStateV1:
    return MicrosoftGraphSubscriptionStateV1.model_validate(
        {
            "schema_version": "ets.connector.microsoft.graph_subscription_state.v1",
            "subscription_id": "subscription-001",
            "tenant_id": TENANT_ID,
            "cloud": cloud,
            "resource": "users",
            "client_state_sha256": hash_graph_client_state(CLIENT_STATE),
            "expiration_date_time": EXPIRATION,
            "status": status,
            "gap_state": gap_state,
        }
    )


def _client(
    responses: list[FixtureResponse | Exception],
    *,
    cloud: str = "global",
) -> tuple[MicrosoftGraphSubscriptionHttpClient, FixtureOpener]:
    client = MicrosoftGraphSubscriptionHttpClient(
        _tenant_profile(cloud=cloud),
        TOKEN,
        notification_url=NOTIFICATION_URL,
        lifecycle_notification_url=LIFECYCLE_URL,
        timeout_seconds=5,
    )
    opener = FixtureOpener(responses)
    client._opener = opener
    return client, opener


def _http_error(url: str, code: int, *, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(url, code, "fixture error", headers, None)


def test_create_uses_qualified_graph_root_and_persists_only_client_state_hash() -> None:
    client, opener = _client(
        [FixtureResponse(201, _subscription_response())]
    )

    state = client.create(
        resource="users",
        change_type="updated,deleted",
        expiration_date_time=EXPIRATION,
        client_state=CLIENT_STATE,
    )

    request = opener.requests[0]
    assert request.method == "POST"
    assert request.full_url == "https://graph.microsoft.com/v1.0/subscriptions"
    assert request.get_header("Authorization") == f"Bearer {TOKEN.decode()}"
    body = json.loads(request.data or b"{}")
    assert body["clientState"] == CLIENT_STATE
    assert body["notificationUrl"] == NOTIFICATION_URL
    assert body["lifecycleNotificationUrl"] == LIFECYCLE_URL
    assert body["latestSupportedTlsVersion"] == "v1_2"
    serialized_state = json.dumps(state.model_dump(mode="json"))
    assert CLIENT_STATE not in serialized_state
    assert state.client_state_sha256 == hash_graph_client_state(CLIENT_STATE)
    assert state.status == "active"
    assert state.gap_state == "none"
    assert TOKEN.decode() not in repr(client)


def test_create_uses_national_cloud_graph_root_without_customer_endpoint_override() -> None:
    client, opener = _client(
        [FixtureResponse(201, _subscription_response())],
        cloud="us_government_l4",
    )

    state = client.create(
        resource="users",
        change_type="updated,deleted",
        expiration_date_time=EXPIRATION,
        client_state=CLIENT_STATE,
    )

    assert opener.requests[0].full_url == "https://graph.microsoft.us/v1.0/subscriptions"
    assert state.cloud == "us_government_l4"


def test_renew_preserves_existing_possible_gap_and_exact_subscription_identity() -> None:
    renewed_expiration = EXPIRATION + timedelta(hours=1)
    client, opener = _client(
        [
            FixtureResponse(
                200,
                _subscription_response(expiration=renewed_expiration),
            )
        ]
    )
    current = _state(gap_state="possible")

    updated = client.renew(current, expiration_date_time=renewed_expiration)

    assert opener.requests[0].method == "PATCH"
    assert opener.requests[0].full_url.endswith("/subscriptions/subscription-001")
    assert updated.subscription_id == current.subscription_id
    assert updated.expiration_date_time == renewed_expiration
    assert updated.gap_state == "possible"
    assert updated.status == "active"


def test_reauthorize_changes_operational_status_but_does_not_clear_possible_gap() -> None:
    client, opener = _client([FixtureResponse(204, content_type=None)])
    current = _state(status="reauthorization_required", gap_state="possible")

    updated = client.reauthorize(current)

    request = opener.requests[0]
    assert request.method == "POST"
    assert request.full_url.endswith("/subscriptions/subscription-001/reauthorize")
    assert request.data is None
    assert updated.status == "active"
    assert updated.gap_state == "possible"


def test_delete_uses_no_body_and_returns_no_evidence_state() -> None:
    client, opener = _client([FixtureResponse(204, content_type=None)])

    result = client.delete(_state())

    request = opener.requests[0]
    assert request.method == "DELETE"
    assert request.full_url.endswith("/subscriptions/subscription-001")
    assert request.data is None
    assert result is None


def test_create_rejects_unqualified_change_types_before_network_call() -> None:
    client, opener = _client([])

    with pytest.raises(ValueError, match="changeType is invalid"):
        client.create(
            resource="users",
            change_type="updated,executed",
            expiration_date_time=EXPIRATION,
            client_state=CLIENT_STATE,
        )

    assert opener.requests == []


def test_renew_rejects_foreign_tenant_state_before_credentials_are_sent() -> None:
    client, opener = _client([])
    foreign = _state().model_copy(update={"tenant_id": "33333333-3333-3333-3333-333333333333"})

    with pytest.raises(MicrosoftGraphSubscriptionTerminalError, match="tenant"):
        client.renew(foreign, expiration_date_time=EXPIRATION)

    assert opener.requests == []


def test_create_rejects_response_resource_or_client_state_mismatch() -> None:
    wrong_resource, _ = _client(
        [FixtureResponse(201, _subscription_response(resource="groups"))]
    )
    with pytest.raises(MicrosoftGraphSubscriptionTerminalError, match="resource"):
        wrong_resource.create(
            resource="users",
            change_type="updated",
            expiration_date_time=EXPIRATION,
            client_state=CLIENT_STATE,
        )

    wrong_state, _ = _client(
        [FixtureResponse(201, _subscription_response(client_state="different-state"))]
    )
    with pytest.raises(MicrosoftGraphSubscriptionTerminalError, match="clientState"):
        wrong_state.create(
            resource="users",
            change_type="updated",
            expiration_date_time=EXPIRATION,
            client_state=CLIENT_STATE,
        )


@pytest.mark.parametrize(
    ("code", "expected_error"),
    [
        (401, MicrosoftGraphSubscriptionAuthenticationError),
        (403, MicrosoftGraphSubscriptionAuthorizationError),
    ],
)
def test_subscription_client_maps_authentication_and_authorization_failures(
    code: int,
    expected_error: type[Exception],
) -> None:
    url = "https://graph.microsoft.com/v1.0/subscriptions"
    client, _ = _client([_http_error(url, code)])

    with pytest.raises(expected_error):
        client.create(
            resource="users",
            change_type="updated",
            expiration_date_time=EXPIRATION,
            client_state=CLIENT_STATE,
        )


def test_subscription_client_preserves_bounded_retry_after() -> None:
    url = "https://graph.microsoft.com/v1.0/subscriptions"
    client, _ = _client([_http_error(url, 429, retry_after="75")])

    with pytest.raises(MicrosoftGraphSubscriptionThrottleError) as exc_info:
        client.create(
            resource="users",
            change_type="updated",
            expiration_date_time=EXPIRATION,
            client_state=CLIENT_STATE,
        )

    assert exc_info.value.retry_after_seconds == 75


def test_subscription_client_close_zeroizes_token_and_prevents_reuse() -> None:
    client, opener = _client([])

    client.close()

    assert bytes(client._credential) == b"\x00" * len(TOKEN)
    with pytest.raises(RuntimeError, match="client is closed"):
        client.delete(_state())
    assert opener.requests == []
