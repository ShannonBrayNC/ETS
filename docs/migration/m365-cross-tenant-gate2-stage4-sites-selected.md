# M365 Cross-Tenant Gate 2 — Stage 4: `Sites.Selected`

## Purpose

Stage 4 assigns exactly one Microsoft Graph application role to the EchoMedia resource-tenant enterprise application created in Stage 3: `Sites.Selected`.

This stage does **not** grant access to any SharePoint site. `Sites.Selected` only establishes the application-level permission boundary required before a later, separately authorized site-specific grant.

## Proven prerequisites

- Resource tenant: `38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe`
- Verified domain: `echomedia.ai`
- Approved operator: `shannon.bray@echomedia.ai`
- Destination owner tenant: `0d20cf0f-3498-46c1-a0db-69b09c634cc2`
- Connector application ID: `0be62a70-45b5-405d-92b6-ca0ce3af953a`
- Stage 2 federated identity credential exists and is verified.
- Stage 3 EchoMedia enterprise application exists and is verified as an enabled `Application` service principal owned by the destination tenant.
- The read-only Gate-2 preview returned `resource_sites_selected_assignment` as the first missing stage.

## Safety boundary

The Stage-4 script defaults to preview-only. Mutation requires `-Apply`.

Before any mutation it verifies:

1. Microsoft Graph is connected to the exact EchoMedia tenant.
2. The signed-in operator is the approved EchoMedia operator.
3. The EchoMedia organization contains the expected verified domain.
4. The connector service principal resolves uniquely by exact app ID and matches the expected owner/type/state.
5. Microsoft Graph resolves uniquely by its fixed application ID.
6. Exactly one enabled `Sites.Selected` app role exists and permits `Application` members.
7. The connector has no unexpected existing Graph app-role assignments.

The only permitted mutation is one Microsoft Graph POST that assigns the resolved `Sites.Selected` role to the connector service principal. The script then re-reads all app-role assignments and requires exactly one assignment matching the resolved Graph service principal and role.

## Explicit exclusions

Stage 4 does not:

- grant access to `echomediaai.sharepoint.com/sites/ETS` or any other SharePoint site;
- request or assign `Sites.FullControl.All`;
- create delegated grants;
- create or modify the destination application;
- create or modify federated identity credentials;
- create enterprise applications;
- create credentials;
- change Azure RBAC, managed identities, replicas, protected state, source fencing, DNS, writer state, or cutover state.

## Operator procedure

Do not run Stage 4 until its implementation PR is green/reviewed and the user separately authorizes **Stage 4 apply**.

Preview-only invocation:

```powershell
./scripts/m365/apply-ets-sharepoint-cross-tenant-stage4-sites-selected.ps1 `
  -MicrosoftResourceTenantId '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe'
```

Apply invocation after explicit authorization:

```powershell
./scripts/m365/apply-ets-sharepoint-cross-tenant-stage4-sites-selected.ps1 `
  -MicrosoftResourceTenantId '38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe' `
  -Apply
```

After a successful apply, restore Azure CLI to the destination Azure tenant if necessary and rerun `preview-ets-sharepoint-cross-tenant-bootstrap.ps1`. Stop at the next observed stage; do not assume or apply the SharePoint site grant automatically.
