# Sprint: Hosted Readiness 3 - Azure Deployment Adapter

## Sprint Goal

Add the SignalForge-owned Azure deployment adapter boundary for hosted ETS
signing and telemetry: Managed Identity configuration, Bicep/App Configuration
and Key Vault references, and hosted integration tests that use environment or
CI-provided configuration only.

## Scope Completed

- Add `AzureManagedIdentitySignerAdapter` in `ets.api.azure_signing`.
- Add environment-driven adapter construction with fail-closed validation for
  missing Managed Identity and signer configuration.
- Add a reference Bicep template for Managed Identity, Key Vault, App
  Configuration, and Application Insights.
- Update `.env.example` with placeholder-only Azure signer variables.
- Add `docs/security/AZURE_DEPLOYMENT_ADAPTER.md`.
- Add hosted adapter tests using fake crypto clients and monkeypatched
  environment values, not committed secrets.
- Add documentation tests for sprint, Bicep, and placeholder-only configuration.

## Acceptance Criteria

- [x] Azure adapter accepts a SignalForge-provided crypto client factory.
- [x] Adapter construction fails closed when Managed Identity is not enabled.
- [x] Adapter construction fails closed when required signer configuration is missing.
- [x] Adapter produces an Azure Key Vault-style tree-head signer without storing
      private key material.
- [x] Reference Bicep includes Managed Identity, Key Vault, App Configuration,
      and Application Insights.
- [x] `.env.example` contains placeholders only.
- [x] Tests cover hosted adapter and documentation gates.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_hosted_azure_adapter.py tests\unit\test_hosted_readiness_docs.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
