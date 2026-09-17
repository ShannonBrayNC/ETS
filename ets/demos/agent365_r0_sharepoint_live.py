"""Live Microsoft Graph SharePoint mission read-back for the frozen Agent 365 + R0 demo.

The source boundary is deliberately narrower than the generic SharePoint delta connector.
It reads one configured list item with ``expand=fields``, retains the exact Microsoft response
bytes before interpretation, validates the frozen mission contract, compares the previously
authorized command commitment, and only then enters the common Gateway/R0 qualification path.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from typing import Final, Literal, NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, OpenerDirector, Request, build_opener

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1
from ets.demos.agent365_r0_mission import (
    MissionAuthorizationState,
    MissionStatus,
    SharePointMissionArtifactV1,
    parse_sharepoint_fields,
)
from ets.demos.agent365_r0_qualification import (
    Agent365R0QualificationReport,
    run_agent365_r0_qualification_from_mission,
)

SHAREPOINT_MISSION_DEFAULT_MAXIMUM_BODY_BYTES: Final = 512 * 1024
SHAREPOINT_MISSION_MAXIMUM_RESPONSE_BYTES: Final = 2 * 1024 * 1024
SHAREPOINT_MISSION_MAXIMUM_TIMEOUT_SECONDS: Final = 60.0
SHAREPOINT_MISSION_USER_AGENT: Final = "ets-agent365-r0-sharepoint-mission/1.0"
SHAREPOINT_MISSION_COLLECTOR_IDENTITY: Final = "ets.microsoft-sharepoint-mission-collector"
SHAREPOINT_MISSION_COLLECTOR_VERSION: Final = "1.0"

_IDENTIFIER_MAXIMUM_CHARACTERS: Final = 500
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class MicrosoftSharePointMissionSourceError(ValueError):
    """Raised when retained SharePoint source material violates the frozen P0 contract."""


class MicrosoftSharePointMissionClientError(RuntimeError):
    """Base credential-safe live source client error."""


class MicrosoftSharePointMissionAuthenticationError(MicrosoftSharePointMissionClientError):
    """Microsoft Graph rejected the access token."""


class MicrosoftSharePointMissionAuthorizationError(MicrosoftSharePointMissionClientError):
    """Microsoft Graph denied the configured SharePoint item read."""


class MicrosoftSharePointMissionNotFoundError(MicrosoftSharePointMissionClientError):
    """The configured mission item does not exist or is not visible."""


class MicrosoftSharePointMissionRetryableError(MicrosoftSharePointMissionClientError):
    """A transient source/network failure may be retried under caller policy."""


class MicrosoftSharePointMissionTerminalError(MicrosoftSharePointMissionClientError):
    """A source/transport failure must fail the bounded qualification closed."""


class MicrosoftSharePointMissionRedirectError(MicrosoftSharePointMissionTerminalError):
    """Credential-bearing mission reads never follow redirects."""


class MicrosoftSharePointMissionResponseTooLargeError(MicrosoftSharePointMissionTerminalError):
    """The response exceeded the configured source-acquisition bound."""


class MicrosoftSharePointMissionThrottleError(MicrosoftSharePointMissionRetryableError):
    """Graph requested a bounded retry delay."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Microsoft Graph SharePoint mission read is rate limited")
        self.retry_after_seconds = max(1, min(retry_after_seconds, 3600))


@dataclass(frozen=True, slots=True)
class SharePointMissionReadProfile:
    """Server-owned Graph origin plus one explicitly configured mission item path."""

    tenant_profile: MicrosoftTenantProfileV1
    site_id: str
    list_id: str
    item_id: str
    request_path: str
    request_url: str


@dataclass(frozen=True, slots=True)
class SharePointMissionRawResponse:
    """Exact source bytes and transport metadata returned before interpretation."""

    body: bytes
    acquired_at: datetime
    request_path: str
    request_url: str
    content_type: str
    etag: str | None


class SharePointMissionSourceEnvelopeV1(BaseModel):
    """Custody metadata for exact Microsoft response bytes retained before parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.sharepoint-source.v1"] = (
        "ets.demo.agent365-r0.sharepoint-source.v1"
    )
    source: Literal["microsoft.sharepoint"] = "microsoft.sharepoint"
    requested_mission_id: str = Field(min_length=36, max_length=36)
    tenant_id: str = Field(min_length=36, max_length=36)
    site_id: str = Field(min_length=1, max_length=_IDENTIFIER_MAXIMUM_CHARACTERS)
    list_id: str = Field(min_length=1, max_length=_IDENTIFIER_MAXIMUM_CHARACTERS)
    item_id: str = Field(min_length=1, max_length=_IDENTIFIER_MAXIMUM_CHARACTERS)
    acquired_at: datetime
    request_path: str = Field(min_length=1, max_length=4096)
    raw_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_payload_size: int = Field(ge=1, le=SHAREPOINT_MISSION_MAXIMUM_RESPONSE_BYTES)
    payload_ref: str = Field(min_length=1, max_length=4096)
    retained_filename: str = Field(min_length=1, max_length=4096)
    content_type: str = Field(min_length=1, max_length=256)
    etag: str | None = Field(default=None, max_length=2048)
    collector_identity: str = Field(min_length=1, max_length=256)
    collector_version: str = Field(min_length=1, max_length=128)

    @field_validator("acquired_at")
    @classmethod
    def normalize_acquired_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("SharePoint source acquisition time must be timezone-aware")
        return value.astimezone(UTC)


class SharePointMissionLiveObservationV1(BaseModel):
    """Interpreted mission bound to its retained Microsoft source envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.sharepoint-observation.v1"] = (
        "ets.demo.agent365-r0.sharepoint-observation.v1"
    )
    mission: SharePointMissionArtifactV1
    source: SharePointMissionSourceEnvelopeV1
    source_item_id: str = Field(min_length=1, max_length=_IDENTIFIER_MAXIMUM_CHARACTERS)
    body_etag: str | None = Field(default=None, max_length=2048)
    authorization_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Agent365R0LiveSharePointQualificationReport(BaseModel):
    """Result of live Microsoft authorization feeding the reference physical qualification."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.demo.agent365-r0.live-sharepoint-qualification.v1"] = (
        "ets.demo.agent365-r0.live-sharepoint-qualification.v1"
    )
    mission_id: str
    microsoft_source: SharePointMissionSourceEnvelopeV1
    downstream: Agent365R0QualificationReport
    live_sharepoint_observed: Literal[True] = True
    physical_input_mode: Literal["reference"] = "reference"
    truth_claim_supported: Literal[False] = False
    claim_boundary: str = (
        "live_sharepoint_authorization_is_source_attributable_and_commitment_checked;_"
        "reference_r0_observations_remain_non_live_until_physical_sensor_substitution"
    )


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
        raise MicrosoftSharePointMissionRedirectError(
            "Microsoft Graph redirects are disabled for credential-bearing mission reads"
        )


def sharepoint_mission_read_profile(
    tenant_profile: MicrosoftTenantProfileV1,
    *,
    site_id: str,
    list_id: str,
    item_id: str,
) -> SharePointMissionReadProfile:
    """Build the only Graph item-read path permitted by the frozen mission source boundary."""

    if tenant_profile.consent_state != "granted":
        raise ValueError("SharePoint mission read requires granted Microsoft administrator consent")
    site_id = _bounded_identifier(site_id, "site_id")
    list_id = _bounded_identifier(list_id, "list_id")
    item_id = _bounded_identifier(item_id, "item_id")
    request_path = (
        f"/v1.0/sites/{quote(site_id, safe='')}/lists/{quote(list_id, safe='')}/"
        f"items/{quote(item_id, safe='')}?expand=fields"
    )
    graph_root = tenant_profile.endpoints.graph_root.rstrip("/")
    request_url = f"{graph_root}{request_path}"
    profile = SharePointMissionReadProfile(
        tenant_profile=tenant_profile,
        site_id=site_id,
        list_id=list_id,
        item_id=item_id,
        request_path=request_path,
        request_url=request_url,
    )
    validate_sharepoint_mission_read_url(profile, request_url)
    return profile


def validate_sharepoint_mission_read_url(
    profile: SharePointMissionReadProfile,
    value: str,
) -> str:
    """Fail closed if a credential-bearing request escapes its server-owned Graph path."""

    root = urlsplit(profile.tenant_profile.endpoints.graph_root)
    parsed = urlsplit(value)
    expected = urlsplit(profile.request_url)
    if parsed.scheme != "https" or parsed.hostname != root.hostname:
        raise MicrosoftSharePointMissionSourceError(
            "SharePoint mission request escaped the server-owned Microsoft Graph origin"
        )
    if parsed.port not in {None, 443}:
        raise MicrosoftSharePointMissionSourceError(
            "SharePoint mission request changed the qualified Graph port"
        )
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise MicrosoftSharePointMissionSourceError(
            "SharePoint mission request contains unsupported URL components"
        )
    if parsed.path != expected.path or parsed.query != "expand=fields":
        raise MicrosoftSharePointMissionSourceError(
            "SharePoint mission request escaped the configured site/list/item fields path"
        )
    return value


class MicrosoftSharePointMissionHttpClient:
    """Credential-safe bounded GET client returning exact bytes without interpreting them."""

    def __init__(
        self,
        profile: SharePointMissionReadProfile,
        credential_material: bytes,
        *,
        timeout_seconds: float = 30.0,
        maximum_response_bytes: int = SHAREPOINT_MISSION_DEFAULT_MAXIMUM_BODY_BYTES,
    ) -> None:
        if not credential_material:
            raise ValueError("Microsoft Graph credential material must not be empty")
        if not 0.1 <= timeout_seconds <= SHAREPOINT_MISSION_MAXIMUM_TIMEOUT_SECONDS:
            raise ValueError("Microsoft Graph timeout_seconds must be between 0.1 and 60")
        if not 1 <= maximum_response_bytes <= SHAREPOINT_MISSION_MAXIMUM_RESPONSE_BYTES:
            raise ValueError("Microsoft Graph maximum_response_bytes exceeds the qualified bound")
        self._profile = profile
        self._credential = bytearray(credential_material)
        self._timeout_seconds = timeout_seconds
        self._maximum_response_bytes = maximum_response_bytes
        self._closed = False
        self._opener: OpenerDirector = build_opener(_RejectRedirects())

    def __repr__(self) -> str:
        return (
            "MicrosoftSharePointMissionHttpClient(credential=<redacted>, "
            f"item_id={self._profile.item_id!r})"
        )

    def __enter__(self) -> MicrosoftSharePointMissionHttpClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._credential)):
            self._credential[index] = 0
        self._closed = True

    def fetch_raw(self) -> SharePointMissionRawResponse:
        if self._closed:
            raise MicrosoftSharePointMissionClientError(
                "Microsoft Graph SharePoint mission client is closed"
            )
        url = validate_sharepoint_mission_read_url(self._profile, self._profile.request_url)
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._credential_text()}",
                "User-Agent": SHAREPOINT_MISSION_USER_AGENT,
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                body = response.read(self._maximum_response_bytes + 1)
                if len(body) > self._maximum_response_bytes:
                    raise MicrosoftSharePointMissionResponseTooLargeError(
                        "Microsoft Graph SharePoint mission response exceeds configured byte bound"
                    )
                content_type = _validate_json_content_type(response.headers.get("Content-Type"))
                etag = response.headers.get("ETag")
        except MicrosoftSharePointMissionClientError:
            raise
        except HTTPError as exc:
            self._raise_http_error(exc)
        except (TimeoutError, URLError, OSError) as exc:
            raise MicrosoftSharePointMissionRetryableError(
                "Microsoft Graph SharePoint mission request failed"
            ) from exc

        if not body:
            raise MicrosoftSharePointMissionTerminalError(
                "Microsoft Graph SharePoint mission response is empty"
            )
        return SharePointMissionRawResponse(
            body=body,
            acquired_at=datetime.now(UTC),
            request_path=self._profile.request_path,
            request_url=url,
            content_type=content_type,
            etag=etag,
        )

    def _credential_text(self) -> str:
        try:
            return bytes(self._credential).decode("ascii")
        except UnicodeDecodeError as exc:
            raise MicrosoftSharePointMissionAuthenticationError(
                "Microsoft Graph credential material must be ASCII token data"
            ) from exc

    def _raise_http_error(self, exc: HTTPError) -> NoReturn:
        if 300 <= exc.code <= 399:
            raise MicrosoftSharePointMissionRedirectError(
                "Microsoft Graph redirects are disabled for mission reads"
            ) from exc
        if exc.code == 401:
            raise MicrosoftSharePointMissionAuthenticationError(
                "Microsoft Graph access token was rejected"
            ) from exc
        if exc.code == 403:
            raise MicrosoftSharePointMissionAuthorizationError(
                "Microsoft Graph SharePoint mission access was denied"
            ) from exc
        if exc.code == 404:
            raise MicrosoftSharePointMissionNotFoundError(
                "Microsoft Graph SharePoint mission item was not found"
            ) from exc
        if exc.code == 429:
            raise MicrosoftSharePointMissionThrottleError(
                _retry_after_seconds(exc.headers.get("Retry-After"))
            ) from exc
        if 500 <= exc.code <= 599:
            raise MicrosoftSharePointMissionRetryableError(
                "Microsoft Graph SharePoint mission endpoint returned a server error"
            ) from exc
        raise MicrosoftSharePointMissionTerminalError(
            f"Microsoft Graph SharePoint mission endpoint rejected request with HTTP {exc.code}"
        ) from exc


def retain_sharepoint_mission_source(
    response: SharePointMissionRawResponse,
    profile: SharePointMissionReadProfile,
    destination: str | Path,
    *,
    requested_mission_id: str,
    collector_identity: str = SHAREPOINT_MISSION_COLLECTOR_IDENTITY,
    collector_version: str = SHAREPOINT_MISSION_COLLECTOR_VERSION,
) -> SharePointMissionSourceEnvelopeV1:
    """Retain exact response bytes and their digest before any SharePoint field parsing."""

    if response.request_url != profile.request_url or response.request_path != profile.request_path:
        raise MicrosoftSharePointMissionSourceError(
            "source response request identity differs from the configured mission profile"
        )
    digest = hashlib.sha256(response.body).hexdigest()
    base = Path(destination)
    raw_dir = base / "raw"
    envelope_dir = base / "envelopes"
    raw_dir.mkdir(parents=True, exist_ok=True)
    envelope_dir.mkdir(parents=True, exist_ok=True)
    relative_raw = Path("raw") / f"sha256-{digest}.json"
    raw_path = base / relative_raw
    _retain_exact_bytes(raw_path, response.body)

    payload_ref = f"ets://microsoft/sharepoint/mission-source/sha256/{digest}"
    envelope = SharePointMissionSourceEnvelopeV1(
        requested_mission_id=requested_mission_id,
        tenant_id=profile.tenant_profile.tenant_id,
        site_id=profile.site_id,
        list_id=profile.list_id,
        item_id=profile.item_id,
        acquired_at=response.acquired_at,
        request_path=response.request_path,
        raw_payload_sha256=digest,
        raw_payload_size=len(response.body),
        payload_ref=payload_ref,
        retained_filename=relative_raw.as_posix(),
        content_type=response.content_type,
        etag=response.etag,
        collector_identity=collector_identity,
        collector_version=collector_version,
    )
    envelope_path = envelope_dir / f"sha256-{digest}.json"
    envelope_bytes = (
        json.dumps(envelope.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    _retain_exact_bytes(envelope_path, envelope_bytes)
    return envelope


def parse_retained_sharepoint_mission(
    envelope: SharePointMissionSourceEnvelopeV1,
    raw_payload: bytes,
    *,
    expected_authorization_material_sha256: str,
) -> SharePointMissionLiveObservationV1:
    """Interpret retained source bytes only after their custody envelope exists."""

    actual_digest = hashlib.sha256(raw_payload).hexdigest()
    source_changed = (
        actual_digest != envelope.raw_payload_sha256
        or len(raw_payload) != envelope.raw_payload_size
    )
    if source_changed:
        raise MicrosoftSharePointMissionSourceError(
            "retained SharePoint mission bytes do not match the source custody envelope"
        )
    if _SHA256_PATTERN.fullmatch(expected_authorization_material_sha256) is None:
        raise ValueError("expected_authorization_material_sha256 must be lowercase SHA-256 hex")
    try:
        decoded = json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph SharePoint mission response is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph SharePoint mission response must be a JSON object"
        )
    if "deleted" in decoded:
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph SharePoint mission item is deleted"
        )
    source_item_id = decoded.get("id")
    if not isinstance(source_item_id, str) or not source_item_id:
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph SharePoint mission response is missing item id"
        )
    if source_item_id != envelope.item_id:
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph returned a different SharePoint mission item"
        )
    fields = decoded.get("fields")
    if not isinstance(fields, dict):
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph SharePoint mission response must contain one fields object"
        )
    try:
        mission = parse_sharepoint_fields(fields)
    except (ValueError, TypeError) as exc:
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph SharePoint mission fields failed the frozen mission contract"
        ) from exc
    if mission.mission_id != envelope.requested_mission_id:
        raise MicrosoftSharePointMissionSourceError(
            "observed SharePoint mission_id differs from the requested mission"
        )
    if mission.authorization_state != MissionAuthorizationState.AUTHORIZED:
        raise MicrosoftSharePointMissionSourceError(
            "observed SharePoint mission is not AUTHORIZED"
        )
    if mission.status != MissionStatus.AUTHORIZED:
        raise MicrosoftSharePointMissionSourceError(
            "observed SharePoint mission is not in pre-dispatch AUTHORIZED status"
        )
    actual_authorization_digest = mission.authorization_material_sha256()
    if actual_authorization_digest != expected_authorization_material_sha256:
        raise MicrosoftSharePointMissionSourceError(
            "observed SharePoint mission command material differs from the authorized baseline"
        )
    body_etag = decoded.get("eTag", decoded.get("@odata.etag"))
    if body_etag is not None and not isinstance(body_etag, str):
        raise MicrosoftSharePointMissionSourceError(
            "Microsoft Graph SharePoint mission eTag must be a string when present"
        )
    return SharePointMissionLiveObservationV1(
        mission=mission,
        source=envelope,
        source_item_id=source_item_id,
        body_etag=body_etag,
        authorization_material_sha256=actual_authorization_digest,
    )


def run_agent365_r0_live_sharepoint_qualification(
    workdir: str | Path,
    *,
    profile: SharePointMissionReadProfile,
    credential_material: bytes,
    expected_mission_id: str,
    expected_authorization_material_sha256: str,
    started_at: datetime | None = None,
    timeout_seconds: float = 30.0,
    maximum_response_bytes: int = SHAREPOINT_MISSION_DEFAULT_MAXIMUM_BODY_BYTES,
) -> Agent365R0LiveSharePointQualificationReport:
    """Feed a live SharePoint authorization observation into the common R0 qualification."""

    t0 = (started_at or datetime.now(UTC)).astimezone(UTC)
    run_dir = Path(workdir) / expected_mission_id
    run_dir.mkdir(parents=True, exist_ok=True)

    with MicrosoftSharePointMissionHttpClient(
        profile,
        credential_material,
        timeout_seconds=timeout_seconds,
        maximum_response_bytes=maximum_response_bytes,
    ) as client:
        response = client.fetch_raw()

    source_dir = run_dir / "microsoft-sharepoint-source"
    envelope = retain_sharepoint_mission_source(
        response,
        profile,
        source_dir,
        requested_mission_id=expected_mission_id,
    )
    raw_path = source_dir / envelope.retained_filename
    retained_bytes = raw_path.read_bytes()
    observation = parse_retained_sharepoint_mission(
        envelope,
        retained_bytes,
        expected_authorization_material_sha256=expected_authorization_material_sha256,
    )

    downstream = run_agent365_r0_qualification_from_mission(
        workdir,
        observation.mission,
        started_at=t0,
        authorization_artifact_ref=envelope.payload_ref,
    )
    report = Agent365R0LiveSharePointQualificationReport(
        mission_id=observation.mission.mission_id,
        microsoft_source=envelope,
        downstream=downstream,
    )
    report_path = run_dir / "live-sharepoint-qualification-report.json"
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _retain_exact_bytes(path: Path, value: bytes) -> None:
    if path.exists():
        if path.read_bytes() != value:
            raise MicrosoftSharePointMissionSourceError(
                "retained source path already contains different bytes"
            )
        return
    path.write_bytes(value)


def _bounded_identifier(value: str, field_name: str) -> str:
    if not 1 <= len(value) <= _IDENTIFIER_MAXIMUM_CHARACTERS:
        raise ValueError(f"{field_name} is outside the qualified identifier bound")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{field_name} contains control data")
    return value


def _validate_json_content_type(value: str | None) -> str:
    if value is None:
        raise MicrosoftSharePointMissionTerminalError(
            "Microsoft Graph SharePoint mission response omitted Content-Type"
        )
    media_type = value.partition(";")[0].strip().lower()
    if media_type != "application/json" and not media_type.endswith("+json"):
        raise MicrosoftSharePointMissionTerminalError(
            "Microsoft Graph SharePoint mission response Content-Type is not JSON"
        )
    return value


def _retry_after_seconds(value: str | None) -> int:
    if value is None:
        return 1
    try:
        parsed = int(value)
    except ValueError:
        return 1
    return max(1, min(parsed, 3600))


__all__ = [
    "Agent365R0LiveSharePointQualificationReport",
    "MicrosoftSharePointMissionAuthenticationError",
    "MicrosoftSharePointMissionAuthorizationError",
    "MicrosoftSharePointMissionClientError",
    "MicrosoftSharePointMissionHttpClient",
    "MicrosoftSharePointMissionNotFoundError",
    "MicrosoftSharePointMissionResponseTooLargeError",
    "MicrosoftSharePointMissionRetryableError",
    "MicrosoftSharePointMissionSourceError",
    "MicrosoftSharePointMissionTerminalError",
    "MicrosoftSharePointMissionThrottleError",
    "SharePointMissionLiveObservationV1",
    "SharePointMissionRawResponse",
    "SharePointMissionReadProfile",
    "SharePointMissionSourceEnvelopeV1",
    "parse_retained_sharepoint_mission",
    "retain_sharepoint_mission_source",
    "run_agent365_r0_live_sharepoint_qualification",
    "sharepoint_mission_read_profile",
    "validate_sharepoint_mission_read_url",
]
