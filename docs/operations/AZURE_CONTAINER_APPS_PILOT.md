# ETS Hosted Azure Container Apps Pilot

## Status

This profile is a hosted **pilot** deployment target for ETS. It is not an HA/GA,
compliance, legal-admissibility, cross-region DR, or hardware-appliance claim.
Passing deployment and verification checks does not establish source truth or
source completeness.

## Topology

`infra/azure/ets-hosted.bicep` deploys:

- one Azure Container Apps environment;
- one internal-ingress ETS API Container App;
- one User Assigned Managed Identity;
- one Azure Storage account and one dedicated Table for ETS event persistence;
- one dedicated Azure Key Vault and a non-exportable RSA signing key;
- Key Vault Crypto User RBAC for the ETS managed identity;
- Storage Table Data Contributor RBAC scoped to the dedicated evidence table;
- App Configuration support resources;
- Application Insights support resources;
- startup, liveness, and readiness probes against `/version`, `/health`, and
  `/ready`.

The Container App is deliberately pinned to one replica for pilot qualification.
That is not an availability claim.

## Runtime profile

The deployment selects the hosted runtime using:

- `ETS_STORAGE_PROVIDER=azure_table`;
- `ETS_SIGNING_MODE=azure_key_vault`;
- `ETS_AUTH_MODE=production_jwks`;
- a deployment-authoritative `ETS_LOG_ID`;
- an explicit JWKS URL, issuer, and audience;
- Managed Identity-backed Azure Table and Key Vault configuration.

No local signing private key, storage account key, SAS token, or bearer token is
placed in the template or its outputs.

## Signing boundary

Azure Key Vault does not provide Ed25519/EdDSA signing keys. The hosted profile
therefore uses an RSA key and ETS `PS256` tree-head signatures. ETS hashes the
canonical tree-head payload with SHA-256 and passes only that digest to Key Vault
for RSA-PSS signing. Local ETS Ed25519 remains a separate profile.

`ETS_AZURE_KEY_VERSION` is intentionally not injected by the Bicep template. On
startup the hosted runtime resolves the current Key Vault key to a concrete
version and pins that version in the tree head `public_key_id` before serving
signed tree heads.

## Network boundary

The ETS API uses Container Apps ingress with `external: false`, so the pilot does
not expose a public ETS HTTP endpoint.

The current pilot template does **not** deploy a VNet, private endpoints, or
private DNS for Storage and Key Vault. Their Azure service endpoints remain
public-network reachable while access is constrained by TLS, Microsoft Entra ID,
RBAC, and disabled Storage Shared Key authorization. A future private-networking
slice may tighten this boundary, but this pilot must not be described as private
endpoint or VNet-isolated.

## Storage boundary

The Storage account:

- disables Shared Key authorization;
- defaults to OAuth authentication;
- requires HTTPS and TLS 1.2;
- grants the ETS managed identity Storage Table Data Contributor only at the
  dedicated table scope.

The Azure Table event store retains validated event JSON, event hashes, leaf
hashes, log metadata, and event-ID indexes. It does not turn raw artifact bytes
into canonical ETS storage.

## Deployment parameters

A deployment owner supplies:

- `environmentName` — a non-customer naming seed;
- `containerImage` — the ETS hosted OCI image;
- `logId` — the authoritative hosted ETS log ID;
- `authJwksUrl` — production JWKS endpoint;
- `authIssuer` — expected token issuer;
- `authAudience` — expected token audience;
- optional table/key naming and RSA key-size parameters.

Do not use customer PII in resource naming parameters or deployment outputs.

## Qualification boundary

HOST-AZ-Q1 (#361) is responsible for proving the deployed system through the full
bounded sequence:

1. clean deployment;
2. health/readiness/version success;
3. authorized client authentication;
4. synthetic evidence append;
5. proof and signed tree-head retrieval;
6. independent proof/signature verification;
7. Container App revision restart;
8. post-restart event/proof recovery;
9. deterministic duplicate rejection;
10. an authorized OpsHelm or equivalent internal client path.

Sanitized qualification evidence may retain resource identifiers, event IDs,
proof bundles for synthetic metadata, revision identifiers, and verification
results. It must not retain bearer tokens, credentials, private keys, raw customer
evidence, or customer identifiers.
