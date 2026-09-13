# Azure Gate 4 one-time protected restore execution

Status: **reviewable execution path only; runtime destination writes are not authorized by this document or by merging its implementation.**

## Why the execution path is two-stage

Gate 4 now has separately reviewed writers for the resumable `ETSEvents` suffix and the rollback-first Gateway snapshot. The execution path must also preserve two repository safety requirements that a normal GitHub-hosted runner cannot satisfy:

1. protected source bytes must remain outside Git and GitHub Actions artifacts in an operator-controlled workspace; and
2. the pre-write destination Gateway rollback snapshot must remain available after the workflow completes or fails.

For that reason both Gate-4 workflows require a persistent self-hosted runner carrying the labels `self-hosted`, `linux`, `x64`, and `ets-migration-gate4`. The protected environment must define `GATE4_OPERATOR_ROOT` as an absolute persistent path outside both the repository checkout and runner temporary directory.

## Stage A — prepare the protected source snapshot

`azure-migration-gate4-prepare-source.yml` is manual-only and uses only the dedicated source transfer identity. It requires the exact reviewed `main` commit plus an operator snapshot tag. It re-proves the source read path and captures the full Table/Gateway protected state into:

```text
<GATE4_OPERATOR_ROOT>/source-snapshots/<snapshot-tag>
```

The workflow records the SHA-256 of `gate3-manifest.json` in the run summary. It performs no destination login or write and retains the protected source workspace. The operator must independently record the snapshot tag and manifest SHA-256 in the protected migration record before Stage B is authorized.

Because the live source remains unfenced, this is still a non-final snapshot. Gate 4 is destination restoration only, not cutover or final-copy certification.

## Stage B — execute the isolated destination restore

`azure-migration-gate4-protected-restore.yml` is also manual-only and bound to `ets-azure-migration-destination-restore`. Before Azure destination login it fails closed unless all of the following are true:

- the workflow is running from `main`;
- the current commit equals the operator-supplied reviewed commit;
- the operator types `GATE4_PROTECTED_TRANSFER_AUTHORIZED` exactly;
- the source snapshot tag resolves under the persistent operator root;
- the supplied protected manifest SHA-256 is exactly 64 lowercase hexadecimal characters and matches the retained manifest;
- the rollback tag is new and resolves under the persistent operator root; and
- the required destination OIDC identifiers are present.

The execution controller then invokes the already reviewed writers in this order:

1. **Resumable Table suffix.** Preserve the exact committed destination prefix, reuse only exact already-staged source rows, insert only missing source rows, verify the staged suffix, update metadata last, then require the destination Table to equal the protected source representation.
2. **Rollback-first Gateway snapshot.** Re-prove zero replicas and exact narrow RBAC, validate the dormant sidecar policy, capture all current destination Gateway files under `rollback-snapshots/<rollback-tag>` before the first Gateway mutation, overwrite only differing durable databases, remove only the approved inert SQLite sidecars, then re-download and verify exact durable path/size/SHA-256 equivalence.
3. **Fence re-proof.** Re-prove zero destination replicas after both writers return.

The rollback workspace is intentionally retained and is never uploaded as a GitHub artifact.

## Explicitly outside Gate 4

A successful Gate-4 run does **not** fence or mutate the live source, activate Core or Gateway replicas, alter RBAC, modify signing identity, change Microsoft Graph or SharePoint permissions, change Azure Front Door/DNS/routing, transfer exclusive writer ownership, or declare a final migration copy.

The next gate after a successful restore is a read-only Gate-5 equivalence qualification covering Table count/high-water, Gateway byte equivalence, historical signature continuity, and zero active replicas. Source fencing and writer activation remain separately reviewed later boundaries.

## Runtime authorization boundary

Merging the execution workflow is not runtime authorization. Before any Stage-B dispatch, require all of the following again at the exact merged commit:

- all CI/proof/security checks green;
- independent review approval current for the exact head;
- Stage-A source preparation successfully completed on the retained operator workspace;
- snapshot tag and manifest SHA-256 independently recorded;
- rollback storage is persistent and has adequate capacity;
- the destination restore environment requires reviewer approval;
- a fresh read-only destination reconciliation remains consistent with the expected resumable prefix and dormant Gateway state; and
- explicit authorization is given for the one-time protected destination write.
