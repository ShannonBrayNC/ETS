# Live Gateway identity bootstrap v1

## Purpose

This gate pre-creates the persistent Azure user-assigned managed identity used by the hosted Microsoft Gateway before ETS Core is deployed.

The identity is created independently of the Core/Gateway runtime so its exact application/client ID can later be bound to two separate server-side controls:

1. the Core `evidence_producer` application role; and
2. Core's `ETS_AUTH_APP_SCOPE_MAP_JSON` tenant/workspace mapping.

Neither control is established by this bootstrap workflow.

## Release identity

The currently authorized live runtime image remains:

- source: `332d7db3a69acd826a2a000264e81a179894e278`
- digest: `sha256:c83a8cb0729d7e00506e4b7b9f0d0e5a7c5bbe3829abad76113ba7fd1ee3424c`

Creating the Azure identity does not rebuild or supersede that image.

## Deterministic Azure boundary

The one-shot workflow uses non-customer naming seeds:

- location: `eastus`
- resource group: `rg-ets-live-eastus`
- environment seed: `ets-live`
- connector seed: `m365-sharepoint-primary`

`infra/azure/ets-gateway-identity.bicep` derives the actual managed-identity name from the resource group ID plus the two seeds. The same values must be supplied to the later Gateway deployment so it resolves the same identity.

The resource group is created only when absent. If it already exists, the workflow refuses to use it unless its region and ownership tags match the expected live ETS boundary.

## Authentication boundary

The workflow runs in the protected `ets-azure-q1` GitHub environment and uses workload-identity federation through the existing Azure OIDC secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

No client secret or reusable Azure credential is introduced.

The workflow verifies that the Azure CLI session tenant and subscription equal the protected environment values before it creates or reuses the resource group.

## Evidence retention

The exact managed-identity client ID and principal ID are masked and are not written to the public handoff artifact or issue comment.

The retained handoff contains only bounded release facts such as the release image identity, generic Azure naming boundary, managed-identity resource name, and explicit release nonclaims.

The exact client ID is re-read from Azure during the subsequent protected deployment/operator gate when it is needed to build the Core scope map or validate the Entra assignment.

## Next operator gate

After the identity is ready, use the governed scripts introduced by #414:

1. `scripts/azure/ensure-core-evidence-producer-app-role.ps1`
2. `scripts/azure/provision-gateway-core-evidence-producer.ps1`

The operator must authenticate Azure CLI and Microsoft Graph PowerShell to the EchoMedia deployment tenant and must validate the expected verified domain before applying directory mutation.

That operator gate must establish all of the following before runtime deployment:

- an existing Core application registration is selected by exact client ID;
- the Core application exposes exactly one enabled `evidence_producer` application role with the governed role ID;
- the exact Gateway UAMI service principal holds that role and no unexpected Core role;
- the exact Gateway client ID is available for Core's server-owned ETS tenant/workspace scope map.

## Nonclaims

This bootstrap does **not**:

- create or alter the Core Entra application registration;
- assign `evidence_producer` to the Gateway;
- configure the Core app-to-ETS-scope map;
- deploy Core or Gateway Container Apps;
- grant Microsoft Graph `Sites.Selected` or SharePoint site permission;
- complete #390 source-to-proof qualification; or
- start the 72-hour soak clock.
