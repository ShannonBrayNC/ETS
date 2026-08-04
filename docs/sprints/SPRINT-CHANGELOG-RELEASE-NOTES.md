# Sprint: Changelog and Release Notes Enforcement

## Goal

Require every public ETS tag to have a matching changelog entry and release-notes boundary.

## Why it matters

ETS is public-facing trust infrastructure tooling. Public releases need traceable history, reviewer validation commands, known limitations, and explicit non-claims so users do not mistake alpha evidence metadata verification for production, legal, or election correctness guarantees.

## Scope

- Add `CHANGELOG.md` with a `v0.1.0-alpha` entry.
- Add release-notes policy documentation.
- Add a PowerShell release gate for changelog and release-note boundaries.
- Add unit tests that keep the gate and docs present.

## Completion criteria

- Public tag has a matching `CHANGELOG.md` entry.
- Release notes include validation commands.
- Release notes include known limitations.
- Release notes include non-claims.
- Release notes and changelog do not overclaim production, legal, or election correctness.
- `scripts/verify-ets-changelog.ps1` passes for `v0.1.0-alpha`.
- `tests/unit/test_changelog_release_notes.py` passes.
