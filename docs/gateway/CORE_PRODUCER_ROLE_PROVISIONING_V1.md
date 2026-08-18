# Core producer app-role provisioning v1

## Purpose

The hosted Microsoft Gateway must be authorized in two independent dimensions before it can
relay evidence into ETS Core:

1. **scope** — Core maps the exact Gateway application/client ID to the deployment-authoritative
   ETS tenant and workspace through `ETS_AUTH_APP_SCOPE_MAP_JSON`; and
2. **permission** — the exact Gateway managed-identity service principal holds the Core
   application's `evidence_producer` app role, which maps to `evidence.create`.

Neither control substitutes for the other. A valid tenant/workspace mapping does not grant
producer authority, and an app-role assignment does not select an ETS tenant/workspace.

The corrected live image currently authorized for the next deployment gate is the immutable Q0
handoff recorded on #389 for source
`332d7db3a69acd826a2a000264e81a179894e278`. The identity gate does not itself deploy that image.

## Governed role identity

The Core application role is intentionally stable across environments:

- value: `evidence_producer`
- id: `062e20df-6571-4fa3-ab90-e1f30cd360bd`
- allowed member type: `Application`
- enabled: `true`

A tenant that already exposes `evidence_producer` under a different role ID is treated as a
migration case and fails closed. The provisioning scripts do not silently replace or normalize
an existing role ID.

## Operator boundary

Directory mutation remains an explicit operator action. GitHub Actions deployment identities are
not granted broad Microsoft Graph directory administration merely to bootstrap this relationship.

Required local/operator tools:

- Azure CLI authenticated to the deployment subscription;
- Microsoft Graph PowerShell authentication commands;
- delegated authority sufficient for the specific step.

The scripts verify that the active Azure tenant and Graph tenant are the same and that the tenant
contains the expected verified domain, which defaults to `echomedia.ai`.

Do not upload raw operator output to public release evidence. The deployment gate should retain
only the bounded non-secret facts needed to prove the binding.

## Step 1 — pre-create the Gateway identity

The Gateway identity must exist before Core is deployed so its exact client ID can be placed into
Core's server-owned app-to-ETS-scope map.

Use `infra/azure/ets-gateway-identity.bicep` with the deployment-authoritative environment and
connector instance. Record the resulting managed identity name and client ID in the protected
operator workspace, not in public workflow inputs.

## Step 2 — validate or create the Core application role

First run without `-Apply`:

```powershell
./scripts/azure/ensure-core-evidence-producer-app-role.ps1 `
  -CoreApplicationId '<core-app-client-id>'
```

If `roleReady` is `false` and `mutationRequired` is `true`, review the target tenant and Core
application before applying:

```powershell
./scripts/azure/ensure-core-evidence-producer-app-role.ps1 `
  -CoreApplicationId '<core-app-client-id>' `
  -Apply
```

The apply path preserves existing Core app roles, creates only the governed producer role when it
is absent, then re-reads the application and requires the role to converge exactly.

## Step 3 — validate or assign the Gateway role

First run without `-Apply`:

```powershell
./scripts/azure/provision-gateway-core-evidence-producer.ps1 `
  -ResourceGroup '<gateway-resource-group>' `
  -ManagedIdentityName '<gateway-uami-name>' `
  -CoreApplicationId '<core-app-client-id>'
```

If `assignmentReady` is `false` and `mutationRequired` is `true`, review the exact Gateway client
ID and Core application ID before applying:

```powershell
./scripts/azure/provision-gateway-core-evidence-producer.ps1 `
  -ResourceGroup '<gateway-resource-group>' `
  -ManagedIdentityName '<gateway-uami-name>' `
  -CoreApplicationId '<core-app-client-id>' `
  -Apply
```

The assignment script requires all of the following:

- the Azure UAMI returns a client ID, principal ID, and resource ID;
- the UAMI service-principal object ID equals Azure's `principalId`;
- the Core service principal resolves uniquely by exact application/client ID;
- the Core service principal exposes exactly one enabled `evidence_producer` application role with
  the governed role ID;
- the Gateway has no unexpected app-role assignment to the Core service principal;
- the producer assignment converges to exactly one grant.

## Deployment release gate

Do not deploy the hosted Core/Gateway pair until the operator has established both the Core role
and the Gateway assignment.

The subsequent deployment must then prove:

1. Core and Gateway use the same corrected immutable image digest from the authoritative Q0
   handoff;
2. Core's server-owned app scope map contains the exact Gateway client ID and intended ETS
   tenant/workspace;
3. a Gateway app-only token for the Core resource contains `roles: ["evidence_producer"]` and is
   accepted for evidence ingestion;
4. a valid authenticated principal without `evidence.create` is denied ingestion;
5. no SharePoint or Graph source-to-proof claim is made until the separate #390 gate succeeds.

The 72-hour soak clock remains stopped until #390 completes and the first retained live
source-to-proof probe succeeds.
