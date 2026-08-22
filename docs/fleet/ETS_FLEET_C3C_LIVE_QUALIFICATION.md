# ETS Fleet C3C Live Qualification

C3C proves the production Fleet control-plane boundary in Azure without treating deployment as evidence of end-to-end correctness. The public hostname remains a separate activation gate.

## Claim-state model

Every retained C3C evidence package records these claims independently:

1. `software_composed`
2. `shared_store_qualified`
3. `entra_enforced`
4. `azure_private_origin_qualified`
5. `frontdoor_route_qualified`
6. `public_hostname_tls_qualified`
7. `live_fleet_mutation_qualified`

A later claim MUST NOT be inferred from an earlier claim. Unknown or unexecuted controls remain `false`.

## Security boundary

The production Fleet BFF accepts identity only through Azure Container Apps built-in authentication (EasyAuth) on the protected private origin. The bridge consumes the platform-injected `X-MS-CLIENT-PRINCIPAL` assertion and then Fleet independently requires the configured issuer, audience, tenant, exact Fleet app roles, current server-owned scope, current session generation, authorization epoch, and current server-side standing.

Browser headers, query parameters, bodies, or cookies never select ETS tenant/workspace scope, Fleet role, or SecurityAdmin step-up standing.

The bridge does not consume access-token or refresh-token headers. EasyAuth token storage is disabled. The application receives claims, not reusable Entra bearer credentials.

### Required Entra claims

The Fleet app registration and Conditional Access design must make these validated claims available through the EasyAuth principal:

- `iss`
- `aud`
- `tid`
- stable `oid` or `sub`
- exact Fleet app role (`Fleet.Viewer`, `Fleet.Operator`, or `Fleet.SecurityAdmin`)
- `exp`
- `auth_time`
- `sid`
- `acrs` when the configured Conditional Access authentication context is satisfied

`ETS_FLEET_STEP_UP_ACRS` identifies the required Entra authentication-context ID for SecurityAdmin step-up. The default qualification convention is `c1`, but production must use the explicitly approved tenant policy. An MFA-looking browser value is never accepted as step-up evidence.

## Secret handling

EasyAuth browser redirect requires the confidential-client credential configured for the Container App authentication provider. C3C follows the existing ETS Azure pattern:

- provision the secret directly in Azure;
- give the workflow only the Azure secret-setting name;
- verify that the setting exists;
- never read the secret value into GitHub Actions;
- never retain the secret in an artifact.

The PostgreSQL runtime remains Entra/managed-identity only. C3C does not add a database password or connection-string fallback.

## Phase 0 — immutable Fleet image

Run `Fleet C3C Q0 Immutable Image Publication` from merged `main`.

The workflow:

- requires `Dockerfile.fleet` and the C3C EasyAuth bridge;
- validates private ACR posture and disabled ACR admin credentials;
- authenticates to ACR through Azure workload identity and direct ACR OAuth exchange;
- builds `linux/amd64` with Buildx provenance and SBOM metadata;
- resolves and verifies a canonical `repository@sha256:<digest>` image;
- retains SPDX JSON SBOM and Trivy HIGH/CRITICAL report;
- fails on fixable HIGH/CRITICAL findings;
- creates GitHub build-provenance and SBOM attestations;
- retains a public-safe manifest tying the immutable image to exact source SHA and workflow run ID.

Only the immutable image reference from this gate may be supplied to C3C live composition.

## Phase 1 — compose protected edge

Run `Fleet C3C Live Qualification` with phase `compose-edge`.

The workflow requires the exact source SHA and Q0 immutable image. It verifies the target Azure tenant/subscription and existing C3B private origin, then updates the exact Fleet app to:

- the immutable Fleet image;
- `ETS_FLEET_AUTH_BRIDGE=container-apps-easyauth`;
- the explicit `ETS_FLEET_STEP_UP_ACRS` value.

It then deploys:

- Container Apps EasyAuth with single-tenant Entra configuration;
- operator-group admission;
- token store disabled;
- Front Door Premium;
- WAF Prevention with Microsoft managed and bot rules;
- a Private Link request to the exact Container Apps managed environment using subresource `managedEnvironments`;
- an HTTPS-only Front Door default-domain route.

The Private Link request remains `Pending`. No `fleet.lanternprotocol.net` custom domain is created. The evidence matrix advances only `software_composed`.

## Phase 2 — approve and qualify the private route

Run `Fleet C3C Live Qualification` with phase `approve-and-qualify-route` only after reviewing the exact pending Private Link connection name from Azure.

The workflow:

- selects exactly that pending connection;
- requires the C3C request description to match;
- approves that connection by exact resource ID;
- confirms the private origin remains non-public;
- fails if direct public access to the Container App origin succeeds;
- requires `/fleet/readyz` to succeed through the Front Door default hostname;
- requires readiness to assert only process/auth-config/store readiness and to keep evidence/health claims false;
- confirms an anonymous Fleet portal request is redirected or denied by the authentication boundary.

This may advance only `azure_private_origin_qualified` and `frontdoor_route_qualified`. It does **not** by itself prove an authenticated Fleet principal, shared-store multi-replica behavior, or a live mutation, so those claims remain false.

## Phase 3 — authenticated control-plane qualification

Before hostname activation, protected live controls must separately prove:

- Viewer: authenticated read is limited to server-owned ETS scope;
- Operator: approved bounded synthetic mutation succeeds;
- SecurityAdmin: high-impact synthetic action fails without current `acrs` step-up and succeeds with current approved step-up;
- forged roles, wrong issuer/audience/tenant, expired/stale sessions, browser-selected scope, cross-scope IDOR, missing/invalid CSRF, idempotency conflicts, and pending replay all fail closed;
- replay through a different Fleet replica returns the retained committed result without repeating the side effect;
- authoritative enrollment/current pointer and administrative evidence survive restart/redeploy;
- browser responses and retained logs/artifacts contain no reusable bearer token, session secret, database credential, SAS, Azure management token, private key, or device credential.

Only retained evidence from these controls can advance `shared_store_qualified`, `entra_enforced`, and `live_fleet_mutation_qualified`.

## Phase 4 — public hostname activation

`fleet.lanternprotocol.net` remains inactive until every preceding claim required by issue #525 is green.

The activation gate must independently verify:

- DNS ownership validation;
- managed TLS certificate healthy;
- WAF route targets only the approved Private Link origin;
- origin public access remains disabled;
- Entra authentication is active on the custom-host path;
- positive and negative Fleet browser/BFF controls pass through the custom hostname.

Do not modify the `lanternprotocol.net` apex or current `www` records as part of Fleet activation.

## Evidence rule

C3C evidence is bounded and public-safe. Retain exact source SHA, immutable image digest, workflow/run IDs, sanitized Azure resource identifiers, sanitized Entra configuration identifiers, control results, restart/redeploy proof, idempotency/evidence correlation IDs, route/TLS posture, and the explicit seven-state claim matrix. Never retain tokens, credentials, private keys, session secrets, or customer-sensitive identifiers.
