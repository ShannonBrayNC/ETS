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
- requires `ETS_AZURE_MANAGED_IDENTITY_ENABLED=true`;
- requires `ETS_AZURE_KEY_VAULT_URL`, `ETS_AZURE_KEY_NAME`, and
  `ETS_AZURE_KEY_VERSION`;
- creates an `AzureKeyVaultTreeHeadSigner` without private key material;
- delegates signing to a Managed Identity-backed Azure SDK client supplied by
  the deployment layer;
- rejects missing configuration and invalid signatures fail closed.

## Required Configuration Sources

Hosted deployments should source values from Azure App Configuration, Key Vault
references, GitHub Actions secrets, or managed environment variables. Do not commit real vault URLs, key names, key versions, tenant IDs, client IDs, access
tokens, private keys, or customer identifiers.

`.env.example` contains placeholders only. Production values must be injected by
CI/CD or the Azure runtime environment.

## Bicep Reference

`infra/azure/ets-hosted.bicep` provides a reference shape for:

- User Assigned Managed Identity;
- Key Vault with RBAC, soft delete, and purge protection;
- App Configuration with local auth disabled;
- Application Insights;
- App Configuration keys for signer mode and non-secret signer references.

The Bicep file intentionally does not create or export private key material.
Deployment owners must provision or approve the signing key and grant the managed
identity least-privilege signing access.

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
