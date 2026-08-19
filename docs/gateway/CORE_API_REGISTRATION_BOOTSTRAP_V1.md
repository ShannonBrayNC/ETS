# Core API registration bootstrap v1

## Purpose

The hosted ETS Core must exist as a Microsoft Entra resource application before the live Gateway
managed identity can request an app-only token for Core.

This gate creates or validates only the Core API application registration and its backing service
principal. It does not grant Gateway producer authority, configure an ETS tenant/workspace scope,
deploy Core or Gateway, grant Microsoft 365 access, complete #390, or start the soak clock.

The runtime release identity remains the corrected Q0 image from #389:

- source: `332d7db3a69acd826a2a000264e81a179894e278`
- digest: `sha256:c83a8cb0729d7e00506e4b7b9f0d0e5a7c5bbe3829abad76113ba7fd1ee3424c`

## Identity model

The Core resource application is intentionally minimal:

- display name: `ETS Core Live API`
- tenant audience: `AzureADMyOrg`
- App ID URI: `api://<core-app-id>`
- Gateway token scope: `api://<core-app-id>/.default`
- access token version: `2`
- delegated OAuth scopes: none
- pre-authorized delegated clients: none
- application password credentials: none
- application key credentials: none

The `.default` scope is required by the existing Gateway managed-identity token provider. The Core
application's App ID URI becomes the expected JWT audience. The tenant-specific issuer and JWKS URL
are derived from the authenticated Microsoft Entra tenant after the application is resolved.

## Operator boundary

This remains an explicit Microsoft Graph operator action. The GitHub Azure deployment identity does
not receive directory-administration permissions merely to create an app registration.

Required local/operator tools:

- Azure CLI authenticated to the intended Azure subscription;
- Microsoft Graph PowerShell authentication commands;
- delegated Graph authority appropriate to the selected mode.

Dry-run requests `Application.Read.All`. Apply requests `Application.ReadWrite.All` because the
operator may create/update the application and create its service principal.

The script also verifies that:

1. the active Azure tenant equals the Graph tenant;
2. the tenant contains the expected verified domain, defaulting to `echomedia.ai`;
3. at most one application uses the governed display name;
4. an existing application carries the governed ETS ownership tags before it can be adopted;
5. an existing App ID URI is either absent or exactly `api://<appId>`;
6. the application does not retain credentials or delegated API exposure;
7. exactly one application service principal exists after apply.

## Step 1 — validate registration state

Run without `-Apply` first:

```powershell
./scripts/azure/ensure-core-api-application.ps1
```

If no governed Core application exists, the script returns `mutationRequired: true` without
creating anything.

If a governed application exists but still needs its App ID URI, v2 access-token setting, or
backing service principal, dry-run also reports that a mutation remains required.

## Step 2 — create or converge the Core resource application

After reviewing the authenticated tenant:

```powershell
./scripts/azure/ensure-core-api-application.ps1 -Apply
```

A successful apply returns the protected operator values required by later gates:

- Core application/client ID;
- Core application object ID;
- Core service-principal object ID;
- Core identifier URI;
- Core managed-identity scope `api://<core-app-id>/.default`;
- expected JWT audience;
- tenant-specific issuer;
- tenant-specific JWKS endpoint.

Do not put the Core application ID or Gateway client ID in public release evidence. Keep the exact
identity values in the protected operator/deployment workspace and publish only bounded readiness
claims.

## Step 3 — establish Core producer authority

Registration alone does not grant evidence creation.

Use the already-governed #414 role bootstrap with the exact Core application ID:

```powershell
./scripts/azure/ensure-core-evidence-producer-app-role.ps1 `
  -CoreApplicationId '<core-app-id>'
```

Review the dry-run result, then apply if required:

```powershell
./scripts/azure/ensure-core-evidence-producer-app-role.ps1 `
  -CoreApplicationId '<core-app-id>' `
  -Apply
```

This establishes the stable `evidence_producer` application role. It still does not authorize any
Gateway principal until an exact assignment exists.

## Step 4 — bind the exact live Gateway UAMI

After #415 has successfully created the persistent Gateway managed identity, validate the role
assignment using the exact Azure resource group and managed-identity name:

```powershell
./scripts/azure/provision-gateway-core-evidence-producer.ps1 `
  -ResourceGroup 'rg-ets-live-eastus' `
  -ManagedIdentityName '<gateway-uami-name>' `
  -CoreApplicationId '<core-app-id>'
```

Apply only after the exact Core application and Gateway managed identity are confirmed:

```powershell
./scripts/azure/provision-gateway-core-evidence-producer.ps1 `
  -ResourceGroup 'rg-ets-live-eastus' `
  -ManagedIdentityName '<gateway-uami-name>' `
  -CoreApplicationId '<core-app-id>' `
  -Apply
```

## Step 5 — construct the server-owned Core scope map

The permission and scope controls remain independent:

- `evidence_producer` answers **what the Gateway may do**;
- `ETS_AUTH_APP_SCOPE_MAP_JSON` answers **where the Gateway may act**.

The later protected deployment must re-read the exact Gateway client ID from Azure and construct
Core's server-owned app-to-ETS-scope mapping from that identity. Neither identity value should be
accepted from a public workflow input.

## Deployment gate

Only after registration, producer-role creation, exact Gateway role assignment, and exact-client-ID
scope mapping are ready may the protected runtime deployment proceed.

That deployment must use the authoritative immutable Q0 image and prove both controls:

1. a Gateway managed-identity token for `api://<core-app-id>/.default` contains
   `roles: ["evidence_producer"]` and succeeds on evidence ingestion; and
2. an authenticated control principal without `evidence.create` is denied ingestion.

This bootstrap does not deploy Core or Gateway and does not claim Microsoft 365 source-to-proof
success. The 72-hour soak clock remains stopped until #390 succeeds and the first retained live
source-to-proof probe completes successfully.
