# M365 cross-tenant Gate 2 — Stage 3 resource enterprise application

## Proven entry condition

The post-Stage-2 read-only preview returned:

- `stage: resource_enterprise_application`
- `mutationRequired: true`
- `mutationPerformed: false`

Stage 1 created destination application `0be62a70-45b5-405d-92b6-ca0ce3af953a` (`ETS Gateway SharePoint Cross-Tenant`) as `AzureADMultipleOrgs`. Stage 2 created and verified the single Gateway UAMI federated identity credential. The EchoMedia resource tenant still lacks the corresponding enterprise application/service principal.

## Stage 3 boundary

Stage 3 may create exactly one service principal in Microsoft resource tenant `38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe` for application `0be62a70-45b5-405d-92b6-ca0ce3af953a`.

Before mutation, the operator script verifies:

- the active Azure CLI tenant is exactly the EchoMedia resource tenant;
- the active operator is `shannon.bray@echomedia.ai`;
- verified domain `echomedia.ai` exists in that tenant;
- zero or one service principal exists for the approved application ID;
- any existing service principal is enabled, type `Application`, and owned by destination tenant `0d20cf0f-3498-46c1-a0db-69b09c634cc2`.

The script defaults to preview. Creation requires `-Apply`. If creation occurs, the script re-reads the tenant and requires exactly one correctly shaped service principal before reporting success.

## Explicit exclusions

Stage 3 does **not** assign Microsoft Graph application roles, grant admin consent, assign `Sites.Selected`, create SharePoint site permissions, modify the Stage-1 application, modify the Stage-2 FIC, create credentials, modify Azure RBAC/UAMIs, move protected state, fence source, enable replicas/writers, alter DNS, or perform cutover.

## Operator flow after merge and explicit Stage 3 authorization

1. Authenticate Azure CLI to the EchoMedia tenant without requiring a subscription:

   `az login --tenant 38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe --allow-no-subscriptions`

2. Preview the bounded operation:

   `./scripts/m365/apply-ets-sharepoint-cross-tenant-stage3-resource-enterprise-app.ps1 -MicrosoftResourceTenantId 38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe`

3. Only after explicit Stage 3 authorization, rerun with `-Apply`.

4. Restore Azure CLI to the destination Azure tenant/subscription before invoking the cross-tenant Gate-2 preview:

   `az login --tenant 0d20cf0f-3498-46c1-a0db-69b09c634cc2`

   `az account set --subscription 5729a82b-8850-4868-b96c-96c3805cbb9d`

5. Rerun `preview-ets-sharepoint-cross-tenant-bootstrap.ps1` and stop at the next observed stage.
