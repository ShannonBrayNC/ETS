"""Microsoft Agent 365 inventory/source-preservation boundary for A365-Q0."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AGENT365_DEFAULT_MAXIMUM_BODY_BYTES = 8 * 1024 * 1024
AGENT365_ENDPOINT_FAMILY = "copilot.admin.catalog.packages"
AGENT365_LIST_PATH = "/copilot/admin/catalog/packages"
AGENT365_SOURCE_ENVELOPE_SCHEMA_VERSION = "ets.connector.microsoft.agent365.source_envelope.v1"
AGENT365_PACKAGE_SCHEMA_VERSION = "ets.connector.microsoft.agent365.package.v1"
AGENT365_INVENTORY_PAGE_SCHEMA_VERSION = "ets.connector.microsoft.agent365.inventory_page.v1"
AGENT365_DETAIL_SCHEMA_VERSION = "ets.connector.microsoft.agent365.package_detail.v1"

_GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

Agent365SourceType = Literal[
    "agent365.package_inventory",
    "agent365.package_detail",
]
Agent365ApiMaturity = Literal["stable", "documented_preview", "beta", "unknown"]
Agent365PayloadRetention = Literal["inline", "protected_reference", "digest_only"]


class MicrosoftAgent365SourceError(ValueError):
    """Raised when an Agent 365 source response violates the bounded A365-Q0 contract."""


class StrictAgent365Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftSourceEnvelopeV1(StrictAgent365Model):
    """Immutable source-preservation envelope created before ETS interpretation."""

    schema_version: Literal["ets.connector.microsoft.agent365.source_envelope.v1"] = (
        AGENT365_SOURCE_ENVELOPE_SCHEMA_VERSION
    )
    source: Literal["microsoft.agent365"] = "microsoft.agent365"
    source_type: Agent365SourceType
    tenant_id: str = Field(min_length=36, max_length=36)
    acquisition_time: datetime
    microsoft_event_time: datetime | None = None
    api_version: str = Field(min_length=1, max_length=32)
    api_maturity: Agent365ApiMaturity
    endpoint_family: Literal["copilot.admin.catalog.packages"] = AGENT365_ENDPOINT_FAMILY
    request_path: str = Field(min_length=1, max_length=2048)
    payload_retention: Agent365PayloadRetention
    raw_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_payload_utf8: str | None = None
    protected_payload_reference: str | None = Field(default=None, min_length=1, max_length=2048)
    collector_identity: str = Field(min_length=1, max_length=256)
    collector_version: str = Field(min_length=1, max_length=128)
    acquisition_sequence: int = Field(ge=0)
    previous_envelope_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    envelope_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("tenant_id")
    @classmethod
    def normalize_tenant_id(cls, value: str) -> str:
        if _GUID_PATTERN.fullmatch(value) is None:
            raise ValueError("tenant_id must be a canonical GUID string")
        return value.lower()

    @field_validator("acquisition_time", "microsoft_event_time")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Agent 365 envelope times must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_retention_shape(self) -> "MicrosoftSourceEnvelopeV1":
        if self.payload_retention == "inline":
            if self.raw_payload_utf8 is None or self.protected_payload_reference is not None:
                raise ValueError("inline retention requires raw_payload_utf8 only")
        elif self.payload_retention == "protected_reference":
            if self.protected_payload_reference is None or self.raw_payload_utf8 is not None:
                raise ValueError(
                    "protected_reference retention requires protected_payload_reference only"
                )
        elif self.payload_retention == "digest_only":
            if self.raw_payload_utf8 is not None or self.protected_payload_reference is not None:
                raise ValueError("digest_only retention cannot include payload material")
        return self


class MicrosoftAgent365PackageV1(StrictAgent365Model):
    """Normalized package summary while the source envelope retains the original record."""

    schema_version: Literal["ets.connector.microsoft.agent365.package.v1"] = (
        AGENT365_PACKAGE_SCHEMA_VERSION
    )
    package_id: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, max_length=1024)
    package_type: str | None = Field(default=None, max_length=128)
    is_blocked: bool | None = None
    supported_hosts: tuple[str, ...] = ()
    element_types: tuple[str, ...] = ()
    publisher: str | None = Field(default=None, max_length=1024)
    platform: str | None = Field(default=None, max_length=512)
    version: str | None = Field(default=None, max_length=256)
    manifest_version: str | None = Field(default=None, max_length=256)
    manifest_id: str | None = Field(default=None, max_length=1024)
    app_id: str | None = Field(default=None, max_length=512)
    asset_id: str | None = Field(default=None, max_length=1024)
    available_to: str | None = Field(default=None, max_length=128)
    deployed_to: str | None = Field(default=None, max_length=128)
    last_modified_date_time: datetime | None = None
    source_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalized_configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    unknown_field_names: tuple[str, ...] = ()

    @field_validator("last_modified_date_time")
    @classmethod
    def normalize_modified_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("last_modified_date_time must be timezone-aware")
        return value.astimezone(UTC)


class MicrosoftAgent365InventoryPageV1(StrictAgent365Model):
    schema_version: Literal["ets.connector.microsoft.agent365.inventory_page.v1"] = (
        AGENT365_INVENTORY_PAGE_SCHEMA_VERSION
    )
    packages: tuple[MicrosoftAgent365PackageV1, ...]
    next_link: str | None = Field(default=None, max_length=4096)


class MicrosoftAgent365PackageDetailV1(StrictAgent365Model):
    schema_version: Literal["ets.connector.microsoft.agent365.package_detail.v1"] = (
        AGENT365_DETAIL_SCHEMA_VERSION
    )
    package: MicrosoftAgent365PackageV1
    long_description_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    sensitivity: str | None = Field(default=None, max_length=256)
    categories: tuple[str, ...] = ()
    allowed_principal_count: int = Field(ge=0)
    acquire_principal_count: int = Field(ge=0)
    element_detail_count: int = Field(ge=0)
    detail_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    unknown_detail_field_names: tuple[str, ...] = ()


def agent365_packages_url(*, api_version: Literal["v1.0", "beta"] = "v1.0") -> str:
    """Return the documented Global-service package inventory endpoint."""

    return f"https://graph.microsoft.com/{api_version}{AGENT365_LIST_PATH}"


def agent365_package_detail_url(
    package_id: str,
    *,
    api_version: Literal["v1.0", "beta"] = "v1.0",
) -> str:
    """Return one package-detail endpoint without accepting arbitrary source URLs."""

    if not package_id or len(package_id) > 512:
        raise ValueError("package_id is outside the bounded Agent 365 profile")
    if "/" in package_id or "?" in package_id or "#" in package_id:
        raise ValueError("package_id contains URL-structural characters")
    return f"{agent365_packages_url(api_version=api_version)}/{package_id}"


def build_source_envelope(
    payload: bytes,
    *,
    source_type: Agent365SourceType,
    tenant_id: str,
    acquisition_time: datetime,
    api_version: str,
    api_maturity: Agent365ApiMaturity,
    request_path: str,
    collector_identity: str,
    collector_version: str,
    acquisition_sequence: int,
    microsoft_event_time: datetime | None = None,
    previous_envelope_hash: str | None = None,
    payload_retention: Agent365PayloadRetention = "inline",
    protected_payload_reference: str | None = None,
    maximum_body_bytes: int = AGENT365_DEFAULT_MAXIMUM_BODY_BYTES,
) -> MicrosoftSourceEnvelopeV1:
    """Hash exact source bytes and create a deterministic chainable source envelope."""

    if not 1 <= maximum_body_bytes <= 64 * 1024 * 1024:
        raise ValueError("maximum_body_bytes is outside the qualified bound")
    if not payload:
        raise MicrosoftAgent365SourceError("Agent 365 source payload is empty")
    if len(payload) > maximum_body_bytes:
        raise MicrosoftAgent365SourceError("Agent 365 source payload exceeds configured bound")
    try:
        payload_text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MicrosoftAgent365SourceError("Agent 365 source payload is not UTF-8") from exc

    raw_digest = hashlib.sha256(payload).hexdigest()
    if payload_retention == "inline":
        retained_payload = payload_text
        protected_reference = None
    elif payload_retention == "protected_reference":
        if not protected_payload_reference:
            raise ValueError(
                "protected_payload_reference is required for protected_reference retention"
            )
        retained_payload = None
        protected_reference = protected_payload_reference
    else:
        retained_payload = None
        protected_reference = None

    normalized_acquisition_time = _normalize_datetime(acquisition_time, "acquisition_time")
    normalized_event_time = (
        None
        if microsoft_event_time is None
        else _normalize_datetime(microsoft_event_time, "microsoft_event_time")
    )
    normalized_tenant = _normalize_guid(tenant_id, "tenant_id")

    envelope_material = {
        "schema_version": AGENT365_SOURCE_ENVELOPE_SCHEMA_VERSION,
        "source": "microsoft.agent365",
        "source_type": source_type,
        "tenant_id": normalized_tenant,
        "acquisition_time": normalized_acquisition_time.isoformat(),
        "microsoft_event_time": (
            normalized_event_time.isoformat() if normalized_event_time is not None else None
        ),
        "api_version": api_version,
        "api_maturity": api_maturity,
        "endpoint_family": AGENT365_ENDPOINT_FAMILY,
        "request_path": request_path,
        "payload_retention": payload_retention,
        "raw_payload_sha256": raw_digest,
        "collector_identity": collector_identity,
        "collector_version": collector_version,
        "acquisition_sequence": acquisition_sequence,
        "previous_envelope_hash": previous_envelope_hash,
    }
    envelope_hash = _sha256_canonical(envelope_material)

    return MicrosoftSourceEnvelopeV1(
        source_type=source_type,
        tenant_id=normalized_tenant,
        acquisition_time=normalized_acquisition_time,
        microsoft_event_time=normalized_event_time,
        api_version=api_version,
        api_maturity=api_maturity,
        request_path=request_path,
        payload_retention=payload_retention,
        raw_payload_sha256=raw_digest,
        raw_payload_utf8=retained_payload,
        protected_payload_reference=protected_reference,
        collector_identity=collector_identity,
        collector_version=collector_version,
        acquisition_sequence=acquisition_sequence,
        previous_envelope_hash=previous_envelope_hash,
        envelope_hash=envelope_hash,
    )


def parse_agent365_inventory_response(
    payload: bytes,
    *,
    maximum_body_bytes: int = AGENT365_DEFAULT_MAXIMUM_BODY_BYTES,
) -> MicrosoftAgent365InventoryPageV1:
    """Parse a documented package inventory response while tolerating unknown source fields."""

    decoded = _decode_json_object(payload, maximum_body_bytes=maximum_body_bytes)
    values = decoded.get("value")
    if not isinstance(values, list):
        raise MicrosoftAgent365SourceError("Agent 365 inventory response value must be an array")

    packages: list[MicrosoftAgent365PackageV1] = []
    for raw in values:
        if not isinstance(raw, Mapping):
            raise MicrosoftAgent365SourceError(
                "Agent 365 inventory response contains a non-object package"
            )
        packages.append(_normalize_package(raw))

    next_link = decoded.get("@odata.nextLink")
    if next_link is not None and not isinstance(next_link, str):
        raise MicrosoftAgent365SourceError("@odata.nextLink must be a string when present")

    return MicrosoftAgent365InventoryPageV1(
        packages=tuple(packages),
        next_link=next_link,
    )


def parse_agent365_package_detail(
    payload: bytes,
    *,
    maximum_body_bytes: int = AGENT365_DEFAULT_MAXIMUM_BODY_BYTES,
) -> MicrosoftAgent365PackageDetailV1:
    """Parse one package-detail response; full source bytes remain in the SourceEnvelope."""

    decoded = _decode_json_object(payload, maximum_body_bytes=maximum_body_bytes)
    package = _normalize_package(decoded)

    long_description = decoded.get("longDescription")
    long_description_sha256 = (
        hashlib.sha256(long_description.encode("utf-8")).hexdigest()
        if isinstance(long_description, str)
        else None
    )
    sensitivity = _optional_string(decoded.get("sensitivity"), maximum=256)
    categories = _string_tuple(decoded.get("categories"), maximum_items=256)
    allowed_count = _object_array_count(decoded.get("allowedUsersAndGroups"))
    acquire_count = _object_array_count(decoded.get("acquireUsersAndGroups"))
    element_detail_count = _object_array_count(decoded.get("elementDetails"))

    detail_known_fields = _PACKAGE_KNOWN_FIELDS | {
        "longDescription",
        "categories",
        "sensitivity",
        "allowedUsersAndGroups",
        "acquireUsersAndGroups",
        "elementDetails",
        "@odata.context",
    }
    unknown = tuple(sorted(str(key) for key in decoded if key not in detail_known_fields))

    return MicrosoftAgent365PackageDetailV1(
        package=package,
        long_description_sha256=long_description_sha256,
        sensitivity=sensitivity,
        categories=categories,
        allowed_principal_count=allowed_count,
        acquire_principal_count=acquire_count,
        element_detail_count=element_detail_count,
        detail_sha256=_sha256_canonical(decoded),
        unknown_detail_field_names=unknown,
    )


_PACKAGE_KNOWN_FIELDS = {
    "id",
    "displayName",
    "type",
    "shortDescription",
    "isBlocked",
    "supportedHosts",
    "lastModifiedDateTime",
    "publisher",
    "availableTo",
    "deployedTo",
    "elementTypes",
    "platform",
    "version",
    "manifestVersion",
    "manifestId",
    "appId",
    "assetId",
}


def _normalize_package(raw: Mapping[str, object]) -> MicrosoftAgent365PackageV1:
    package_id = raw.get("id")
    if not isinstance(package_id, str) or not 1 <= len(package_id) <= 512:
        raise MicrosoftAgent365SourceError("Agent 365 package id is invalid")

    is_blocked = raw.get("isBlocked")
    if is_blocked is not None and not isinstance(is_blocked, bool):
        raise MicrosoftAgent365SourceError("Agent 365 package isBlocked must be boolean")

    modified = _optional_datetime(raw.get("lastModifiedDateTime"))
    supported_hosts = _string_tuple(raw.get("supportedHosts"), maximum_items=128)
    element_types = _string_tuple(raw.get("elementTypes"), maximum_items=128)

    normalized_material = {
        "id": package_id,
        "displayName": _optional_string(raw.get("displayName"), maximum=1024),
        "type": _optional_string(raw.get("type"), maximum=128),
        "isBlocked": is_blocked,
        "supportedHosts": supported_hosts,
        "publisher": _optional_string(raw.get("publisher"), maximum=1024),
        "availableTo": _optional_string(raw.get("availableTo"), maximum=128),
        "deployedTo": _optional_string(raw.get("deployedTo"), maximum=128),
        "elementTypes": element_types,
        "platform": _optional_string(raw.get("platform"), maximum=512),
        "version": _optional_string(raw.get("version"), maximum=256),
        "manifestVersion": _optional_string(raw.get("manifestVersion"), maximum=256),
        "manifestId": _optional_string(raw.get("manifestId"), maximum=1024),
        "appId": _optional_string(raw.get("appId"), maximum=512),
        "assetId": _optional_string(raw.get("assetId"), maximum=1024),
        "lastModifiedDateTime": modified.isoformat() if modified is not None else None,
    }

    unknown = tuple(
        sorted(
            str(key)
            for key in raw
            if key not in _PACKAGE_KNOWN_FIELDS and not str(key).startswith("@odata.")
        )
    )

    return MicrosoftAgent365PackageV1(
        package_id=package_id,
        display_name=normalized_material["displayName"],
        package_type=normalized_material["type"],
        is_blocked=is_blocked,
        supported_hosts=supported_hosts,
        element_types=element_types,
        publisher=normalized_material["publisher"],
        platform=normalized_material["platform"],
        version=normalized_material["version"],
        manifest_version=normalized_material["manifestVersion"],
        manifest_id=normalized_material["manifestId"],
        app_id=normalized_material["appId"],
        asset_id=normalized_material["assetId"],
        available_to=normalized_material["availableTo"],
        deployed_to=normalized_material["deployedTo"],
        last_modified_date_time=modified,
        source_record_sha256=_sha256_canonical(raw),
        normalized_configuration_sha256=_sha256_canonical(normalized_material),
        unknown_field_names=unknown,
    )


def _decode_json_object(payload: bytes, *, maximum_body_bytes: int) -> dict[str, object]:
    if not 1 <= maximum_body_bytes <= 64 * 1024 * 1024:
        raise ValueError("maximum_body_bytes is outside the qualified bound")
    if not payload:
        raise MicrosoftAgent365SourceError("Agent 365 response body is empty")
    if len(payload) > maximum_body_bytes:
        raise MicrosoftAgent365SourceError("Agent 365 response exceeds configured byte bound")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftAgent365SourceError("Agent 365 response is not valid UTF-8 JSON") from exc
    if not isinstance(decoded, dict):
        raise MicrosoftAgent365SourceError("Agent 365 response root must be an object")
    return decoded


def _optional_string(value: object, *, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > maximum:
        raise MicrosoftAgent365SourceError("Agent 365 string field is outside the bounded profile")
    return value


def _string_tuple(value: object, *, maximum_items: int) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > maximum_items:
        raise MicrosoftAgent365SourceError("Agent 365 array field is outside the bounded profile")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or len(item) > 1024:
            raise MicrosoftAgent365SourceError(
                "Agent 365 string-array item is outside the bounded profile"
            )
        result.append(item)
    return tuple(result)


def _object_array_count(value: object) -> int:
    if value is None:
        return 0
    if not isinstance(value, list) or len(value) > 4096:
        raise MicrosoftAgent365SourceError(
            "Agent 365 object-array field is outside the bounded profile"
        )
    if any(not isinstance(item, Mapping) for item in value):
        raise MicrosoftAgent365SourceError("Agent 365 object-array contains a non-object item")
    return len(value)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MicrosoftAgent365SourceError("Agent 365 datetime field must be a string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MicrosoftAgent365SourceError("Agent 365 datetime field is invalid") from exc
    return _normalize_datetime(parsed, "Agent 365 datetime field")


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _normalize_guid(value: str, field_name: str) -> str:
    if _GUID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical GUID string")
    return value.lower()


def _sha256_canonical(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")
