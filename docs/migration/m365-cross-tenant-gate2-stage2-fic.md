# M365 cross-tenant Gate 2 — Stage 2 FIC

## Proven starting state

Stage 1 created exactly one destination multitenant application:

- display name: `ETS Gateway SharePoint Cross-Tenant`
- application ID: `0be62a70-45b5-405d-92b6-ca0ce3af953a`
- sign-in audience: `AzureADMultipleOrgs`
- no application passwords, certificates, redirect URIs, or requested API permissions

The post-Stage-1 read-only preview advanced to `destination_federated_identity_credential`.

## Stage 2 objective

Bind the destination Gateway UAMI to the Stage-1 application with exactly one federated identity credential:

- destination tenant: `0d20cf0f-3498-46c1-a0db-69b09c634cc2`
- resource group: `rg-ets-prod-eastus`
- UAMI: `ets-oif5r5ydprrou-gw-id`
- application ID: `0be62a70-45b5-405d-92b6-ca0ce3af953a`
- FIC name: `ets-gateway-sharepoint-uami`
- issuer: `https://login.microsoftonline.com/0d20cf0f-3498-46c1-a0db-69b09c634cc2/v2.0`
- subject: the live `principalId` of the exact UAMI above
- audience: exactly `api://AzureADTokenExchange`

The subject is intentionally resolved at execution time from the approved UAMI instead of being copied into source control.

## Safety boundary

The Stage-2 script defaults to preview and requires `-Apply` for the one permitted mutation. It re-reads Azure tenant context, the UAMI, the Stage-1 application, and the current FIC set before mutation. Any existing unexpected credential set is a hard stop.

Stage 2 does **not** create or modify the EchoMedia enterprise application, Graph app-role/admin-consent state, SharePoint permissions, Azure RBAC, managed identities, Gateway replicas, protected state, source fencing, DNS, writers, or cutover.

## Operator sequence

Preview first:

```powershell
./scripts/m365/apply-ets-sharepoint-cross-tenant-stage2-fic.ps1 `
  -DestinationAzureTenantId '0d20cf0f-3498-46c1-a0db-69b09c634cc2'
```

After explicit Stage-2 authorization, apply exactly once:

```powershell
./scripts/m365/apply-ets-sharepoint-cross-tenant-stage2-fic.ps1 `
  -DestinationAzureTenantId '0d20cf0f-3498-46c1-a0db-69b09c634cc2' `
  -Apply
```

After a successful apply, rerun the merged read-only bootstrap preview:

```powershell
./scripts/m365/preview-ets-sharepoint-cross-tenant-bootstrap.ps1 `
  -DestinationAzureTenantId '0d20cf0f-3498-46c1-a0db-69b09c634cc2' `
  -MicrosoftResourceTenantId '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'
```

Do not proceed automatically beyond the FIC boundary. The next preview result determines the Stage-3 work item.
