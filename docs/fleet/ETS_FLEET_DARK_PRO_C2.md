# ETS Fleet Dark Pro C2 — Trust Mutation Security

Status: implementation candidate for FLEET-C2 / #519.

## Purpose

C2 adds bounded trust-changing operations to the Fleet Dark Pro backend-for-frontend while preserving the authoritative Fleet enrollment lifecycle implemented by `DeviceEnrollmentService`.

C2 does **not** create a second lifecycle state machine. It supplies the controls that a browser-facing administrative surface needs before it may invoke the existing authoritative transition functions.

## Security boundary

The browser is never authoritative for:

- tenant or workspace scope;
- Fleet roles or capabilities;
- step-up authentication state;
- device credentials;
- IoT Hub or DPS service credentials;
- Azure management tokens;
- Core or Gateway credentials;
- private signing keys.

The hosting composition resolves an authenticated `FleetPrincipal` and a server-owned `FleetSecuritySession`. The session contains the CSRF binding and the timestamp of the most recent successful step-up authentication. These objects are not deserialized from mutation JSON.

## Roles

C2 uses the C1 Entra application roles.

`Fleet.Viewer` remains read-only.

`Fleet.Operator` may:

- approve an already-submitted pending enrollment;
- restore a quarantined enrollment to enrolled state.

`Fleet.SecurityAdmin` may also:

- quarantine;
- revoke;
- decommission;
- begin credential rotation;
- complete credential rotation.

SecurityAdmin mutations require a fresh server-side step-up timestamp. The reference policy accepts step-up authentication no older than ten minutes and rejects future timestamps.

Role checks run on the server. UI visibility is not an authorization boundary.

## Object authorization and IDOR behavior

Every mutation resolves the current canonical ETS enrollment from the authoritative enrollment store and compares its `ScopeBinding` to the server-owned principal scope mappings.

Unknown devices and devices outside the operator's authorized scopes produce the same bounded not-found result. This prevents the mutation API from becoming a cross-tenant device enumeration oracle.

Rotation replacement enrollments must belong to the same canonical device. The underlying `DeviceEnrollmentService` additionally enforces device identity, scope, profile, trust class, auth method, key custody, supersession, and public-identity invariants.

## CSRF

Every mutation requires `X-CSRF-Token`. The supplied value is constant-time compared with the CSRF value retained in the authenticated server session.

A missing or incorrect token fails closed before a lifecycle mutation occurs.

The CSRF token is not written to administrative evidence or returned by the mutation result.

## Idempotency

Every mutation requires `Idempotency-Key`.

The key is scoped to the authenticated actor subject. C2 retains:

- a SHA-256 request fingerprint;
- the prior bounded mutation result.

An identical retry returns the retained result with `idempotent_replay=true` and does not emit a second administrative evidence record.

Reuse of the same actor/key pair for a different mutation fails with an idempotency conflict.

Administrative evidence stores only the SHA-256 hash of the idempotency key, never the raw key.

Object authorization and CSRF/role checks still run before an idempotent result can be returned.

## Destructive confirmation

SecurityAdmin/destructive operations require an explicit confirmation value bound to the exact action and canonical device identifier:

`<ACTION_NAME>:<device_id>`

Examples include `REVOKE:ets-edge:...` and `BEGIN_ROTATION:ets-edge:...`.

A confirmation for another device or action is rejected. Confirmation is a guard against operator error; it does not replace role, scope, step-up, or CSRF authorization.

## BFF endpoints

When the router is composed with both a `FleetPortalAdminService` and a `SecuritySessionResolver`, C2 adds:

- `POST /fleet/bff/v1/devices/{device_id}/actions/{action}`
- `GET /fleet/bff/v1/audit`

The mutation body is a strict extra-forbidden model containing only:

- optional destructive confirmation;
- optional replacement enrollment identifier;
- optional rotation overlap expiry.

Tenant, workspace, role, capability, subject, lifecycle state, and credential fields are not accepted in the body.

Mutation request bodies are capped at 4096 bytes. A server-side rate limiter hook is provided for the deployment composition.

C1 routes remain compatible when C2 services are not configured.

## Administrative evidence

Every accepted non-replay mutation emits `ets.fleet.admin.evidence.v1` through the provider-neutral `FleetAdministrativeEvidenceSink`.

The bounded record contains:

- generated evidence ID;
- administrative action;
- authenticated actor subject;
- canonical device ID;
- affected/current enrollment ID;
- authoritative tenant/workspace scope;
- resulting registration state;
- SHA-256 request fingerprint;
- SHA-256 idempotency-key digest;
- trusted server occurrence time.

It does not contain bearer tokens, session cookies, CSRF values, raw idempotency keys, private keys, passwords, SAS values, IoT Hub/DPS credentials, raw attestation material, or customer evidence payloads.

The C2 in-memory sink is a deterministic reference implementation. Production should bind the same evidence port to the durable ETS administrative evidence path and preserve equivalent append/idempotency guarantees.

## Audit export

`GET /fleet/bff/v1/audit` returns only administrative evidence records whose authoritative `ScopeBinding` is visible to the authenticated principal. The export is bounded and contains only the sanitized evidence schema above.

This is an administrative audit view, not raw customer evidence export.

## Lifecycle delegation

C2 delegates accepted mutations to the existing `DeviceEnrollmentService` methods:

- `activate()`;
- `transition()`;
- `begin_rotation()`;
- `complete_rotation()`.

Invalid lifecycle transitions therefore remain fail-closed under the A1 lifecycle rules. C2 does not replicate `_ALLOWED_TRANSITIONS`.

## Error semantics

Browser responses use bounded error codes. Internal validator messages, identity-validation details, credentials, and secret-bearing values are not returned.

Representative codes include:

- `ETS_FLEET_AUTHENTICATION_REQUIRED`;
- `ETS_FLEET_SESSION_REQUIRED`;
- `ETS_FLEET_DEVICE_NOT_FOUND`;
- `ETS_FLEET_MUTATION_FORBIDDEN`;
- `ETS_FLEET_STEP_UP_REQUIRED`;
- `ETS_FLEET_CONFIRMATION_REQUIRED`;
- `ETS_FLEET_IDEMPOTENCY_CONFLICT`;
- `ETS_FLEET_LIFECYCLE_CONFLICT`;
- `ETS_FLEET_MUTATION_RATE_LIMITED`.

C1 security headers and `Cache-Control: no-store` remain applied.

## Qualification

The C2 test suite covers:

- Viewer mutation denial;
- Operator approval authorization;
- SecurityAdmin step-up freshness;
- destructive confirmation;
- CSRF failure;
- server-owned object scope and cross-tenant denial;
- identical idempotent replay;
- conflicting key reuse;
- credential-rotation replay after the current enrollment changes;
- sanitized hashed administrative evidence;
- scope-filtered audit export;
- mass-assignment rejection;
- missing CSRF/idempotency headers;
- server-side mutation rate limiting;
- architecture guards against Azure product-plane and reusable-secret coupling.

## Deployment boundary

C2 is a software/control-plane qualification. It does not by itself prove that `fleet.lanternprotocol.net`, Entra Conditional Access/PIM, the durable production evidence sink, or any live Azure fleet deployment is operational.

A production deployment must separately qualify:

1. Entra token/session validation and application-role assignment;
2. server-owned ETS tenant/workspace mappings;
3. Conditional Access/PIM or equivalent step-up policy for SecurityAdmin;
4. durable shared mutation-idempotency state for multi-replica operation;
5. durable ETS administrative evidence retention;
6. public-edge/WAF/rate-limit configuration;
7. live operator actions against a bounded synthetic or approved physical device and retained evidence.
