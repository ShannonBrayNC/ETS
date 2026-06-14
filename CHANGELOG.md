# Changelog

All notable public ETS changes are recorded here. Public tags must have a matching entry before the tag is created.

## [v0.1.0-alpha] - Unreleased

### Added

- Alpha release notes with validation commands, known limitations, and explicit non-claims.
- Changelog and release-notes enforcement policy for public tags.

### Validation commands

- `ruff check .`
- `mypy`
- `pytest`
- `ets-verify --version`
- `pwsh -NoProfile -File scripts/verify-ets-changelog.ps1 -Tag v0.1.0-alpha`

### Known limitations

- ETS stores metadata and hashes, not raw evidence bytes.
- Unsigned local tree heads are not production trust anchors.
- SQLite and local auth modes are for development, local validation, and fictional demos.
- Hosted multi-tenant production operation requires additional hardening and key-management automation.

### Non-claims

- This release does not claim production readiness.
- This release does not provide legal, compliance, or election certification.
- This release does not verify authenticity, legality, completeness, election correctness, ballot validity, tabulation accuracy, or official results.
