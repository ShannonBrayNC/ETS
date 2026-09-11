# M365 Gate 2 isolated runtime qualification

This runbook handles the final Gate 2 workload-identity proof when the production Gateway Container App is intentionally staged at zero active revisions and zero replicas.

## Observed boundary

The merged runtime preview proved:

- destination tenant and subscription are correct;
- Gateway Container App `ets-oif5r5ydprrou-gw` exists;
- Gateway UAMI `ets-oif5r5ydprrou-gw-id` exists and is attached;
- active revisions: `0`;
- active replicas: `0`;
- `runtimeReadReady: false`;
- `runtimeActivationRequired: true`;
- no mutation was performed.

The normal Gateway must **not** be scaled up merely to satisfy the proof. Its production entrypoint composes the hosted Microsoft Gateway and starts bounded polling workers, which can update Gateway runtime/store state. That is broader than the read-only identity qualification.

## Safer execution model

The approved implementation prepares a temporary **manual Azure Container Apps Job** in the same managed environment instead of activating a Gateway revision.

The job reuses only:

- the exact immutable Gateway image already configured on the Gateway Container App;
- the exact Gateway UAMI for the cross-tenant token exchange;
- the already-existing dedicated ACR pull identity and registry configuration;
- the audited `qualify_ets_sharepoint_workload_identity.py` harness.

The job deliberately does **not** inherit or mount Gateway state, does not run `ets.gateway.container_entrypoint`, does not receive Core relay configuration, and does not start connector workers.

The job is one-shot:

- manual trigger;
- one replica;
- one successful completion required;
- zero retries;
- 180-second timeout;
- Graph GETs only inside the Python harness.

The apply wrapper creates the job through the `Microsoft.App/jobs` ARM resource directly so no CLI helper can opportunistically create ACR role assignments. The existing pull identity must already have the required registry access.

## Preview

After the implementation PR is merged, authenticate Azure CLI to the destination tenant and subscription and run without `-Apply`:

```powershell
az login --tenant '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
az account set --subscription '5729a82b-8850-4868-b96c-96c3805cbb9d'

.\scripts\m365\invoke-ets-sharepoint-workload-identity-isolated-job.ps1
```

Expected preview characteristics:

```json
{
  "mode": "preview_only",
  "stage": "gateway_isolated_workload_identity_execution",
  "mutationRequired": true,
  "mutationPerformed": false,
  "productionGatewayZeroRuntimeVerified": true,
  "gatewayManagedIdentityVerified": true,
  "registryPullIdentityVerified": true,
  "immutableGatewayImageVerified": true,
  "temporaryJobRequired": true,
  "gatewayContainerAppMutationPlanned": false,
  "azureRbacMutationPlanned": false,
  "gatewayStateMountPlanned": false,
  "gatewayEntrypointPlanned": false
}
```

Stop after preview until the isolated runtime execution is separately authorized.

## Apply authorization boundary

`-Apply` temporarily creates, starts, verifies, and deletes one qualification job. That is an Azure control-plane mutation even though the workload itself is read-only.

The authorization does **not** include:

- production Gateway revision activation or scale changes;
- Gateway runtime/store writes;
- ACR or other Azure RBAC changes;
- UAMI/FIC/application/service-principal changes;
- Microsoft Graph role changes;
- SharePoint permission changes;
- Gateway state-share mounts;
- protected-state movement;
- source fencing;
- DNS, writer activation, routing, or cutover.

## Apply behavior

When separately authorized:

```powershell
.\scripts\m365\invoke-ets-sharepoint-workload-identity-isolated-job.ps1 -Apply
```

The wrapper must:

1. re-prove the production Gateway remains at zero active revisions/replicas;
2. re-read the exact Gateway UAMI, immutable image, managed environment, registry, and pull identity;
3. create one temporary manual job with the exact image and identities;
4. inject only the audited runtime qualification harness;
5. start one execution and require `Succeeded`;
6. require sanitized success markers proving the federated provider, `Sites.Selected`, exact `/sites/ETS`, and default-drive-root read;
7. delete the job in `finally`;
8. verify the temporary job no longer exists;
9. re-prove the production Gateway still has zero active revisions/replicas.

Expected final sanitized result:

```json
{
  "qualification": "pass",
  "mode": "gateway_uami_isolated_container_apps_job",
  "stage": "gateway_workload_identity_runtime_read",
  "temporaryAzureMutationPerformed": true,
  "temporaryJobCreated": true,
  "temporaryJobDeleted": true,
  "productionGatewayMutationPerformed": false,
  "productionGatewayZeroRuntimeRestored": true,
  "gatewayEntrypointStarted": false,
  "gatewayStateMounted": false,
  "azureRbacMutationPerformed": false,
  "federatedCredentialProviderVerified": true,
  "resourceTenantTokenVerified": true,
  "applicationTokenVerified": true,
  "sitesSelectedRoleClaimVerified": true,
  "exactSharePointSiteVerified": true,
  "defaultDriveRootReadVerified": true,
  "reusableCredentialRetained": false,
  "sharePointPayloadRetained": false
}
```

## Gate completion rule

M365 Gate 2 is green only when both are true:

1. the structural qualification has already reported `qualification: pass` with no mutation; and
2. this isolated Gateway-UAMI runtime proof reports `qualification: pass` and successfully removes the temporary job.

A Gate 2 pass still does not authorize source fencing, destination writer activation, DNS changes, protected-state transfer, production routing, or cutover.
