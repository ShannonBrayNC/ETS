# ETS Research Boundary

ETS is the **Evidence Transparency System**. The research documentation in this
folder supports alpha-stage protocol, verification, reproducibility, formal
model review, and public-safe comparison against adjacent protocols.

## Research Scope

This folder contains:

- formal model claim mapping;
- reproducibility guidance;
- research notes for verifier federation and temporal behavior;
- publication-oriented drafts and appendices;
- technical comparison of similar transparency, provenance, timestamping,
  supply-chain, policy, and audit protocols;
- traceability artifacts connecting claims to models, code, and tests.

## Current research documents

- [ETS Protocol Comparison Living Document](ETS_PROTOCOL_COMPARISON_LIVING_DOCUMENT.md) - full technical comparison of adjacent protocols, including Certificate Transparency, Trillian/Tessera-style logs, Sigstore/Rekor, SCITT, C2PA, OpenTimestamps, W3C PROV, in-toto/SLSA-style supply-chain metadata, OPA, SIEM/audit platforms, and blockchain chain-of-custody systems.

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
- Patent-pending status may be stated through `PATENT_NOTICE.md`, but private
  patent filings, claim charts, USPTO receipts, and attorney-review materials
  must remain outside this public repository.

## Release Gate

Before tagging a public alpha release, run:

```powershell
.\scripts\verify-ets-release-readiness.ps1
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```
