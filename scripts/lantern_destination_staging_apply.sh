#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 5 ]]; then
  echo "usage: lantern_destination_staging_apply.sh <tenant> <subscription> <resource-group> <site-source> <report>" >&2
  exit 2
fi

expected_tenant="$1"
expected_subscription="$2"
resource_group="$3"
site_source="$4"
qualification_report="$5"

approved_tenant="0d20cf0f-3498-46c1-a0db-69b09c634cc2"
approved_subscription="5729a82b-8850-4868-b96c-96c3805cbb9d"
approved_resource_group="rg-ets-prod-eastus"
profile_name="lantern-destination-fd"
origin_group_name="lantern-destination-static"
origin_name="lantern-destination-storage"
route_name="lantern-destination-site"

if [[ "${expected_tenant,,}" != "$approved_tenant" ]]; then
  echo "Lantern destination staging blocked: unexpected destination tenant" >&2
  exit 2
fi
if [[ "${expected_subscription,,}" != "$approved_subscription" ]]; then
  echo "Lantern destination staging blocked: unexpected destination subscription" >&2
  exit 2
fi
if [[ "$resource_group" != "$approved_resource_group" ]]; then
  echo "Lantern destination staging blocked: unexpected destination resource group" >&2
  exit 2
fi
if [[ ! -d "$site_source" || ! -f "$site_source/index.html" ]]; then
  echo "Lantern destination staging blocked: deployable site is unavailable" >&2
  exit 2
fi

active_subscription="$(az account show --query id -o tsv)"
active_tenant="$(az account show --query tenantId -o tsv)"
if [[ "${active_subscription,,}" != "$approved_subscription" ]]; then
  echo "Lantern destination staging blocked: active subscription differs" >&2
  exit 2
fi
if [[ "${active_tenant,,}" != "$approved_tenant" ]]; then
  echo "Lantern destination staging blocked: active tenant differs" >&2
  exit 2
fi
location="$(az group show --name "$resource_group" --query location -o tsv)"
if [[ "$location" != "eastus" ]]; then
  echo "Lantern destination staging blocked: destination resource group region differs" >&2
  exit 2
fi

suffix="$(printf '%s' "${approved_subscription}:${resource_group}:lantern-destination" | sha256sum | cut -c1-13)"
storage_account="lanterndst${suffix}"
endpoint_suffix="$(printf '%s' "${approved_subscription}:${resource_group}:lantern-destination-frontdoor" | sha256sum | cut -c1-10)"
endpoint_name="lantern-dst-${endpoint_suffix}"

if az storage account show --name "$storage_account" --resource-group "$resource_group" >/dev/null 2>&1; then
  workload_tag="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query tags.workload -o tsv)"
  purpose_tag="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query tags.purpose -o tsv)"
  if [[ "$workload_tag" != "lantern-site" || "$purpose_tag" != "tenant-exit-staging" ]]; then
    echo "Lantern destination staging blocked: deterministic storage account is not owned by this gate" >&2
    exit 2
  fi
else
  az storage account create \
    --name "$storage_account" \
    --resource-group "$resource_group" \
    --location eastus \
    --sku Standard_LRS \
    --kind StorageV2 \
    --https-only true \
    --min-tls-version TLS1_2 \
    --public-network-access Enabled \
    --tags workload=lantern-site purpose=tenant-exit-staging owner=lantern-protocol \
    --output none
fi

kind="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query kind -o tsv)"
https_only="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query enableHttpsTrafficOnly -o tsv)"
min_tls="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query minimumTlsVersion -o tsv)"
if [[ "$kind" != "StorageV2" || "${https_only,,}" != "true" || "$min_tls" != "TLS1_2" ]]; then
  echo "Lantern destination staging blocked: storage security posture differs" >&2
  exit 2
fi

az storage blob service-properties update \
  --account-name "$storage_account" \
  --auth-mode login \
  --static-website \
  --index-document index.html \
  --output none

storage_endpoint="$(az storage account show --name "$storage_account" --resource-group "$resource_group" --query primaryEndpoints.web -o tsv)"
if [[ "$storage_endpoint" != https://*.web.core.windows.net/ ]]; then
  echo "Lantern destination staging blocked: static website endpoint is invalid" >&2
  exit 2
fi

# Dedicated destination staging storage may be replaced exactly; source storage is never addressed.
az storage blob delete-batch \
  --account-name "$storage_account" \
  --auth-mode login \
  --source '$web' \
  --output none || true
az storage blob upload-batch \
  --account-name "$storage_account" \
  --auth-mode login \
  --destination '$web' \
  --source "$site_source" \
  --overwrite true \
  --output none

origin_host="${storage_endpoint#https://}"
origin_host="${origin_host%/}"

if az afd profile show -g "$resource_group" --profile-name "$profile_name" >/dev/null 2>&1; then
  purpose_tag="$(az afd profile show -g "$resource_group" --profile-name "$profile_name" --query tags.purpose -o tsv)"
  sku_name="$(az afd profile show -g "$resource_group" --profile-name "$profile_name" --query sku.name -o tsv)"
  if [[ "$purpose_tag" != "tenant-exit-staging" || "$sku_name" != "Standard_AzureFrontDoor" ]]; then
    echo "Lantern destination staging blocked: deterministic Front Door profile is not owned by this gate" >&2
    exit 2
  fi
else
  az afd profile create \
    -g "$resource_group" \
    --profile-name "$profile_name" \
    --sku Standard_AzureFrontDoor \
    --tags workload=lantern-site purpose=tenant-exit-staging owner=lantern-protocol \
    --output none
fi

if ! az afd endpoint show -g "$resource_group" --profile-name "$profile_name" --endpoint-name "$endpoint_name" >/dev/null 2>&1; then
  az afd endpoint create \
    -g "$resource_group" \
    --profile-name "$profile_name" \
    --endpoint-name "$endpoint_name" \
    --enabled-state Enabled \
    --tags workload=lantern-site purpose=tenant-exit-staging \
    --output none
fi

if ! az afd origin-group show -g "$resource_group" --profile-name "$profile_name" --origin-group-name "$origin_group_name" >/dev/null 2>&1; then
  az afd origin-group create \
    -g "$resource_group" \
    --profile-name "$profile_name" \
    --origin-group-name "$origin_group_name" \
    --probe-request-type GET \
    --probe-protocol Https \
    --probe-interval-in-seconds 60 \
    --probe-path / \
    --sample-size 4 \
    --successful-samples-required 3 \
    --additional-latency-in-milliseconds 50 \
    --output none
fi

if az afd origin show -g "$resource_group" --profile-name "$profile_name" --origin-group-name "$origin_group_name" --origin-name "$origin_name" >/dev/null 2>&1; then
  az afd origin update \
    -g "$resource_group" \
    --profile-name "$profile_name" \
    --origin-group-name "$origin_group_name" \
    --origin-name "$origin_name" \
    --host-name "$origin_host" \
    --origin-host-header "$origin_host" \
    --priority 1 \
    --weight 1000 \
    --enabled-state Enabled \
    --http-port 80 \
    --https-port 443 \
    --output none
else
  az afd origin create \
    -g "$resource_group" \
    --profile-name "$profile_name" \
    --origin-group-name "$origin_group_name" \
    --origin-name "$origin_name" \
    --host-name "$origin_host" \
    --origin-host-header "$origin_host" \
    --priority 1 \
    --weight 1000 \
    --enabled-state Enabled \
    --http-port 80 \
    --https-port 443 \
    --output none
fi

if az afd route show -g "$resource_group" --profile-name "$profile_name" --endpoint-name "$endpoint_name" --route-name "$route_name" >/dev/null 2>&1; then
  az afd route update \
    -g "$resource_group" \
    --profile-name "$profile_name" \
    --endpoint-name "$endpoint_name" \
    --route-name "$route_name" \
    --origin-group "$origin_group_name" \
    --enabled-state Enabled \
    --forwarding-protocol HttpsOnly \
    --https-redirect Enabled \
    --link-to-default-domain Enabled \
    --patterns-to-match '/*' \
    --supported-protocols Http Https \
    --output none
else
  az afd route create \
    -g "$resource_group" \
    --profile-name "$profile_name" \
    --endpoint-name "$endpoint_name" \
    --route-name "$route_name" \
    --origin-group "$origin_group_name" \
    --enabled-state Enabled \
    --forwarding-protocol HttpsOnly \
    --https-redirect Enabled \
    --link-to-default-domain Enabled \
    --patterns-to-match '/*' \
    --supported-protocols Http Https \
    --output none
fi

afd_host="$(az afd endpoint show -g "$resource_group" --profile-name "$profile_name" --endpoint-name "$endpoint_name" --query hostName -o tsv)"
if [[ "$afd_host" != *.azurefd.net ]]; then
  echo "Lantern destination staging blocked: Front Door default endpoint is invalid" >&2
  exit 2
fi

python -m scripts.lantern_destination_staging_verify \
  --site-root "$site_source" \
  --storage-endpoint "$storage_endpoint" \
  --frontdoor-endpoint "https://${afd_host}/" \
  --storage-account "$storage_account" \
  --frontdoor-profile "$profile_name" \
  --frontdoor-endpoint-name "$endpoint_name" \
  --attempts 24 \
  --delay-seconds 15 \
  --output "$qualification_report"
