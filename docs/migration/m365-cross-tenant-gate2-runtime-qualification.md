# M365 Gate 2 runtime qualification

This runbook is the final read-only proof for the ETS SharePoint cross-tenant Gate 2 chain.
It follows the structural qualification that already passed for the destination Gateway UAMI,
multitenant application, FIC, EchoMedia enterprise application, Microsoft Graph
`Sites.Selected`, and the exact `/sites/ETS` `read` grant.

## Approved runtime target

- destination tenant: `0d20cf0f-3498-46c1-a0db-69b09c634cc2`
- destination subscription: `5729a82b-8850-4868-b96c-96c3805cbb9d`
- resource group: `rg-ets-prod-eastus`
- Gateway Container App: `ets-oif5r5ydprrou-gw`
- Gateway UAMI: `ets-oif5r5ydprrou-gw-id`
- EchoMedia resource tenant: `38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe`
- multitenant application: `0be62a70-45b5-405d-92b6-ca0ce3af953a`
- site host/path: `echomediaai.sharepoint.com` / `/sites/ETS`
- canonical site ID:
  `echomediaai.sharepoint.com,2604ea4c-3b40-4195-b1a8-e3d7327b7c41,9ddf1ece-7f81-4258-af25-91e06afaa682`
- required app role: `Sites.Selected`

## What this qualification proves

The runtime harness uses the same production credential implementation used by the hosted
Gateway: `AzureFederatedManagedIdentityCredentialProvider`.

It asks the configured Gateway UAMI for an assertion at
`api://AzureADTokenExchange/.default`, exchanges that assertion through the approved
multitenant application into the EchoMedia tenant, obtains a Microsoft Graph app-only token,
and performs two bounded GETs:

1. resolve the exact approved `/sites/ETS` site;
2. read only the default document-library root metadata.

The harness verifies the access-token tenant, application identity, app-only shape, and exact
`Sites.Selected` role claim. It does not print or persist token material. It does not emit
SharePoint payload contents.

## Phase 1: Azure-side preview

Authenticate Azure CLI to the destination tenant and subscription, then run:

```powershell
az login --tenant '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
az account set --subscription '5729a82b-8850-4868-b96c-96c3805cbb9d'

.\scripts\m365\preview-ets-sharepoint-workload-identity-runtime.ps1
```

The preview reads only Azure resource state. It verifies the exact Container App and UAMI
attachment and reports active revision/replica counts. It never activates or deactivates a
revision, changes replica settings, modifies RBAC, or changes identity configuration.

If the result contains:

```json
{
  "stage": "gateway_runtime_activation_boundary",
  "runtimeReadReady": false,
  "runtimeActivationRequired": true
}
```

**Stop.** The current Gate 2 authorization does not permit activating the Gateway or changing
replica state. A separate runtime-execution authorization is required before proceeding.

## Phase 2: existing-replica workload-identity proof

Proceed only when the preview reports `runtimeReadReady: true` and at least one active replica.
Run:

```powershell
.\scripts\m365\invoke-ets-sharepoint-workload-identity-runtime-qualification.ps1
```

The invoker re-runs the read-only preview first. If no active replica exists, it fails closed.
When a replica is already active, it injects the audited Python qualification source through
`az containerapp exec`; it does not deploy a new image or modify Container App configuration.
The remote script imports the installed ETS production credential provider from the running
Gateway image.

Expected successful sanitized result:

```json
{
  "qualification": "pass",
  "mode": "gateway_workload_identity",
  "mutationPerformed": false,
  "managedIdentityEndpointVerified": true,
  "managedIdentityClientIdPresent": true,
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

## Failure interpretation

A failure is evidence, not permission to broaden the configuration.

- Missing managed-identity runtime endpoint means the command is not executing in an Azure
  managed-identity context.
- Missing `AzureFederatedManagedIdentityCredentialProvider` means the deployed Gateway image is
  stale relative to the audited repository implementation.
- Token-exchange failure means the UAMI/FIC/application cross-tenant path is not yet usable from
  the runtime context.
- Token claim mismatch means the token is not the exact approved EchoMedia app-only Graph token.
- Site or drive-root GET failure means the effective `Sites.Selected` site authorization is not
  functioning for the workload identity.

Do not add broader Graph roles, SharePoint permissions, RBAC, or activate writers in response to
a failed qualification without a separate reviewed change.

## Gate completion rule

Gate 2 is complete only after both conditions are true:

1. structural qualification reports `qualification: pass` with no mutation;
2. the runtime workload-identity harness reports `qualification: pass` from the actual Gateway
   managed-identity execution context.

This runbook does not authorize source fencing, destination writer activation, DNS changes,
protected-state movement, production routing, or cutover.
