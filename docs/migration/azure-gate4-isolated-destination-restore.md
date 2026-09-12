# Azure migration Gate 4 — isolated destination restore

Status: **code-only restore engine prepared for review; no Gate-4 destination write has been executed by this change.**

Tracking issue: #702.

## Proven input boundary

Gate 3 runtime export/integrity proof completed in run `34672413452` with sanitized evidence:

- source evidence entities: `99`;
- source `next_index`: `49`;
- Gateway files: `5`;
- Gateway bytes: `364544`;
- protected Gate-3 manifest SHA-256: `e3d9d132fd2161fa76c89e606e64cdba660897284520da6407afd7aa9b7a6074`;
- `source_fenced=false`;
- `final_copy=false`;
- no destination write, source mutation, protected artifact upload, writer activation, DNS change, or cutover.

The source remains authoritative and live. The Gate-3 capture proves exportability and integrity mechanics only; it is not the final migration copy.

The read-only `Azure Migration Restore Preflight` has passed for the previously reviewed migration head. Because this Gate-4 implementation changes repository state, **a fresh preflight is required on the exact reviewed head before any write execution**.

## Code-only implementation

`scripts/azure_migration_gate4_restore.py` implements a manifest-driven restore engine with two modes:

- default **plan-only** mode: validates the protected workspace, manifest hash, source payload structure, destination fence, storage targets, and exact restore-identity RBAC; it performs no destination write;
- `--apply`: contains the bounded Table/Gateway restore path but requires the exact authorization phrase `GATE4_DESTINATION_WRITE_AUTHORIZED` in addition to `--apply`.

There is intentionally **no** `.github/workflows/azure-migration-gate4-restore.yml` in this checkpoint. The approval-gated execution workflow remains a later, separately reviewable boundary after this code passes exact-head CI and review.

## Protected workspace contract

The restore engine accepts only an operator-controlled protected workspace outside the repository checkout. The workspace must contain the Gate-3 files directly:

```text
<protected-workspace>/
  gate3-manifest.json
  ETSEvents.full.json
  gateway/
    <manifest-listed files only>
```

The expected Gate-3 manifest SHA-256 is supplied independently through `--expected-manifest-sha256`. The engine then:

1. hashes `gate3-manifest.json` and requires the independent digest to match;
2. requires Gate 3 / manifest version 1 and the non-final/no-write flags recorded by Gate 3;
3. hashes `ETSEvents.full.json` and requires the manifest payload digest to match;
4. validates the ETS metadata/entry/event-index structure, exact entity count, `next_index`, metadata digest, and ordered pair digests;
5. rejects duplicate PartitionKey/RowKey pairs, nested/unsupported Table values, and malformed entities;
6. requires the Gateway directory to contain exactly the manifest-listed root files;
7. checks every Gateway file name, byte length, SHA-256, total count, and aggregate byte count;
8. rejects symlinked protected files/workspaces and unsafe/path-like Gateway names.

Protected bytes are never printed by the implementation. The restore code contains no GitHub artifact upload path.

## Destination and identity guard

Before `--apply` can reach a write call, the engine must prove all of the following:

- expected Azure tenant/subscription context;
- existing read-only restore preflight still passes;
- exactly two destination Container Apps remain fenced at `minReplicas=0`, `maxReplicas=1` with zero active replicas;
- destination `ETSEvents` remains initialization-only;
- destination Gateway share remains the approved inert initialization file set;
- destination Core/Gateway storage accounts resolve uniquely;
- the authenticated restore identity has **exactly**:
  - `Reader` on `rg-ets-prod-eastus`;
  - `Storage Table Data Contributor` on the exact destination `ETSEvents` table;
  - `Storage File Data Privileged Contributor` on the exact active Gateway share;
- no additional or broad restore RBAC is present; `Owner`, `Contributor`, `User Access Administrator`, and `Role Based Access Control Administrator` are explicitly refused.

RBAC creation or modification is not implemented by Gate 4.

## Table restore semantics

The Table path writes directly to Azure Table Storage. It does **not** replay historical evidence through Core ingestion APIs.

For each protected entity, the restore engine:

- preserves PartitionKey/RowKey and application properties;
- preserves explicit `@odata.type` annotations supplied by the protected payload;
- excludes only service-managed `Timestamp`/ETag fields, which Azure assigns on copy;
- uses replace semantics so the inert destination metadata row is replaced rather than merged with source metadata;
- restores metadata, entry, and event-index entities from the protected payload;
- performs a full post-write read and compares the complete restorable entity representation to the protected source payload;
- re-runs ETS structural validation and requires the manifest entity count, high-water mark, metadata digest, and pair digests to match.

Any mismatch blocks Gate 4. A failure after a partial write does not activate the destination; the destination remains fenced and must be reconciled from the retained rollback reference before another execution.

## Gateway restore semantics

The Gateway path requires the destination share to begin with only the approved inert initialization files. It then:

- uploads each manifest-listed protected snapshot file with Entra/OAuth and backup intent;
- overwrites matching inert filenames instead of merging SQLite contents;
- removes an inert initialization file only when it is absent from the approved protected manifest;
- requires the resulting root file set to equal the protected manifest exactly;
- downloads each restored file into a temporary directory inside the protected workspace for post-write byte-length/SHA-256 verification;
- deletes the temporary verification copy automatically on completion.

Gate 4 never mounts the restored state into a running Gateway.

## Explicitly outside this checkpoint

This code-only checkpoint does not authorize or perform:

- a Gate-4 GitHub Actions write workflow;
- any destination Table or Azure Files write;
- source fencing or source writer changes;
- destination writer activation or replica scale-up;
- DNS, Front Door, route, or cutover changes;
- app configuration or signing-key changes;
- Graph, SharePoint, Entra, connector-permission, or RBAC changes;
- source decommission;
- a claim that the restored copy is final.

## Next boundary after review

After this PR is green and independently reviewed:

1. rerun `Azure Migration Restore Preflight` on the exact reviewed/merged head;
2. rehydrate the approved protected source artifacts outside Git/GitHub artifacts and independently re-verify the manifest hash and source capture identifiers;
3. retain the destination initialization rollback reference outside Git;
4. add a **separate** workflow-dispatch-only Gate-4 restore workflow bound to `ets-azure-migration-destination-restore`, required reviewers, branch restrictions, exact manifest digest/count inputs, and no artifact upload;
5. review that workflow and stop again;
6. require fresh explicit authorization for the one-time destination write;
7. after a successful restore, advance only to Gate 5 read-only equivalence proof. Do not activate writers.

Gate 4 becomes green only from the separately authorized runtime restore and post-write verification. Merging this code does not make Gate 4 green.
