# ETS Azure SDK And RBAC Validation

## Status

- Sprint: Hosted Readiness Sprint 4.
- Review state: Requires Human Review.
- Trust label: Real Analysis.
- Approval state: Approval Required before hosted use.
- Risk level: High until SignalForge validates Azure SDK wiring and RBAC in a hosted environment.
- Trace ID: `ets-hosted-readiness-4-2026-07-18`.

## Purpose

Hosted Readiness Sprint 4 connects the SDK-agnostic ETS adapter boundary to a
SignalForge-owned Azure SDK runtime path. ETS remains the evidence, consent,
trust, and authenticity layer. SignalForge owns Managed Identity configuration,
Key Vault or Managed HSM RBAC, App Configuration, and CI secret providers.

## Runtime SDK Wiring

`create_managed_identity_crypto_client_factory` loads Azure SDK modules only when
the hosted Azure signer path is used. The runtime path uses
`ManagedIdentityCredential`, creates `CryptographyClient` instances for the
resolved Key Vault or Managed HSM key ID, and binds ETS hosted signing to the SDK
`SignatureAlgorithm.ps256` value. ETS passes a SHA-256 digest, not raw tree-head
bytes, to the SDK sign operation.

Required configuration:

- hosted deployments set `ETS_AZURE_MANAGED_IDENTITY_ENABLED=true`;
- `ETS_AZURE_KEY_VAULT_URL` from App Configuration or runtime environment;
- `ETS_AZURE_KEY_NAME` identifying an RSA signing key;
- optional `ETS_AZURE_KEY_VERSION`; when omitted, the adapter resolves the latest
  key and pins its concrete version;
- optional `ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID` from CI or runtime environment
  only when using user-assigned managed identity.

Do not commit real managed identity client IDs, tenant IDs, tokens, vault URLs,
key names, key versions, private keys, or customer data.

## Cryptographic Boundary

Azure Key Vault supports RSA/EC signing algorithms but not Ed25519/EdDSA. The ETS
hosted Azure profile therefore uses RSA-PSS with SHA-256 (`PS256`). Local ETS
Ed25519 remains independently supported and is not treated as a Key Vault
algorithm. Historical verification must select the verifier from the retained
`signature_alg` and public-key metadata.

## Least-Privilege RBAC

Before hosted signing is enabled, SignalForge deployment evidence must prove the
runtime managed identity has the signing role needed for the selected key service:

| Key service | Required role |
| --- | --- |
| Azure Key Vault | `Key Vault Crypto User` |
| Azure Managed HSM | `Managed HSM Crypto User` |

The role assignment should be scoped to the specific vault/HSM or key where
possible. Do not grant broad owner/contributor roles for signing.

## Optional Hosted CI Tests

`.github/workflows/hosted-azure-readiness.yml` runs only on manual dispatch. The
hosted test path is gated by `ETS_AZURE_HOSTED_TESTS_ENABLED=true` and requires
all Azure resource references to be supplied through repository secrets or
runtime environment variables. When the gate is not enabled, hosted tests skip
without attempting Azure network calls.

## Evidence Requirements

A hosted validation run should create ETS evidence with:

- run ID;
- managed identity label, not secret value;
- key ID hash;
- RBAC role evidence hash;
- signer test result hash;
- reviewer role;
- approval state;
- trace ID.
