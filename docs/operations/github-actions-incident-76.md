# GitHub Actions incident #76 triage

## Summary

Issue #76 captured a GitHub Actions failure mode where pull-request jobs failed
before any workflow steps were recorded and before logs were retained. The
observed CI run `28110797049` reported failed jobs for Python validation and the
Explorer frontend build, but both jobs had no step list, no retrievable logs, and
no artifacts.

That failure mode is distinct from a normal test failure. A normal failure should
show at least runner setup, checkout, tool setup, and the failing command. Empty
steps plus missing logs means the run failed before useful job-level diagnostics
were available, or the logs were never retained by the Actions service.

## Evidence

Observed failure mode from the historical CI run:

- CI run: `28110797049`
- Python job: `83246618563`
- Frontend job: `83246618579`
- Job conclusion: `failure`
- Job steps: empty or unavailable
- Job logs: unavailable / blob not found
- Workflow artifacts: none

Current comparison run from PR #92 shows that runners now start and record normal
steps. The Python job reached Ruff, Mypy, and Pytest successfully before failing
at the dependency vulnerability scan. The Explorer frontend build completed
successfully. That means the original no-step/no-log symptom is not currently
reproducing on new pull-request runs.

## Operational diagnosis

The available evidence points to two separate classes of failures:

1. **Historical runner/startup failure**
   - Jobs completed as failed before steps were recorded.
   - Logs were unavailable.
   - No artifacts existed.
   - This is likely an Actions platform, hosted-runner startup, permissions,
     approval, or log-retention failure rather than a repository test failure.

2. **Current actionable CI failure**
   - Jobs now have normal step lists.
   - Ruff, Mypy, and Pytest can pass.
   - Failure can occur after primary validation in advisory/security checks.
   - This should be handled with explicit reports and artifacts so it does not
     hide the real test state.

## Expected healthy behavior

Every pull-request workflow should satisfy these conditions:

- A failed job exposes a populated step list.
- A failed command leaves logs or annotations.
- Pytest results are uploaded with `if: always()`.
- Advisory scans produce report artifacts even when they find issues.
- Required merge gates distinguish primary validation failures from advisory
  security findings.

## Triage steps

Use the GitHub CLI or connector equivalent to inspect future incidents:

```powershell
gh run view <run-id> --json jobs,status,conclusion,url
gh run view <run-id> --log-failed
gh run download <run-id>
```

For a no-step/no-log incident, record:

- run ID
- job IDs
- branch and PR
- head SHA
- workflow name
- whether job steps are empty
- whether logs return `BlobNotFound`
- whether artifacts exist
- whether newer runs on the same repository can start runners

## Current remediation

The repository CI should be hardened so that once runners start, the workflow
emits useful diagnostics and artifacts. This does not claim to fix a GitHub
hosted-runner platform outage. It reduces blind spots after runner startup by
ensuring advisory checks produce machine-readable reports and do not mask core
validation results.

## Validation expectation for closing #76

Close #76 only when:

- PR workflows start runners and show normal step logs.
- Failed jobs expose actionable logs or annotations.
- The affected PRs can be rerun or superseded by current runs that produce
  populated steps.
- Any remaining failures are command-level failures with evidence, not empty-step
  runner/startup failures.
