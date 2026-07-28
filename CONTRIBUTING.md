# Contributing to ETS

Thanks for helping improve ETS — Evidence Transparency System.

ETS is an alpha-stage protocol and reference implementation. Contributions
should improve verifiable evidence handling while preserving the project's
security, privacy, patent, and claim-boundary guardrails.

## Local Setup

Use Python 3.12 or newer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Checks

Run these before opening a pull request:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\scripts\verify-ets-release-readiness.ps1
```

If you work on the Explorer UI, also run:

```powershell
Set-Location ets\explorer-ui
npm ci
npm run build
Set-Location ..\..
```

## Architecture Boundary

Core protocol code must stay independent of API, persistence, hosted identity,
and UI runtime dependencies.

## Public Contribution Boundary

Do not submit:

- real secrets, tokens, credentials, certificates, private keys, or signing keys;
- real PII, medical records, financial records, legal records, production
  customer evidence, or restricted incident data;
- official election data or non-fictional civic evidence records;
- USPTO receipts, application numbers, confirmation numbers, claim charts,
  provisional drafts, prior-art matrices, attorney-review notes, or assignment
  strategy.

Use synthetic fixtures and fictional demo packets only.

## Claim-Safe Language

Use restrained language:

> ETS verifies submitted-event inclusion, ordering, consistency, and reproducible
> verification for supplied proof material.

Do not state or imply that ETS proves real-world truth, legal sufficiency,
official chain of custody, election correctness, vote totals, ballot validity,
or completeness without external policy and observation.

## Pull Request Expectations

A pull request should include:

- a concise summary;
- tests or rationale for no tests;
- security/privacy impact;
- claim-boundary impact;
- confirmation that no restricted evidence or private IP material was added.

Pull requests that weaken security boundaries, introduce sensitive fixtures, or
overclaim ETS verification semantics should be treated as blocked until fixed.
