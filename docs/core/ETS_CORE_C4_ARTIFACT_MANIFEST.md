# ETS Core C4 Artifact Manifest

Status: Proposed normative release manifest

## Release artifact set

Each release candidate shall produce:

1. Python wheel for `ets-core`.
2. Python source distribution.
3. SHA-256 digest file covering every release artifact.
4. CycloneDX or SPDX SBOM for the wheel and build environment.
5. SLSA-compatible provenance statement or equivalent in-toto attestation.
6. Sigstore keyless signature bundle or approved equivalent for each artifact.
7. Public API manifest.
8. Protocol/profile registry snapshot.
9. Schema bundle.
10. Conformance-vector bundle and manifest.
11. Offline verifier usage guide.
12. Release notes, changelog, license, notices, and security-policy references.

## Required wheel paths

The wheel must include the implementation modules corresponding to the approved package boundary and these release resources:

```text
ets/
  core/
    api/
    canonical/
    profiles/
    merkle/
    proofs/
    signatures/
    models/
    bundles/
    verification/
    resources/
      schemas/
      vectors/
      profiles/
  verifier/
    cli.py
py.typed
```

Exact implementation paths may evolve before C4 implementation, but every shipped path must map to an approved classification and public or internal ownership category.

## Prohibited wheel contents

Artifact inspection shall reject:

- `.env` files, credentials, private keys, tokens, or certificates containing private material;
- test caches, virtual environments, local databases, generated logs, or coverage output;
- Git metadata;
- private IP, patent-preparation, customer, or production data;
- portal assets or product service code;
- Azure, FastAPI, database, Edge, Cloud, AI, billing, or telemetry implementation modules;
- source maps or build artifacts not declared in the manifest.

## Required metadata

Wheel metadata shall declare:

- normalized distribution name `ets-core`;
- exact version;
- Python version compatibility;
- license expression and included notices;
- project, source, issue, documentation, and security URLs;
- runtime dependency ranges;
- optional extras;
- typed-package marker;
- console entry point `ets-verify`.

## Manifest verification

The build workflow shall generate a machine-readable artifact manifest containing:

- artifact filename;
- media type;
- size;
- SHA-256 digest;
- source commit;
- package version;
- build workflow identity;
- build timestamp derived from controlled release metadata;
- SBOM digest;
- provenance digest;
- signature-bundle digest.

CI compares actual wheel and sdist contents against an allowlist. Undeclared additions and missing required resources fail the build.

## Schema and vector packaging

Schemas and vectors must be accessible through package-resource APIs and also published as standalone archives. Package-resource copies and standalone archives must have matching manifest digests.

## Reproducibility comparison

Two authorized clean builds from the same source, toolchain lock, and release metadata shall produce equivalent normalized artifacts. Where byte-for-byte equality is prevented by a documented packaging-format field, the workflow must normalize that field and compare all remaining content and metadata.

Any non-reproducible difference must be explained and accepted before release.
