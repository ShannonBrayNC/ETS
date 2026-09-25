# ETS SDK public release

Status: SDK-4 public-release preparation

Release tag: `v0.1.0-alpha`

Application contract: `ets.application.sdk.v1`

## Public package identities

| Ecosystem | Public package | Version | Runtime/import |
|---|---|---:|---|
| PyPI | `lanternprotocol-ets` | `0.1.0a1` | `import ets` / Python 3.12+ |
| NuGet | `LanternProtocol.ETS.Application` | `0.1.0-alpha` | `Ets.Application` / .NET 8 |
| npm | `@lanternprotocol/ets-sdk` | `0.1.0-alpha` | Node 22.14+ |

The Python distribution is deliberately **not** named `ets`. That name is
already used by an unrelated PyPI distribution. The source/import namespace
remains `ets`.

The version spelling differs because Python uses PEP 440 while npm and NuGet
use SemVer-style prerelease syntax. `docs/sdk/RELEASE_MATRIX.json` is the
machine-readable authority for this mapping.

## Release gates

A public SDK release requires all of the following:

1. repository release-readiness gate passes;
2. Python Ruff, Mypy, Pytest, dependency audit, and secret scan pass;
3. .NET and TypeScript cross-language compatibility gate passes;
4. the shared `conformance/sdk/v1` vectors pass;
5. all three registry packages build successfully;
6. the SDK release manifest and SHA-256 checksums are generated;
7. an SPDX SBOM is generated for the release bundle;
8. GitHub build provenance is attested for the release artifacts;
9. the `sdk-public-release` GitHub environment is approved;
10. the GitHub release tag exactly matches the release matrix.

## Trusted-publisher configuration

Publication is designed for OIDC trusted publishing rather than long-lived
registry tokens.

### PyPI

Configure a GitHub Trusted Publisher for:

- owner: `ShannonBrayNC`
- repository: `ETS`
- workflow: `sdk-publish.yml`
- environment: `sdk-public-release`
- project/distribution: `lanternprotocol-ets`

PyPI pending publishers may be used when creating the distribution for the
first time.

### npm

The public package is `@lanternprotocol/ets-sdk`.

Configure the npm trusted publisher with the same repository, workflow, and
environment and allow `npm publish`. npm trusted publishing requires a
GitHub-hosted runner and a sufficiently recent Node/npm runtime. If npm requires
the scoped package to exist before trusted publishing can be configured, create
the package interactively under the `@lanternprotocol` scope first, then
remove long-lived automation credentials.

### NuGet

The public package is `LanternProtocol.ETS.Application`.

Configure NuGet.org Trusted Publishing for:

- repository owner: `ShannonBrayNC`
- repository: `ETS`
- workflow: `sdk-publish.yml`
- environment: `sdk-public-release`

Set repository variable `NUGET_USER` to the NuGet.org profile name used by
the trusted-publishing policy. Do not store a long-lived NuGet API key.

## GitHub environment

Create `sdk-public-release` as a protected GitHub environment and require at
least one manual reviewer. Registry publishing jobs use that environment even
after a GitHub release is published.

The publish workflow does not run on pull requests or ordinary pushes. Its
registry jobs are reachable only from the GitHub `release.published` event.

## Build artifacts

The release bundle contains:

- Python wheel and source distribution;
- NuGet `.nupkg` and symbols package;
- npm `.tgz`;
- `sdk-release.spdx.json`;
- `sdk-release-manifest.json`;
- `SHA256SUMS`.

The manifest records the source commit and SHA-256 of each retained release
artifact. GitHub artifact attestations provide build provenance for the bundle.

## Verification

Before creating the GitHub release:

```powershell
python scripts/verify_sdk_release_matrix.py
docker compose -f compose.sdk-dev.yml up --build
python examples/sdk/chess/chess_evidence_walkthrough.py
```

After downloading a GitHub release artifact, verify its digest against
`SHA256SUMS`. GitHub-hosted provenance can additionally be checked with the
GitHub CLI attestation verification commands.

## Claim boundary

A package publication proves neither evidence truth nor production deployment
readiness. The SDK makes ETS protocol operations available to developers. A
`committed_local` receipt remains distinct from synchronization, independent
verification, completeness, authorization standing, and real-world truth.
