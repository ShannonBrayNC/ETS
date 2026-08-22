# ETS Fleet C3B Production Control-Plane Boundary

Status: implementation/qualification for #524. C3B does **not** activate `fleet.lanternprotocol.net` and does not claim C3C live Entra/Azure qualification.

## Purpose

C3B replaces process-local Fleet control-plane state with a shared transactional production boundary while preserving the C1/C2/C3A trust model. The authoritative lifecycle remains `DeviceEnrollmentService`; PostgreSQL supplies persistence and cross-replica serialization rather than a second state machine.

The C3B path is:

1. private Azure Container Apps Fleet BFF, minimum two replicas;
2. Microsoft Entra-only Azure Database for PostgreSQL Flexible Server;
3. managed-identity PostgreSQL token acquisition with TLS verification;
4. shared enrollment, current-pointer, identity-owner, rotation, mutation-journal, evidence, scope, and session-standing state;
5. server-owned Entra-to-ETS scope mapping and current session standing;
6. bounded readiness that states only process/auth-configuration/store readiness.

## Persistence and concurrency

`PostgresEnrollmentStore` implements the same provider-neutral `EnrollmentStore` contract used by the in-memory C1/C2 composition. A complete enrollment lifecycle or authorization operation runs inside one `SERIALIZABLE` transaction. PostgreSQL serialization failures, deadlocks, and uniqueness races are converted to the provider-neutral `EnrollmentStoreConflict`; the BFF returns the bounded `ETS_FLEET_CONCURRENT_UPDATE` conflict rather than overwriting stale state.

The shared schema retains:

- canonical enrollment JSON plus normalized lookup columns and a monotonically increasing `record_version`;
- current device-to-enrollment pointers with `pointer_version`;
- unique public-identity ownership;
- credential-rotation windows with `rotation_version`;
- C3A administrative mutation reservations and committed results;
- C3A administrative evidence;
- server-owned Entra subject-to-ETS scope mappings;
- server-owned role/revocation/session-generation standing.

Raw idempotency keys remain prohibited. Browser session identifiers are also retained only as SHA-256 values. Access tokens, refresh tokens, browser cookies, CSRF tokens, database passwords, device private keys, Core credentials, Gateway credentials, and IoT Hub/DPS management credentials are not part of this datastore.

## C3A mutation semantics on PostgreSQL

The PostgreSQL mutation journal preserves C3A reservation-before-mutation semantics:

- the `(actor subject, idempotency-key hash)` slot is reserved first;
- a conflicting request fingerprint fails closed;
- a retained `pending` mutation never automatically repeats a possibly-applied trust mutation and returns reconciliation-required;
- a committed replay returns the retained result without re-running the lifecycle side effect;
- result plus administrative evidence are committed atomically;
- malformed retained state fails validation.

## Production Entra/session boundary

`ProductionFleetSessionAdapter` accepts only a typed `TrustedEntraIdentityContext` created by a trusted authentication/hosting layer. It does not derive authority from browser-supplied tenant, workspace, role, step-up, or scope headers.

For every request, Fleet rechecks the security properties it depends on:

- exact issuer;
- exact audience;
- exact Entra tenant;
- expiration and authentication time;
- stable `oid` or `sub` subject;
- only `Fleet.Viewer`, `Fleet.Operator`, and `Fleet.SecurityAdmin` roles;
- current server-side session generation and active/revoked standing;
- current server-side role set;
- authorization `not_before` epoch;
- server-owned ETS tenant/workspace scope;
- server-owned step-up epoch before elevated SecurityAdmin operations.

The production cookie contract is `__Host-` prefixed, Secure, HttpOnly, `Path=/`, no Domain, and SameSite Strict/Lax. C3B defines and tests this contract; C3C is responsible for binding and live-qualifying the protected browser/Entra hosting bridge.

Until that trusted bridge is installed, the dedicated C3B runtime intentionally returns 401 on authenticated portal routes. This is a fail-closed deployment state, not an authentication bypass.

## Azure composition

`infra/azure/ets-fleet-c3b.bicep` creates the production-composable private boundary:

- an internal Azure Container Apps managed environment with `publicNetworkAccess: Disabled`;
- a dedicated non-root Fleet BFF image;
- minimum two and maximum six application replicas;
- one user-assigned managed identity for runtime ACR pull and PostgreSQL token acquisition;
- Azure Database for PostgreSQL Flexible Server with Microsoft Entra authentication enabled and password authentication disabled;
- PostgreSQL public network access disabled;
- a PostgreSQL Private Endpoint using group `postgresqlServer`;
- `privatelink.postgres.database.azure.com` private DNS linked to the Fleet VNet;
- no Azure Front Door profile, route, custom domain, or `fleet.lanternprotocol.net` activation;
- no new public Core, Gateway, IoT Hub, or DPS management endpoint.

The Bicep output explicitly reports the public-hostname/Core/Gateway/IoT activation flags as false. Those outputs are boundary assertions, not runtime health claims.

## PostgreSQL Entra bootstrap

The runtime managed identity must be created as a **non-admin** PostgreSQL Microsoft Entra principal. Run the principal creation from the `postgres` database while authenticated as an approved PostgreSQL Microsoft Entra administrator. Prefer the object-ID-bound form so name collisions cannot select a different Entra object:

```sql
SELECT *
FROM pg_catalog.pgaadauth_create_principal_with_oid(
  '<fleet-runtime-role>',
  '<fleet-runtime-managed-identity-object-id>',
  'service',
  false,
  false
);
```

After the Fleet database/schema has been migrated by an authorized migration identity, grant only the runtime data-plane privileges required by Fleet:

```sql
GRANT CONNECT ON DATABASE fleet TO "<fleet-runtime-role>";
GRANT USAGE ON SCHEMA public TO "<fleet-runtime-role>";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "<fleet-runtime-role>";
```

Do **not** grant `azure_pg_admin`, `CREATEDB`, `CREATEROLE`, superuser-equivalent permissions, or schema DDL to the Fleet runtime identity.

## Controlled migration

Schema creation is intentionally not performed by the application runtime identity. From a private-network execution environment, authenticate with an authorized Microsoft Entra migration/admin identity and set:

```text
ETS_FLEET_POSTGRES_HOST=<server>.postgres.database.azure.com
ETS_FLEET_POSTGRES_DATABASE=fleet
ETS_FLEET_POSTGRES_MIGRATION_USER=<entra-migration-role>
```

Then run:

```bash
python -m ets.fleet.migrate
```

The migration entrypoint uses Microsoft Entra token acquisition and TLS `verify-full`; it has no database-password fallback. Migrations are repeatable and the runtime fails startup if the expected schema is not ready.

## Backup, restore, retention, and recovery

The Azure template enables PostgreSQL managed backups with a 14-day retention window. Before C3C activation, qualification must prove the operational recovery procedure on a non-production database:

1. capture the source server/database identity and backup timestamp;
2. restore to an isolated replacement server or point-in-time target;
3. keep restored public network access disabled and private DNS isolated from production;
4. run schema/readiness checks;
5. verify current enrollment pointers, rotation windows, pending/committed mutation state, administrative evidence, scope mappings, and session standing;
6. verify a committed idempotency replay remains idempotent after restore;
7. verify pending mutations remain reconciliation-required;
8. destroy the recovery target after evidence capture.

A restore must never be treated as proof that device health, presence, or historical evidence validity is current. Recovery verifies retained control-plane state only.

## Readiness semantics

`/fleet/readyz` exposes only:

- `process_ready`;
- `auth_config_ready`;
- `store_ready`;
- aggregate `ready`.

It always reports `evidence_verified: false` and `health_asserted: false`. A healthy process/database is not evidence that a device is healthy, online, trusted, or producing valid ETS proofs.

## C3C handoff

C3B stops before public activation. #525/C3C must separately prove at least:

- protected live Entra login and typed trusted-context bridge;
- wrong issuer, audience, tenant, role, scope, stale generation, revoked standing, and stale step-up denial;
- two-replica shared-state behavior in Azure;
- durable restart/replay and reconciliation behavior;
- private PostgreSQL connectivity and denial of public database access;
- private Fleet origin reachability without exposing Core/Gateway/IoT management planes;
- backup/restore recovery evidence;
- Azure Front Door/private-origin integration if selected;
- TLS/custom-domain qualification for `fleet.lanternprotocol.net`;
- explicit activation gate after all prior evidence is green.

Only C3C may change the public-hostname boundary from false to true.
