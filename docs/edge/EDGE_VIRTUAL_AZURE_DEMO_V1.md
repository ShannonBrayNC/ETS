# ETS Edge Virtual Azure Demo v1

Status: Draft deployment profile
Date: 2026-08-21
Parent: #490
Depends on: #487, #488

## Purpose

This profile publishes the ETS Edge Dark Pro demonstration without making a physical
Edge appliance, ETS Core, or ETS Gateway Internet-addressable. It is an isolated
software simulation for synthetic/non-sensitive evidence only.

The hosted environment MUST identify itself as `virtual_demo`, software custody, and
`hardware_attested=false`. It is not a substitute for the physical ETS Edge R1 trust
boundary.

## Inbound architecture

```text
Browser
  -> Azure Front Door Premium
  -> WAF (Prevention)
  -> Microsoft Entra authentication/authorization
  -> Front Door Private Link
  -> internal Container Apps workload-profile environment
  -> unprivileged Dark Pro Nginx
  -> allow-listed /edge/ui/v1/* BFF
  -> local synthetic Edge Virtual runtime
```

No public route terminates directly on ETS Core, ETS Gateway, a physical Edge device,
or the raw Edge API.

## Activation is intentionally multi-stage

### Gate 1 — private origin

Run `Deploy Edge Dark Pro Azure` with `phase=origin` only after all four OCI image
inputs are immutable `repository@sha256:<digest>` references.

The origin deployment must prove:

- Container Apps environment `publicNetworkAccess=Disabled`;
- internal VNet integration;
- one pull-only ACR managed identity and zero application runtime identities;
- synthetic tenant/workspace/log identifiers only;
- `EmptyDir` demo persistence only;
- syslog disabled in the hosted profile;
- raw Edge/Core-like HTTP routes unavailable from hosted Nginx;
- software-held demo identity is not represented as hardware attestation.

Record the exact `container_app_name` and `managed_environment_name` emitted by the
successful deployment. Phase 2 requires those exact names; it does not discover an
origin by wildcard or prefix.

### Gate 2 — Entra application and Azure-side secret provisioning

Create/configure the single-tenant Microsoft Entra app registration outside the
repository. Restrict the application to the approved presenter/operator group.

The current Container Apps EasyAuth profile may require a confidential-client secret.
If used, provision that value directly into the Container App protected secret plane.
Do not put the value in:

- GitHub Actions secrets;
- repository variables;
- Bicep parameters;
- workflow inputs;
- source files;
- ETS evidence;
- build logs or retained artifacts.

Only the non-secret setting name (default
`MICROSOFT_PROVIDER_AUTHENTICATION_SECRET`) is passed to the public-edge template.
The workflow verifies the setting name exists in Azure without reading its value.

A future production Fleet console should reassess certificate/federated application
credentials so this bounded demo exception does not silently become a permanent
identity architecture.

### Gate 3 — Front Door/WAF/auth deployment

Run `Deploy Edge Dark Pro Azure` with `phase=public-edge` and provide:

- the exact Container App name from Gate 1;
- the exact managed environment name from Gate 1;
- the single-tenant Entra client ID;
- a JSON array containing one or more approved Entra group object IDs;
- the Azure-side EasyAuth secret setting name.

The workflow uses GitHub OIDC (`id-token: write` + `azure/login@v2`). It has no Azure
client secret path.

The public-edge deployment requires:

- Front Door Premium;
- custom domain `edge-demo.lanternprotocol.net`;
- managed TLS certificate using the strong Front Door TLS 1.2 cipher profile;
- HTTPS-only route;
- Front Door default domain disconnected from the route;
- Private Link target group `managedEnvironments`;
- certificate-name validation on the origin;
- WAF enabled in `Prevention` mode;
- Microsoft Default Rule Set 2.2;
- Microsoft Bot Manager Rule Set 1.1;
- per-client rate limiting;
- Container Apps EasyAuth enabled;
- single-tenant Entra issuer;
- explicit allowed group IDs;
- only `/afd-healthz` excluded from authentication;
- token store disabled for the demo;
- all other routes redirected to Entra login when unauthenticated.

## Gate 4 — Private Link approval

The Bicep template deliberately creates the Front Door shared Private Link resource in
`Pending` state. The deployment workflow does not approve it.

Before approval, inspect the pending private endpoint connection on the exact managed
environment from Gate 1 and require:

- the request corresponds to the newly deployed ETS Edge demo Front Door profile;
- target resource is the exact managed environment from Gate 1;
- target group is `managedEnvironments`;
- there are no unexplained competing pending requests;
- the request message identifies the ETS authenticated Edge Virtual demo.

Approve only that exact request. Do not create a broad auto-approval path.

## Gate 5 — DNS and TLS activation

Do not alter production Lantern Protocol DNS until the Front Door custom domain
validation value is known and the preceding gates are green.

After validation:

1. add only the required validation DNS record;
2. wait for Azure custom-domain validation and the managed certificate to become ready;
3. point `edge-demo.lanternprotocol.net` to the qualified Front Door endpoint;
4. prove the final HTTPS route and certificate;
5. do not expose or publish the Container Apps origin hostname as an operator URL.

## Required live qualification

Before demo acceptance, prove from an unauthenticated external client:

- `/` requires Entra authentication;
- `/edge/ui/v1/status` requires Entra authentication;
- `/afd-healthz` contains only the bounded health result;
- the Container Apps origin cannot be reached directly over the public Internet;
- the Front Door default hostname is not linked to the application route;
- WAF is enabled in Prevention mode;
- an approved presenter can authenticate and execute the bounded synthetic
  source-to-proof flow;
- a non-approved tenant user/group cannot access the app;
- cross-site state changes are rejected by the BFF;
- raw `/api`, `/edge/v1`, `/docs`, `/openapi.json`, `/internal`, `/ready`, and `/version`
  paths remain unavailable from the hosted surface;
- no reusable credential exists in browser storage, source maps, HTML/JS bundles,
  URLs, response payloads, or retained logs.

## Claim boundary

A successful hosted demonstration establishes only that this Azure Edge Virtual
profile can execute the qualified ETS software evidence lifecycle behind the defined
security controls. It does not establish physical hardware attestation, source truth,
observation completeness, legal admissibility, or equivalence to the physical Edge R1
hardware trust boundary.
