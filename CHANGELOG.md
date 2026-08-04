# Changelog

All notable ETS changes are tracked here. ETS follows Semantic Versioning. Releases in
the `0.x` series are unstable and may include breaking changes.

## [v0.1.0-alpha] — Unreleased

### Release status

Technical alpha freeze candidate. This release is intended for evaluation, reproducibility
testing, protocol review, and non-production experimentation.

### Added

- Canonical `ets.core` architecture.
- FastAPI `/api/v1` local API.
- In-memory and SQLite event stores.
- Merkle roots, inclusion proofs, consistency proofs, and verifier CLI.
- Ed25519 tree-head signing support.
- Local header, local API key, HS256 bearer, and JWKS authentication modes.
- Tenant/workspace scoping, redaction, audit logging, and proof bundles.
- Explorer UI build and API v1 wiring.
- Durable artifact registry reconstruction from persisted event data.
- Explicit artifact-registry initialization without framework monkey patching.
- Scoped artifact read, proof, and verification enforcement.
- Cross-platform release-readiness validation.
- CI validation for pull requests, pushes to `main`, release-candidate tags, and release tags.

### Changed

- Artifact registry startup now uses explicit initialization in `create_app`.
- Release-readiness verification now fails closed when Python or the verifier cannot be executed.
- Release validation no longer depends on a Windows-only virtual-environment path.

### Fixed

- Cross-tenant and cross-workspace artifact metadata access through artifact read, proof,
  and verification routes.
- Durable artifact-registry reconstruction after SQLite-backed application restart.
- Silent skipping of executable release checks on Linux and macOS runners.

### Security

- Artifact access is checked against the tenant/workspace scope of the backing evidence event.
- Out-of-scope artifact access returns a generic `404` response to avoid existence disclosure.
- Raw artifact payload bytes are not persisted in the artifact registry.
- Secret scanning and dependency auditing run in CI.
- Freeze-candidate dependency audits are hardened for Python and Explorer UI.
- Hosted-auth documentation is aligned around the implemented JWKS alpha profile.
- Repository text handling is normalized with Git LF line-ending rules.

### Validation

Run from the repository root:

```powershell
python -m ruff check .
python -m mypy
python -m pytest
python -m ets.verifier.cli --version

pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\verify-ets-release-readiness.ps1
```

The release candidate must also pass the GitHub Actions CI workflow on:

- the pull request targeting `main`;
- the resulting merge commit on `main`;
- the `rc/v0.1.0-alpha.1` tag;
- the final `v0.1.0-alpha` tag.

### Supported evaluation environment

- Python 3.12 is the release-validation runtime.
- Node.js 22 is used for the Explorer frontend build.
- Windows, Linux, and macOS are supported for local protocol and verifier evaluation where
  the documented Python and PowerShell prerequisites are available.
- Python 3.14 may emit third-party FastAPI/Starlette deprecation warnings and is not the
  authoritative release-validation runtime.

### Known limitations

- This is a technical alpha, not a production trust service.
- Hosted Azure deployment, Managed Identity signing, Key Vault operations, and hosted
  telemetry are outside the scope of this release.
- The default local unsigned tree head is not a production trust anchor.
- ETS does not guarantee that every relevant event or artifact was submitted.
- Formal-model and research evidence apply only to the explicitly documented models,
  assumptions, bounds, and execution artifacts.
- Backward compatibility is not guaranteed during the `0.x` series.
- Independent security review has not yet been completed.

### Compatibility

- Public CLI and data formats may change before `1.0.0`.
- Existing evidence bundles should be treated as alpha fixtures unless explicitly marked
  as stable.
- Consumers should pin the exact release tag and retain validation artifacts.

### Explicit non-claims

ETS does not prove:

- real-world truth;
- evidence completeness;
- legal sufficiency or legal admissibility;
- election correctness;
- vote tabulation correctness;
- that submitted evidence is authentic at its original source;
- production trust-service readiness;
- Byzantine consensus;
- Internet-scale adversarial liveness;
- patent filing, patent allowance, or freedom to operate.

### Release evidence

The final release entry must record:

- release date;
- final commit SHA;
- release-candidate tag;
- final release tag;
- Python and Node versions;
- Ruff result;
- mypy result;
- pytest count;
- verifier version result;
- release-readiness gate result;
- dependency-audit result;
- secret-scan result;
- frontend build result;
- known warnings and unresolved limitations.
