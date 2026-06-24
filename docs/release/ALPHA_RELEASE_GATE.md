# ETS Alpha Release Gate

This gate defines the required criteria before tagging or announcing a public ETS alpha release.

## Gate Decision

The alpha release is blocked unless every required gate below passes.

## Required Artifacts

| Artifact | Required |
|---|---|
| `README.md` | Yes |
| `ets/spec/protocol.md` | Yes |
| `docs/research/README.md` | Yes |
| `docs/research/non-claims.md` | Yes |
| `docs/research/FORMAL_TRACEABILITY_MATRIX.md` | Yes |
| `docs/research/FORMAL_MODEL_CLAIMS.md` | Yes |
| `docs/research/reproducibility-matrix.md` | Yes |
| `docs/research/REPRODUCIBILITY_APPENDIX.md` | Yes |
| `docs/reports/CERTIFICATE_CLAIM_SAFETY.md` | Yes |
| `docs/demo/election-rc-walkthrough.md` | Yes |
| `docs/ip` | Yes |
| `scripts/verify-ets-release-readiness.ps1` | Yes |

## Required Validation Commands

```powershell
.\scripts\verify-ets-release-readiness.ps1
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```

## Alpha Boundary

The alpha release may claim:

- deterministic canonical hashing for supported event payloads;
- submitted-event inclusion proof verification;
- supported consistency verification;
- verification bundle reproduction;
- certificate generation from supplied proof material;
- fictional demo workflows for evidence/audit storytelling;
- formal and reproducibility documentation at stated maturity levels.

The alpha release must not claim:

- production trust service readiness;
- legal sufficiency;
- real-world truth;
- raw evidence authenticity;
- election correctness;
- vote totals or official results;
- completeness without external expected-event policy and independent observation;
- Byzantine consensus;
- Internet-scale adversarial liveness;
- patent filing, patent allowance, or legal strategy unless counsel-approved.

## Tagging Rule

Recommended tag format:

```text
v0.1.0-alpha
```

Recommended sprint gate tag:

```text
sprint/release-readiness-gate
```

Do not create a public release if `verify-ets-release-readiness.ps1` fails.