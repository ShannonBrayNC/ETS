"""Azure Table-backed ETS append-only event store for hosted pilot profiles."""

from __future__ import annotations

import hashlib
import importlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

from pydantic import ValidationError

from ets.core.canonical_json import canonical_sha256
from ets.core.log import DuplicateEventError, EventNotFoundError, LogEntry
from ets.core.merkle import leaf_hash_for_event_hash
from ets.core.models import EvidenceEvent
from ets.core.storage import StorageValidationError

AZURE_TABLE_SCHEMA_VERSION = 1
DEFAULT_MAX_APPEND_RETRIES = 8
_META_ROW = "meta"
_ENTRY_PREFIX = "entry-"
_EVENT_PREFIX = "event-"


class AzureTableConflictError(RuntimeError):
    """Raised when an optimistic Azure Table transaction conflicts."""


@dataclass(frozen=True)
class VersionedTableEntity:
    values: Mapping[str, object]
    etag: str


@dataclass(frozen=True)
class TableAction:
    kind: Literal["create", "replace"]
    values: Mapping[str, object]
    etag: str | None = None


class AzureTableBackend(Protocol):
    def get(self, partition_key: str, row_key: str) -> VersionedTableEntity | None:
        """Read one entity and its concurrency token."""

    def create(self, values: Mapping[str, object]) -> None:
        """Create one entity or raise AzureTableConflictError when it exists."""

    def transact(self, actions: Sequence[TableAction]) -> None:
        """Commit one same-partition transaction atomically."""

    def list_entries(self, partition_key: str) -> list[Mapping[str, object]]:
        """Return entry rows for one log partition in row-key order."""


class AzureTableEventStore:
    """Append-only EventStore using one Azure Table partition per ETS log."""

    provider_name = "azure_table"

    def __init__(
        self,
        backend: AzureTableBackend,
        *,
        log_id: str,
        max_append_retries: int = DEFAULT_MAX_APPEND_RETRIES,
    ) -> None:
        normalized_log_id = log_id.strip()
        if not normalized_log_id or len(normalized_log_id) > 256:
            raise ValueError("log_id must be between 1 and 256 characters")
        if not 1 <= max_append_retries <= 64:
            raise ValueError("max_append_retries must be between 1 and 64")
        self._backend = backend
        self._log_id = normalized_log_id
        digest = hashlib.sha256(normalized_log_id.encode("utf-8")).hexdigest()[:32]
        self._partition_key = f"log-{digest}"
        self._max_append_retries = max_append_retries
        self._ensure_metadata()

    def append(self, event: EvidenceEvent) -> LogEntry:
        event_json = event.model_dump_json()
        event_hash = canonical_sha256(event.hashable_payload())
        leaf_hash = leaf_hash_for_event_hash(event_hash)
        event_row_key = _event_row_key(event.event_id)

        for _ in range(self._max_append_retries):
            duplicate = self._backend.get(self._partition_key, event_row_key)
            if duplicate is not None:
                self._validate_event_index(duplicate.values, event.event_id)
                raise DuplicateEventError(f"event_id already exists: {event.event_id}")

            metadata = self._load_metadata()
            index = _required_int(metadata.values, "next_index")
            next_metadata = {
                "PartitionKey": self._partition_key,
                "RowKey": _META_ROW,
                "kind": "metadata",
                "schema_version": AZURE_TABLE_SCHEMA_VERSION,
                "log_id": self._log_id,
                "next_index": index + 1,
            }
            entry = {
                "PartitionKey": self._partition_key,
                "RowKey": _entry_row_key(index),
                "kind": "entry",
                "log_index": index,
                "event_json": event_json,
                "event_hash": event_hash,
                "leaf_hash": leaf_hash,
            }
            event_index = {
                "PartitionKey": self._partition_key,
                "RowKey": event_row_key,
                "kind": "event_index",
                "event_id": event.event_id,
                "log_index": index,
            }

            try:
                self._backend.transact(
                    (
                        TableAction("replace", next_metadata, metadata.etag),
                        TableAction("create", entry),
                        TableAction("create", event_index),
                    )
                )
            except AzureTableConflictError:
                duplicate = self._backend.get(self._partition_key, event_row_key)
                if duplicate is not None:
                    self._validate_event_index(duplicate.values, event.event_id)
                    raise DuplicateEventError(
                        f"event_id already exists: {event.event_id}"
                    ) from None
                continue

            return LogEntry(
                log_index=index,
                event=event,
                event_hash=event_hash,
                leaf_hash=leaf_hash,
            )

        raise StorageValidationError("Azure Table append exceeded bounded concurrency retries")

    def get_by_index(self, index: int) -> LogEntry:
        if index < 0:
            raise EventNotFoundError(f"log index not found: {index}")
        entity = self._backend.get(self._partition_key, _entry_row_key(index))
        if entity is None:
            raise EventNotFoundError(f"log index not found: {index}")
        return self._entity_to_entry(entity.values, expected_index=index)

    def get_by_event_id(self, event_id: str) -> LogEntry:
        entity = self._backend.get(self._partition_key, _event_row_key(event_id))
        if entity is None:
            raise EventNotFoundError(f"event_id not found: {event_id}")
        self._validate_event_index(entity.values, event_id)
        return self.get_by_index(_required_int(entity.values, "log_index"))

    def list_entries(self) -> list[LogEntry]:
        metadata = self._load_metadata()
        expected_count = _required_int(metadata.values, "next_index")
        entities = self._backend.list_entries(self._partition_key)
        if len(entities) != expected_count:
            raise StorageValidationError("Azure Table log metadata does not match entry count")

        entries = [
            self._entity_to_entry(entity, expected_index=index)
            for index, entity in enumerate(entities)
        ]
        if [entry.log_index for entry in entries] != list(range(expected_count)):
            raise StorageValidationError("Azure Table log entries are not contiguous")
        return entries

    def schema_version(self) -> int:
        return _required_int(self._load_metadata().values, "schema_version")

    def _ensure_metadata(self) -> None:
        current = self._backend.get(self._partition_key, _META_ROW)
        if current is None:
            try:
                self._backend.create(
                    {
                        "PartitionKey": self._partition_key,
                        "RowKey": _META_ROW,
                        "kind": "metadata",
                        "schema_version": AZURE_TABLE_SCHEMA_VERSION,
                        "log_id": self._log_id,
                        "next_index": 0,
                    }
                )
            except AzureTableConflictError:
                pass
        self._load_metadata()

    def _load_metadata(self) -> VersionedTableEntity:
        metadata = self._backend.get(self._partition_key, _META_ROW)
        if metadata is None:
            raise StorageValidationError("Azure Table log metadata is missing")
        if metadata.values.get("kind") != "metadata":
            raise StorageValidationError("Azure Table metadata row has invalid kind")
        if metadata.values.get("log_id") != self._log_id:
            raise StorageValidationError("Azure Table metadata log_id mismatch")
        if _required_int(metadata.values, "schema_version") != AZURE_TABLE_SCHEMA_VERSION:
            raise StorageValidationError("unsupported Azure Table schema version")
        next_index = _required_int(metadata.values, "next_index")
        if next_index < 0:
            raise StorageValidationError("Azure Table metadata next_index is invalid")
        if not metadata.etag:
            raise StorageValidationError("Azure Table metadata ETag is missing")
        return metadata

    def _entity_to_entry(
        self,
        entity: Mapping[str, object],
        *,
        expected_index: int,
    ) -> LogEntry:
        if entity.get("kind") != "entry":
            raise StorageValidationError("Azure Table event row has invalid kind")
        if _required_int(entity, "log_index") != expected_index:
            raise StorageValidationError("Azure Table event row index mismatch")
        event_json = _required_str(entity, "event_json")
        try:
            event = EvidenceEvent.model_validate_json(event_json)
        except ValidationError as exc:
            raise StorageValidationError("stored event JSON failed validation") from exc

        stored_event_hash = _required_str(entity, "event_hash")
        stored_leaf_hash = _required_str(entity, "leaf_hash")
        event_hash = canonical_sha256(event.hashable_payload())
        leaf_hash = leaf_hash_for_event_hash(event_hash)
        if event_hash != stored_event_hash or leaf_hash != stored_leaf_hash:
            raise StorageValidationError("stored event hashes do not match event JSON")

        return LogEntry(
            log_index=expected_index,
            event=event,
            event_hash=stored_event_hash,
            leaf_hash=stored_leaf_hash,
        )

    def _validate_event_index(
        self,
        entity: Mapping[str, object],
        expected_event_id: str,
    ) -> None:
        if entity.get("kind") != "event_index":
            raise StorageValidationError("Azure Table event-index row has invalid kind")
        if _required_str(entity, "event_id") != expected_event_id:
            raise StorageValidationError("Azure Table event-id index hash collision detected")
        index = _required_int(entity, "log_index")
        if index < 0:
            raise StorageValidationError("Azure Table event-id index is invalid")


def _entry_row_key(index: int) -> str:
    if index < 0:
        raise ValueError("log index must be non-negative")
    return f"{_ENTRY_PREFIX}{index:020d}"


def _event_row_key(event_id: str) -> str:
    return f"{_EVENT_PREFIX}{hashlib.sha256(event_id.encode('utf-8')).hexdigest()}"


def _required_str(entity: Mapping[str, object], key: str) -> str:
    value = entity.get(key)
    if not isinstance(value, str) or not value:
        raise StorageValidationError(f"Azure Table entity field {key} is invalid")
    return value


def _required_int(entity: Mapping[str, object], key: str) -> int:
    value = entity.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise StorageValidationError(f"Azure Table entity field {key} is invalid")
    return value


class AzureSdkTableBackend:
    """Lazy Azure SDK adapter using Managed Identity and conditional transactions."""

    def __init__(
        self,
        *,
        endpoint: str,
        table_name: str,
        managed_identity_client_id: str | None = None,
    ) -> None:
        normalized_endpoint, audience = _validate_azure_table_endpoint(endpoint)
        if not table_name.isalnum() or not 3 <= len(table_name) <= 63:
            raise ValueError("Azure Table name must be 3-63 alphanumeric characters")

        identity_module = importlib.import_module("azure.identity")
        tables_module = importlib.import_module("azure.data.tables")
        self._exceptions = importlib.import_module("azure.core.exceptions")
        azure_core = importlib.import_module("azure.core")
        self._table_transaction_error = tables_module.TableTransactionError
        self._update_mode = tables_module.UpdateMode
        self._if_not_modified = azure_core.MatchConditions.IfNotModified
        credential = identity_module.ManagedIdentityCredential(
            client_id=managed_identity_client_id or None
        )
        self._client = tables_module.TableClient(
            endpoint=normalized_endpoint,
            table_name=table_name,
            credential=credential,
            audience=audience,
        )

    def get(self, partition_key: str, row_key: str) -> VersionedTableEntity | None:
        try:
            entity = self._client.get_entity(partition_key, row_key)
        except self._exceptions.ResourceNotFoundError:
            return None
        etag = getattr(getattr(entity, "metadata", None), "etag", None)
        if not isinstance(etag, str) or not etag:
            raise StorageValidationError("Azure Table entity ETag is missing")
        return VersionedTableEntity(values=dict(entity), etag=etag)

    def create(self, values: Mapping[str, object]) -> None:
        try:
            self._client.create_entity(dict(values))
        except self._exceptions.ResourceExistsError as exc:
            raise AzureTableConflictError("Azure Table entity already exists") from exc

    def transact(self, actions: Sequence[TableAction]) -> None:
        operations: list[tuple[Any, ...]] = []
        for action in actions:
            entity = dict(action.values)
            if action.kind == "create":
                operations.append(("create", entity))
                continue
            if not action.etag:
                raise StorageValidationError("conditional Azure Table replace requires an ETag")
            operations.append(
                (
                    "update",
                    entity,
                    {
                        "mode": self._update_mode.REPLACE,
                        "etag": action.etag,
                        "match_condition": self._if_not_modified,
                    },
                )
            )
        try:
            self._client.submit_transaction(operations)
        except self._table_transaction_error as exc:
            status = getattr(exc, "status_code", None)
            if status in {404, 409, 412}:
                raise AzureTableConflictError("Azure Table transaction conflicted") from exc
            raise

    def list_entries(self, partition_key: str) -> list[Mapping[str, object]]:
        query = (
            f"PartitionKey eq '{partition_key}' and "
            f"RowKey ge '{_ENTRY_PREFIX}' and RowKey lt 'entry.'"
        )
        entities = [dict(entity) for entity in self._client.query_entities(query)]
        entities.sort(key=lambda entity: cast(str, entity.get("RowKey", "")))
        return entities


def create_azure_table_event_store(
    *,
    endpoint: str,
    table_name: str,
    log_id: str,
    managed_identity_client_id: str | None = None,
    max_append_retries: int = DEFAULT_MAX_APPEND_RETRIES,
) -> AzureTableEventStore:
    return AzureTableEventStore(
        AzureSdkTableBackend(
            endpoint=endpoint,
            table_name=table_name,
            managed_identity_client_id=managed_identity_client_id,
        ),
        log_id=log_id,
        max_append_retries=max_append_retries,
    )


def _validate_azure_table_endpoint(endpoint: str) -> tuple[str, str]:
    from urllib.parse import urlsplit

    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port is not None
    ):
        raise ValueError("Azure Table endpoint must be a credential-free HTTPS origin")
    hostname = (parsed.hostname or "").lower()
    suffixes = {
        ".table.core.windows.net": "https://storage.azure.com",
        ".table.core.usgovcloudapi.net": "https://storage.azure.us",
        ".table.core.chinacloudapi.cn": "https://storage.azure.cn",
    }
    audience = next(
        (
            value
            for suffix, value in suffixes.items()
            if hostname.endswith(suffix)
        ),
        None,
    )
    if audience is None:
        raise ValueError("Azure Table endpoint must use a supported Azure Storage hostname")
    return f"https://{hostname}", audience
