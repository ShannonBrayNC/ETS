# Live Core/Gateway identity orchestration v1

## Purpose

This operator gate composes the three governed identity steps required before the persistent hosted
ETS Core and Microsoft Gateway can be deployed:

1. create or validate the single-tenant `ETS Core Live API` Microsoft Entra application and backing
   service principal;
2. create or validate the Core `evidence_producer` application role; and
3. assign that exact role to the already-qualified persistent Gateway UAMI.

The persistent Gateway identity was qualified by the #415 Azure bootstrap as:

- resource group: `rg-ets-live-eastus`
- managed identity: `ets-o23bf2d6oq44s-gw-id`

This orchestration remains an explicit operator action. Merging the script does not mutate Microsoft
Entra and does not grant GitHub Actions directory-administration authority.

## ETS scope is explicit

The Core application-to-ETS-scope map answers **where** an authenticated application is authorized
to operate. The `evidence_producer` app role answers **what** the Gateway may do. They remain
independent controls.

The live ETS tenant and workspace are therefore mandatory operator inputs. The script does not
invent default tenant/workspace values.

## Prerequisites

Run from a trusted operator workstation with:

- Azure CLI authenticated to the subscription containing `rg-ets-live-eastus`;
- Microsoft Graph PowerShell available;
- delegated authority required by the three governed child scripts;
- the exact intended ETS tenant and workspace identifiers reviewed before `-Apply`.

The child scripts validate that Azure and Microsoft Graph resolve to the same tenant and that the
required verified domain is `echomedia.ai` by default.

## Dry run

Start without `-Apply`:

```powershell
./scripts/azure/provision-live-core-gateway-identity.ps1 `
  -EtsTenantId '<ets-tenant-id>' `
  -EtsWorkspaceId '<ets-workspace-id>'
```

The script stops at the first incomplete stage and reports one of:

- `core_api_registration`
- `core_evidence_producer_role`
- `gateway_evidence_producer_assignment`
- `ready_for_protected_deployment`

A dry run that reports `mutationRequired: true` performs no directory mutation.

## Apply

After reviewing the Azure tenant, Graph tenant, verified domain, live ETS tenant/workspace, resource
group, and Gateway identity, run:

```powershell
./scripts/azure/provision-live-core-gateway-identity.ps1 `
  -EtsTenantId '<ets-tenant-id>' `
  -EtsWorkspaceId '<ets-workspace-id>' `
  -Apply
```

A successful apply returns `stage: ready_for_protected_deployment` and the exact values required by
the later protected Azure deployment boundary:

- `coreApplicationId`
- `coreIdentifierUri`
- `coreScope` (`api://<core-app-id>/.default`)
- `authAudience`
- `authIssuer`
- `authJwksUrl`
- `authTenantId`
- `gatewayManagedIdentityClientId`
- `authAppScopeMapJson`

The scope-map JSON is built from the **exact client ID re-read by the Gateway role-assignment
script** and the explicitly supplied ETS tenant/workspace. Its shape is compatible with
`ETS_AUTH_APP_SCOPE_MAP_JSON`:

```json
{
  "<gateway-client-id>": {
    "tenant_id": "<ets-tenant-id>",
    "workspace_id": "<ets-workspace-id>"
  }
}
```

## Evidence handling

The output contains no password, client secret, application key, or reusable credential. It does,
however, contain the exact Gateway client ID and app-scope mapping and is intentionally marked
`publicEvidenceSafe: false`.

Keep the full output in the protected operator/deployment workspace. Public release evidence should
retain only bounded facts such as identity/role/scope-map readiness, never the complete operator
handoff unless explicitly approved.

## Next release gate

Do not claim hosted runtime deployment merely because this identity orchestration succeeds.

After `ready_for_protected_deployment`:

1. place the exact Core auth values and ETS scope values into the protected deployment boundary;
2. have deployment re-read the same Gateway UAMI and require its client ID to match the scope-map
   key;
3. deploy Core and Gateway from the same authoritative immutable image
   `sha256:c83a8cb0729d7e00506e4b7b9f0d0e5a7c5bbe3829abad76113ba7fd1ee3424c`;
4. prove a Gateway token carrying `evidence_producer` can ingest evidence;
5. prove a valid authenticated control principal without `evidence.create` is denied;
6. provision the approved EchoMedia `Sites.Selected` SharePoint scope and qualify #390; and
7. start the governed 72-hour soak only after the first retained live source-to-proof probe succeeds.
