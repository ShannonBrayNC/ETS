# Azure migration Gate 3 — source export integrity proof

Gate 3 proves that the protected ETS source state can be read, captured, and integrity-verified without writing the destination or mutating the source.

This is deliberately **not** a final migration copy. The source remains authoritative and live, so every Gate-3 result must record:

- `source_fenced=false`
- `final_copy=false`
- `destination_write_performed=false`
- `source_mutation_performed=false`
- `protected_bytes_uploaded=false`

## Protected execution boundary

The workflow is:

`.github/workflows/azure-migration-gate3-source-export.yml`

It is `workflow_dispatch` only and runs inside the already protected GitHub environment:

`ets-azure-migration-destination-restore`

The job authenticates only with the dedicated source-transfer OIDC identity. It does not authenticate the destination restore identity.

The workflow first re-runs the existing protected source inventory with `--require-data-plane`, then invokes:

```text
python -m scripts.azure_migration_gate3_export
```

All protected bytes are written only beneath a runner-local directory under `RUNNER_TEMP`, outside the repository checkout.

## Evidence Table capture

The Gate-3 exporter queries the complete `ETSEvents` entity representation through Azure login authentication, retains the full returned entity payload in the protected workspace, and reuses the existing resumable-prefix validator to require:

- exactly one ETS metadata row;
- the expected log identity and schema version;
- contiguous `entry` and `event_index` rows;
- row counts consistent with `next_index`;
- valid event-index row-key derivation;
- stable event/pair digests.

The protected Table payload is written with owner-only permissions and hashed with SHA-256. Only sanitized entity count, `next_index`, and the protected manifest digest are emitted.

## Gateway capture

The exporter enumerates the approved source Gateway share using OAuth plus Azure Files backup intent. Root entries must be uniquely named files with verifiable byte lengths; directories and path-like names fail closed.

Each root file is downloaded into the protected runner workspace using OAuth plus backup intent. The exporter verifies the downloaded byte length against the enumerated length and computes SHA-256 for the protected manifest.

Because source writers remain live, the Gateway capture is explicitly labeled:

`live_unfenced_nonfinal_capture`

A Gate-3 pass therefore proves the export/integrity mechanism only. It does not prove that sequential live SQLite downloads form the final coherent migration snapshot.

## Protected manifest

The runner-local manifest contains the source storage identifiers, capture timestamp, repository commit, Table integrity material, Gateway file sizes/hashes, and the explicit non-final safety claims.

The manifest and all protected payloads are deleted in an `always()` cleanup step. The workflow fails if the protected workspace still exists after cleanup.

No protected payload or manifest is uploaded as a GitHub Actions artifact.

## Gate-3 success

A protected execution may mark Gate 3 green only when it reports `qualification=pass` and the workflow also verifies protected workspace cleanup.

A Gate-3 pass does **not** authorize:

- destination Table/File restore;
- source fencing or queue/lease mutation;
- destination replica/image/configuration changes;
- writer activation;
- RBAC/UAMI/FIC/Entra/Graph/SharePoint permission changes;
- DNS/routing/cutover;
- source decommission.

Gate 4 remains the separately reviewed and separately authorized isolated destination restore boundary.
