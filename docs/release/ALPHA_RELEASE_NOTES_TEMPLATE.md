# ETS Alpha Release Notes Template

## Release

- Version: `v0.1.0-alpha`
- Product name: Evidence Transparency System
- Acronym: ETS
- Release type: public alpha / research preview
- Patent notice: ETS is patent pending; private filing records are maintained outside the public repository.

## What This Release Demonstrates

- Deterministic evidence-event hashing.
- Append-only log behavior.
- Inclusion proof verification.
- Supported consistency verification.
- Verification bundle reproduction.
- Claim-safe certificate generation.
- Fictional, non-PII evidence/audit demos.
- Research documentation for formal traceability and reproducibility.

## What This Release Does Not Claim

- Real-world truth.
- Raw evidence authenticity.
- Evidence completeness.
- Legal sufficiency.
- Regulatory acceptance.
- Election correctness.
- Vote totals, ballot validity, official results, or vote of record.
- Production trust-service readiness.
- Byzantine consensus.
- Internet-scale adversarial liveness.
- Patent allowance, claim scope, freedom to operate, or legal strategy.

## Validation Commands

```powershell
.\scripts\verify-ets-release-readiness.ps1
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```

## Required Links

- `PATENT_NOTICE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `docs/release/PUBLIC_RELEASE_CHECKLIST.md`
- `docs/release/ALPHA_RELEASE_GATE.md`
- `docs/research/non-claims.md`
- `docs/research/reproducibility-matrix.md`
- `docs/reports/CERTIFICATE_CLAIM_SAFETY.md`
