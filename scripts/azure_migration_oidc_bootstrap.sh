#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  azure_migration_oidc_bootstrap.sh source-data-read
  azure_migration_oidc_bootstrap.sh destination-read <destination-subscription-id>

Run only from an operator-authenticated Azure Cloud Shell. The script performs no
DNS, application, evidence, or replica changes. It creates only scoped RBAC grants
for source read access or one destination read-only user-assigned identity/FIC.
EOF
}

mode="${1:-}"

case "$mode" in
  source-data-read)
    SRC_RG="rg-ets-live-eastus"

    echo "Discovering the existing GitHub OIDC service principal from its bounded job roles..."
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT

    az role assignment list --all \
      --role "Container Apps Jobs Contributor" \
      --query '[].principalId' -o tsv | sort -u > "$tmpdir/contributor"
    az role assignment list --all \
      --role "Container Apps Jobs Operator" \
      --query '[].principalId' -o tsv | sort -u > "$tmpdir/operator"

    mapfile -t candidates < <(comm -12 "$tmpdir/contributor" "$tmpdir/operator")
    if [[ "${#candidates[@]}" -ne 1 ]]; then
      echo "STOP: expected exactly one principal holding both ETS GitHub job roles; found ${#candidates[@]}." >&2
      echo "No RBAC changes were made." >&2
      exit 2
    fi
    principal_id="${candidates[0]}"

    mapfile -t storage_rows < <(
      az storage account list -g "$SRC_RG" \
        --query "[].[name,id]" -o tsv
    )
    core_id=""
    gateway_id=""
    for row in "${storage_rows[@]}"; do
      name="${row%%$'\t'*}"
      id="${row#*$'\t'}"
      case "$name" in
        etsgw*) gateway_id="$id" ;;
        lantern*) ;;
        *)
          if [[ -n "$core_id" ]]; then
            echo "STOP: multiple non-Gateway/non-Lantern storage accounts found." >&2
            exit 2
          fi
          core_id="$id"
          ;;
      esac
    done
    if [[ -z "$core_id" || -z "$gateway_id" ]]; then
      echo "STOP: could not uniquely discover source Core and Gateway storage accounts." >&2
      exit 2
    fi

    echo "Granting only the two missing source data-plane reader roles..."
    az role assignment create \
      --assignee-object-id "$principal_id" \
      --assignee-principal-type ServicePrincipal \
      --role "Storage Table Data Reader" \
      --scope "$core_id" \
      --only-show-errors -o none

    az role assignment create \
      --assignee-object-id "$principal_id" \
      --assignee-principal-type ServicePrincipal \
      --role "Storage File Data Privileged Reader" \
      --scope "$gateway_id" \
      --only-show-errors -o none

    echo "Source GitHub OIDC data-plane read roles are assigned."
    echo "Allow Azure RBAC propagation before rerunning source/inventory."
    ;;

  destination-read)
    DEST_SUB="${2:-}"
    if [[ -z "$DEST_SUB" ]]; then
      usage >&2
      exit 2
    fi
    DEST_RG="rg-ets-shared-eastus"
    IDENTITY="ets-gh-migration-dst-read"
    FIC="github-ets-migration-destination-read"
    SUBJECT="repo:ShannonBrayNC/ETS:environment:ets-azure-migration-destination-read"

    az account set --subscription "$DEST_SUB"
    actual_sub="$(az account show --query id -o tsv)"
    if [[ "${actual_sub,,}" != "${DEST_SUB,,}" ]]; then
      echo "STOP: destination subscription context mismatch." >&2
      exit 2
    fi

    if ! az identity show -g "$DEST_RG" -n "$IDENTITY" --only-show-errors -o none 2>/dev/null; then
      az identity create \
        --resource-group "$DEST_RG" \
        --name "$IDENTITY" \
        --location eastus \
        --only-show-errors -o none
    fi

    client_id="$(az identity show -g "$DEST_RG" -n "$IDENTITY" --query clientId -o tsv)"
    principal_id="$(az identity show -g "$DEST_RG" -n "$IDENTITY" --query principalId -o tsv)"
    tenant_id="$(az account show --query tenantId -o tsv)"

    if ! az identity federated-credential show \
      --resource-group "$DEST_RG" \
      --identity-name "$IDENTITY" \
      --name "$FIC" \
      --only-show-errors -o none 2>/dev/null; then
      az identity federated-credential create \
        --resource-group "$DEST_RG" \
        --identity-name "$IDENTITY" \
        --name "$FIC" \
        --issuer 'https://token.actions.githubusercontent.com' \
        --subject "$SUBJECT" \
        --audiences 'api://AzureADTokenExchange' \
        --only-show-errors -o none
    fi

    for rg in rg-ets-prod-eastus rg-ets-shared-eastus; do
      scope="$(az group show -n "$rg" --query id -o tsv)"
      az role assignment create \
        --assignee-object-id "$principal_id" \
        --assignee-principal-type ServicePrincipal \
        --role Reader \
        --scope "$scope" \
        --only-show-errors -o none || true
    done

    echo
    echo "Destination read-only OIDC identity is ready."
    echo "Add the following values to GitHub environment: ets-azure-migration-destination-read"
    printf 'AZURE_CLIENT_ID=%s\nAZURE_TENANT_ID=%s\nAZURE_SUBSCRIPTION_ID=%s\n' \
      "$client_id" "$tenant_id" "$DEST_SUB"
    echo
    echo "These are identifiers, not client secrets. Do not create a client secret."
    ;;

  *)
    usage >&2
    exit 2
    ;;
esac
