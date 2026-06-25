# Branch Protection Runbook

## Purpose

This runbook defines the governance guardrails for the ETS default branch. The
goal is to keep release-readiness checks from being bypassed during branch
handoff, while still keeping solo-maintainer operations unblocked.

## Protected Branch

- Branch: `main`
- Protection model: GitHub classic branch protection
- Admin enforcement: enabled
- Force pushes: disabled
- Branch deletion: disabled
- Required branch freshness: enabled through strict status checks

## Required Checks

The following checks are required before a pull request can merge into `main`:

- `Release readiness gate`
- `Python test, lint, and type check`
- `Explorer frontend build`
- `tla`
- `symbolic-verification`
- `benchmarks`
- `lean-proofs`

These names must match the GitHub check contexts exactly. If a workflow job name
changes, update branch protection in the same sprint as the workflow change.

## Merge Expectations

- Use pull requests for changes targeting `main`.
- Keep the pull request branch up to date with `main` before merge.
- Wait for all required checks to pass on the current head commit.
- Treat missing release artifacts as merge blockers when the release-readiness
  gate fails.
- Do not bypass branch protection for routine sprint handoff.
- If branch protection must be changed, document the reason in the pull request
  or issue that required the change.

## Updating Check Contexts Safely

Use this sequence when renaming a workflow job or replacing a required check:

1. Add the new workflow job while keeping the old required check name in place.
2. Open a pull request and confirm both the old and new checks run successfully.
3. Update branch protection to require the new check context.
4. Confirm GitHub reports the new context under required status checks.
5. Remove the old workflow job or old job name in a follow-up pull request.
6. Confirm a fresh pull request cannot merge unless the new context passes.

Avoid renaming a required job and updating branch protection in separate,
uncoordinated changes. That can leave `main` blocked by a required context that
no longer exists, or temporarily allow a handoff without the intended gate.

## Verification Commands

Run these commands from a checkout authenticated with a GitHub token that can
read repository administration settings:

```powershell
$env:GITHUB_TOKEN=$null
gh api repos/ShannonBrayNC/ETS/branches/main/protection `
  --jq '{strict: .required_status_checks.strict, contexts: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, allow_force_pushes: .allow_force_pushes.enabled, allow_deletions: .allow_deletions.enabled}'
```

Expected result:

- `strict` is `true`.
- `enforce_admins` is `true`.
- `allow_force_pushes` is `false`.
- `allow_deletions` is `false`.
- The required contexts match the list in this runbook.

## Scheduled Audit

The `Governance Audit` workflow runs weekly and can be started manually from
GitHub Actions. It runs `scripts/verify-branch-protection-runbook.py` with
`ETS_VERIFY_LIVE_BRANCH_PROTECTION=1` so settings drift is caught even when no
pull request is open.

For repositories where the default `GITHUB_TOKEN` cannot read branch protection,
configure a repository secret named `BRANCH_PROTECTION_AUDIT_TOKEN`. The token
must be limited to repository administration read access and must not grant
write access unless GitHub requires that shape for the selected token type.
The scheduled audit fails fast when this secret is missing, because falling back
to the default Actions token hides the governance gap and returns `403 Resource
not accessible by integration`.

After configuring the secret, run the workflow manually once from GitHub Actions
and confirm `Branch protection drift audit` passes before relying on the
weekly schedule.

## Recovery

If a required context is stuck because a workflow job was renamed:

1. Verify the current check names on the latest pull request.
2. Update branch protection to require the current passing context.
3. Re-run or push a no-op commit to trigger a fresh check suite.
4. Record the change in the issue or pull request that caused the mismatch.

Do not disable the release-readiness gate as a shortcut. Replace stale contexts
with the current equivalent check instead.
