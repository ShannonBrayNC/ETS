"""ETS Vault preservation and retention primitives."""

from ets.vault.models import (
    RetentionMode,
    VaultAuthorization,
    VaultBackendCapabilities,
    VaultIntegrityResult,
    VaultJournalEntry,
    VaultJournalVerification,
    VaultReceipt,
    VaultRecord,
    VaultRetention,
)
from ets.vault.service import (
    VaultPolicy,
    VaultPolicyError,
    VaultProductionReadinessError,
    VaultService,
)
from ets.vault.store import (
    InMemoryVaultBackend,
    InMemoryVaultCatalog,
    VaultBackend,
    VaultCatalog,
    VaultCatalogError,
    VaultObjectAlreadyExists,
    VaultObjectNotFound,
    VaultStorageError,
)

__all__ = [
    "InMemoryVaultBackend",
    "InMemoryVaultCatalog",
    "RetentionMode",
    "VaultAuthorization",
    "VaultBackend",
    "VaultBackendCapabilities",
    "VaultCatalog",
    "VaultCatalogError",
    "VaultIntegrityResult",
    "VaultJournalEntry",
    "VaultJournalVerification",
    "VaultObjectAlreadyExists",
    "VaultObjectNotFound",
    "VaultPolicy",
    "VaultPolicyError",
    "VaultProductionReadinessError",
    "VaultReceipt",
    "VaultRecord",
    "VaultRetention",
    "VaultService",
    "VaultStorageError",
]
