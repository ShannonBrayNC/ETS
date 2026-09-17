from __future__ import annotations

import json
from datetime import UTC, datetime
from email.message import Message
from urllib.error import HTTPError

import pytest

from ets.connectors.credentials.models import CredentialReferenceV1
from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.demos.agent365_r0_mission import (
    authorize_mission,
    create_pending_mission,
    sharepoint_create_item_body,
)
from ets.demos.agent365_r0_qualification import POLICY_VERSION
from ets.demos.agent365_r0_sharepoint_live import (
    MicrosoftSharePointMissionAuthenticationError,
    MicrosoftSharePointMissionAuthorizationError,
    MicrosoftSharePointMissionHttpClient,
    MicrosoftSharePointMissionRetryableError,
    MicrosoftSharePointMissionSourceError,
    MicrosoftSharePointMissionThrottleError,
    SharePointMissionRawResponse,
    parse_retained_sharepoint_mission,
    retain_sharepoint_mission_source,
    run_agent365_r0_live_sharepoint_qualification,
    sharepoint_mission_read_profile,
    validate_sharepoint_mission_read_url,
)

MISSION_ID = "4db39caa-3794-47f7-9bf0-bf5cf79fb912"
AUTHORIZER_ID = "11111111-1111-4111-8111-111111111111"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
APPLICATION_ID = "33333333-3333-4333-8333-333333333333"
T0 = datetime(2026, 9, 17, 21, 0, tzinfo=UTC)
PARAMETERS = {
    "max_speed_mps": 0.25,
    "max_distance_m": 2.0,
    "max_duration_s": 20,
    "stop_distance_m": 0.45,
}


def _tenant_profile() -> MicrosoftTenantProfileV1:
    return MicrosoftTenantProfileV1(
        schema_version="ets.connector.microsoft.tenant_profile.v1",
        tenant_id=TENANT_ID,
        application_id=APPLICATION_ID,
        cloud="global",
        credential_ref=CredentialReferenceV1(
            schema_version="ets.connector.credential_ref.v1",
            ref="env://GRAPH_FIXTURE",
        ),
        consent_state="granted",
    )


def _authorized_mission():
    pending = create_pending_mission(
        policy_version=POLICY_VERSION,
        command_parameters=PARAMETERS,
        mission_id_factory=lambda: MISSION_ID,
    )
    return authorize_mission(
        pending,
        authorized_by_object_id=AUTHORIZER_ID,
        authorized_at=T0,
    )


def _profile():
    return sharepoint_mission_read_profile(
        _tenant_profile(),
        site_id="contoso.sharepoint.com,site-guid,web-guid",
        list_id="list-guid",
        item_id="42",
    )


def _source_bytes(*, mission=None, item_id: str = "42", deleted: bool = False) -> bytes:
    mission = mission or _authorized_mission()
    body = sharepoint_create_item_body(mission)
    payload: dict[str, object] = {
        "id": item_id,
        "eTag": '"42,7"',
        "fields": body["fields"],
    }
    if deleted:
        payload["deleted"] = {}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _raw_response(body: bytes) -> SharePointMissionRawResponse:
    profile = _profile()
    return SharePointMissionRawResponse(
        body=body,
        acquired_at=T0,
        request_path=profile.request_path,
        request_url=profile.request_url,
        content_type="application/json; charset=utf-8",
        etag='"42,7"',
    )


def test_profile_is_server_owned_and_rejects_origin_or_path_escape() -> None:
    profile = _profile()

    assert profile.request_url.startswith("https://graph.microsoft.com/v1.0/sites/")
    assert profile.request_url.endswith("/items/42?expand=fields")
    assert validate_sharepoint_mission_read_url(profile, profile.request_url) == profile.request_url

    with pytest.raises(MicrosoftSharePointMissionSourceError):
        validate_sharepoint_mission_read_url(
            profile,
            profile.request_url.replace("graph.microsoft.com", "example.invalid"),
        )
    with pytest.raises(MicrosoftSharePointMissionSourceError):
        validate_sharepoint_mission_read_url(
            profile,
            profile.request_url.replace("/items/42", "/items/43"),
        )


def test_exact_source_is_retained_before_interpretation_and_authorization_matches(tmp_path) -> None:
    mission = _authorized_mission()
    body = _source_bytes(mission=mission)
    profile = _profile()
    envelope = retain_sharepoint_mission_source(
        _raw_response(body),
        profile,
        tmp_path,
        requested_mission_id=MISSION_ID,
    )

    retained = (tmp_path / envelope.retained_filename).read_bytes()
    observation = parse_retained_sharepoint_mission(
        envelope,
        retained,
        expected_authorization_material_sha256=mission.authorization_material_sha256(),
    )

    assert retained == body
    assert observation.mission == mission
    assert observation.source_item_id == "42"
    assert observation.body_etag == '"42,7"'
    assert observation.source.payload_ref.startswith(
        "ets://microsoft/sharepoint/mission-source/sha256/"
    )


def test_wrong_mission_and_changed_authorization_material_fail_closed(tmp_path) -> None:
    mission = _authorized_mission()
    profile = _profile()
    body = _source_bytes(mission=mission)
    envelope = retain_sharepoint_mission_source(
        _raw_response(body),
        profile,
        tmp_path,
        requested_mission_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    )
    with pytest.raises(MicrosoftSharePointMissionSourceError, match="mission_id"):
        parse_retained_sharepoint_mission(
            envelope,
            body,
            expected_authorization_material_sha256=mission.authorization_material_sha256(),
        )

    correct_envelope = retain_sharepoint_mission_source(
        _raw_response(body),
        profile,
        tmp_path / "correct",
        requested_mission_id=MISSION_ID,
    )
    with pytest.raises(MicrosoftSharePointMissionSourceError, match="authorized baseline"):
        parse_retained_sharepoint_mission(
            correct_envelope,
            body,
            expected_authorization_material_sha256="0" * 64,
        )


def test_deleted_malformed_and_tampered_source_fail_closed(tmp_path) -> None:
    mission = _authorized_mission()
    profile = _profile()

    deleted = _source_bytes(mission=mission, deleted=True)
    deleted_envelope = retain_sharepoint_mission_source(
        _raw_response(deleted),
        profile,
        tmp_path / "deleted",
        requested_mission_id=MISSION_ID,
    )
    with pytest.raises(MicrosoftSharePointMissionSourceError, match="deleted"):
        parse_retained_sharepoint_mission(
            deleted_envelope,
            deleted,
            expected_authorization_material_sha256=mission.authorization_material_sha256(),
        )

    malformed = json.dumps({"id": "42", "fields": []}).encode("utf-8")
    malformed_envelope = retain_sharepoint_mission_source(
        _raw_response(malformed),
        profile,
        tmp_path / "malformed",
        requested_mission_id=MISSION_ID,
    )
    with pytest.raises(MicrosoftSharePointMissionSourceError, match="fields object"):
        parse_retained_sharepoint_mission(
            malformed_envelope,
            malformed,
            expected_authorization_material_sha256=mission.authorization_material_sha256(),
        )

    good = _source_bytes(mission=mission)
    good_envelope = retain_sharepoint_mission_source(
        _raw_response(good),
        profile,
        tmp_path / "tamper",
        requested_mission_id=MISSION_ID,
    )
    with pytest.raises(MicrosoftSharePointMissionSourceError, match="custody envelope"):
        parse_retained_sharepoint_mission(
            good_envelope,
            good + b" ",
            expected_authorization_material_sha256=mission.authorization_material_sha256(),
        )


def test_http_error_classification_is_bounded() -> None:
    client = MicrosoftSharePointMissionHttpClient(_profile(), b"x")
    try:
        headers = Message()
        with pytest.raises(MicrosoftSharePointMissionAuthenticationError):
            client._raise_http_error(HTTPError(client._profile.request_url, 401, "", headers, None))
        with pytest.raises(MicrosoftSharePointMissionAuthorizationError):
            client._raise_http_error(HTTPError(client._profile.request_url, 403, "", headers, None))
        with pytest.raises(MicrosoftSharePointMissionRetryableError):
            client._raise_http_error(HTTPError(client._profile.request_url, 503, "", headers, None))
        headers["Retry-After"] = "7"
        with pytest.raises(MicrosoftSharePointMissionThrottleError) as exc_info:
            client._raise_http_error(HTTPError(client._profile.request_url, 429, "", headers, None))
        assert exc_info.value.retry_after_seconds == 7
    finally:
        client.close()


def test_live_sharepoint_input_enters_existing_downstream_qualification(tmp_path, monkeypatch) -> None:
    mission = _authorized_mission()
    body = _source_bytes(mission=mission)
    response = _raw_response(body)

    monkeypatch.setattr(
        MicrosoftSharePointMissionHttpClient,
        "fetch_raw",
        lambda self: response,
    )
    report = run_agent365_r0_live_sharepoint_qualification(
        tmp_path,
        profile=_profile(),
        credential_material=b"x",
        expected_mission_id=MISSION_ID,
        expected_authorization_material_sha256=mission.authorization_material_sha256(),
        started_at=T0,
    )

    assert report.mission_id == MISSION_ID
    assert report.live_sharepoint_observed is True
    assert report.physical_input_mode == "reference"
    assert report.downstream.chain_verified is True
    assert report.downstream.authorization_artifact_ref == report.microsoft_source.payload_ref
    assert (tmp_path / MISSION_ID / "live-sharepoint-qualification-report.json").is_file()
