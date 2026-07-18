# Sprint: Hosted Readiness 4 - Azure SDK Client Wiring And RBAC Validation

## Sprint Goal

Add SignalForge runtime wiring for Azure SDK Managed Identity crypto clients,
least-privilege Key Vault / Managed HSM RBAC validation, and optional CI-gated
hosted tests that run only when Azure test resource references are supplied by
repository secrets or runtime environment variables.

## Scope Completed

- Add `create_managed_identity_crypto_client_factory` for runtime Azure SDK
  `ManagedIdentityCredential` and `CryptographyClient` creation.
- Add `required_signing_rbac_roles` and `validate_signing_rbac_roles` helpers.
- Allow `AzureManagedIdentitySignerAdapter.from_env` to build the runtime Azure
  SDK client factory when no fake/test factory is supplied.
- Add optional user-assigned managed identity and hosted test gates to
  `.env.example` as blank/disabled placeholders.
- Add `docs/security/AZURE_SDK_RBAC_VALIDATION.md`.
- Add `.github/workflows/hosted-azure-readiness.yml` for manual, secret-backed
  hosted validation.
- Add optional hosted tests that skip unless `ETS_AZURE_HOSTED_TESTS_ENABLED=true`.
- Add unit tests for SDK factory wiring and RBAC validation without Azure network calls.

## Acceptance Criteria

- [x] Runtime Azure SDK factory uses Managed Identity and CryptographyClient.
- [x] User-assigned Managed Identity client ID is optional and environment-supplied.
- [x] RBAC validation requires `Key Vault Crypto User` for Key Vault signing.
- [x] RBAC validation requires `Managed HSM Crypto User` for Managed HSM signing.
- [x] Hosted CI tests are manually dispatched and secret/environment gated.
- [x] Tests skip hosted Azure calls unless explicitly enabled.
- [x] No secrets, tenant IDs, client IDs, tokens, private keys, or customer data are committed.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_hosted_azure_adapter.py tests\hosted\test_azure_live_signer.py tests\unit\test_hosted_readiness_docs.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
