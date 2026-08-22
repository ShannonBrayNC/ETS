# ETS Fleet C3D Live Private Substrate

Status: implementation/qualification for #528 under FLEET-C3 parent #521.

C3D exists because the post-#527 live preflight proved that `rg-ets-live-eastus` contained no Fleet Container App and no qualifying private Fleet PostgreSQL server. C3C cannot qualify an edge route or Entra session boundary until that private substrate exists.

## Boundary

C3D deploys only the private production substrate. It does **not** activate Azure Front Door for Fleet, create `fleet.lanternprotocol.net`, modify the Lantern apex or `www`, claim physical-device attestation, or claim device health/trust/evidence verification.

The protected workflow accepts only an exact approved source SHA and an immutable Fleet Q0 image in the established private repository:

```text
etsq1a352eb89.azurecr.io/ets/fleet/control-plane@sha256:<digest>
```

Mutable tags are not deployment authority.

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

The protected deployment workflow resolves exactly one application named `ETS Fleet Control Plane`. If absent and provisioning is explicitly enabled, it creates a single-tenant (`AzureADMyOrg`) registration, enables ID-token issuance, creates its service principal, and declares exactly these user app roles:

- `Fleet.Viewer`
- `Fleet.Operator`
- `Fleet.SecurityAdmin`

C3D creates no EasyAuth client secret. C3C remains responsible for the Azure-side EasyAuth credential, redirect URI, operator-group admission, authentication configuration, and live positive/negative browser controls.

The Fleet BFF exact audience is the governed Entra application client ID. The issuer is the tenant-specific v2 issuer.

## Deployment sequence

1. validate exact source SHA and canonical Fleet Q0 digest;
2. verify Azure subscription/tenant and private ACR posture;
3. create or verify the governed single-tenant Fleet Entra application and exact app roles;
4. deploy `ets-fleet-c3d-live.bicep`, which composes C3B plus the migration UAMI and private manual migration job;
5. run the migration job inside the Fleet managed environment;
6. create/verify the runtime PostgreSQL Entra role by object ID;
7. apply Fleet schema and authorization migrations;
8. grant runtime data-plane privileges and prove the runtime identity can read the expected schema;
9. set the fail-closed runtime bridge contract (`container-apps-easyauth`) and configured step-up authentication-context ID without enabling the public EasyAuth edge yet;
10. run a separate private-network readiness job from the same managed environment;
11. verify the managed environment is internal/public-disabled, PostgreSQL is Entra-only/public-disabled, the Fleet image is the exact immutable digest, and the app has at least two replicas;
12. attempt a bounded PostgreSQL TCP connection from the public GitHub runner and require denial;
13. retain a sanitized C3C handoff artifact.

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

A successful C3D evidence package supplies C3C with the exact source/image and sanitized live resource identities needed for `compose-edge`, including the Fleet Container App, internal managed environment, PostgreSQL server, runtime identity, and Entra application client ID.

C3C still must independently provision and qualify:

- EasyAuth client credential and callback configuration;
- operator-group admission and app-role assignments;
- Front Door Premium + WAF + Private Link;
- authenticated Viewer/Operator/SecurityAdmin controls;
- CSRF, step-up, IDOR, revocation, and role-change negatives;
- cross-replica idempotent replay and restart retention;
- backup/restore recovery evidence;
- custom-domain ownership, TLS, and routed controls before `fleet.lanternprotocol.net` may be called qualified.
