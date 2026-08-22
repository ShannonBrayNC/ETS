# ETS Fleet C3D Live Private Substrate

Status: implementation/qualification for #528 under FLEET-C3 parent #521.

C3D exists because the post-#527 live preflight proved that the live subscription contained no Fleet Container App and no qualifying private Fleet PostgreSQL server. The first PostgreSQL deployment attempts then proved that the subscription is restricted from Flexible Server provisioning in East US. The approved private Fleet boundary is therefore `rg-ets-live-eastus2` in East US 2. C3C cannot qualify an edge route or Entra session boundary until that private substrate exists.

## Boundary

C3D deploys only the private production substrate. It does **not** activate Azure Front Door for Fleet, create `fleet.lanternprotocol.net`, modify the Lantern apex or `www`, claim physical-device attestation, or claim device health/trust/evidence verification.

The protected workflow accepts only an exact approved source SHA and an immutable Fleet Q0 image in the established private repository:

```text
etsq1a352eb89.azurecr.io/ets/fleet/control-plane@sha256:<digest>
```

Mutable tags are not deployment authority. The workflow also requires the exact successful Fleet Q0 workflow-run ID and downloads its retained manifest **before any Azure mutation**. The manifest source SHA must equal the checked-out deployment SHA, its immutable image must equal the requested deployment image, and its vulnerability/credential-retention gates must pass. A Q0 image built from an earlier source revision is not valid for a later C3D deployment even if the repository name and digest are otherwise well formed.

This means a new Fleet Q0 must be published after any merged change to the C3D runtime/bootstrap code that the live image must execute.

## Regional capability boundary

The protected C3D workflow pins the production boundary to:

- resource group `rg-ets-live-eastus2` located in `eastus2`;
- PostgreSQL 17, matching the version exercised by the protected C3B integration workflow;
- General Purpose SKU `Standard_D2ds_v5`;
- `ZoneRedundant` high availability.

Before deployment, the workflow calls the subscription-scoped `Microsoft.DBforPostgreSQL` location-capabilities API. It fails before substrate mutation unless East US 2 is unrestricted, PostgreSQL 17 is available, the target SKU admits ZoneRedundant HA, the location reports ZoneRedundant HA enabled, and the SKU exposes at least two zones. A sanitized capability artifact retains only the exact source, workflow run, location, version, SKU, HA mode, restriction result, and supported zones.

The resource group is deliberately separate from `rg-ets-live-eastus`; the latter contains other live ETS resources and its East US location is not a valid PostgreSQL provisioning boundary for this subscription. Create the approved group once before the first corrected C3D dispatch:

```powershell
az group create --name rg-ets-live-eastus2 --location eastus2
```

## Identity separation

C3D uses two user-assigned managed identities:

- **Fleet runtime identity** — the identity already composed by C3B for ACR pull and PostgreSQL data-plane access. It becomes a non-admin PostgreSQL Microsoft Entra principal.
- **Fleet migration identity** — a dedicated identity used by the private manual migration job and registered as the PostgreSQL Microsoft Entra administrator for controlled schema/bootstrap work.

The migration job runs inside the same internal Container Apps managed environment as Fleet. Both database identities acquire short-lived Microsoft Entra tokens; no PostgreSQL password or connection-string fallback exists.

The runtime principal is created or verified using its immutable Entra object ID through `pgaadauth_create_principal_with_oid(..., 'service', false, false)`. Bootstrap then checks `pgaadauth_list_principals(false)` and PostgreSQL role attributes before granting any data-plane access. A runtime role that is mapped to a different object ID, is not a service principal, belongs to `azure_pg_admin`, or has `CREATEROLE`, `CREATEDB`, or superuser standing fails closed.

Runtime grants are bounded to:

- `CONNECT` on the Fleet database;
- `USAGE` on schema `public`;
- `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on Fleet tables;
- the corresponding default table privileges for future controlled migrations.

The runtime identity receives no schema DDL or PostgreSQL administration rights.

## Governed Fleet Entra application

Microsoft Entra application administration is deliberately outside the C3D GitHub deployment identity. The first live C3D attempt proved that the Azure deployment identity did not have Microsoft Graph application-management privileges and failed before any substrate deployment. C3E preserves that least-privilege result rather than broadening CI authority.

An authorized operator separately runs `scripts/azure/ensure-fleet-entra-application.ps1` as documented in `ETS_FLEET_C3E_ENTRA_BOOTSTRAP.md`. That delegated bootstrap creates or verifies the single-tenant `ETS Fleet Control Plane` application, its service principal, ID-token issuance, and exact user app roles:

- `Fleet.Viewer`
- `Fleet.Operator`
- `Fleet.SecurityAdmin`

The protected C3D workflow then accepts only the resulting pinned `entra_client_id`. It contains no `az ad app`, `az ad sp`, Microsoft Graph application mutation, or Graph write permission path.

C3D creates no EasyAuth client secret. C3C remains responsible for the Azure-side EasyAuth credential, redirect URI, operator-group admission, authentication configuration, and live positive/negative browser controls.

The Fleet BFF exact audience is the pinned Entra application client ID. The issuer is the tenant-specific v2 issuer.

## Deployment sequence

1. complete the separate delegated C3E Entra bootstrap and retain its sanitized `fleetClientId` output;
2. validate the exact source SHA, Q0 workflow-run identity, retained Q0 manifest, canonical immutable Fleet image, and GUID-form pinned `entra_client_id`;
3. require the Q0 manifest source SHA and immutable image to match the deployment inputs before Azure login/mutation;
4. verify Azure subscription/tenant, the exact East US 2 resource-group boundary, and private ACR posture;
5. require subscription-qualified East US 2 support for PostgreSQL 17, `Standard_D2ds_v5`, and ZoneRedundant HA before deployment;
6. deploy `ets-fleet-c3d-live.bicep`, which composes C3B plus the migration UAMI and private manual migration job using the pinned Fleet client ID as the BFF audience;
7. run the migration job inside the Fleet managed environment;
8. create/verify the runtime PostgreSQL Entra role by object ID;
9. apply Fleet schema and authorization migrations;
10. grant runtime data-plane privileges and prove the runtime identity can read the expected schema;
11. set the fail-closed runtime bridge contract (`container-apps-easyauth`) and configured step-up authentication-context ID without enabling the public EasyAuth edge yet;
12. run a separate private-network readiness job from the same managed environment;
13. verify every private resource remains in East US 2, the managed environment is internal/public-disabled, PostgreSQL is Entra-only/public-disabled and matches the capability-qualified version/SKU/HA mode, the Fleet image is the exact immutable digest, and the app has at least two replicas;
14. attempt a bounded PostgreSQL TCP connection from the public GitHub runner and require denial;
15. retain a sanitized C3C handoff artifact that includes the exact Q0 workflow-run ID, pinned Entra client ID, region, PostgreSQL version/SKU/HA mode, and `github_graph_write_required=false`.

## Readiness semantics

The private readiness job accepts only:

- `ready=true`
- `process_ready=true`
- `auth_config_ready=true`
- `store_ready=true`
- `evidence_verified=false`
- `health_asserted=false`

This establishes process/auth-configuration/store readiness only. It says nothing about whether a device is present, healthy, trusted, attested, or producing verified ETS evidence.

## C3C handoff

A successful C3D evidence package supplies C3C with the exact source/image/Q0-run binding and sanitized live resource identities needed for `compose-edge`, including the Fleet Container App, internal managed environment, PostgreSQL server, runtime identity, and pinned Entra application client ID.

C3C still must independently provision and qualify:

- EasyAuth client credential and callback configuration;
- operator-group admission and app-role assignments;
- Front Door Premium + WAF + Private Link;
- authenticated Viewer/Operator/SecurityAdmin controls;
- CSRF, step-up, IDOR, revocation, and role-change negatives;
- cross-replica idempotent replay and restart retention;
- backup/restore recovery evidence;
- custom-domain ownership, TLS, and routed controls before `fleet.lanternprotocol.net` may be called qualified.
