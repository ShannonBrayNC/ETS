# Microsoft P0 separated-identity bootstrap v1

Parent: #543

## Purpose

This preview-first bootstrap creates and attaches two dedicated user-assigned managed identities
(UAMIs) to the private hosted Gateway and grants only the application permissions required by the
bounded P0 Microsoft connector family:

| Runtime profile | Resource application | Required application roles |
| --- | --- | --- |
| Entra users/groups delta | Microsoft Graph | `User.Read.All`, `Group.Read.All` |
| Purview audit activity | Office 365 Management APIs | `ActivityFeed.Read` |

The existing Gateway identity remains the SharePoint/Core identity. Its `Sites.Selected` site grant
and Core `evidence_producer` assignment are not inspected, copied, or changed by this bootstrap.
The directory allowlist excludes `Directory.Read.All` and every Graph write role. The Purview
allowlist excludes `ActivityFeed.ReadDlp`, `ServiceHealth.Read`, and every Microsoft Graph role.

Microsoft documents `User.Read.All` and `Group.Read.All` as application permissions that require
admin consent. Microsoft also documents `ActivityFeed.Read` as the Office 365 Management API
application permission for collecting audit activity. App-only permissions are represented as
`appRoleAssignment` records whose `principalId`, `resourceId`, and `appRoleId` bind the client
service principal to an exact role on an exact resource service principal.

References:

- [Microsoft Graph permissions reference](https://learn.microsoft.com/graph/permissions-reference)
- [Office 365 Management APIs setup](https://learn.microsoft.com/office/office-365-management-api/get-started-with-office-365-management-apis)
- [Grant a service-principal app role](https://learn.microsoft.com/graph/api/serviceprincipal-post-approleassignedto?view=graph-rest-1.0)
- [Container Apps managed identities](https://learn.microsoft.com/azure/container-apps/managed-identity)
- [Container Apps Bicep identity settings](https://learn.microsoft.com/azure/templates/microsoft.app/containerapps)

## Infrastructure boundary

`infra/azure/ets-gateway-identity.bicep` pre-creates three deterministic UAMIs:

1. the existing SharePoint/Core Gateway identity;
2. a directory-only identity; and
3. a Purview-only identity.

`infra/azure/ets-gateway.bicep` attaches all three runtime identities to the private Container App
with `lifecycle: 'Main'`. The ACR pull identity remains separate with `lifecycle: 'None'`. Only the
directory and Purview client IDs are exposed to the container as configuration; no token, password,
certificate, client secret, or operator credential is placed in Bicep output or container state.

The identity resources do not grant Microsoft Graph or Office 365 Management API permissions by
themselves. Directory mutation remains an explicit delegated operator action.

## Operator prerequisites

- Azure CLI authenticated to the deployment subscription;
- Microsoft Graph PowerShell commands (`Connect-MgGraph`, `Get-MgContext`,
  `Invoke-MgGraphRequest`, and `Disconnect-MgGraph`);
- an operator eligible to consent to the requested application permissions; and
- active Azure CLI and Graph contexts bound to the same tenant containing the verified
  `echomedia.ai` domain.

Preview uses process-scoped delegated `User.Read` and `Application.Read.All`. Apply additionally
requests `AppRoleAssignment.ReadWrite.All`, which Microsoft documents together with
`Application.Read.All` as the least-privileged delegated permission pair for creating a service
principal app-role assignment. The script does not request `Directory.Read.All` or
`Application.ReadWrite.All` and has no app-only secret or certificate path.

## Preview first

Deploy the pre-bootstrap template and retain its outputs only in the protected operator workspace:

```powershell
az deployment group create `
  --resource-group '<gateway-resource-group>' `
  --template-file ./infra/azure/ets-gateway-identity.bicep `
  --parameters environmentName='<environment>' connectorInstanceId='<instance-id>'
```

Run the permission bootstrap without `-Apply`:

```powershell
./scripts/azure/provision-microsoft-p0-connector-app-roles.ps1 `
  -ResourceGroup '<gateway-resource-group>' `
  -SharePointManagedIdentityName '<sharepoint-core-uami-name>' `
  -DirectoryManagedIdentityName '<directory-uami-name>' `
  -PurviewManagedIdentityName '<purview-uami-name>'
```

The preview resolves Microsoft Graph and Office 365 Management APIs by immutable application ID,
resolves role IDs dynamically by exact role value, checks that all three client service principals
are distinct exact Azure UAMIs, and enumerates every directory/Purview app-role assignment with
bounded pagination. It does not enumerate or mutate the SharePoint/Core identity's permissions.

Preview fails closed if:

- either resource application or role is missing, disabled, ambiguous, or not assignable to an
  application;
- the SharePoint/Core, directory, and Purview UAMIs are not distinct;
- a UAMI service-principal object ID differs from Azure's `principalId`;
- a required assignment is duplicated; or
- either UAMI has any application permission outside its exact allowlist.

An unexpected permission is never deleted or normalized implicitly. It requires separate operator
investigation and an explicit remediation decision.

## Apply and reread

After reviewing the exact identities, resource applications, roles, and `mutationRequired=true`,
run:

```powershell
./scripts/azure/provision-microsoft-p0-connector-app-roles.ps1 `
  -ResourceGroup '<gateway-resource-group>' `
  -SharePointManagedIdentityName '<sharepoint-core-uami-name>' `
  -DirectoryManagedIdentityName '<directory-uami-name>' `
  -PurviewManagedIdentityName '<purview-uami-name>' `
  -Apply
```

Apply creates only missing allowlisted assignments, rereads the complete assignment sets, and
requires both identities to converge exactly. Re-running the command is idempotent.

## Evidence and nonclaims

Raw operator output can contain managed-identity identifiers and must not be published. Retain only
protected, bounded evidence needed for the live gate: verified-domain outcome, exact role values and
IDs, assignment outcomes, and the explicit `reusableCredentialRetained=false` and
`sourcePayloadRetained=false` flags.

This bootstrap does not prove token acquisition, source authorization, delta continuity, Purview
subscription health, evidence completeness, live source-to-proof operation, or customer isolation.
It does not start the 72-hour soak and does not authorize a public hostname. The next #543 slice
must compose the separated credential profiles and connector instances in the hosted runtime and
qualify each identity/audience pair independently.
