# Sprint: CLI Golden-Path Fixture Enforcement

## Goal

Every public `ets-verify` command has a stable fixture and a passing regression test.

## Why it matters

ETS credibility depends on reproducible verification. Public verifier promises should be backed by small, deterministic artifacts that reviewers can run locally and in CI.

## Scope

- Add static verifier fixtures under `tests/fixtures/verifier/`.
- Add CLI regression tests for each public `ets-verify` command.
- Add a PowerShell fixture gate for reviewers and CI.
- Document fixture purpose, commands, expected results, and trust boundaries.

## Completion criteria

- `ets-verify --version` passes.
- `event-hash`, `inclusion-proof`, `verify-proof`, `consistency-proof`, `bundle`, `certificate`, `tree-head`, and `election-proof` all have passing fixture tests.
- A tampered bundle copy fails with a non-zero verifier result.
- CLI docs reference every static fixture.
- `scripts/verify-ets-cli-fixtures.ps1` is available as the local/CI gate.
