# ETS Research Boundary

ETS is the **Evidence Transparency System**. The research documentation in this
folder supports alpha-stage protocol, verification, reproducibility, and formal
model review.

## Research Scope

This folder contains:

- formal model claim mapping;
- reproducibility guidance;
- research notes for verifier federation and temporal behavior;
- publication-oriented drafts and appendices;
- traceability artifacts connecting claims to models, code, and tests.

## Claim Boundary

ETS research artifacts support restrained claims about submitted evidence
material, deterministic verification, append-only behavior, inclusion proofs,
consistency verification, and reproducible review of supplied proof bundles.

They do not prove real-world truth, legal sufficiency, election correctness, raw
evidence authenticity, or evidence completeness without an external expected-event policy and
independent observation process.

## Required Public Posture

Public research, alpha release notes, and demo material must preserve these
boundaries:

- ETS is a research/alpha evidence transparency system, not production trust
  infrastructure.
- Election-adjacent demos are fictional, non-PII, and not voting software,
  tabulation software, ballot software, election correctness software, or the
  vote of record.
- Formal models are bounded or assumption-scoped unless a stronger claim is
  explicitly mapped in `FORMAL_TRACEABILITY_MATRIX.md`.
- Patent and IP artifacts are technical preparation material for counsel review,
  not legal advice or filed claims.

## Release Gate

Before tagging a public alpha release, run:

```powershell
.\scripts\verify-ets-release-readiness.ps1
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```
