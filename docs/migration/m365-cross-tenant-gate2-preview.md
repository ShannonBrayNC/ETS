# Microsoft 365 cross-tenant Gate 2 preview

## Purpose

Gate 2 qualifies the Microsoft 365 identity path required by the destination ETS Gateway without
changing either tenant. The preview is intentionally separate from the merged Azure migration
control in PR #611.

The approved SharePoint path is:

`destination Gateway UAMI -> destination multitenant application/FIC -> EchoMedia enterprise application -> Microsoft Graph Sites.Selected -> echomediaai.sharepoint.com/sites/ETS read grant`

The exact destination SharePoint/Core Gateway UAMI proven by the merged migration-control work is:

- resource group: `rg-ets-prod-eastus`
- managed identity: `ets-oif5r5ydprrou-gw-id`

Directory and Purview use distinct destination UAMIs and are outside this SharePoint preview slice.

## Preview-only operator command

Run from a trusted operator workstation that is already authenticated to the destination Azure
subscription and can authenticate interactively to Microsoft Graph in both tenants:

```powershell
./scripts/m365/preview-ets-sharepoint-cross-tenant-bootstrap.ps1 `
  -DestinationAzureTenantId '0d20cf0f-3498-46c1-a0db-69b09c634cc2' `
  -MicrosoftResourceTenantId '<echomedia-tenant-id>'
```

The script performs Azure and Microsoft Graph reads only. It has no `-Apply` switch and contains no
Graph POST/PATCH/PUT/DELETE path.

## Stages

The preview stops at the first missing or incomplete component and reports `mutationRequired: true`
without performing the mutation:

1. `destination_multitenant_application`
2. `destination_multitenant_application_configuration`
3. `destination_federated_identity_credential`
4. `resource_enterprise_application`
5. `resource_sites_selected_assignment`
6. `sharepoint_site_read_grant`
7. `ready_for_read_only_qualification`

Unexpected duplicate applications, unexpected federated credentials, additional Graph application
permissions, wrong enterprise-app ownership, or non-read SharePoint grants fail closed rather than
being normalized automatically.

## Required federation contract

The dedicated SharePoint application must be multitenant (`AzureADMultipleOrgs`) and have exactly
one federated identity credential with:

- issuer: `https://login.microsoftonline.com/<destination-tenant-id>/v2.0`
- subject: the exact destination Gateway UAMI principal ID
- audience: `api://AzureADTokenExchange`

The corresponding enterprise application in the EchoMedia tenant must be owned by the destination
Azure tenant and must have only Microsoft Graph `Sites.Selected` as an application permission.
The approved SharePoint site must expose exactly one grant to that application, with role `read`.

## Nonclaims

A green preview does not deploy the Gateway, raise replicas, transfer writer ownership, copy
protected state, change DNS, or complete the migration. It only proves that the identity and
permission components required for the later read-only qualification already exist in the expected
shape.

If the preview reports a missing stage, any mutation to create that component requires a separate
explicitly reviewed and authorized apply step. After all components exist, rerun
`test-ets-sharepoint-connector-qualification.ps1` and then perform separate positive and negative
token-authorization tests before raising destination replicas above zero.
