# ETS Azure Deployment Adapter

## Status

- Sprint: Hosted Readiness Sprint 3.
- Review state: Requires Human Review.
- Trust label: Real Analysis.
- Approval state: Approval Required before hosted use.
- Risk level: High until SignalForge deployment owners review identity, signing, telemetry, and incident response.
- Trace ID: `ets-hosted-readiness-3-2026-07-18`.

## Purpose

This document defines the ETS-to-SignalForge boundary for hosted Azure signing
and telemetry. ETS remains the evidence, consent, trust, and authenticity layer.
SignalForge owns Azure resource provisioning, Managed Identity, App
Configuration, Key Vault or Managed HSM access, and Application Insights routing.

## Adapter Contract

`AzureManagedIdentitySignerAdapter` lives in `ets.api.azure_signing` and accepts a
SignalForge-provided crypto client factory. The adapter:

- reads only non-secret configuration from environment or App Configuration;
- uses Managed Identity and rejects an explicitly disabled managed-identity flag;
- hosted deployments set `ETS_AZURE_MANAGED_IDENTITY_ENABLED=true`;
- requires `ETS_AZURE_KEY_VAULT_URL` and `ETS_AZURE_KEY_NAME`;
- accepts optional `ETS_AZURE_KEY_VERSION`; when omitted, resolves the current key
  to a concrete version before signing;
- requires an RSA Key Vault/Managed HSM key capable of `PS256` signing;
- creates an `AzureKeyVaultTreeHeadSigner` without private key material;
- SHA-256 hashes the canonical tree-head payload before delegating the digest to
  the Managed Identity-backed Azure SDK `CryptographyClient`;
- rejects missing configuration and invalid signature results fail closed.

Azure Key Vault does not support Ed25519/EdDSA keys. Local ETS Ed25519 signing is
a separate profile and must not be represented as Key Vault signing.

The hosted Azure runtime also exposes
`POST /api/v1/verify/tree-head-signature` for independent PS256 verification using
a caller-supplied DER SubjectPublicKeyInfo RSA public key. The existing local
Ed25519 verification route remains unchanged.

## Required Configuration Sources

Hosted deployments should source values from Azure App Configuration, Key Vault
references, GitHub Actions secrets, or managed environment variables. **Do not commit real vault URLs**, key names, key versions, tenant IDs, client IDs, access
tokens, private keys, or customer identifiers.

`.env.example` contains placeholders only. Production values must be injected by
CI/CD or the Azure runtime environment.

## Bicep Reference

`infra/azure/ets-hosted.bicep` provides the hosted pilot deployment shape for:

- User Assigned Managed Identity;
- dedicated Key Vault with RBAC, soft delete, and purge protection;
- non-exportable RSA signing key with `sign` and `verify` operations;
- Key Vault Crypto User access for the ETS managed identity;
- OAuth-only Azure Table storage and table-scoped Storage Table Data Contributor;
- internal-ingress Azure Container App with startup, liveness, and readiness probes;
- App Configuration with local auth disabled;
- Application Insights and Azure Monitor-compatible platform logging.

The template creates key metadata and the non-exportable Key Vault key through
Azure Resource Manager. It never contains, returns, or exports private key
material. The runtime resolves the current key to a concrete version when
`ETS_AZURE_KEY_VERSION` is omitted.

The current pilot keeps Storage and Key Vault public-network endpoints enabled so
the Container App can reach them without an unqualified VNet/private-endpoint
design. Authorization remains TLS + Microsoft Entra ID + least-privilege RBAC.
Do not describe this pilot as private-endpoint or VNet-isolated.

## Hosted Integration Test Boundary

Hosted integration tests must receive all environment-specific configuration
through environment variables or CI secret providers. Tests must not commit:

- bearer tokens;
- private keys;
- tenant IDs;
- client IDs;
- real issuer URLs;
- customer data;
- raw evidence payloads.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_hosted_azure_adapter.py tests\unit\test_hosted_readiness_docs.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
