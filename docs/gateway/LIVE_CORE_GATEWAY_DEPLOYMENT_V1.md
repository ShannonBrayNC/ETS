# Live Core + Gateway deployment v1

## Purpose

This gate deploys the persistent hosted ETS Core and Microsoft Gateway into the already-qualified live Azure resource group after the operator-governed Entra identity binding is complete.

It does not create or modify Entra application registrations, grant application roles, grant SharePoint access, prove a live Gateway producer token, complete #390, or start the 72-hour soak clock.

The deployment-authoritative release identity remains:

- source: `332d7db3a69acd826a2a000264e81a179894e278`
- image: `etsq1a352eb89.azurecr.io/ets/hosted-q1@sha256:c83a8cb0729d7e00506e4b7b9f0d0e5a7c5bbe3829abad76113ba7fd1ee3424c`

The earlier `3a8e4547...` image is superseded and must not be deployed.

## Preconditions

The following gates must be complete before dispatch:

1. the persistent Gateway UAMI exists in `rg-ets-live-eastus` as `ets-o23bf2d6oq44s-gw-id`;
2. the governed ETS Core API registration exists in the target Microsoft tenant;
3. the stable Core `evidence_producer` application role exists;
4. that exact live Gateway UAMI is assigned the Core `evidence_producer` role;
5. the operator has selected explicit ETS tenant and workspace identifiers;
6. the exact Gateway client ID is the only key in the Core app-to-ETS-scope map;
7. the protected deployment environment contains the exact authentication and connector values described below.

The recommended operator path is the merged `scripts/azure/provision-live-core-gateway-identity.ps1` orchestration. Run it without `-Apply` first, then with `-Apply` after validating the target tenant and ETS tenant/workspace values.

## Protected environment values

The deployment reuses the protected `ets-azure-q1` environment for Azure workload-identity federation. It requires the existing Azure OIDC values:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

It also requires these protected live values from the identity orchestration and approved Microsoft connector scope:

- `ETS_LIVE_CORE_SCOPE` — exact `api://<core-app-id>/.default` scope;
- `ETS_LIVE_AUTH_AUDIENCE` — exact `api://<core-app-id>` audience;
- `ETS_LIVE_AUTH_ISSUER` — tenant-specific v2 issuer;
- `ETS_LIVE_AUTH_JWKS_URL` — tenant-specific v2 JWKS endpoint;
- `ETS_LIVE_AUTH_TENANT_ID` — target Microsoft tenant ID;
- `ETS_LIVE_AUTH_APP_SCOPE_MAP_JSON` — exact single-client Gateway scope map;
- `ETS_LIVE_TENANT_ID` — selected ETS tenant identifier;
- `ETS_LIVE_WORKSPACE_ID` — selected ETS workspace identifier;
- `ETS_LIVE_MICROSOFT_TENANT_ID` — Microsoft connector tenant ID;
- `ETS_LIVE_SHAREPOINT_DRIVE_ID` — exact approved SharePoint drive ID for the later #390 gate.

Do not put these exact values in a public issue comment or public artifact. They are not reusable credentials, but they are deployment identity and customer-scope material.

## Fail-closed preflight

`.github/workflows/live-core-gateway-deployment.yml` is manual-only and accepts no workflow inputs.

Before creating runtime resources it:

1. authenticates to Azure using workload identity federation;
2. requires the active tenant and subscription to match the protected environment;
3. requires the existing live resource group to remain in `eastus` with the governed ownership tags;
4. re-reads `ets-o23bf2d6oq44s-gw-id` from Azure;
5. requires the Core auth tenant and Microsoft connector tenant to equal the protected Azure tenant;
6. requires the Core scope to equal `<audience>/.default`;
7. requires the issuer and JWKS URL to be the exact tenant-specific v2 endpoints;
8. parses `ETS_LIVE_AUTH_APP_SCOPE_MAP_JSON` and requires exactly one application/client key;
9. requires that key to equal the re-read live Gateway client ID;
10. requires the scope-map tenant/workspace binding to equal the separately protected ETS tenant/workspace values.

Any mismatch stops deployment.

## Core deployment

The workflow deploys `infra/azure/ets-hosted.bicep` using the authoritative immutable image.

The Core profile remains:

- Azure Table durable event storage;
- Azure Key Vault PS256 tree-head signing;
- production JWKS authentication;
- server-owned application-to-ETS-scope mapping;
- internal Container Apps ingress;
- one replica;
- managed identity for runtime data-plane access;
- separate pull-only managed identity for ACR.

The Core deployment creates the shared Container Apps managed environment. The workflow then resolves that environment from the live resource group and refuses to continue unless exactly one managed environment exists.

## Gateway deployment

The workflow deploys `infra/azure/ets-gateway.bicep` into that exact shared managed environment.

It passes:

- the same authoritative immutable image as Core;
- the Core internal HTTPS FQDN;
- the exact Core `.default` scope;
- the selected ETS tenant/workspace;
- deterministic connector/source identifiers;
- the exact Microsoft tenant and approved SharePoint drive;
- the same production JWKS contract;
- the same server-owned Gateway app-to-ETS-scope map.

After deployment it re-reads the live UAMI again and requires the Gateway Bicep output client ID to match that exact Azure identity. A newly created or substituted Gateway principal is therefore rejected.

## Deployment verification

The workflow reads the resulting Container App resource definitions without exposing them publicly and verifies:

- Core and Gateway both use the authoritative digest-pinned image;
- both ingresses remain internal;
- both are fixed at one replica;
- Core is configured for Azure Table storage and Azure Key Vault signing;
- both use `production_jwks`;
- both contain the exact protected authentication scope map;
- Gateway points to the exact Core internal FQDN;
- Gateway uses the exact Core `.default` scope;
- Gateway uses the selected ETS tenant/workspace and exact Microsoft connector scope.

This proves configuration convergence, not live request success.

## Public evidence boundary

The successful workflow may publish only bounded release evidence such as:

- release source SHA and image digest;
- Azure resource group;
- non-customer Core/Gateway resource names;
- non-customer Gateway managed-identity name;
- immutable image verified: true;
- internal ingress verified: true;
- single-replica configuration verified: true;
- Core scope map configured: true;
- Azure runtime resources deployed: true.

It must not publish the Gateway client/principal IDs, Core application ID, ETS tenant/workspace IDs, Microsoft tenant ID, SharePoint drive ID, exact scope map, or reusable credentials.

## Nonclaims after deployment

A successful deployment does **not** by itself prove:

- Core or Gateway health from an in-environment client;
- that the Gateway managed identity can obtain a Core token;
- that the token contains `roles: ["evidence_producer"]`;
- that Core accepts Gateway evidence ingestion;
- that a principal without `evidence.create` is denied by the live deployment;
- that SharePoint `Sites.Selected` is granted;
- that Microsoft Graph notification/delta collection works live;
- #390 source-to-proof success;
- soak-clock start.

Those claims remain false until separately retained evidence exists.

## Next gate

After this deployment succeeds, run a same-environment qualification client that proves both sides of the Core authorization boundary:

1. the live Gateway UAMI obtains a token for the exact Core `.default` scope with the `evidence_producer` role and successfully submits a synthetic evidence event to Core; and
2. a bounded authenticated control principal without `evidence.create` receives the expected denial.

Only after that identity proof should the approved EchoMedia SharePoint `Sites.Selected` scope and #390 live source-to-proof qualification be enabled. The 72-hour soak clock begins only after the first retained #390 source-to-proof probe succeeds.
