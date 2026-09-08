# GitHub OIDC migration control plane

Status: source management-plane OIDC proven; source Table/File data-plane reads require two narrow
RBAC grants; destination OIDC bootstrap remains operator-authenticated one-time work.

## Purpose

Move recurring Azure authentication out of interactive Work/browser sessions. The control plane
uses GitHub Actions OIDC for bounded Azure reads, so a human account remains an operator/bootstrap
identity instead of the automation identity.

The workflow intentionally accepts only `context` and `inventory`. It does not accept arbitrary
shell commands, perform writes, transfer protected evidence, change DNS, change replicas, or alter
RBAC. Sensitive Azure CLI stderr is suppressed and the workflow emits only sanitized counts and
resource-type summaries.

## Proven source side

The existing `ets-azure-q1` GitHub environment successfully authenticates to the source Azure
subscription with OIDC. A bounded source context probe verified the expected tenant, subscription,
and Enabled state without an interactive human sign-in.

A subsequent read-only inventory successfully enumerated the live resource group (24 resources)
but reported both protected data planes as `blocked`:

- Azure Table `ETSEvents`
- Azure Files Gateway state share

The OIDC principal is a `ServicePrincipal`. Its sanitized role inventory includes scoped Reader,
AcrPush, Container Apps Jobs Contributor/Operator, Managed Identity Operator, Container Registry
configuration/data-access reader, and Storage Blob Data Contributor. It does **not** include the two
roles needed for the migration's protected Table/File reads, and it does not expose an RBAC
administrator role that would justify self-escalation.

Therefore do not create a new source identity. After the next operator-authenticated source session,
run:

```bash
bash scripts/azure_migration_oidc_bootstrap.sh source-data-read
```

The helper discovers the existing GitHub OIDC principal by the intersection of its bounded
Container Apps Jobs roles, fails unless there is exactly one match, discovers the Core and Gateway
storage accounts without printing their protected data, and ensures only:

- `Storage Table Data Reader` on the source Core storage account
- `Storage File Data Privileged Reader` on the source Gateway storage account

After Azure RBAC propagation, change `.github/migration-control/request.json` to `source/inventory`
and rerun. The expected success condition is protected Table/File read status `ok` with only
sanitized counts in public Actions output.

## Destination side bootstrap

Create one read-only user-assigned managed identity after the human Azure sign-in pause expires.
Use the existing destination shared resource group so no new billable compute is introduced.
The exact tenant/subscription values belong in the operator session and GitHub environment settings,
not this public file.

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

It verifies the selected subscription, creates or reuses the read-only user-assigned identity,
creates or reuses the GitHub federated credential, and ensures Reader only on
`rg-ets-prod-eastus` and `rg-ets-shared-eastus`. It then prints the three identifiers needed by
GitHub. It creates no client secret.

Microsoft supports federated identity credentials on user-assigned managed identities. GitHub OIDC
uses `api://AzureADTokenExchange` as the Azure Login audience.

## GitHub destination environment

Create `ets-azure-migration-destination-read` in repository Settings, then add environment values
for:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

The workflow currently consumes those names through the environment's existing secret interface;
they are identifiers, not authentication secrets. The OIDC token issued by GitHub is the actual
short-lived credential. Do not create or store a client secret.

Do not put passwords, SAS tokens, account keys, evidence payloads, or private key material into
GitHub variables, Actions logs, artifacts, or this public repository.

## Trigger model while PR #611 remains open

The workflow supports both the migration branch push-control file and PR execution. The request is
deliberately tiny and contains no Azure identifiers:

```json
{
  "schema_version": 1,
  "target": "source",
  "operation": "inventory"
}
```

The fixed operation set is currently:

- `context`
- `inventory`

No arbitrary Azure CLI arguments are forwarded from the request.

## Recommended sequence

1. While human Azure sign-in is paused, keep using ordinary ChatGPT/GitHub work to prepare and test
   migration code; do not spend Work cycles retrying Azure authentication.
2. When source human access is available, run `source-data-read` once and allow RBAC propagation.
3. Rerun `source/inventory` and require both Table and Gateway data planes to report `ok`.
4. In the destination human session, run `destination-read` once.
5. Add the three returned destination identifiers to the GitHub environment.
6. Trigger `destination/context` and require a verified tenant/subscription/state result.
7. Trigger `destination/inventory` and add only any exact data-plane reader roles proven missing.
8. Keep protected evidence transfer and restoration out of this read-only workflow. Implement the
   write path as a separately approval-gated identity/workflow after both OIDC contexts are proven.

## Security boundary

The migration branch is the execution boundary while PR #611 is open. Azure Login receives OIDC
tokens only through the configured GitHub environment trust. The Python control accepts a fixed
operation set and never forwards user-supplied Azure CLI arguments.

The OIDC control plane reduces repeated human MFA; it does not bypass Azure policy. Human
authentication remains limited to one-time identity/RBAC bootstrap and later operator-only approval
for write/cutover or irreversible operations.
