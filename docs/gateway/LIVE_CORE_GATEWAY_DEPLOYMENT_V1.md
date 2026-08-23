# Live Core + Gateway deployment v1

## Purpose

This gate deploys the persistent hosted ETS Core and Microsoft Gateway into the already-qualified live Azure resource group after the operator-governed Entra identity binding is complete.

It does not create or modify Entra application registrations, grant application roles, grant SharePoint access, prove a live Gateway producer token, complete #390, or start the 72-hour soak clock.

The deployment-authoritative release identity is supplied only through protected manual inputs and
must be backed by one successful `hosted-azure-q0-image.yml` run on the same exact `main` SHA. The
deployment workflow downloads that run's retained manifest and vulnerability gate before Azure
mutation. It rejects a moved `main`, a mutable/tag-only image, a different repository, a failed or
non-manual Q0 run, ambiguous evidence, or any fixable HIGH/CRITICAL finding.

## Preconditions

The following gates must be complete before dispatch:

1. the protected manual identity bootstrap has created the distinct SharePoint/Core, directory,
   and Purview UAMIs in `rg-ets-live-eastus`;
2. the governed ETS Core API registration exists in the target Microsoft tenant;
3. the stable Core `evidence_producer` application role exists;
4. that exact live Gateway UAMI is assigned the Core `evidence_producer` role;
5. the operator has selected explicit ETS tenant and workspace identifiers;
6. the exact Gateway client ID is the only key in the Core app-to-ETS-scope map;
7. the directory identity has only `User.Read.All` and `Group.Read.All`, and the Purview identity
   has only `ActivityFeed.Read`, after preview-first operator review;
8. one successful Q0 run has retained the exact source, digest, SBOM, provenance, and passing
   vulnerability evidence; and
9. the protected deployment environment contains the exact authentication and connector values
   described below.

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

Run `.github/workflows/live-core-gateway-deployment.yml` from `main` with:

- `image_source_sha`: the exact current `main` SHA used by the approved Q0 publication;
- `container_image`: `etsq1a352eb89.azurecr.io/ets/hosted-q1@sha256:<digest>` from that run; and
- `q0_workflow_run_id`: the successful `hosted-azure-q0-image.yml` run ID.

The workflow is manual-only. Before creating runtime resources it:

1. authenticates to Azure using workload identity federation;
2. requires the active tenant and subscription to match the protected environment;
3. requires the existing live resource group to remain in `eastus` with the governed ownership tags;
4. requires the dispatch SHA to equal both current `main` and `image_source_sha`;
5. verifies the exact successful Q0 run and retained Q0 manifest/vulnerability gate;
6. re-reads the three deterministic runtime identities from Azure and requires distinct client and
   principal IDs;
7. requires the Core auth tenant and Microsoft connector tenant to equal the protected Azure tenant;
8. requires the Core scope to equal `<audience>/.default`;
9. requires the issuer and JWKS URL to be the exact tenant-specific v2 endpoints;
10. parses `ETS_LIVE_AUTH_APP_SCOPE_MAP_JSON` and requires exactly one application/client key;
11. requires that key to equal the re-read live SharePoint/Core Gateway client ID; and
12. requires the scope-map tenant/workspace binding to equal the separately protected ETS tenant/workspace values.

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

After deployment it requires the SharePoint/Core, directory, and Purview Bicep output client IDs to
match the three pre-qualified Azure identities. A newly created or substituted runtime principal is
therefore rejected. The ACR pull identity remains a fourth distinct identity with lifecycle `None`;
the three runtime identities use lifecycle `Main`.

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
- Gateway uses the selected ETS tenant/workspace and exact Microsoft connector scope;
- Gateway exposes the exact separated directory and Purview client IDs;
- no Graph notification URL, clientState, lifecycle timing, or health-policy environment variable
  is present; and
- Graph callback ingress remains internal.

This proves configuration convergence, not live request success.

## Public evidence boundary

The successful workflow may publish only bounded release evidence such as:

- release source SHA and image digest;
- Q0 publication workflow run ID and successful evidence-verification result;
- Azure resource group;
- non-customer Core/Gateway resource names;
- non-customer SharePoint/Core, directory, and Purview managed-identity names;
- immutable image verified: true;
- internal ingress verified: true;
- single-replica configuration verified: true;
- separated Microsoft identities verified: true;
- Graph lifecycle configuration present: false;
- Graph callback ingress external: false;
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

## Next gates

After this deployment succeeds, run the protected RC1B and RC1C read-only preflights from the same
unchanged `main` SHA and immutable image. RC1B proves the dedicated directory identity, bounded
users/groups delta access, SharePoint negative control, and query-only durable state. RC1C proves
the dedicated Purview audience/role, read-only `Audit.General` subscription listing, query-only
runtime state, and the accepted Graph deferral boundary.

Neither preflight completes the full live slice. Tombstone/replay/throttle/recovery exercises,
Purview subscription mutation/recovery, candidate freeze, and the new 72-hour soak remain separate
governed gates.
