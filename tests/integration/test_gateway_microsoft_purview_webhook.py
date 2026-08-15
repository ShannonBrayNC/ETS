from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.connectors.enterprise.microsoft_purview_activity import purview_management_profile
from ets.gateway.microsoft_purview_webhook import (
    PURVIEW_WEBHOOK_PATH,
    InMemoryMicrosoftPurviewDiscoverySink,
    MicrosoftPurviewWebhookSinkError,
    create_microsoft_purview_webhook_app,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = "22222222-2222-2222-2222-222222222222"
PUBLISHER_ID = "33333333-3333-3333-3333-333333333333"
AUTH_ID = "server-owned-purview-auth-id"
CREATED = datetime(2026, 8, 14, 20, 0, tzinfo=UTC)
EXPIRATION = CREATED + timedelta(days=7)


class FailingSink:
    def record(self, page: object) -> None:
        raise MicrosoftPurviewWebhookSinkError("simulated operational store outage")


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


def _notification(*, content_id: str = "content-001") -> dict[str, object]:
    profile = _profile()
    return {
        "tenantId": TENANT_ID,
        "clientId": APPLICATION_ID,
        "contentType": "Audit.General",
        "contentId": content_id,
        "contentUri": (
            f"{profile.management_root}/api/v1.0/{TENANT_ID}/activity/feed/"
            f"audit/{content_id}"
        ),
        "contentCreated": CREATED.isoformat().replace("+00:00", "Z"),
        "contentExpiration": EXPIRATION.isoformat().replace("+00:00", "Z"),
    }


def _client(sink: object) -> TestClient:
    app = create_microsoft_purview_webhook_app(
        _profile(),
        sink,  # type: ignore[arg-type]
        allowed_content_types=("Audit.General",),
        webhook_auth_id=AUTH_ID,
    )
    return TestClient(app)


def test_purview_webhook_validation_requires_matching_header_body_and_auth_id() -> None:
    sink = InMemoryMicrosoftPurviewDiscoverySink()
    client = _client(sink)
    code = "opaque-validation-code"

    response = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={
            "Webhook-AuthID": AUTH_ID,
            "Webhook-ValidationCode": code,
            "Content-Type": "application/json",
        },
        content=json.dumps({"validationCode": code}),
    )

    assert response.status_code == 200
    assert response.content == b""
    assert sink.snapshot().descriptors == ()

    mismatch = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={
            "Webhook-AuthID": AUTH_ID,
            "Webhook-ValidationCode": code,
            "Content-Type": "application/json",
        },
        content=json.dumps({"validationCode": "different"}),
    )
    assert mismatch.status_code == 400


def test_purview_webhook_records_discovery_only_and_dedupes_retry() -> None:
    sink = InMemoryMicrosoftPurviewDiscoverySink()
    client = _client(sink)
    payload = [_notification()]

    first = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": AUTH_ID},
        json=payload,
    )
    retry = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": AUTH_ID},
        json=payload,
    )

    assert first.status_code == 200
    assert retry.status_code == 200
    snapshot = sink.snapshot()
    assert len(snapshot.descriptors) == 1
    assert snapshot.descriptors[0].content_id == "content-001"


def test_purview_webhook_rejects_wrong_auth_tenant_and_client() -> None:
    sink = InMemoryMicrosoftPurviewDiscoverySink()
    client = _client(sink)

    wrong_auth = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": "wrong"},
        json=[_notification()],
    )
    wrong_tenant = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": AUTH_ID},
        json=[{**_notification(), "tenantId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}],
    )
    wrong_client = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": AUTH_ID},
        json=[{**_notification(), "clientId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}],
    )

    assert wrong_auth.status_code == 400
    assert wrong_tenant.status_code == 400
    assert wrong_client.status_code == 400
    assert sink.snapshot().descriptors == ()


def test_purview_webhook_sink_failure_returns_retryable_status_for_microsoft_retry() -> None:
    client = _client(FailingSink())

    response = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": AUTH_ID},
        json=[_notification()],
    )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"


def test_purview_webhook_conflicting_duplicate_fails_closed() -> None:
    sink = InMemoryMicrosoftPurviewDiscoverySink()
    client = _client(sink)

    first = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": AUTH_ID},
        json=[_notification()],
    )
    conflicting = client.post(
        PURVIEW_WEBHOOK_PATH,
        headers={"Webhook-AuthID": AUTH_ID},
        json=[
            {
                **_notification(),
                "contentExpiration": (EXPIRATION + timedelta(hours=1)).isoformat().replace(
                    "+00:00",
                    "Z",
                ),
            }
        ],
    )

    assert first.status_code == 200
    assert conflicting.status_code == 503
    assert len(sink.snapshot().descriptors) == 1
