"""Storage and catalog contracts for ETS Vault."""

from __future__ import annotations

from typing import Protocol

from ets.vault.models import (
    VaultBackendCapabilities,
    VaultJournalEntry,
    VaultRecord,
    VaultRetention,
)


class VaultStorageError(RuntimeError):
    """Base exception for Vault storage failures."""


class VaultObjectAlreadyExists(VaultStorageError):
    """Raised when a write-once object identifier already exists."""


class VaultObjectNotFound(VaultStorageError):
    """Raised when a requested Vault object is missing."""


class VaultCatalogError(RuntimeError):
    """Raised when Vault catalog state cannot be updated safely."""


class VaultBackend(Protocol):
    """Object-retention boundary implemented by production or test storage."""

    provider_name: str
    capabilities: VaultBackendCapabilities

    def put_once(self, object_id: str, payload: bytes, retention: VaultRetention) -> None:
        """Persist one object without allowing overwrite."""

    def get(self, object_id: str) -> bytes:
        """Return preserved bytes."""

    def extend_retention(self, object_id: str, retention: VaultRetention) -> None:
        """Apply a retention state that is at least as strong as the prior state."""

    def apply_legal_hold(self, object_id: str, retention: VaultRetention) -> None:
        """Apply a legal hold state to the object."""

    def release_legal_hold(self, object_id: str, retention: VaultRetention) -> None:
        """Release a legal hold after higher-level authorization."""

    def delete(self, object_id: str) -> None:
        """Delete content only after Vault policy has authorized purge."""

    def exists(self, object_id: str) -> bool:
        """Return whether the object is present."""


class VaultCatalog(Protocol):
    """Metadata and audit-journal persistence contract."""

    def create_record(self, record: VaultRecord) -> None:
        """Create a Vault record exactly once."""

    def get_record(self, object_id: str) -> VaultRecord:
        """Return the current logical record state."""

    def update_record(self, record: VaultRecord) -> None:
        """Replace current logical state with a newer generation."""

    def append_journal(self, entry: VaultJournalEntry) -> None:
        """Append one administration event."""

    def list_journal(self) -> list[VaultJournalEntry]:
        """Return journal entries in sequence order."""


class InMemoryVaultBackend:
    """Deterministic semantic backend for tests; never a production WORM boundary."""

    provider_name = "memory"
    capabilities = VaultBackendCapabilities(
        write_once=True,
        retention_enforced=True,
        compliance_lock=True,
        legal_hold=True,
        encryption_at_rest=False,
        durable_write=False,
        audit_logging=False,
        replication=False,
        hardware_backed_keys=False,
        enforcement_boundary="test",
    )

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._retention: dict[str, VaultRetention] = {}

    def put_once(self, object_id: str, payload: bytes, retention: VaultRetention) -> None:
        if object_id in self._objects:
            raise VaultObjectAlreadyExists(object_id)
        self._objects[object_id] = bytes(payload)
        self._retention[object_id] = retention

    def get(self, object_id: str) -> bytes:
        try:
            return self._objects[object_id]
        except KeyError as exc:
            raise VaultObjectNotFound(object_id) from exc

    def extend_retention(self, object_id: str, retention: VaultRetention) -> None:
        current = self._require_retention(object_id)
        if retention.retain_until_utc < current.retain_until_utc:
            raise VaultStorageError("backend refuses retention shortening")
        if current.mode == "compliance" and retention.mode != "compliance":
            raise VaultStorageError("backend refuses compliance-mode downgrade")
        if retention.legal_holds != current.legal_holds:
            raise VaultStorageError("retention extension cannot change legal holds")
        self._retention[object_id] = retention

    def apply_legal_hold(self, object_id: str, retention: VaultRetention) -> None:
        current = self._require_retention(object_id)
        if not set(current.legal_holds).issubset(retention.legal_holds):
            raise VaultStorageError("backend refuses removal during hold application")
        self._retention[object_id] = retention

    def release_legal_hold(self, object_id: str, retention: VaultRetention) -> None:
        current = self._require_retention(object_id)
        if not set(retention.legal_holds).issubset(current.legal_holds):
            raise VaultStorageError("backend refuses added hold during hold release")
        self._retention[object_id] = retention

    def delete(self, object_id: str) -> None:
        self._require_retention(object_id)
        del self._objects[object_id]
        del self._retention[object_id]

    def exists(self, object_id: str) -> bool:
        return object_id in self._objects

    def _require_retention(self, object_id: str) -> VaultRetention:
        try:
            return self._retention[object_id]
        except KeyError as exc:
            raise VaultObjectNotFound(object_id) from exc


class InMemoryVaultCatalog:
    """In-memory catalog used for conformance and unit tests."""

    def __init__(self) -> None:
        self._records: dict[str, VaultRecord] = {}
        self._journal: list[VaultJournalEntry] = []

    def create_record(self, record: VaultRecord) -> None:
        if record.object_id in self._records:
            raise VaultCatalogError(f"record already exists: {record.object_id}")
        self._records[record.object_id] = record

    def get_record(self, object_id: str) -> VaultRecord:
        try:
            return self._records[object_id]
        except KeyError as exc:
            raise VaultObjectNotFound(object_id) from exc

    def update_record(self, record: VaultRecord) -> None:
        current = self.get_record(record.object_id)
        if record.generation != current.generation + 1:
            raise VaultCatalogError("record generation must advance by exactly one")
        self._records[record.object_id] = record

    def append_journal(self, entry: VaultJournalEntry) -> None:
        expected_sequence = len(self._journal) + 1
        if entry.sequence != expected_sequence:
            raise VaultCatalogError("journal sequence must be contiguous")
        self._journal.append(entry)

    def list_journal(self) -> list[VaultJournalEntry]:
        return list(self._journal)
