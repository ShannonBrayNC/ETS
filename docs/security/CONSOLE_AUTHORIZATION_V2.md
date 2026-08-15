# ETS Console Authorization Contract v2

Status: P1.1 candidate  
Parent: #209  
Implements: #222

## Purpose

Define the server-derived identity, scope, role, and capability contract used by the production ETS
Console and Gateway management surface. Browser navigation state is never an authorization boundary.

## Roles

ETS v2 recognizes these bounded roles:

- `viewer`;
- `evidence_producer`;
- `operator`;
- `auditor`;
- `administrator`.

A production JWT/JWKS identity may carry one or more of these role identifiers in its signed `roles`
claim. Unknown roles fail authentication rather than being passed through.

## Capabilities

Roles map through the server-owned `ROLE_CAPABILITIES` table. The browser and bearer token do not
supply arbitrary capability identifiers. A token `capabilities` claim, if present, is ignored by the
ETS authorization model.

The v2 capability vocabulary is:

- `evidence.read`;
- `evidence.create`;
- `evidence.verify`;
- `evidence.export`;
- `connector.read`;
- `connector.manage`;
- `audit.read`;
- `admin.read`;
- `admin.manage`.

The role-to-capability mapping can evolve only through reviewed server code. A role name therefore
remains a policy input; the derived capability set is the stable contract consumed by UI components
and server authorization checks.

## Scope

For production JWT/JWKS modes, subject, tenant, and workspace come from validated signed claims.
Supplying a conflicting `X-ETS-Tenant` or `X-ETS-Workspace` header to the Gateway management host
fails closed. Editing browser state therefore cannot widen the authenticated management scope.

For local development profiles, scope may be supplied through the existing local headers. The v2
authorization response always marks that mode as `local_nonproduction` so the Console can render an
unambiguous development warning.

## Local development

`LocalHeaderAuthPolicy` and `LocalAPIKeyAuthPolicy` receive administrator-equivalent capabilities to
keep appliance and developer workflows usable without a hosted identity provider. They do **not**
claim production authorization. The returned authorization profile is always
`local_nonproduction`.

## Gateway management host

`create_gateway_management_app()` composes:

- `/api/v2/auth/context` for the Console identity/capability contract;
- the versioned `/gateway/connectors/v1` G2C management router.

The outer host authenticates the request once and adapts it to `ConnectorManagementPrincipal` with
read and manage authority represented separately. `connector.manage` implies connector read access
inside the service, but `connector.read` never implies mutation authority.

The G2C service requires connector read authority for catalog, instance-list, instance-detail, and
runtime-state inspection. Create, update, enable/disable, validation, connection testing, checkpoint
changes, and gap-state changes continue to require `connector.manage`. Tenant/workspace equality is
enforced for both read and management access to instance-specific resources.

This composition keeps the generic ETS transparency-log API independent from Gateway connector
management while giving the production Console one coherent authenticated management surface.

## Browser contract

The Console may use the authorization context to hide or disable unavailable actions, but it must
assume that UI controls can be bypassed. All administrative and trust-changing operations remain
server-enforced.

The browser never receives:

- production signing private keys;
- connector credential values;
- reusable administrative secrets from the credential-provider layer;
- authority merely because a route or button is visible.

## Failure semantics

- missing/invalid production authentication: HTTP 401;
- unknown signed ETS role: HTTP 401;
- missing required management identity/scope: HTTP 403;
- browser scope override conflicting with signed scope: HTTP 403;
- authenticated identity without `connector.read` or `connector.manage`: HTTP 403 for connector read;
- authenticated identity without `connector.manage`: HTTP 403 for connector administration.

Failures return bounded diagnostics and do not expose policy internals or credentials.

## Nonclaims

This contract does not define an enterprise identity-provider product, session-cookie implementation,
or external RBAC directory. It defines the stable ETS authorization vocabulary and adapter boundary
that hosted identity integrations must populate after cryptographic token validation.

## Exit gate

P1.1 qualifies when local and production profiles, signed role parsing, server-derived capabilities,
scope-tamper rejection, privilege denial, Gateway management composition, and negative authorization
paths pass exact-head CI/security gates and independent review. The Console can then remove its
`console-user` and editable-production-scope placeholders and consume this contract.
