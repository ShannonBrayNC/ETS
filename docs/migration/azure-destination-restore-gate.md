# Azure destination protected-state restore gate

Status: repository-side restore preparation only. No protected source evidence or
Gateway state has been transferred by this checkpoint. No destination file/table
entity has been overwritten, no destination writer has been activated, and no DNS
or production routing change is authorized by this document.

## Proven prerequisites

The source and destination GitHub OIDC read paths are proven. Destination read-only
inventory reports the isolated zero-replica Core/Gateway staging stack, one initialized
`ETSEvents` metadata entity with `next_index=0`, and three inert Gateway initialization
files. The protected source Table export, Gateway snapshots, and historical public-key
continuity material remain outside Git.

Gate 3 runtime export/integrity proof completed in run `34672413452` with `99`
source entities, `next_index=49`, five Gateway files totaling `364544` bytes, and
protected manifest SHA-256
`e3d9d132fd2161fa76c89e606e64cdba660897284520da6407afd7aa9b7a6074`.
That capture remains explicitly non-final because the source is not fenced.

The read-only destination restore preflight has passed for the previously reviewed
migration head. Any later code/workflow change requires a fresh exact-head preflight
before a destination write.

## Repository controls added for the next gate

`azure-migration-restore-preflight.yml` is a workflow-dispatch-only, read-only check
that uses the already proven destination read identity. It fails closed unless:

- the Azure tenant/subscription context matches the configured destination;
- exactly two destination Container Apps are present;
- both apps remain fenced at `minReplicas=0`, `maxReplicas=1`;
- no active Container App replica exists;
- `ETSEvents` still contains only the initialized metadata row with `next_index=0`;
- the active Gateway share still contains exactly the three known inert initialization
  files.

The workflow contains no write job and cannot restore protected state.

`scripts/azure_migration_gate4_restore.py` now provides the separately reviewable,
**code-only** Gate-4 restore engine required by issue #702. It is manifest-driven,
defaults to plan-only validation, requires an independent manifest SHA-256, validates
the protected Table/Gateway source workspace outside Git, re-runs the destination
fence checks, and requires the restore identity to hold exactly the documented narrow
RBAC scopes. Its `--apply` path additionally requires the literal authorization phrase
`GATE4_DESTINATION_WRITE_AUTHORIZED`.

This checkpoint deliberately does **not** add an executable Gate-4 GitHub Actions
write workflow. A later workflow must be reviewed separately and bound to the protected
restore environment before runtime authorization is considered.

`azure_migration_restore_oidc_bootstrap.sh` prepares the future write identity only
when an operator explicitly runs it in authenticated destination Cloud Shell. It
creates/reuses `ets-gh-migration-dst-restore` and the federated subject:

```text
repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-restore
```

The helper grants only:

- `Reader` on `rg-ets-prod-eastus`;
- `Storage Table Data Contributor` on the exact destination `ETSEvents` table;
- `Storage File Data Privileged Contributor` on the exact active Gateway file share.

It fails closed if the restore identity already holds a known broad administrative
role. It creates no client secret and performs no protected-state transfer.

## Required operator gate before creating the restore identity

Create GitHub environment `ets-azure-migration-destination-restore` first and configure
required-reviewer approval plus branch restrictions limited to the migration branch.
Only after that protection is visibly in place should an operator run:

```bash
bash scripts/azure_migration_restore_oidc_bootstrap.sh \
  <destination-subscription-id>
```

Add only the printed non-secret identifiers to that environment:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

Do not create an application client secret.

## Protected artifact gate

Before any restore workflow is implemented or executed, rehydrate the protected
source artifacts into an operator-controlled workspace outside Git and re-verify the
recorded archive/file SHA-256 values from the migration runbook. Record fresh local
hash verification, source snapshot identifiers, export high-water mark, and restore
manifest hash in protected migration records. A GitHub repository commit, issue, PR,
or Actions artifact must not contain protected evidence payloads, Gateway database
files, private keys, access tokens, SAS values, or storage account keys.

The Table restore must preserve the exact protected entity representation and replace
the initialized metadata row; it must not replay historical evidence through the
Core ingestion API. Service-assigned Table timestamps/ETags may change on copy and
must not be rewritten from the source. The Gateway restore must preserve the protected
snapshot bytes and must not merge SQLite initialization rows into the source databases.

## Restore execution gate

The actual write workflow remains intentionally absent. Add it only after all of the
following are simultaneously true:

1. the read-only restore preflight passes at the exact reviewed migration head;
2. the restore GitHub environment is protected by required reviewers and branch rules;
3. the restore OIDC identity exists with only the documented scopes;
4. protected source artifacts have been rehydrated and their hashes independently
   verified;
5. the destination initialization snapshot/metadata rollback reference is retained;
6. the exact restore manifest and expected entity/file counts are recorded outside Git;
7. the code-only Gate-4 restore engine has passed exact-head CI and review;
8. the later execution workflow has passed its own exact-head CI and review;
9. explicit authorization is given for the protected source-to-destination transfer.

The restore workflow must be manifest-driven and fail closed on any hash, count,
partition/log-ID, scope, tenant/subscription, replica-fence, or destination-state
mismatch. It must not change DNS, application configuration, replicas, signing-key
identity, cross-tenant connector permissions, RBAC, source state, or production traffic.

## Post-restore boundary

Restoring bytes is not cutover. After restore, use the read-only OIDC control to prove
entity counts/high-water marks, Gateway file hashes, historical signature continuity,
and zero active destination replicas. Only a later, separately approved writer
activation gate may move `minReplicas` above zero or transfer exclusive writer
ownership. Immediately before that activation, fence the live source and capture a
final source high-water mark because source evidence continues to advance.

See `docs/migration/azure-gate4-isolated-destination-restore.md` for the code-level
Gate-4 contract and the next review boundary.
