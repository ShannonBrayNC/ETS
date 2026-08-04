# Sprint: Certificate Claim Safety

## Sprint Goal

Harden ETS verification certificates so public alpha outputs do not overclaim
what ETS proof material verifies.

## Scope Completed

- Add `docs/reports/CERTIFICATE_CLAIM_SAFETY.md`.
- Add claim-safe certificate sections for JSON, Markdown, and HTML output.
- Add `ets/version.py` as the centralized version helper.
- Update verifier imports to use `ets.version`.
- Add `scripts/verify-ets-certificate-claim-safety.ps1`.
- Add `tests/unit/test_certificate_claim_safety.py`.

## Acceptance Criteria

- [x] Certificates state `What This Verifies`.
- [x] Certificates state `What This Does Not Verify`.
- [x] Certificates warn that supplied ETS proof material does not prove
      real-world truth, completeness, or legal sufficiency.
- [x] Verifier code no longer imports `__version__` from the package root.
- [x] Sprint patch artifacts are not committed as runtime files.

## Validation

```powershell
.\scripts\verify-ets-certificate-claim-safety.ps1
.\.venv\Scripts\python.exe -m pytest tests\unit\test_certificate_claim_safety.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```
