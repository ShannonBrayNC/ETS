#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  azure_migration_source_transfer_oidc_bootstrap.sh <source-subscription-id>

Run only from an operator-authenticated SOURCE Azure Cloud Shell.

This helper creates/reuses one dedicated source read-only user-assigned managed
identity plus one GitHub OIDC federated credential for the already protected
restore environment. It grants only:

- Reader on rg-ets-live-eastus
- Storage Table Data Reader on the exact source ETSEvents table
- Storage File Data Privileged Reader on the exact active Gateway share

It does not copy evidence, modify Gateway files, create snapshots, change DNS,
change replicas, create application credentials, or activate a writer.
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

SRC_SUB="${1:-}"
if [[ -z "$SRC_SUB" ]]; then
  usage >&2
  exit 2
fi

SRC_LIVE_RG="rg-ets-live-eastus"
SRC_IDENTITY_RG="rg-ets-q1-eastus"
GATEWAY_SHARE="ets-gateway-state-q1-v2"
IDENTITY="ets-gh-migration-src-transfer"
FIC="github-ets-migration-source-transfer"
SUBJECT="repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-restore"

az account set --subscription "$SRC_SUB"
actual_sub="$(az account show --query id -o tsv)"
if [[ "${actual_sub,,}" != "${SRC_SUB,,}" ]]; then
  echo "STOP: source subscription context mismatch." >&2
  exit 2
fi

for rg in "$SRC_LIVE_RG" "$SRC_IDENTITY_RG"; do
  if ! az group show -n "$rg" --only-show-errors -o none 2>/dev/null; then
    echo "STOP: required source resource group '$rg' is missing." >&2
    exit 2
  fi
done

mapfile -t storage_rows < <(
  az storage account list -g "$SRC_LIVE_RG" --query "[].[name,id]" -o tsv
)
core_id=""
gateway_id=""
for row in "${storage_rows[@]}"; do
  name="${row%%$'\t'*}"
  id="${row#*$'\t'}"
  case "$name" in
    etsgw*)
      if [[ -n "$gateway_id" ]]; then
        echo "STOP: multiple source Gateway storage accounts found." >&2
        exit 2
      fi
      gateway_id="$id"
      ;;
    lantern*) ;;
    *)
      if [[ -n "$core_id" ]]; then
        echo "STOP: multiple source Core storage accounts found." >&2
        exit 2
      fi
      core_id="$id"
      ;;
  esac
done
if [[ -z "$core_id" || -z "$gateway_id" ]]; then
  echo "STOP: source Core/Gateway storage accounts were not uniquely discoverable." >&2
  exit 2
fi

table_id="$(az resource show \
  --ids "$core_id/tableServices/default/tables/ETSEvents" \
  --query id -o tsv)"
share_id="$(az resource show \
  --ids "$gateway_id/fileServices/default/shares/$GATEWAY_SHARE" \
  --query id -o tsv)"
live_rg_id="$(az group show -n "$SRC_LIVE_RG" --query id -o tsv)"
if [[ -z "$table_id" || -z "$share_id" || -z "$live_rg_id" ]]; then
  echo "STOP: exact source transfer scopes could not be resolved." >&2
  exit 2
fi

if ! az identity show -g "$SRC_IDENTITY_RG" -n "$IDENTITY" --only-show-errors -o none 2>/dev/null; then
  az identity create \
    --resource-group "$SRC_IDENTITY_RG" \
    --name "$IDENTITY" \
    --location eastus \
    --only-show-errors -o none
fi

client_id="$(az identity show -g "$SRC_IDENTITY_RG" -n "$IDENTITY" --query clientId -o tsv)"
principal_id="$(az identity show -g "$SRC_IDENTITY_RG" -n "$IDENTITY" --query principalId -o tsv)"
tenant_id="$(az account show --query tenantId -o tsv)"

broad_count="$(az role assignment list --all \
  --query "[?principalId=='$principal_id' && contains(['Owner','Contributor','User Access Administrator','Role Based Access Control Administrator'], roleDefinitionName)] | length(@)" \
  -o tsv)"
if [[ "$broad_count" != "0" ]]; then
  echo "STOP: source transfer identity already has a broad administrative role; no scoped roles were added." >&2
  exit 2
fi

if ! az identity federated-credential show \
  --resource-group "$SRC_IDENTITY_RG" \
  --identity-name "$IDENTITY" \
  --name "$FIC" \
  --only-show-errors -o none 2>/dev/null; then
  az identity federated-credential create \
    --resource-group "$SRC_IDENTITY_RG" \
    --identity-name "$IDENTITY" \
    --name "$FIC" \
    --issuer 'https://token.actions.githubusercontent.com' \
    --subject "$SUBJECT" \
    --audiences 'api://AzureADTokenExchange' \
    --only-show-errors -o none
fi

ensure_role "$principal_id" "Reader" "$live_rg_id"
ensure_role "$principal_id" "Storage Table Data Reader" "$table_id"
ensure_role "$principal_id" "Storage File Data Privileged Reader" "$share_id"

echo
echo "Source transfer OIDC identity is read-only and ready for the protected restore environment."
echo "GitHub environment: ets-azure-migration-destination-restore"
printf 'SOURCE_AZURE_CLIENT_ID=%s\nSOURCE_AZURE_TENANT_ID=%s\nSOURCE_AZURE_SUBSCRIPTION_ID=%s\n' \
  "$client_id" "$tenant_id" "$SRC_SUB"
echo
echo "These are identifiers, not client secrets. Do not create a client secret."
echo "This identity cannot write ETS evidence or Gateway state."
