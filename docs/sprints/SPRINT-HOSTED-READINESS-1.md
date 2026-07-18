# Sprint: Hosted Readiness 1 - Production Auth And Key Custody

## Sprint Goal

Start hosted readiness by hardening production JWKS auth edge cases and adding
hosted auth operations, Azure key custody posture, fail-closed signing behavior,
and incident response runbooks.

## Scope Completed

- Expand JWKS fail-closed tests for missing, malformed, expired, not-yet-valid,
  wrong issuer, wrong key, unsupported algorithm, unsupported JWK use, and
  invalid claim type cases.
- Harden auth token parsing so malformed JWT headers, claims, and signatures are
  converted into `AuthError` instead of leaking parser exceptions.
- Reject unsupported JWKS key `use` values unless the key is explicitly a
  signature key or does not declare use.
- Add hosted auth operations guidance for Azure-ready production JWKS posture.
- Add Azure Key Vault/Managed HSM key custody posture for production signing.
- Add hosted auth and signing incident response runbook.
- Add regression tests for sprint artifacts.

## Acceptance Criteria

- [x] JWKS missing/malformed/expired/wrong issuer/wrong key/unsupported algorithm
      edge cases return `401` with `ETS_AUTH_REQUIRED`.
- [x] Unsupported JWK `use` values fail closed.
- [x] Production signing remains fail-closed when configured without signer
      material.
- [x] Hosted auth operations doc exists and requires managed issuer/JWKS,
      no committed secrets, audit/telemetry, and approval records.
- [x] Azure key custody doc exists and recommends Key Vault or Managed HSM,
      Managed Identity, rotation evidence, and compromise handling.
- [x] Incident response runbook exists for auth and signing incidents.
- [x] Tests cover implementation and documentation gates.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_api_security_persistence.py tests\unit\test_hosted_readiness_docs.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
