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

ensure_role() {
  local principal_id="$1"
  local role="$2"
  local scope="$3"
  local count

  # Do not use `--assignee` here. For a newly created managed identity Azure AD/
  # Microsoft Graph replication can lag behind ARM, causing `az role assignment
  # list --assignee ...` to fail even though the principalId is already valid.
  # Enumerating the exact scope and filtering by principalId avoids that Graph
  # lookup; creation below also uses --assignee-object-id for the same reason.
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

mode="${1:-}"

case "$mode" in
  source-data-read)
    SRC_RG="rg-ets-live-eastus"

    echo "Discovering the existing GitHub OIDC service principal from its bounded job roles..."
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT

    # Avoid `az role assignment list --all --role ...` here. Some Cloud Shell
    # Azure CLI builds fail while resolving a role name without an explicit scope
    # (ValueError: No value for given attribute). Enumerate once, then filter the
    # returned roleDefinitionName values locally in JMESPath instead.
    az role assignment list --all \
      --query "[?roleDefinitionName=='Container Apps Jobs Contributor'].principalId" \
      -o tsv | sort -u > "$tmpdir/contributor"
    az role assignment list --all \
      --query "[?roleDefinitionName=='Container Apps Jobs Operator'].principalId" \
      -o tsv | sort -u > "$tmpdir/operator"

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

    echo "Ensuring only the two required source data-plane reader roles..."
    ensure_role "$principal_id" "Storage Table Data Reader" "$core_id"
    ensure_role "$principal_id" "Storage File Data Privileged Reader" "$gateway_id"

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
    DEST_PROD_RG="rg-ets-prod-eastus"
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

    for rg in "$DEST_PROD_RG" "$DEST_RG"; do
      scope="$(az group show -n "$rg" --query id -o tsv)"
      ensure_role "$principal_id" "Reader" "$scope"
    done

    # If the isolated zero-replica destination stack already exists, also grant
    # the read-only OIDC identity the two narrow data-plane roles needed for
    # migration validation. These grants do not permit evidence/file mutation.
    mapfile -t dest_storage_rows < <(
      az storage account list -g "$DEST_PROD_RG" \
        --query "[].[name,id]" -o tsv
    )
    if [[ "${#dest_storage_rows[@]}" -gt 0 ]]; then
      dest_core_id=""
      dest_gateway_id=""
      for row in "${dest_storage_rows[@]}"; do
        name="${row%%$'\t'*}"
        id="${row#*$'\t'}"
        case "$name" in
          etsgw*) dest_gateway_id="$id" ;;
          *)
            if [[ -n "$dest_core_id" ]]; then
              echo "STOP: multiple destination non-Gateway storage accounts found." >&2
              exit 2
            fi
            dest_core_id="$id"
            ;;
        esac
      done
      if [[ -z "$dest_core_id" || -z "$dest_gateway_id" ]]; then
        echo "STOP: destination storage exists but Core/Gateway accounts were not uniquely discoverable." >&2
        exit 2
      fi

      table_id="$(az resource show \
        --ids "$dest_core_id/tableServices/default/tables/ETSEvents" \
        --query id -o tsv)"
      if [[ -z "$table_id" ]]; then
        echo "STOP: destination ETSEvents table ARM resource was not found." >&2
        exit 2
      fi

      echo "Ensuring destination read-only data-plane roles..."
      ensure_role "$principal_id" "Storage Table Data Reader" "$table_id"
      ensure_role "$principal_id" "Storage File Data Privileged Reader" "$dest_gateway_id"
    fi

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
