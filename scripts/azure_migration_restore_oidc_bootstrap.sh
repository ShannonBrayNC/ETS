#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  azure_migration_restore_oidc_bootstrap.sh <destination-subscription-id>

Run only from an operator-authenticated destination Azure Cloud Shell after the
GitHub environment `ets-azure-migration-destination-restore` has been created and
protected with required reviewers / restricted deployment branches.

This helper creates or reuses one user-assigned managed identity plus one GitHub
OIDC federated credential. It grants only:

- Reader on rg-ets-prod-eastus
- Storage Table Data Contributor on the destination ETSEvents table
- Storage File Data Privileged Reader on the destination Gateway storage account
- Storage File Data Privileged Contributor on the destination active Gateway share

The account-level Azure Files grant is read-only and exists because the verified
`az storage file list --auth-mode login --backup-intent` path requires account-level
read authorization. File mutation authority remains constrained to the active
Gateway share.

It does not copy evidence, modify Gateway files, change DNS, change replicas,
create application credentials, or activate a destination writer.
EOF
}

ensure_role() {
  local principal_id="$1"
  local role="$2"
  local scope="$3"
  local count

  count="$(az role assignment list \
    --scope "$scope" \
    --query "[?principalId=='$principal_id' && roleDefinitionName=='$role'] | length(@)" \
    -o tsv)"
  if [[ "$count" == "0" ]]; then
    az role assignment create \
      --assignee-object-id "$principal_id" \
      --assignee-principal-type ServicePrincipal \
      --role "$role" \
      --scope "$scope" \
      --only-show-errors -o none
  elif [[ "$count" != "1" ]]; then
    echo "STOP: expected zero or one '$role' assignment at the exact scope; found $count." >&2
    exit 2
  fi
}

DEST_SUB="${1:-}"
if [[ -z "$DEST_SUB" ]]; then
  usage >&2
  exit 2
fi

DEST_SHARED_RG="rg-ets-shared-eastus"
DEST_PROD_RG="rg-ets-prod-eastus"
GATEWAY_SHARE="ets-gateway-state-q1-v2"
IDENTITY="ets-gh-migration-dst-restore"
FIC="github-ets-migration-destination-restore"
SUBJECT="repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-restore"

az account set --subscription "$DEST_SUB"
actual_sub="$(az account show --query id -o tsv)"
if [[ "${actual_sub,,}" != "${DEST_SUB,,}" ]]; then
  echo "STOP: destination subscription context mismatch." >&2
  exit 2
fi

for rg in "$DEST_SHARED_RG" "$DEST_PROD_RG"; do
  if ! az group show -n "$rg" --only-show-errors -o none 2>/dev/null; then
    echo "STOP: required destination resource group '$rg' is missing." >&2
    exit 2
  fi
done

mapfile -t storage_rows < <(
  az storage account list -g "$DEST_PROD_RG" --query "[].[name,id]" -o tsv
)
core_id=""
gateway_id=""
for row in "${storage_rows[@]}"; do
  name="${row%%$'\t'*}"
  id="${row#*$'\t'}"
  case "$name" in
    etsgw*)
      if [[ -n "$gateway_id" ]]; then
        echo "STOP: multiple destination Gateway storage accounts found." >&2
        exit 2
      fi
      gateway_id="$id"
      ;;
    *)
      if [[ -n "$core_id" ]]; then
        echo "STOP: multiple destination Core storage accounts found." >&2
        exit 2
      fi
      core_id="$id"
      ;;
  esac
done
if [[ -z "$core_id" || -z "$gateway_id" ]]; then
  echo "STOP: destination Core/Gateway storage accounts were not uniquely discoverable." >&2
  exit 2
fi

table_id="$(az resource show \
  --ids "$core_id/tableServices/default/tables/ETSEvents" \
  --query id -o tsv)"
share_id="$(az resource show \
  --ids "$gateway_id/fileServices/default/shares/$GATEWAY_SHARE" \
  --query id -o tsv)"
prod_rg_id="$(az group show -n "$DEST_PROD_RG" --query id -o tsv)"
if [[ -z "$table_id" || -z "$share_id" || -z "$gateway_id" || -z "$prod_rg_id" ]]; then
  echo "STOP: exact destination restore scopes could not be resolved." >&2
  exit 2
fi

if ! az identity show -g "$DEST_SHARED_RG" -n "$IDENTITY" --only-show-errors -o none 2>/dev/null; then
  az identity create \
    --resource-group "$DEST_SHARED_RG" \
    --name "$IDENTITY" \
    --location eastus \
    --only-show-errors -o none
fi

client_id="$(az identity show -g "$DEST_SHARED_RG" -n "$IDENTITY" --query clientId -o tsv)"
principal_id="$(az identity show -g "$DEST_SHARED_RG" -n "$IDENTITY" --query principalId -o tsv)"
tenant_id="$(az account show --query tenantId -o tsv)"

# Fail closed if this restore identity has any known broad administrative role.
broad_count="$(az role assignment list --all \
  --query "[?principalId=='$principal_id' && contains(['Owner','Contributor','User Access Administrator','Role Based Access Control Administrator'], roleDefinitionName)] | length(@)" \
  -o tsv)"
if [[ "$broad_count" != "0" ]]; then
  echo "STOP: restore identity already has a broad administrative role; no scoped roles were added." >&2
  exit 2
fi

if ! az identity federated-credential show \
  --resource-group "$DEST_SHARED_RG" \
  --identity-name "$IDENTITY" \
  --name "$FIC" \
  --only-show-errors -o none 2>/dev/null; then
  az identity federated-credential create \
    --resource-group "$DEST_SHARED_RG" \
    --identity-name "$IDENTITY" \
    --name "$FIC" \
    --issuer 'https://token.actions.githubusercontent.com' \
    --subject "$SUBJECT" \
    --audiences 'api://AzureADTokenExchange' \
    --only-show-errors -o none
fi

ensure_role "$principal_id" "Reader" "$prod_rg_id"
ensure_role "$principal_id" "Storage Table Data Contributor" "$table_id"
ensure_role "$principal_id" "Storage File Data Privileged Reader" "$gateway_id"
ensure_role "$principal_id" "Storage File Data Privileged Contributor" "$share_id"

echo
echo "Destination restore OIDC identity is scoped and ready for an approval-gated workflow."
echo "GitHub environment: ets-azure-migration-destination-restore"
printf 'AZURE_CLIENT_ID=%s\nAZURE_TENANT_ID=%s\nAZURE_SUBSCRIPTION_ID=%s\n' \
  "$client_id" "$tenant_id" "$DEST_SUB"
echo
echo "These are identifiers, not client secrets. Do not create a client secret."
echo "Do not implement or trigger protected-state writes until the restore preflight and protected artifact hash checks pass."
