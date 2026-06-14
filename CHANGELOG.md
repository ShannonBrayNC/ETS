# Changelog

All notable ETS changes are tracked here. ETS follows SemVer; `0.x` releases are unstable and may include breaking changes.

Public tags must have a matching changelog entry before the tag is created. Each public-tag entry must include validation commands, known limitations, and non-claims.

## [v0.1.0-alpha] - Unreleased

### Added

- Establish canonical `ets.core` architecture.
- Add FastAPI `/api/v1` local API.
- Add in-memory and SQLite event stores.
- Add Merkle roots, inclusion proofs, consistency proofs, and verifier CLI.
- Add Ed25519 tree-head signing support.
- Add local header, local API key, and HS256 bearer auth modes.
- Add tenant/workspace scoping, redaction, audit logging, and proof bundles.
- Add Explorer UI build and API v1 wiring.
- Add alpha release notes with validation commands, known limitations, and explicit non-claims.
- Add changelog and release-notes enforcement policy for public tags.

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
- This release does not provide legal certification, compliance certification, or election certification.
- This release does not verify authenticity, legality, completeness, election correctness, ballot validity, tabulation accuracy, or official election results.
- This release is not voting software, tabulation software, legal advice, or a substitute for human review.
