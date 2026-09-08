# GitHub OIDC migration control plane

Status: staged, read-only, not yet authorized for destination Azure access.

## Purpose

Move recurring Azure authentication out of interactive Work/browser sessions. The control plane
uses GitHub Actions OIDC for bounded Azure reads, so a human account remains an operator/bootstrap
identity instead of the automation identity.

The workflow intentionally accepts only `context` and `inventory`. It does not accept arbitrary
shell commands, perform writes, transfer protected evidence, change DNS, change replicas, or alter
RBAC. Sensitive Azure CLI stderr is suppressed and the workflow emits only sanitized counts and
resource-type summaries.

## Source side

Reuse the existing `ets-azure-q1` GitHub environment first. Existing ETS workflows already use its
OIDC workload identity. No new source identity should be created unless the bounded probe proves
that the existing identity lacks required read access.

Set these environment variables in `ets-azure-q1` if they are not already present:

- `MIGRATION_SOURCE_RESOURCE_GROUP`
- `MIGRATION_SOURCE_CORE_STORAGE_ACCOUNT`
- `MIGRATION_SOURCE_GATEWAY_STORAGE_ACCOUNT`
- `MIGRATION_EVIDENCE_TABLE`
- `MIGRATION_SOURCE_GATEWAY_SHARE`

The workflow continues to use the existing environment secrets `AZURE_CLIENT_ID`,
`AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID`.

For an `inventory` request, the source workload identity needs only the data-plane permissions
required for the existing protected reads. If the probe reports `blocked`, add the exact missing
role at the narrow storage/table scope rather than broadening the subscription role.

## Destination side bootstrap

Create one read-only user-assigned managed identity after the human Azure sign-in pause expires.
Use the existing destination shared resource group so no new billable compute is introduced.
The exact tenant/subscription values belong in the operator session and GitHub environment secrets,
not this public file.

Suggested names:

```text
GitHub environment: ets-azure-migration-destination-read
Azure identity:     ets-gh-migration-dst-read
Federated subject:  repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-read
```

One-time Azure CLI bootstrap:

```bash
set -euo pipefail

DEST_SUB='<verified destination subscription id>'
DEST_RG='rg-ets-shared-eastus'
IDENTITY='ets-gh-migration-dst-read'
FIC='github-ets-migration-destination-read'
SUBJECT='repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-read'

az account set --subscription "$DEST_SUB"

az identity create \
  --resource-group "$DEST_RG" \
  --name "$IDENTITY" \
  --location eastus \
  --only-show-errors \
  -o none

CLIENT_ID="$(az identity show -g "$DEST_RG" -n "$IDENTITY" --query clientId -o tsv)"
PRINCIPAL_ID="$(az identity show -g "$DEST_RG" -n "$IDENTITY" --query principalId -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"

az identity federated-credential create \
  --resource-group "$DEST_RG" \
  --identity-name "$IDENTITY" \
  --name "$FIC" \
  --issuer 'https://token.actions.githubusercontent.com' \
  --subject "$SUBJECT" \
  --audiences 'api://AzureADTokenExchange' \
  --only-show-errors \
  -o none

for rg in rg-ets-prod-eastus rg-ets-shared-eastus; do
  scope="$(az group show -n "$rg" --query id -o tsv)"
  az role assignment create \
    --assignee-object-id "$PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role Reader \
    --scope "$scope" \
    --only-show-errors \
    -o none
done

printf 'AZURE_CLIENT_ID=%s\nAZURE_TENANT_ID=%s\nAZURE_SUBSCRIPTION_ID=%s\n' \
  "$CLIENT_ID" "$TENANT_ID" "$DEST_SUB"
```

Microsoft supports federated identity credentials on user-assigned managed identities. GitHub OIDC
uses `api://AzureADTokenExchange` as the Azure Login audience.

## GitHub destination environment

Create `ets-azure-migration-destination-read` in repository Settings, then add environment secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

Add environment variables after the destination resource names are read back:

- `MIGRATION_DESTINATION_RESOURCE_GROUP`
- `MIGRATION_DESTINATION_CORE_STORAGE_ACCOUNT`
- `MIGRATION_DESTINATION_GATEWAY_STORAGE_ACCOUNT`
- `MIGRATION_EVIDENCE_TABLE`
- `MIGRATION_DESTINATION_GATEWAY_SHARE`

Do not put passwords, SAS tokens, account keys, client secrets, evidence payloads, or private key
material into GitHub variables or this repository.

## Trigger model while PR #611 remains open

`workflow_dispatch` is retained for use after the workflow reaches the default branch. While the
workflow exists only on the migration branch, use the push-controlled request file instead. A
request is deliberately tiny and contains no Azure identifiers:

```json
{
  "schema_version": 1,
  "target": "destination",
  "operation": "context"
}
```

Store that as `.github/migration-control/request.json` on
`migration/azure-ets-destination-discovery`. Each change to the request file triggers one bounded
run. Do not add the request file until the corresponding GitHub environment is configured.

Recommended bootstrap sequence:

1. Configure the destination GitHub environment while Azure sign-in is paused.
2. After the pause, create the destination user-assigned identity and federated credential once.
3. Add the three returned IDs to the GitHub environment secrets.
4. Trigger `destination/context` and require a verified tenant/subscription/state result.
5. Add the destination resource-name variables and trigger `destination/inventory`.
6. Trigger `source/context` using the existing `ets-azure-q1` environment.
7. Trigger `source/inventory`; only if a data-plane read is blocked, grant the missing narrow role
   to the existing workload identity.
8. Keep protected evidence transfer and restoration out of this read-only workflow. Implement the
   write path as a separately approval-gated identity/workflow after both OIDC contexts are proven.

## Security boundary

The migration branch is the execution boundary while PR #611 is open. The workflow is push-triggered
only when the request file changes on that branch. Azure Login receives OIDC tokens only through the
configured GitHub environment trust. The Python control accepts a fixed operation set and never
forwards user-supplied Azure CLI arguments.

This control plane reduces repeated human MFA but does not bypass Azure policy. Human authentication
is still required for the one-time identity/RBAC bootstrap and any later operator-only approval.
