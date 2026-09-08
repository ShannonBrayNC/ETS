# GitHub OIDC migration control plane

Status: source management-plane and protected Table/File data-plane OIDC reads proven; destination OIDC bootstrap remains operator-authenticated one-time work.

## Purpose

Move recurring Azure authentication out of interactive Work/browser sessions. The control plane uses GitHub Actions OIDC for bounded Azure reads, so a human account remains an operator/bootstrap identity instead of the automation identity.

The workflow intentionally accepts only `context` and `inventory`. It does not accept arbitrary shell commands, perform writes, transfer protected evidence, change DNS, change replicas, or alter RBAC. Sensitive Azure CLI stderr is suppressed and the workflow emits only sanitized counts and resource-type summaries.

## Proven source side

The existing `ets-azure-q1` GitHub environment successfully authenticates to the source Azure subscription with OIDC. A bounded source context probe verified the expected tenant, subscription, and Enabled state without an interactive human sign-in.

The one-time source bootstrap granted only:

- `Storage Table Data Reader` on the source Core storage account
- `Storage File Data Privileged Reader` on the source Gateway storage account

After propagation, GitHub OIDC run 12 completed source inventory with both protected data planes `ok`:

- live resource group: 24 resources
- Azure Table `ETSEvents`: 89 entities
- metadata rows: 1
- metadata `next_index`: 44
- Gateway active-share root entries: 3

The live evidence high-water mark increased from earlier protected captures, proving the source writer remains active. Do not treat any prior snapshot/export as the final cutover state; take a final fenced sync/high-water mark immediately before destination writer activation.

The OIDC principal is a `ServicePrincipal`. Its sanitized role inventory now includes the two scoped migration read roles in addition to its pre-existing bounded ETS roles. It does not expose an RBAC administrator role and must not self-escalate.

No new source workload identity is required for recurring read-only migration operations. Source human authentication should now be reserved for operator-only RBAC changes, write bootstrap, cutover approval, or irreversible actions.

## Destination side bootstrap

Create one read-only user-assigned managed identity in the verified destination shared resource group. The exact tenant/subscription values belong in the operator session and GitHub environment settings, not this public file.

Suggested names:

```text
GitHub environment: ets-azure-migration-destination-read
Azure identity:     ets-gh-migration-dst-read
Federated subject:  repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-read
```

The checked-in helper performs the bounded bootstrap:

```bash
bash scripts/azure_migration_oidc_bootstrap.sh destination-read '<verified destination subscription id>'
```

It verifies the selected subscription, creates or reuses the read-only user-assigned identity, creates or reuses the GitHub federated credential, and ensures Reader only on `rg-ets-prod-eastus` and `rg-ets-shared-eastus`. It then prints the three identifiers needed by GitHub. It creates no client secret.

Microsoft supports federated identity credentials on user-assigned managed identities. GitHub OIDC uses `api://AzureADTokenExchange` as the Azure Login audience.

## GitHub destination environment

Create `ets-azure-migration-destination-read` in repository Settings, then add environment values for:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

The workflow consumes those names through the environment's existing secret interface; they are identifiers, not authentication secrets. The OIDC token issued by GitHub is the actual short-lived credential. Do not create or store a client secret.

Do not put passwords, SAS tokens, account keys, evidence payloads, or private key material into GitHub variables, Actions logs, artifacts, or this public repository.

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

## Recommended sequence

1. Keep recurring source discovery in ordinary ChatGPT/GitHub through OIDC; do not spend Work cycles on source sign-in.
2. In the destination human session, run `destination-read` once.
3. Add the three returned destination identifiers to the GitHub environment.
4. Trigger `destination/context` and require a verified tenant/subscription/state result.
5. Trigger `destination/inventory` and add only any exact data-plane reader roles proven missing.
6. Keep protected evidence transfer and restoration out of this read-only workflow. Implement the write path as a separately approval-gated identity/workflow after both OIDC contexts are proven.
7. Before cutover, fence source writers and capture a final evidence/Gateway high-water mark because the live source state continues to advance.

## Security boundary

The migration branch is the execution boundary while PR #611 is open. Azure Login receives OIDC tokens only through the configured GitHub environment trust. The Python control accepts a fixed operation set and never forwards user-supplied Azure CLI arguments.

The OIDC control plane reduces repeated human MFA; it does not bypass Azure policy. Human authentication remains limited to one-time identity/RBAC bootstrap and later operator-only approval for write/cutover or irreversible operations.
