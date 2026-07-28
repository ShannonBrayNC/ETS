# ETS Public Release Checklist

ETS is the **Evidence Transparency System**. This checklist blocks public release until the alpha documentation, verifier behavior, claim boundaries, and public IP-boundary controls are complete.

## Release Classification

- Release type: `v0.1.0-alpha`
- Public name: **Evidence Transparency System**
- Public acronym: **ETS**
- Release posture: research/alpha, not production trust service
- Default storage posture: local/in-memory or documented local SQLite unless explicitly configured otherwise
- Public demo posture: fictional, non-PII, non-production, non-official

## Required Gates

| Gate | Required Evidence | Status |
|---|---|---|
| Public naming normalized | README/spec/research docs use Evidence Transparency System as the public name. | Required |
| Research boundary present | `docs/research/README.md` and `docs/research/non-claims.md` exist and state non-claims. | Required |
| Formal traceability present | `docs/research/FORMAL_TRACEABILITY_MATRIX.md` and `docs/research/FORMAL_MODEL_CLAIMS.md` exist. | Required |
| Reproducibility matrix present | `docs/research/reproducibility-matrix.md` exists and maps artifacts to inputs, outputs, verifier command, failure condition, and claim boundary. | Required |
| Certificate claim-safety present | `docs/reports/CERTIFICATE_CLAIM_SAFETY.md` exists and certificates include claim-safe sections. | Required |
| IP review boundary acknowledged | `PATENT_NOTICE.md` exists; private patent filings, claim charts, USPTO receipts, and attorney-review material are excluded from the public repository. | Required |
| Public contribution guardrails present | `SECURITY.md`, `CONTRIBUTING.md`, pull request templates, issue templates, and Dependabot configuration exist. | Required |
| Election demo boundary present | Election RC docs state ETS is not voting software, tabulation software, voter registration software, ballot software, election correctness, or vote of record. | Required |
| Verifier CLI works | `ets-verify --version` imports cleanly. | Required |
| Local checks documented | Ruff, mypy, pytest, verifier, and release readiness checks are documented. | Required |
| No production overclaim | Release notes do not state production trust, real-world truth, legal sufficiency, official election correctness, or completeness without external policy. | Required |

## Mandatory Local Validation

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\verify-ets-release-readiness.ps1
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```

## Required Public Language

Use:

> ETS verifies submitted-event inclusion, ordering, consistency, and reproducible verification for supplied proof material.

Use:

> ETS does not prove real-world truth, legal sufficiency, election correctness, or completeness without external policy and observation.

Use:

> ETS is patent pending. Private filing records, claim strategy, and attorney-review materials are maintained outside the public repository.

## Prohibited Public Language

Do not publish language that says or implies:

- ETS proves evidence is true.
- ETS proves raw evidence is authentic.
- ETS proves all expected evidence was submitted.
- ETS proves legal sufficiency.
- ETS proves election correctness.
- ETS is voting software, tabulation software, voter registration software, ballot-marking software, ballot-counting software, or the vote of record.
- ETS is production trust infrastructure without a deployment-owner security review, key-management review, durability review, and monitoring/anchoring plan.
- The USPTO has granted or allowed any ETS patent claim.
- The public repository contains the complete patent filing record or legal strategy.

## Release Sign-Off

A public alpha tag may be created only after:

- all required gates pass;
- all local validation commands pass;
- IP review boundary is acknowledged;
- release notes repeat the research/alpha and non-claim boundaries;
- demo artifacts are confirmed fictional and non-PII;
- public repository settings are verified: secret scanning, push protection, Dependabot alerts, CodeQL/default code scanning, and `main` branch protection are enabled.
