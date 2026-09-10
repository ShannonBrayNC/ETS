# GitHub OIDC migration control plane

Status: source and destination OIDC authentication, management-plane inventory, and bounded protected Table/File data-plane reads are proven. Recurring read-only migration discovery no longer requires interactive human MFA.

## Purpose

Move recurring Azure authentication out of interactive Work/browser sessions. The control plane uses GitHub Actions OIDC for bounded Azure reads, so a human account remains an operator/bootstrap identity instead of the automation identity.

The workflow intentionally accepts only `context` and `inventory`. It does not accept arbitrary shell commands, perform writes, transfer protected evidence, change DNS, change replicas, or alter RBAC. Sensitive Azure CLI stderr is suppressed and the workflow emits only sanitized counts and resource-type summaries.

## Proven source side

The existing `ets-azure-q1` GitHub environment successfully authenticates to the source Azure subscription with OIDC. A bounded source context probe verified the expected tenant, subscription, and Enabled state without an interactive human sign-in.

The one-time source bootstrap granted only:

- `Storage Table Data Reader` on the source Core storage account
- `Storage File Data Privileged Reader` on the source Gateway storage account

After propagation, GitHub OIDC completed source inventory with both protected data planes `ok`:

- live resource group: 24 resources
- Azure Table `ETSEvents`: 89 entities
- metadata rows: 1
- metadata `next_index`: 44
- Gateway active-share root entries: 3

The live evidence high-water mark increased from earlier protected captures, proving the source writer remains active. Do not treat any prior snapshot/export as the final cutover state; take a final fenced sync/high-water mark immediately before destination writer activation.

The source OIDC principal is a `ServicePrincipal`. Its sanitized role inventory includes the two scoped migration read roles in addition to its pre-existing bounded ETS roles. It does not expose an RBAC administrator role and must not self-escalate.

No new source workload identity is required for recurring read-only migration operations. Source human authentication should now be reserved for operator-only RBAC changes, write bootstrap, cutover approval, or irreversible actions.

## Proven destination side

The destination bootstrap created or reused:

```text
GitHub environment: ets-azure-migration-destination-read
Azure identity:     ets-gh-migration-dst-read
Federated subject:  repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-read
```

No client secret is required by this control path. GitHub receives a short-lived OIDC token and exchanges it through Azure Login.

The GitHub environment is configured with non-secret environment variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

A destination `context` run completed successfully and verified the expected tenant/subscription through OIDC without human MFA.

The first destination `inventory` run proved management-plane access and intentionally exposed the missing data-plane grants:

- context: `verified`
- resource count in the migration production group: 16
- RBAC summary: `ok`
- OIDC principal type: `ServicePrincipal`
- OIDC role summary: Reader at two resource-group scopes
- protected evidence data plane: `blocked`
- protected Gateway data plane: `blocked`

The 16 resources match the already approved zero-replica Core/Gateway staging deployment documented in the main migration runbook.

The idempotent `destination-read` bootstrap then ensured only:

- `Storage Table Data Reader` on the destination `ETSEvents` table
- `Storage File Data Privileged Reader` on the destination Gateway storage account

These are read-only validation grants; they do not permit evidence or Gateway file mutation.

After RBAC propagation, authoritative branch-push OIDC run `34270043390` at commit `aa0005be7c472ca93cd78100db47774fc5b90d5b` completed successfully on 2026-09-08. Azure Login succeeded through the federated environment subject and the bounded destination inventory reported:

- context: `verified`
- resource count: 16
- RBAC summary: `ok`
- evidence data plane: `ok`
- evidence entities: 1
- metadata rows: 1
- metadata `next_index`: 0
- Gateway data plane: `ok`
- Gateway root entries: 3
- `Reader`: two resource-group scopes
- `Storage Table Data Reader`: one resource scope
- `Storage File Data Privileged Reader`: one resource scope

The single destination evidence entity is the known initialized metadata row and the three Gateway root entries are the known inert initialization files from zero-replica staging. This run performed no evidence/file write, protected-state transfer, DNS change, replica change, or RBAC mutation.

## Trigger model while PR #611 remains open

The workflow supports the migration branch push-control file and PR execution. The request is deliberately tiny and contains no Azure identifiers. A `request_id` may be changed solely to force a fresh bounded run without changing operation semantics.

Example:

```json
{
  "schema_version": 1,
  "target": "source",
  "operation": "inventory",
  "request_id": "source-inventory-after-rbac"
}
```

The fixed operation set is currently:

- `context`
- `inventory`

No arbitrary Azure CLI arguments are forwarded from the request.

Push and pull-request executions use separate concurrency groups so PR validation cannot cancel the authoritative branch-push OIDC execution.

## Recommended sequence

1. Keep recurring source and destination discovery in ordinary ChatGPT/GitHub through OIDC; do not spend Work cycles on routine Azure sign-in.
2. Keep protected evidence transfer and restoration out of this read-only workflow. Implement the write path as a separately approval-gated identity/workflow with the narrowest destination data-plane contributor scopes.
3. Require protected source artifact rehydration and manifest/hash verification before any destination restore.
4. Preserve the destination initialization snapshot/metadata as rollback material before overwrite.
5. Before cutover, fence source writers and capture a final evidence/Gateway high-water mark because the live source state continues to advance.
6. Activate a destination writer only after restored evidence/Gateway state and historical signing continuity independently verify.

## Security boundary

The migration branch is the execution boundary while PR #611 is open. Azure Login receives OIDC tokens only through the configured GitHub environment trust. The Python control accepts a fixed operation set and never forwards user-supplied Azure CLI arguments.

The OIDC control plane reduces repeated human MFA; it does not bypass Azure policy. Human authentication remains limited to one-time identity/RBAC bootstrap and later operator-only approval for write/cutover or irreversible operations.
