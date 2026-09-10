# Microsoft 365 cross-tenant Gate 2 stage 1 apply

## Proven prerequisite

The merged Gate 2 preview was run interactively against the approved destination Azure tenant and
EchoMedia Microsoft resource tenant. It returned:

- `stage: destination_multitenant_application`
- `mutationRequired: true`
- `mutationPerformed: false`
- destination Azure tenant verified
- destination Gateway UAMI `ets-oif5r5ydprrou-gw-id` verified

Therefore the first missing Gate 2 component is the destination application registration.

## Authorized stage 1 mutation

Stage 1 may create exactly one Entra application object in destination tenant
`0d20cf0f-3498-46c1-a0db-69b09c634cc2` with:

- display name `ETS Gateway SharePoint Cross-Tenant`;
- `signInAudience` equal to `AzureADMultipleOrgs`;
- no password credentials;
- no certificate credentials;
- no redirect URIs;
- no identifier URIs;
- no requested API permissions.

The stage 1 script defaults to preview and requires `-Apply` before it can create the application.
It re-reads the destination state before mutation, refuses duplicate or mismatched state, and
re-reads the application after creation before reporting success.

## Explicit exclusions

Stage 1 does not create or modify federated identity credentials, service principals in the
EchoMedia tenant, Microsoft Graph role assignments or admin consent, SharePoint site permissions,
Azure managed identities/RBAC, Gateway replicas, protected state, source fencing, writers, DNS, or
cutover state.

## Operator command

Use a trusted PowerShell 7 session with Azure CLI authenticated to the destination tenant and
subscription. Preview first:

```powershell
.\scripts\m365\apply-ets-sharepoint-cross-tenant-stage1.ps1 `
  -DestinationAzureTenantId '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
```

After explicit Stage 1 authorization, execute:

```powershell
.\scripts\m365\apply-ets-sharepoint-cross-tenant-stage1.ps1 `
  -DestinationAzureTenantId '0d20cf0f-3498-46c1-a0db-69b09c634cc2' `
  -Apply
```

## Post-apply gate

Capture the JSON result. A successful creation must report `mutationPerformed: true` and the
verified application ID. Then rerun the merged
`preview-ets-sharepoint-cross-tenant-bootstrap.ps1` against both tenant IDs. Do not create a FIC or
any resource-tenant permission automatically; the preview must identify the next missing stage and
that mutation must be separately reviewed.
