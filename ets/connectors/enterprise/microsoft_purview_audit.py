"""Common-schema-first Microsoft Purview audit content normalization for G2E-E."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, cast

from pydantic import JsonValue

from ets.connectors.enterprise.microsoft_purview_activity import (
    MicrosoftPurviewContentDescriptorV1,
    MicrosoftPurviewManagementProfile,
    PurviewContentType,
)

PURVIEW_AUDIT_MAXIMUM_BODY_BYTES: Final = 16 * 1024 * 1024
PURVIEW_AUDIT_MAXIMUM_RECORDS: Final = 10_000
PURVIEW_AUDIT_MAXIMUM_SERVICE_FIELDS: Final = 32
PURVIEW_AUDIT_MAXIMUM_SERVICE_VALUE_BYTES: Final = 8192
PURVIEW_AUDIT_MAXIMUM_STRING_CHARACTERS: Final = 4096

_GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_COMMON_KEYS = frozenset(
    {
        "Id",
        "RecordType",
        "CreationTime",
        "Operation",
        "OrganizationId",
        "UserType",
        "UserKey",
        "Workload",
        "UserId",
        "ResultStatus",
        "ObjectId",
        "ClientIP",
        "Scope",
        "Version",
    }
)


class MicrosoftPurviewAuditError(ValueError):
    """Raised when a retrieved Purview audit blob violates the qualified profile."""


@dataclass(frozen=True, slots=True)
class MicrosoftPurviewAuditRecordV1:
    """Normalized common-schema audit observation with bounded service claims."""

    source_record_id: str
    record_type: int
    creation_time_utc: datetime
    operation: str
    organization_id: str
    user_type: int
    user_key: str
    workload: str
    user_id: str
    result_status: str | None
    object_id: str | None
    client_ip: str | None
    scope: int | None
    version: int | None
    content_type: PurviewContentType
    content_id: str
    service_specific: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class MicrosoftPurviewAuditContentV1:
    """One retrieved content blob after bounded parsing; raw bytes are not retained."""

    content_type: PurviewContentType
    content_id: str
    content_sha256: str
    content_created_utc: datetime
    content_expiration_utc: datetime
    records: tuple[MicrosoftPurviewAuditRecordV1, ...]


def parse_purview_audit_content(
    body: bytes,
    descriptor: MicrosoftPurviewContentDescriptorV1,
    profile: MicrosoftPurviewManagementProfile,
    *,
    service_specific_allowlist: frozenset[str] = frozenset(),
    include_client_ip: bool = False,
    maximum_body_bytes: int = PURVIEW_AUDIT_MAXIMUM_BODY_BYTES,
    maximum_records: int = PURVIEW_AUDIT_MAXIMUM_RECORDS,
) -> MicrosoftPurviewAuditContentV1:
    """Parse one content blob without retaining raw bytes or unapproved workload fields."""

    if not 1 <= maximum_body_bytes <= PURVIEW_AUDIT_MAXIMUM_BODY_BYTES:
        raise ValueError("maximum_body_bytes exceeds the Purview audit qualified bound")
    if not 1 <= maximum_records <= PURVIEW_AUDIT_MAXIMUM_RECORDS:
        raise ValueError("maximum_records exceeds the Purview audit qualified bound")
    if len(service_specific_allowlist) > PURVIEW_AUDIT_MAXIMUM_SERVICE_FIELDS:
        raise ValueError("Purview service-specific allowlist exceeds the qualified field bound")
    if any(
        not isinstance(key, str) or not 1 <= len(key) <= 128
        for key in service_specific_allowlist
    ):
        raise ValueError("Purview service-specific allowlist contains an invalid key")
    if service_specific_allowlist & _COMMON_KEYS:
        raise ValueError("Purview service-specific allowlist must not duplicate common fields")
    if len(body) > maximum_body_bytes:
        raise MicrosoftPurviewAuditError("Purview audit content exceeds configured byte bound")

    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftPurviewAuditError("Purview audit content is not valid UTF-8 JSON") from exc
    if not isinstance(decoded, list):
        raise MicrosoftPurviewAuditError("Purview audit content root must be an array")
    if len(decoded) > maximum_records:
        raise MicrosoftPurviewAuditError("Purview audit content exceeds configured record bound")

    by_id: dict[str, MicrosoftPurviewAuditRecordV1] = {}
    for raw in decoded:
        record = _parse_record(
            raw,
            descriptor,
            profile,
            service_specific_allowlist=service_specific_allowlist,
            include_client_ip=include_client_ip,
        )
        existing = by_id.get(record.source_record_id)
        if existing is None:
            by_id[record.source_record_id] = record
        elif existing != record:
            raise MicrosoftPurviewAuditError(
                "Purview audit record Id repeated with conflicting normalized content"
            )

    return MicrosoftPurviewAuditContentV1(
        content_type=descriptor.content_type,
        content_id=descriptor.content_id,
        content_sha256=hashlib.sha256(body).hexdigest(),
        content_created_utc=descriptor.content_created_utc,
        content_expiration_utc=descriptor.content_expiration_utc,
        records=tuple(by_id.values()),
    )


def _parse_record(
    raw: object,
    descriptor: MicrosoftPurviewContentDescriptorV1,
    profile: MicrosoftPurviewManagementProfile,
    *,
    service_specific_allowlist: frozenset[str],
    include_client_ip: bool,
) -> MicrosoftPurviewAuditRecordV1:
    if not isinstance(raw, dict):
        raise MicrosoftPurviewAuditError("Purview audit content contains a non-object record")

    source_record_id = _guid(raw.get("Id"), "Id")
    record_type = _bounded_int(raw.get("RecordType"), "RecordType", minimum=0)
    creation_time = _timestamp(raw.get("CreationTime"), "CreationTime")
    operation = _string(raw.get("Operation"), "Operation", 1000)
    organization_id = _guid(raw.get("OrganizationId"), "OrganizationId")
    if organization_id.casefold() != profile.tenant_profile.tenant_id.casefold():
        raise MicrosoftPurviewAuditError(
            "Purview audit OrganizationId does not match server-owned tenant profile"
        )
    user_type = _bounded_int(raw.get("UserType"), "UserType", minimum=0)
    user_key = _string(raw.get("UserKey"), "UserKey", PURVIEW_AUDIT_MAXIMUM_STRING_CHARACTERS)
    workload = _string(raw.get("Workload"), "Workload", 500)
    user_id = _string(raw.get("UserId"), "UserId", PURVIEW_AUDIT_MAXIMUM_STRING_CHARACTERS)
    result_status = _optional_string(raw.get("ResultStatus"), "ResultStatus", 1000)
    object_id = _optional_string(
        raw.get("ObjectId"),
        "ObjectId",
        PURVIEW_AUDIT_MAXIMUM_STRING_CHARACTERS,
    )
    client_ip = (
        _optional_string(raw.get("ClientIP"), "ClientIP", 200)
        if include_client_ip
        else None
    )
    scope = _optional_int(raw.get("Scope"), "Scope", minimum=0)
    version = _optional_int(raw.get("Version"), "Version", minimum=0)

    service_specific: dict[str, JsonValue] = {}
    for key in sorted(service_specific_allowlist):
        if key not in raw:
            continue
        value = raw[key]
        _validate_json_value(key, value)
        service_specific[key] = cast(JsonValue, value)

    return MicrosoftPurviewAuditRecordV1(
        source_record_id=source_record_id,
        record_type=record_type,
        creation_time_utc=creation_time,
        operation=operation,
        organization_id=organization_id,
        user_type=user_type,
        user_key=user_key,
        workload=workload,
        user_id=user_id,
        result_status=result_status,
        object_id=object_id,
        client_ip=client_ip,
        scope=scope,
        version=version,
        content_type=descriptor.content_type,
        content_id=descriptor.content_id,
        service_specific=service_specific,
    )


def _guid(value: object, field_name: str) -> str:
    text = _string(value, field_name, 36)
    if _GUID_PATTERN.fullmatch(text) is None:
        raise MicrosoftPurviewAuditError(f"Purview audit {field_name} is not a GUID")
    return text.lower()


def _string(value: object, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise MicrosoftPurviewAuditError(f"Purview audit {field_name} is invalid")
    return value


def _optional_string(value: object, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    return _string(value, field_name, maximum)


def _bounded_int(value: object, field_name: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MicrosoftPurviewAuditError(f"Purview audit {field_name} is invalid")
    return value


def _optional_int(value: object, field_name: str, *, minimum: int) -> int | None:
    if value is None:
        return None
    return _bounded_int(value, field_name, minimum=minimum)


def _timestamp(value: object, field_name: str) -> datetime:
    text = _string(value, field_name, 100)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MicrosoftPurviewAuditError(f"Purview audit {field_name} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MicrosoftPurviewAuditError(
            f"Purview audit {field_name} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def _validate_json_value(key: str, value: object) -> None:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MicrosoftPurviewAuditError(
            f"Purview service-specific field {key} is not JSON-native"
        ) from exc
    if len(encoded) > PURVIEW_AUDIT_MAXIMUM_SERVICE_VALUE_BYTES:
        raise MicrosoftPurviewAuditError(
            f"Purview service-specific field {key} exceeds the qualified byte bound"
        )
