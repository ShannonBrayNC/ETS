# Azure protected cross-tenant transfer control

Status: identity-path preparation only. No protected ETS source bytes are transferred by this control.

## Why this exists

The migration now has proven recurring read-only GitHub OIDC access to both Azure subscriptions. The protected restore boundary needs a different trust shape: one approval-gated GitHub environment must be able to read the exact source state and, later and only after explicit authorization, use the narrowly scoped destination restore identity. Reusing a human Azure session would reintroduce MFA/session churn and Work-credit consumption.

The protected environment is:

`ets-azure-migration-destination-restore`

It must retain required-reviewer protection and deployment-branch restriction to `migration/azure-ets-destination-discovery` before any transfer workflow is authorized.

## Identities

### Source transfer identity

`scripts/azure_migration_source_transfer_oidc_bootstrap.sh` creates/reuses `ets-gh-migration-src-transfer` in the source Azure subscription with the GitHub OIDC subject:

`repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-restore`

Its allowed roles are deliberately read-only and narrowly scoped:

- Reader on `rg-ets-live-eastus`;
- Storage Table Data Reader on the exact source `ETSEvents` table;
- Storage File Data Privileged Reader on the source Gateway storage account.

The Azure Files role is account-scoped because the verified Azure CLI login/backup-intent enumeration path requires account-level read authorization before the active share can be listed. This grant remains read-only. It receives no source Table/File contributor role and no broad Azure administrative role.

### Destination restore identity

`ets-gh-migration-dst-restore` is separately scoped to:

- Reader on `rg-ets-prod-eastus`;
- Storage Table Data Contributor on the exact destination `ETSEvents` table;
- Storage File Data Privileged Reader on the destination Gateway storage account;
- Storage File Data Privileged Contributor on the exact active destination Gateway share.

The account-level File role is read-only and supports preflight enumeration. File mutation authority remains bounded to the active Gateway share. The identity is capable of the future restore only when a workflow runs inside the protected GitHub environment. No client secret is used.

## Preflight workflow

`.github/workflows/azure-migration-protected-transfer-preflight.yml` proves that one approved ephemeral GitHub runner can:

1. obtain a short-lived OIDC token for the dedicated source read identity;
2. verify source context and require both ETSEvents and Gateway protected-state reads to succeed;
3. clear the source Azure session;
4. obtain a separate short-lived OIDC token for the destination restore identity;
5. verify the destination is still fenced at zero replicas and initialization-only.

The preflight intentionally contains no protected-state export, GitHub artifact upload, destination write, source snapshot creation, DNS change, or writer activation.

### 2026-09-09 fail-closed finding

The first approved protected-transfer preflight proved both OIDC logins but failed before any write. The source inventory showed ETSEvents readable at 89 entities with `next_index=44`, while the dedicated source-transfer identity could not enumerate the Gateway share. The destination restore identity then failed its initialization-state preflight. Independent validation with the already-proven destination read-only identity confirmed the destination itself was healthy: 16 resources, one initialization metadata row with `next_index=0`, three Gateway root entries, and the standalone zero-replica restore preflight passed.

The failure therefore exposed an Azure Files authorization-scope mismatch rather than destination drift. The working read-only controls use `Storage File Data Privileged Reader` at the Gateway storage-account scope. The transfer bootstraps were corrected to use that verified account-level read scope, while destination write authority remains constrained to the exact active share. The protected source inventory was also changed to fail closed if either ETSEvents or Gateway protected reads are unavailable; a diagnostic `blocked` result can no longer let the transfer preflight continue.

No protected source bytes were copied and no destination state was changed during the failed run.

## Protected bytes rule

Protected ETSEvents entity data and Gateway SQLite bytes must never be committed to this public repository or emitted to GitHub logs. A future transfer job should keep source bytes only on the ephemeral runner filesystem while it changes Azure identities, validate hashes before any destination write, and delete the runner workspace at job completion. Do not pass unencrypted protected bytes through GitHub artifacts.

The Table capture must preserve the custom entity representation used by `AzureTableEventStore`: metadata, entry, and event-index rows; PartitionKey/RowKey; integer indexes/schema version; log ID; exact event JSON; event hash; leaf hash; and event-ID mapping. Source service timestamps/ETags belong in the protected migration manifest even though Azure regenerates service metadata on destination writes.

Gateway state must be copied from a coherent source snapshot/fenced state, not from independently changing live SQLite files. A live read may be used only as a non-final diagnostic capture.

## Final write fence

The source remains live and the latest sanitized inventory reports `next_index=44`. Therefore no current copy can be called final. Before destination writer activation:

1. fence all source write paths;
2. drain/capture retries, queues, and leases;
3. establish a coherent final Gateway snapshot;
4. capture the final ETSEvents high-water mark and protected state;
5. hash-verify source capture;
6. rerun destination zero-replica preflight;
7. perform the approved destination restore;
8. independently compare counts, indexes, event/leaf hashes, Gateway DB hashes/state, and historical verification material;
9. activate exactly one destination writer only after all gates pass.

DNS/routing and source shutdown remain later, separately authorized gates.
