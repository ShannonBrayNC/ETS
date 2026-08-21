# ETS Vault

`ets.vault` is the backend-neutral preservation core for ETS Vault.

It implements write-once object semantics at the service contract, SHA-256 integrity binding,
retention extension, compliance-mode non-downgrade, legal holds, dual-control disposition, and a
hash-chained administrative journal.

## Minimal example

```python
from datetime import UTC, datetime, timedelta

from ets.vault import InMemoryVaultBackend, InMemoryVaultCatalog, VaultService

vault = VaultService(InMemoryVaultBackend(), InMemoryVaultCatalog())
receipt = vault.preserve(
    b"proof bundle bytes",
    tenant_id="tenant_demo",
    workspace_id="workspace_alpha",
    media_type="application/json",
    retain_until_utc=datetime.now(UTC) + timedelta(days=365),
    actor_id="ets-core",
)

assert vault.verify_integrity(receipt.record.object_id).valid
```

The in-memory backend is for unit tests and conformance only. It intentionally does not satisfy
`VaultPolicy(require_production_backend=True)`.

## Production rule

Do not claim production WORM or regulatory immutability by placing normal files on a read-only
filesystem. A production adapter must independently enforce the capabilities in
`VaultBackendCapabilities.production_ready()`, including storage-boundary write-once retention,
compliance lock, legal hold, encryption, durability, audit, redundancy, and hardware-backed key
protection.

See `docs/spec/ETS_VAULT_V1.md` for the complete appliance, security, hardware, recovery,
sanitation, and qualification contract.
