# Sprint: Hosted Readiness 5 - Live Azure Validation And Deployment Evidence

## Sprint Goal

Add a secret-gated live Azure validation path and sanitized deployment evidence
record so hosted signer readiness can be reviewed without exposing secrets,
private keys, tenant IDs, client IDs, vault URLs, raw key IDs, customer data, or
raw evidence payloads.

## Scope Completed

- Add `HostedValidationEvidence` and `build_hosted_validation_evidence`.
- Update optional hosted Azure signer test to perform a live sign when explicitly
  enabled through CI/runtime environment variables.
- Ensure hosted validation evidence hashes key IDs, RBAC roles, and signer test result instead of storing raw Azure references.
- Add `docs/security/HOSTED_VALIDATION_EVIDENCE.md`.
- Add Sprint 5 documentation and regression tests.

## Acceptance Criteria

- [x] Hosted evidence model includes trust label, approval state, trace ID, run
      ID, managed identity label, and reviewer role.
- [x] Hosted evidence hashes raw key ID, RBAC role list, and signer test result.
- [x] Hosted live signer test remains skipped unless Azure test resources are
      supplied through CI/runtime environment variables.
- [x] Hosted live signer test creates sanitized evidence when enabled.
- [x] Documentation states the evidence is advisory until deployment-owner review.
- [x] Tests cover evidence sanitization and documentation gates.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_hosted_validation_evidence.py tests\hosted\test_azure_live_signer.py tests\unit\test_hosted_readiness_docs.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
