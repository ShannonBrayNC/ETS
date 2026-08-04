# ETS Verifier Golden Paths

The files in `tests/fixtures/verifier/` are deterministic, fictional, metadata-only artifacts for public `ets-verify` regression tests and reviewer demos. They do not contain real customer data, real voter data, real ballot data, real tabulation data, or official election results.

## Fixture inventory

| Fixture | Public command covered | Expected result |
| --- | --- | --- |
| `tests/fixtures/verifier/event.json` | `ets-verify event-hash tests/fixtures/verifier/event.json` | Prints the canonical SHA-256 event hash. |
| `tests/fixtures/verifier/event.json` | `ets-verify event-hash tests/fixtures/verifier/event.json --expected <hash>` | Returns `valid: true` when `<hash>` is the computed hash. |
| `tests/fixtures/verifier/inclusion-proof.json` | `ets-verify inclusion-proof tests/fixtures/verifier/inclusion-proof.json` | Returns `valid: true`. |
| `tests/fixtures/verifier/inclusion-proof.json` | `ets-verify verify-proof tests/fixtures/verifier/inclusion-proof.json` | Returns `valid: true` through the compatibility alias. |
| `tests/fixtures/verifier/consistency-proof.json` | `ets-verify consistency-proof tests/fixtures/verifier/consistency-proof.json` | Returns `valid: true`. |
| `tests/fixtures/verifier/bundle.json` | `ets-verify bundle tests/fixtures/verifier/bundle.json` | Returns `valid: true`. |
| `tests/fixtures/verifier/bundle.json` | `ets-verify certificate tests/fixtures/verifier/bundle.json --format markdown` | Renders a certificate with claim-boundary sections. |
| `tests/fixtures/verifier/tree-head-previous.json` and `tests/fixtures/verifier/tree-head-latest.json` | `ets-verify tree-head tests/fixtures/verifier/tree-head-previous.json tests/fixtures/verifier/tree-head-latest.json` | Returns `tree size advanced`. |
| `tests/fixtures/verifier/election-proof.json` | `ets-verify election-proof tests/fixtures/verifier/election-proof.json` | Returns `valid: true` for a fictional election evidence metadata proof. |

## Required local validation

```powershell
pwsh -NoProfile -File scripts/verify-ets-cli-fixtures.ps1
```

Equivalent Python regression test:

```powershell
python -m pytest tests/unit/test_verifier_cli_golden_paths.py
```

## Trust boundaries

These fixtures verify verifier mechanics only:

- event hash canonicalization;
- Merkle inclusion proof verification;
- consistency proof verification;
- proof bundle verification;
- certificate rendering boundaries;
- local tree-head rollback/equivocation sanity checks;
- fictional election evidence metadata inclusion proof verification.

These fixtures do not verify evidence authenticity, evidence legality, evidence completeness, election correctness, ballot validity, tabulation accuracy, official election results, or production trust readiness. ETS is not voting software or tabulation software.

## Tamper regression

`tests/unit/test_verifier_cli_golden_paths.py` creates a temporary tampered copy of `tests/fixtures/verifier/bundle.json` and asserts that `ets-verify bundle` exits non-zero with `valid: false`. Keep tampered artifacts temporary so the checked-in fixture set remains the minimal stable golden path.
