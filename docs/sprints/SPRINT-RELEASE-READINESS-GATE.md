# Sprint: Release Readiness Gate

## Sprint Goal

Complete the ETS backlog recommendation **Harden release readiness gates**.

This sprint creates public alpha release controls that prevent accidental overclaiming and block public release unless the required research, formal, reproducibility, certificate, IP, and election-demo boundaries are present.

## Backlog Item

**Harden release readiness gates**

## Scope Completed By This Sprint

- Add `docs/release/PUBLIC_RELEASE_CHECKLIST.md`.
- Add `docs/release/ALPHA_RELEASE_GATE.md`.
- Add `docs/release/ALPHA_RELEASE_NOTES_TEMPLATE.md`.
- Add `scripts/verify-ets-release-readiness.ps1`.
- Add `tests/unit/test_release_readiness_docs.py`.

## Acceptance Criteria

- [ ] Public release checklist exists.
- [ ] Alpha release gate exists.
- [ ] Release notes template exists.
- [ ] Release readiness verification script exists.
- [ ] Unit tests exist.
- [ ] Gates require public naming normalization.
- [ ] Gates require research boundary and non-claims docs.
- [ ] Gates require formal traceability docs.
- [ ] Gates require reproducibility matrix.
- [ ] Gates require certificate claim safety.
- [ ] Gates require IP review acknowledgement.
- [ ] Gates prohibit election/voting overclaims.
- [ ] Gates prohibit production trust-service overclaims.
- [ ] Local validation commands are documented.

## Test / Verification Plan

Run:

```powershell
.\scripts\verify-ets-release-readiness.ps1
.\.venv\Scripts\python.exe -m pytest tests/unit/test_release_readiness_docs.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ets-verify.exe --version
```

## Sprint Tag

Suggested sprint tag after commit:

```powershell
git tag -a sprint/release-readiness-gate -m "Sprint: ETS release readiness gate"
git push origin sprint/release-readiness-gate
```

## Completion Definition

This sprint is complete when the release gate docs, verification script, and tests pass locally; the sprint tag is pushed; and the default branch is synced.