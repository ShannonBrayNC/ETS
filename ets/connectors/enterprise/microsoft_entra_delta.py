"""Microsoft Entra users/groups delta boundary for G2E-C."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ets.connectors.enterprise.microsoft import MicrosoftTenantProfileV1

ENTRA_DELTA_PAGE_SCHEMA_VERSION = "ets.connector.microsoft.entra_delta_page.v1"
ENTRA_DELTA_RECORD_SCHEMA_VERSION = "ets.connector.microsoft.entra_delta_record.v1"
ENTRA_DEFAULT_MAXIMUM_BODY_BYTES = 2 * 1024 * 1024
ENTRA_DEFAULT_MAXIMUM_RECORDS = 1000
ENTRA_MAXIMUM_LINK_CHARACTERS = 8000

EntraDeltaCollection = Literal["users", "groups"]
EntraRemovalReason = Literal["changed", "deleted"]


class MicrosoftEntraDeltaError(ValueError):
    """Raised when a Graph delta response fails the qualified boundary."""


class StrictDeltaModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MicrosoftEntraDeltaRecordV1(StrictDeltaModel):
    """Minimized directory delta observation with no actor or completeness inference."""

    schema_version: Literal["ets.connector.microsoft.entra_delta_record.v1"]
    source_record_id: str = Field(min_length=1, max_length=100)
    collection: EntraDeltaCollection
    object_id: str = Field(min_length=1, max_length=500)
    removed_reason: EntraRemovalReason | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class MicrosoftEntraDeltaPageV1(StrictDeltaModel):
    """One bounded source page plus the exact opaque continuation or terminal delta link."""

    schema_version: Literal["ets.connector.microsoft.entra_delta_page.v1"]
    collection: EntraDeltaCollection
    records: tuple[MicrosoftEntraDeltaRecordV1, ...]
    next_link: str | None = Field(default=None, min_length=1, max_length=ENTRA_MAXIMUM_LINK_CHARACTERS)
    delta_link: str | None = Field(default=None, min_length=1, max_length=ENTRA_MAXIMUM_LINK_CHARACTERS)

    @property
    def cycle_complete(self) -> bool:
        return self.delta_link is not None

    @property
    def checkpoint_url(self) -> str:
        value = self.delta_link or self.next_link
        if value is None:  # pragma: no cover - parser enforces one terminal link
            raise ValueError("Entra delta page has no checkpoint URL")
        return value


@dataclass(frozen=True, slots=True)
class EntraDeltaRequestProfile:
    """Qualified collection/request identity used to validate opaque Graph cursor URLs."""

    collection: EntraDeltaCollection
    graph_root: str

    @property
    def initial_path(self) -> str:
        return f"/v1.0/{self.collection}/delta"

    @property
    def initial_url(self) -> str:
        return f"{self.graph_root}{self.initial_path}"


def entra_delta_request_profile(
    tenant_profile: MicrosoftTenantProfileV1,
    collection: EntraDeltaCollection,
) -> EntraDeltaRequestProfile:
    """Build one server-owned Graph delta request profile from the qualified cloud mapping."""

    return EntraDeltaRequestProfile(
        collection=collection,
        graph_root=tenant_profile.endpoints.graph_root,
    )


def validate_entra_delta_cursor_url(
    profile: EntraDeltaRequestProfile,
    value: str,
) -> str:
    """Accept only source cursors that stay on the qualified cloud and collection endpoint."""

    if not 1 <= len(value) <= ENTRA_MAXIMUM_LINK_CHARACTERS:
        raise MicrosoftEntraDeltaError("Entra delta cursor URL exceeds configured limit")
    parsed = urlsplit(value)
    root = urlsplit(profile.graph_root)
    if parsed.scheme != "https" or parsed.hostname != root.hostname:
        raise MicrosoftEntraDeltaError("Entra delta cursor changed the qualified Graph origin")
    if parsed.port not in {None, 443}:
        raise MicrosoftEntraDeltaError("Entra delta cursor changed the qualified Graph port")
    normalized_path = parsed.path.rstrip("/")
    if normalized_path != profile.initial_path:
        raise MicrosoftEntraDeltaError("Entra delta cursor changed the qualified collection path")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise MicrosoftEntraDeltaError("Entra delta cursor contains unsupported URL components")
    return value


def parse_entra_delta_page(
    payload: bytes,
    *,
    profile: EntraDeltaRequestProfile,
    request_url: str,
    maximum_body_bytes: int = ENTRA_DEFAULT_MAXIMUM_BODY_BYTES,
    maximum_records: int = ENTRA_DEFAULT_MAXIMUM_RECORDS,
) -> MicrosoftEntraDeltaPageV1:
    """Decode one bounded users/groups delta page and preserve its opaque state link."""

    if maximum_body_bytes < 1:
        raise ValueError("maximum_body_bytes must be positive")
    if not 1 <= maximum_records <= ENTRA_DEFAULT_MAXIMUM_RECORDS:
        raise ValueError("maximum_records must be between 1 and 1000")
    if not payload:
        raise MicrosoftEntraDeltaError("Entra delta body is empty")
    if len(payload) > maximum_body_bytes:
        raise MicrosoftEntraDeltaError("Entra delta body exceeds configured limit")

    request_url = validate_entra_delta_cursor_url(profile, request_url)
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MicrosoftEntraDeltaError("Entra delta body is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise MicrosoftEntraDeltaError("Entra delta response must be an object")

    allowed_root = {"@odata.context", "@odata.nextLink", "@odata.deltaLink", "value"}
    unexpected = set(decoded) - allowed_root
    if unexpected:
        raise MicrosoftEntraDeltaError("Entra delta response contains unsupported root fields")
    values = decoded.get("value")
    if not isinstance(values, list):
        raise MicrosoftEntraDeltaError("Entra delta value must be an array")
    if len(values) > maximum_records:
        raise MicrosoftEntraDeltaError("Entra delta page exceeds configured record limit")

    next_link = decoded.get("@odata.nextLink")
    delta_link = decoded.get("@odata.deltaLink")
    if (next_link is None) == (delta_link is None):
        raise MicrosoftEntraDeltaError(
            "Entra delta response must contain exactly one nextLink or deltaLink"
        )
    if next_link is not None:
        if not isinstance(next_link, str):
            raise MicrosoftEntraDeltaError("Entra delta nextLink must be a URL string")
        next_link = validate_entra_delta_cursor_url(profile, next_link)
    if delta_link is not None:
        if not isinstance(delta_link, str):
            raise MicrosoftEntraDeltaError("Entra delta deltaLink must be a URL string")
        delta_link = validate_entra_delta_cursor_url(profile, delta_link)

    records = tuple(
        _normalize_record(
            raw,
            collection=profile.collection,
            request_url=request_url,
        )
        for raw in values
    )
    return MicrosoftEntraDeltaPageV1(
        schema_version="ets.connector.microsoft.entra_delta_page.v1",
        collection=profile.collection,
        records=records,
        next_link=next_link,
        delta_link=delta_link,
    )


def _normalize_record(
    raw: object,
    *,
    collection: EntraDeltaCollection,
    request_url: str,
) -> MicrosoftEntraDeltaRecordV1:
    if not isinstance(raw, Mapping):
        raise MicrosoftEntraDeltaError("Entra delta page contains a non-object record")
    object_id = raw.get("id")
    if not isinstance(object_id, str) or not 1 <= len(object_id) <= 500:
        raise MicrosoftEntraDeltaError("Entra delta record id is invalid")

    removed_reason = _removed_reason(raw.get("@removed"))
    metadata = _minimized_metadata(raw, collection=collection)
    source_record_id = _source_record_id(
        collection=collection,
        request_url=request_url,
        object_id=object_id,
        removed_reason=removed_reason,
        metadata=metadata,
    )
    return MicrosoftEntraDeltaRecordV1(
        schema_version="ets.connector.microsoft.entra_delta_record.v1",
        source_record_id=source_record_id,
        collection=collection,
        object_id=object_id,
        removed_reason=removed_reason,
        metadata=metadata,
    )


def _removed_reason(value: object) -> EntraRemovalReason | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise MicrosoftEntraDeltaError("Entra delta @removed value must be an object")
    reason = value.get("reason")
    if reason not in {"changed", "deleted"}:
        raise MicrosoftEntraDeltaError("Entra delta @removed reason is not supported")
    return reason


def _minimized_metadata(
    raw: Mapping[str, object],
    *,
    collection: EntraDeltaCollection,
) -> dict[str, JsonValue]:
    metadata: dict[str, JsonValue] = {"object_type": collection[:-1]}
    if collection == "users":
        account_enabled = raw.get("accountEnabled")
        if isinstance(account_enabled, bool):
            metadata["account_enabled"] = account_enabled
        user_type = raw.get("userType")
        if isinstance(user_type, str) and user_type:
            metadata["user_type"] = user_type[:100]
    else:
        for source_key, target_key in (
            ("mailEnabled", "mail_enabled"),
            ("securityEnabled", "security_enabled"),
        ):
            value = raw.get(source_key)
            if isinstance(value, bool):
                metadata[target_key] = value
        group_types = raw.get("groupTypes")
        if isinstance(group_types, list):
            bounded_types = [
                item[:100]
                for item in group_types[:16]
                if isinstance(item, str) and item
            ]
            if bounded_types:
                metadata["group_types"] = bounded_types
    return metadata


def _source_record_id(
    *,
    collection: EntraDeltaCollection,
    request_url: str,
    object_id: str,
    removed_reason: EntraRemovalReason | None,
    metadata: Mapping[str, JsonValue],
) -> str:
    material = {
        "schema": "ets.connector.microsoft.entra-delta-record-id.v1",
        "collection": collection,
        "request_url_sha256": hashlib.sha256(request_url.encode("utf-8")).hexdigest(),
        "object_id": object_id,
        "removed_reason": removed_reason,
        "metadata": dict(metadata),
    }
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "entra-delta:" + hashlib.sha256(encoded).hexdigest()
