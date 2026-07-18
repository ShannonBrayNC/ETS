# Sprint: Hosted Readiness 2 - Azure Signer And Hosted Telemetry

## Sprint Goal

Continue hosted readiness by adding a production signer abstraction for Azure Key
Vault or Managed HSM, JWKS refresh/cache behavior for key rotation, and
Application Insights-compatible auth/signing failure telemetry.

## Scope Completed

- Add `AzureKeyVaultTreeHeadSigner` as an injected-adapter production signer
  abstraction that keeps private key material and Azure credentials outside ETS
  core.
- Add key rotation tests for externally signed tree heads and JWKS key refresh.
- Add fail-closed JWKS refresh behavior when unknown key IDs cannot be refreshed.
- Add Application Insights-compatible `ets.telemetry` structured security events.
- Emit auth rejection telemetry from API auth failures.
- Emit signing failure telemetry when tree-head signing fails.
- Add hosted signer and telemetry documentation.
- Add regression tests for implementation and documentation gates.

## Acceptance Criteria

- [x] Azure signer abstraction signs canonical tree-head payloads through an
      injected adapter.
- [x] Azure signer rejects non-HTTPS vault URLs.
- [x] JWKS auth refreshes keys for key rotation on unknown key ID.
- [x] JWKS refresh failure fails closed with `ETS_AUTH_REQUIRED`.
- [x] Auth failures emit Application Insights-compatible structured events.
- [x] Signing failures emit Application Insights-compatible structured events.
- [x] Hosted telemetry documentation states no tokens, keys, PII, customer
      secrets, or raw evidence payloads may be logged.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_api_security_persistence.py tests\unit\test_tree_head_signing_envelope.py tests\unit\test_hosted_telemetry.py tests\unit\test_hosted_readiness_docs.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
