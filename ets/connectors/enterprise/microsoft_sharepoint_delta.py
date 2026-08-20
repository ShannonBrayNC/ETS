"""Bounded Microsoft Graph SharePoint/OneDrive metadata delta boundary for G2E-D.

This module treats Graph delta as a latest-state metadata feed, not an audit history.
It never downloads file content and does not infer actor identity, rename, move, restore,
or source completeness from a single delta page.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Literal
from urllib.parse import quote, urlsplit

from pydantic import JsonValue

from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1

SHAREPOINT_DELTA_DEFAULT_MAXIMUM_BODY_BYTES: Final = 1024 * 1024
SHAREPOINT_DELTA_DEFAULT_MAXIMUM_RECORDS: Final = 1000
SHAREPOINT_DELTA_MAXIMUM_CHECKPOINT_CHARACTERS: Final = 4000
SHAREPOINT_DELTA_MAXIMUM_IDENTIFIER_CHARACTERS: Final = 500
SHAREPOINT_DELTA_MAXIMUM_SOURCE_HASH_CHARACTERS: Final = 1024

SharePointDeltaScope = Literal["drive", "list"]


class MicrosoftSharePointDeltaError(ValueError):
    """Raised when a Graph metadata delta response violates the qualified profile."""


@dataclass(frozen=True, slots=True)
class MicrosoftSharePointDeltaRequestProfile:
    """Server-owned Graph origin and approved delta resource path."""

    tenant_profile_id: str
    cloud: str
    graph_root: str
    scope: SharePointDeltaScope
    resource_path: str
    initial_url: str


@dataclass(frozen=True, slots=True)
class MicrosoftSharePointDeltaRecordV1:
    """Minimized latest-state metadata observation for one Graph object."""

    source_record_id: str
    object_id: str
    scope: SharePointDeltaScope
    deleted: bool
    source_modified_at_utc: datetime | None
    metadata: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class MicrosoftSharePointDeltaPageV1:
    """One bounded delta page with opaque source-controlled continuation state."""

    scope: SharePointDeltaScope
    records: tuple[MicrosoftSharePointDeltaRecordV1, ...]
    checkpoint_url: str
    cycle_complete: bool


def sharepoint_drive_delta_request_profile(
    tenant_profile_id: str,
    tenant_profile: MicrosoftTenantProfileV1,
    drive_id: str,
) -> MicrosoftSharePointDeltaRequestProfile:
    """Build a server-owned drive root delta profile."""

    drive_id = _bounded_identifier(drive_id, "drive_id")
    path = f"/v1.0/drives/{quote(drive_id, safe='')}/root/delta"
    return _request_profile(tenant_profile_id, tenant_profile, "drive", path)


def sharepoint_list_delta_request_profile(
    tenant_profile_id: str,
    tenant_profile: MicrosoftTenantProfileV1,
    site_id: str,
    list_id: str,
) -> MicrosoftSharePointDeltaRequestProfile:
    """Build a server-owned SharePoint list item delta profile."""

    site_id = _bounded_identifier(site_id, "site_id")
    list_id = _bounded_identifier(list_id, "list_id")
    path = (
        f"/v1.0/sites/{quote(site_id, safe='')}/lists/"
        f"{quote(list_id, safe='')}/items/delta"
    )
    return _request_profile(tenant_profile_id, tenant_profile, "list", path)


def validate_sharepoint_delta_url(
    profile: MicrosoftSharePointDeltaRequestProfile,
    value: str,
) -> str:
    """Revalidate every source continuation before credentials may be sent."""

    if not 1 <= len(value) <= SHAREPOINT_DELTA_MAXIMUM_CHECKPOINT_CHARACTERS:
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta continuation exceeds the durable checkpoint bound"
        )
    root = urlsplit(profile.graph_root)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname != root.hostname:
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta continuation changed the server-owned Graph origin"
        )
    if parsed.port not in {None, 443}:
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta continuation changed the qualified Graph port"
        )
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta continuation contains unsupported URL components"
        )
    if not _continuation_path_matches_resource(profile.resource_path, parsed.path):
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta continuation escaped the approved resource path"
        )
    return value


def _continuation_path_matches_resource(resource_path: str, candidate_path: str) -> bool:
    """Allow Graph's documented opaque continuations on the approved delta resource."""

    approved_resources = [resource_path]
    drive_root_suffix = "/root/delta"
    if resource_path.startswith("/v1.0/drives/") and resource_path.endswith(
        drive_root_suffix
    ):
        approved_resources.append(
            resource_path[: -len(drive_root_suffix)] + "/delta"
        )

    for approved_resource in approved_resources:
        if candidate_path == approved_resource:
            return True
        if not candidate_path.startswith(approved_resource):
            continue
        suffix = candidate_path[len(approved_resource) :]
        if suffix.startswith("(") and suffix.endswith(")") and "/" not in suffix:
            return True
    return False


def parse_sharepoint_delta_page(
    body: bytes,
    profile: MicrosoftSharePointDeltaRequestProfile,
    *,
    maximum_body_bytes: int = SHAREPOINT_DELTA_DEFAULT_MAXIMUM_BODY_BYTES,
    maximum_records: int = SHAREPOINT_DELTA_DEFAULT_MAXIMUM_RECORDS,
) -> MicrosoftSharePointDeltaPageV1:
    """Decode one Graph delta page into minimized metadata-only observations."""

    if not 1 <= maximum_body_bytes <= SHAREPOINT_DELTA_DEFAULT_MAXIMUM_BODY_BYTES:
        raise ValueError("maximum_body_bytes exceeds the SharePoint delta qualified bound")
    if not 1 <= maximum_records <= SHAREPOINT_DELTA_DEFAULT_MAXIMUM_RECORDS:
        raise ValueError("maximum_records exceeds the SharePoint delta qualified bound")
    if len(body) > maximum_body_bytes:
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta response exceeds configured byte bound"
        )
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta response is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise MicrosoftSharePointDeltaError("Microsoft Graph delta response must be an object")

    raw_records = decoded.get("value")
    if not isinstance(raw_records, list):
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta response value must be an array"
        )
    if len(raw_records) > maximum_records:
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta response exceeds configured record bound"
        )

    next_link = decoded.get("@odata.nextLink")
    delta_link = decoded.get("@odata.deltaLink")
    if (next_link is None) == (delta_link is None):
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta page must expose exactly one nextLink or deltaLink"
        )
    continuation = next_link if next_link is not None else delta_link
    if not isinstance(continuation, str):
        raise MicrosoftSharePointDeltaError(
            "Microsoft Graph delta continuation must be a string"
        )
    checkpoint_url = validate_sharepoint_delta_url(profile, continuation)

    records: list[MicrosoftSharePointDeltaRecordV1] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise MicrosoftSharePointDeltaError(
                "Microsoft Graph delta array contains a non-object value"
            )
        records.append(_minimize_record(raw, profile.scope))

    return MicrosoftSharePointDeltaPageV1(
        scope=profile.scope,
        records=tuple(records),
        checkpoint_url=checkpoint_url,
        cycle_complete=delta_link is not None,
    )


def _request_profile(
    tenant_profile_id: str,
    tenant_profile: MicrosoftTenantProfileV1,
    scope: SharePointDeltaScope,
    path: str,
) -> MicrosoftSharePointDeltaRequestProfile:
    tenant_profile_id = _bounded_identifier(tenant_profile_id, "tenant_profile_id")
    graph_root = tenant_profile.endpoints.graph_root.rstrip("/")
    root = urlsplit(graph_root)
    if root.scheme != "https" or not root.hostname or root.path:
        raise ValueError("Microsoft tenant profile Graph root is not a qualified HTTPS origin")
    initial_url = f"{graph_root}{path}"
    return MicrosoftSharePointDeltaRequestProfile(
        tenant_profile_id=tenant_profile_id,
        cloud=tenant_profile.cloud,
        graph_root=graph_root,
        scope=scope,
        resource_path=path,
        initial_url=initial_url,
    )


def _minimize_record(
    raw: dict[str, object],
    scope: SharePointDeltaScope,
) -> MicrosoftSharePointDeltaRecordV1:
    object_id = _required_string(raw, "id", SHAREPOINT_DELTA_MAXIMUM_IDENTIFIER_CHARACTERS)
    metadata: dict[str, JsonValue] = {}

    _copy_bounded_string(raw, metadata, "name", 1024)
    _copy_bounded_string(raw, metadata, "eTag", 1000, output_key="etag")
    _copy_bounded_string(raw, metadata, "cTag", 1000, output_key="ctag")
    _copy_bounded_int(raw, metadata, "size", minimum=0)

    created = _optional_datetime(raw.get("createdDateTime"), "createdDateTime")
    modified = _optional_datetime(raw.get("lastModifiedDateTime"), "lastModifiedDateTime")
    if created is not None:
        metadata["created_at_utc"] = _format_utc(created)
    if modified is not None:
        metadata["modified_at_utc"] = _format_utc(modified)

    parent = raw.get("parentReference")
    if parent is not None:
        if not isinstance(parent, dict):
            raise MicrosoftSharePointDeltaError("parentReference must be an object")
        minimized_parent: dict[str, JsonValue] = {}
        for source_key, output_key in (
            ("id", "id"),
            ("driveId", "drive_id"),
            ("siteId", "site_id"),
            ("listId", "list_id"),
            ("path", "path"),
        ):
            _copy_bounded_string(parent, minimized_parent, source_key, 2048, output_key=output_key)
        if minimized_parent:
            metadata["parent"] = minimized_parent

    file_facet = raw.get("file")
    if file_facet is not None:
        if not isinstance(file_facet, dict):
            raise MicrosoftSharePointDeltaError("file facet must be an object")
        minimized_file: dict[str, JsonValue] = {}
        _copy_bounded_string(file_facet, minimized_file, "mimeType", 500, output_key="mime_type")
        _copy_minimized_file_hashes(file_facet, minimized_file)
        metadata["file"] = minimized_file

    folder_facet = raw.get("folder")
    if folder_facet is not None:
        if not isinstance(folder_facet, dict):
            raise MicrosoftSharePointDeltaError("folder facet must be an object")
        minimized_folder: dict[str, JsonValue] = {}
        _copy_bounded_int(folder_facet, minimized_folder, "childCount", minimum=0)
        metadata["folder"] = minimized_folder

    package_facet = raw.get("package")
    if package_facet is not None:
        if not isinstance(package_facet, dict):
            raise MicrosoftSharePointDeltaError("package facet must be an object")
        minimized_package: dict[str, JsonValue] = {}
        _copy_bounded_string(package_facet, minimized_package, "type", 200)
        metadata["package"] = minimized_package

    content_type = raw.get("contentType")
    if content_type is not None:
        if not isinstance(content_type, dict):
            raise MicrosoftSharePointDeltaError("contentType must be an object")
        minimized_content_type: dict[str, JsonValue] = {}
        _copy_bounded_string(content_type, minimized_content_type, "id", 500)
        _copy_bounded_string(content_type, minimized_content_type, "name", 500)
        if minimized_content_type:
            metadata["content_type"] = minimized_content_type

    _copy_minimized_sharing(raw, metadata)

    deleted = "deleted" in raw
    if deleted:
        deleted_facet = raw.get("deleted")
        if deleted_facet is not None and not isinstance(deleted_facet, dict):
            raise MicrosoftSharePointDeltaError("deleted facet must be an object")
        metadata["deleted"] = True

    fingerprint = hashlib.sha256(
        json.dumps(
            {"scope": scope, "object_id": object_id, "metadata": metadata},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    source_record_id = f"{scope}:{object_id}:{fingerprint[:32]}"

    return MicrosoftSharePointDeltaRecordV1(
        source_record_id=source_record_id,
        object_id=object_id,
        scope=scope,
        deleted=deleted,
        source_modified_at_utc=modified,
        metadata=metadata,
    )


def _copy_minimized_file_hashes(
    file_facet: dict[str, object],
    minimized_file: dict[str, JsonValue],
) -> None:
    """Copy supported source-reported hashes without retrieving file content."""

    hashes = file_facet.get("hashes")
    if hashes is None:
        return
    if not isinstance(hashes, dict):
        raise MicrosoftSharePointDeltaError("file hashes facet must be an object")

    minimized_hashes: dict[str, JsonValue] = {}
    for source_key, output_key in (
        ("crc32Hash", "crc32_hash"),
        ("quickXorHash", "quick_xor_hash"),
        ("sha1Hash", "sha1_hash"),
    ):
        _copy_bounded_string(
            hashes,
            minimized_hashes,
            source_key,
            SHAREPOINT_DELTA_MAXIMUM_SOURCE_HASH_CHARACTERS,
            output_key=output_key,
        )
    if minimized_hashes:
        minimized_file["hashes"] = minimized_hashes


def _copy_minimized_sharing(
    raw: dict[str, object],
    metadata: dict[str, JsonValue],
) -> None:
    """Copy bounded sharing state without owner/sharedBy identity material."""

    shared = raw.get("shared")
    if shared is not None:
        if not isinstance(shared, dict):
            raise MicrosoftSharePointDeltaError("shared facet must be an object")
        minimized_shared: dict[str, JsonValue] = {}
        sharing_scope = shared.get("scope")
        if sharing_scope is not None:
            if not isinstance(sharing_scope, str) or sharing_scope not in {
                "anonymous",
                "organization",
                "users",
            }:
                raise MicrosoftSharePointDeltaError("shared facet scope is invalid")
            minimized_shared["scope"] = sharing_scope
        shared_at = _optional_datetime(shared.get("sharedDateTime"), "shared.sharedDateTime")
        if shared_at is not None:
            minimized_shared["shared_at_utc"] = _format_utc(shared_at)
        metadata["shared"] = minimized_shared

    shared_changed = raw.get("@microsoft.graph.sharedChanged")
    if shared_changed is not None:
        if shared_changed not in {"True", "False"}:
            raise MicrosoftSharePointDeltaError(
                "Microsoft Graph sharedChanged annotation is invalid"
            )
        metadata["sharing_changed"] = shared_changed == "True"


def _bounded_identifier(value: str, field_name: str) -> str:
    if not 1 <= len(value) <= SHAREPOINT_DELTA_MAXIMUM_IDENTIFIER_CHARACTERS:
        raise ValueError(f"{field_name} is outside the qualified identifier bound")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{field_name} contains control data")
    return value


def _required_string(raw: dict[str, object], key: str, maximum: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise MicrosoftSharePointDeltaError(f"Microsoft Graph delta {key} is invalid")
    return value


def _copy_bounded_string(
    raw: dict[str, object],
    target: dict[str, JsonValue],
    source_key: str,
    maximum: int,
    *,
    output_key: str | None = None,
) -> None:
    value = raw.get(source_key)
    if value is None:
        return
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise MicrosoftSharePointDeltaError(
            f"Microsoft Graph delta {source_key} is invalid"
        )
    target[output_key or source_key] = value


def _copy_bounded_int(
    raw: dict[str, object],
    target: dict[str, JsonValue],
    source_key: str,
    *,
    minimum: int,
) -> None:
    value = raw.get(source_key)
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MicrosoftSharePointDeltaError(
            f"Microsoft Graph delta {source_key} is invalid"
        )
    target[source_key] = value


def _optional_datetime(value: object, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= 100:
        raise MicrosoftSharePointDeltaError(
            f"Microsoft Graph delta {field_name} is invalid"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MicrosoftSharePointDeltaError(
            f"Microsoft Graph delta {field_name} is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MicrosoftSharePointDeltaError(
            f"Microsoft Graph delta {field_name} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
