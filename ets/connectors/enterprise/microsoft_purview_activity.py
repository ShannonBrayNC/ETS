"""Microsoft Purview Management Activity content-discovery boundary for G2E-E.

Webhook notifications and polling results are discovery state only. Evidence candidates
are created only after a separately qualified retrieval of the referenced content blob.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast
from urllib.parse import SplitResult, parse_qs, quote, urlencode, urlsplit

from ets.connectors.enterprise.microsoft import MicrosoftCloud, MicrosoftTenantProfileV1

PurviewManagementPlan = Literal["enterprise", "gcc", "gcc_high", "dod"]
PurviewContentType = Literal[
    "Audit.AzureActiveDirectory",
    "Audit.Exchange",
    "Audit.SharePoint",
    "Audit.General",
    "DLP.All",
]
PurviewDiscoverySource = Literal["poll", "webhook"]

PURVIEW_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "Audit.AzureActiveDirectory",
        "Audit.Exchange",
        "Audit.SharePoint",
        "Audit.General",
        "DLP.All",
    }
)
PURVIEW_MAX_CONTENT_ID_CHARACTERS = 2000
PURVIEW_MAX_CONTENT_URI_CHARACTERS = 4096
PURVIEW_MAX_PAGE_URI_CHARACTERS = 4096
PURVIEW_MAX_DISCOVERY_RECORDS = 5000
_GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

_MANAGEMENT_ROOTS: dict[PurviewManagementPlan, str] = {
    "enterprise": "https://manage.office.com",
    "gcc": "https://manage-gcc.office.com",
    "gcc_high": "https://manage.office365.us",
    "dod": "https://manage.protection.apps.mil",
}


class MicrosoftPurviewActivityError(ValueError):
    """Raised when Management Activity discovery violates the qualified profile."""


@dataclass(frozen=True, slots=True)
class MicrosoftPurviewManagementProfile:
    """Server-owned Management Activity tenant, plan, and publisher boundary."""

    profile_id: str
    tenant_profile: MicrosoftTenantProfileV1
    plan: PurviewManagementPlan
    management_root: str
    publisher_identifier: str


@dataclass(frozen=True, slots=True)
class MicrosoftPurviewContentDescriptorV1:
    """One available content blob reference; this is not an audit event."""

    content_type: PurviewContentType
    content_id: str
    content_uri: str
    content_created_utc: datetime
    content_expiration_utc: datetime
    discovery_source: PurviewDiscoverySource


@dataclass(frozen=True, slots=True)
class MicrosoftPurviewDiscoveryPageV1:
    """Bounded discovery page with optional source-owned pagination state."""

    content_type: PurviewContentType
    descriptors: tuple[MicrosoftPurviewContentDescriptorV1, ...]
    next_page_uri: str | None
    discovery_source: PurviewDiscoverySource


def purview_management_profile(
    profile_id: str,
    tenant_profile: MicrosoftTenantProfileV1,
    *,
    plan: PurviewManagementPlan,
    publisher_identifier: str,
) -> MicrosoftPurviewManagementProfile:
    """Create one qualified server-owned Management Activity profile."""

    if not 1 <= len(profile_id) <= 128:
        raise ValueError("Purview management profile_id is outside the qualified bound")
    publisher_identifier = _canonical_guid(
        publisher_identifier,
        "publisher_identifier",
    )
    _validate_plan_for_cloud(tenant_profile.cloud, plan)
    return MicrosoftPurviewManagementProfile(
        profile_id=profile_id,
        tenant_profile=tenant_profile,
        plan=plan,
        management_root=_MANAGEMENT_ROOTS[plan],
        publisher_identifier=publisher_identifier,
    )


def build_purview_content_list_url(
    profile: MicrosoftPurviewManagementProfile,
    content_type: PurviewContentType,
    *,
    start_time_utc: datetime | None = None,
    end_time_utc: datetime | None = None,
) -> str:
    """Build a bounded polling URL for available content discovery."""

    content_type = _content_type(content_type)
    if (start_time_utc is None) != (end_time_utc is None):
        raise ValueError("Purview start_time_utc and end_time_utc must be supplied together")
    query: dict[str, str] = {
        "contentType": content_type,
        "PublisherIdentifier": profile.publisher_identifier,
    }
    if start_time_utc is not None and end_time_utc is not None:
        start = _aware_utc(start_time_utc, "start_time_utc")
        end = _aware_utc(end_time_utc, "end_time_utc")
        if end <= start:
            raise ValueError("Purview content discovery end time must follow start time")
        if (end - start).total_seconds() > 86_400:
            raise ValueError("Purview content discovery window must not exceed 24 hours")
        query["startTime"] = _format_utc(start)
        query["endTime"] = _format_utc(end)
    return f"{_tenant_activity_root(profile)}/subscriptions/content?" + urlencode(query)


def validate_purview_next_page_uri(
    profile: MicrosoftPurviewManagementProfile,
    content_type: PurviewContentType,
    value: str,
) -> str:
    """Revalidate Management Activity polling pagination before credential use."""

    if not 1 <= len(value) <= PURVIEW_MAX_PAGE_URI_CHARACTERS:
        raise MicrosoftPurviewActivityError(
            "Purview next-page URI exceeds the durable source-state bound"
        )
    parsed = _validate_management_origin(profile, value)
    allowed_paths = {
        f"/api/v1/{profile.tenant_profile.tenant_id}/activity/feed/subscriptions/content",
        f"/api/v1.0/{profile.tenant_profile.tenant_id}/activity/feed/subscriptions/content",
    }
    if parsed.path not in allowed_paths:
        raise MicrosoftPurviewActivityError(
            "Purview next-page URI escaped the approved content-discovery path"
        )
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=False)
    if query.get("contentType") != [content_type]:
        raise MicrosoftPurviewActivityError(
            "Purview next-page URI changed the approved content type"
        )
    publisher = query.get("PublisherIdentifier")
    if publisher is not None and publisher != [profile.publisher_identifier]:
        raise MicrosoftPurviewActivityError(
            "Purview next-page URI changed the server-owned publisher identifier"
        )
    return value


def validate_purview_content_uri(
    profile: MicrosoftPurviewManagementProfile,
    value: str,
) -> str:
    """Revalidate a source-provided contentUri before bearer credentials are sent."""

    if not 1 <= len(value) <= PURVIEW_MAX_CONTENT_URI_CHARACTERS:
        raise MicrosoftPurviewActivityError(
            "Purview contentUri exceeds the qualified URL bound"
        )
    parsed = _validate_management_origin(profile, value)
    prefixes = (
        f"/api/v1/{profile.tenant_profile.tenant_id}/activity/feed/audit/",
        f"/api/v1.0/{profile.tenant_profile.tenant_id}/activity/feed/audit/",
    )
    if not any(parsed.path.startswith(prefix) for prefix in prefixes):
        raise MicrosoftPurviewActivityError(
            "Purview contentUri escaped the approved tenant audit-content path"
        )
    if parsed.query:
        raise MicrosoftPurviewActivityError(
            "Purview contentUri contains unsupported query parameters"
        )
    return value


def parse_purview_discovery_page(
    value: object,
    profile: MicrosoftPurviewManagementProfile,
    content_type: PurviewContentType,
    *,
    discovery_source: PurviewDiscoverySource,
    next_page_uri: str | None = None,
    maximum_records: int = PURVIEW_MAX_DISCOVERY_RECORDS,
) -> MicrosoftPurviewDiscoveryPageV1:
    """Parse polling or webhook discovery without upgrading it to audit evidence."""

    content_type = _content_type(content_type)
    if not 1 <= maximum_records <= PURVIEW_MAX_DISCOVERY_RECORDS:
        raise ValueError("maximum_records exceeds the Purview discovery qualified bound")
    if not isinstance(value, list):
        raise MicrosoftPurviewActivityError("Purview discovery body must be a JSON array")
    if len(value) > maximum_records:
        raise MicrosoftPurviewActivityError(
            "Purview discovery body exceeds the configured record bound"
        )
    if next_page_uri is not None:
        if discovery_source != "poll":
            raise MicrosoftPurviewActivityError(
                "Purview webhook discovery must not carry polling pagination state"
            )
        next_page_uri = validate_purview_next_page_uri(
            profile,
            content_type,
            next_page_uri,
        )

    by_content_id: dict[str, MicrosoftPurviewContentDescriptorV1] = {}
    for raw in value:
        descriptor = _parse_descriptor(
            raw,
            profile,
            content_type,
            discovery_source,
        )
        existing = by_content_id.get(descriptor.content_id)
        if existing is None:
            by_content_id[descriptor.content_id] = descriptor
        elif existing != descriptor:
            raise MicrosoftPurviewActivityError(
                "Purview contentId repeated with conflicting immutable discovery state"
            )

    return MicrosoftPurviewDiscoveryPageV1(
        content_type=content_type,
        descriptors=tuple(by_content_id.values()),
        next_page_uri=next_page_uri,
        discovery_source=discovery_source,
    )


def _parse_descriptor(
    raw: object,
    profile: MicrosoftPurviewManagementProfile,
    content_type: PurviewContentType,
    discovery_source: PurviewDiscoverySource,
) -> MicrosoftPurviewContentDescriptorV1:
    if not isinstance(raw, dict):
        raise MicrosoftPurviewActivityError(
            "Purview discovery array contains a non-object value"
        )
    raw_content_type = raw.get("contentType")
    if raw_content_type != content_type:
        raise MicrosoftPurviewActivityError(
            "Purview discovery record changed the requested content type"
        )
    if discovery_source == "webhook":
        tenant_id = raw.get("tenantId")
        client_id = raw.get("clientId")
        if tenant_id != profile.tenant_profile.tenant_id:
            raise MicrosoftPurviewActivityError(
                "Purview webhook tenantId does not match server-owned tenant profile"
            )
        if client_id != profile.tenant_profile.application_id:
            raise MicrosoftPurviewActivityError(
                "Purview webhook clientId does not match server-owned application profile"
            )

    content_id = _bounded_string(raw.get("contentId"), "contentId", 2000)
    content_uri = validate_purview_content_uri(
        profile,
        _bounded_string(raw.get("contentUri"), "contentUri", 4096),
    )
    created = _parse_datetime(raw.get("contentCreated"), "contentCreated")
    expiration = _parse_datetime(raw.get("contentExpiration"), "contentExpiration")
    if expiration <= created:
        raise MicrosoftPurviewActivityError(
            "Purview content expiration must follow content availability time"
        )
    return MicrosoftPurviewContentDescriptorV1(
        content_type=content_type,
        content_id=content_id,
        content_uri=content_uri,
        content_created_utc=created,
        content_expiration_utc=expiration,
        discovery_source=discovery_source,
    )


def _tenant_activity_root(profile: MicrosoftPurviewManagementProfile) -> str:
    tenant_id = quote(profile.tenant_profile.tenant_id, safe="")
    return f"{profile.management_root}/api/v1.0/{tenant_id}/activity/feed"


def _validate_management_origin(
    profile: MicrosoftPurviewManagementProfile,
    value: str,
) -> SplitResult:
    root = urlsplit(profile.management_root)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != root.hostname:
        raise MicrosoftPurviewActivityError(
            "Purview source URI changed the server-owned management origin"
        )
    if parsed.port not in {None, 443}:
        raise MicrosoftPurviewActivityError(
            "Purview source URI changed the qualified management port"
        )
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise MicrosoftPurviewActivityError(
            "Purview source URI contains unsupported URL components"
        )
    return parsed


def _validate_plan_for_cloud(cloud: MicrosoftCloud, plan: PurviewManagementPlan) -> None:
    if cloud == "china_21vianet":
        raise ValueError(
            "Purview Management Activity is unsupported for China until a root is qualified"
        )
    allowed: dict[MicrosoftCloud, frozenset[PurviewManagementPlan]] = {
        "global": frozenset({"enterprise", "gcc"}),
        "us_government_l4": frozenset({"gcc_high"}),
        "us_government_l5_dod": frozenset({"dod"}),
        "china_21vianet": frozenset(),
    }
    if plan not in allowed[cloud]:
        raise ValueError("Purview management plan is incompatible with Microsoft cloud profile")


def _content_type(value: str) -> PurviewContentType:
    if value not in PURVIEW_CONTENT_TYPES:
        raise ValueError("unsupported Purview Management Activity content type")
    return cast(PurviewContentType, value)


def _canonical_guid(value: str, field_name: str) -> str:
    if _GUID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"Purview {field_name} must be a canonical GUID string")
    return value.lower()


def _bounded_string(value: object, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise MicrosoftPurviewActivityError(f"Purview {field_name} is invalid")
    return value


def _parse_datetime(value: object, field_name: str) -> datetime:
    text = _bounded_string(value, field_name, 100)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MicrosoftPurviewActivityError(f"Purview {field_name} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MicrosoftPurviewActivityError(
            f"Purview {field_name} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def _aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"Purview {field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
