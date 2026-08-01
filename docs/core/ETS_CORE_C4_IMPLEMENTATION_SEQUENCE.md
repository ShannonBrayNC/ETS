# ETS Core C4 Implementation Sequence

Status: Proposed implementation plan

C4 implementation is divided into narrow pull requests so package metadata, code movement, supply-chain controls, and publication are reviewed independently.

## C4.1 — Package source layout and API ownership

- Create the approved internal source layout.
- Move or wrap normative modules without changing outputs.
- Add the stable `ets.core.api` facade and `py.typed`.
- Add import-boundary and side-effect tests.
- Preserve compatibility imports through explicit shims.

Exit: source layout matches C0-C1 contracts and all historical vectors remain unchanged.

## C4.2 — Distribution metadata and dependency split

- Introduce `ets-core` distribution metadata.
- Define minimal base runtime dependencies.
- Move product dependencies to separate distributions or extras.
- Add package metadata and dependency-policy tests.
- Test clean install with no extras.

Exit: a locally built wheel installs and performs offline verification without FastAPI, database, Azure, Edge, Cloud, portal, or AI dependencies.

## C4.3 — Artifact manifest and inspection

- Implement wheel/sdist allowlist inspection.
- Package schemas, profiles, vectors, notices, and typed metadata.
- Reject prohibited files and undeclared modules.
- Compare package resources with standalone release archives.

Exit: actual artifact contents exactly match the reviewed manifest.

## C4.4 — Compatibility migration

- Implement selected compatibility-package or shim strategy.
- Add deprecation warnings where approved.
- Test representative current consumers.
- Test install, upgrade, downgrade, coexistence, and uninstall behavior.
- Publish migration guide.

Exit: existing supported consumers have a tested migration path and no ambiguous namespace ownership exists.

## C4.5 — Reproducible build and supply-chain evidence

- Lock build frontend and backend versions.
- Normalize timestamps and archive metadata.
- Build independently in two clean environments.
- Compare artifacts and document any permitted normalization.
- Generate SBOM and provenance.
- Sign artifacts and attestations.

Exit: release-candidate artifacts are reproducible, attributable to one source commit and workflow, and independently verifiable.

## C4.6 — Release-candidate workflow

- Add tag/release-candidate trigger with protected environment.
- Run complete CI, conformance, audits, content inspection, and installed-wheel tests.
- Publish immutable candidate artifacts to staging.
- Produce a release evidence record with URLs, digests, and workflow identities.

Exit: signed release candidate is available for C5 independent validation.

## C4.7 — Promotion and post-release verification

- Promote approved candidate bytes unchanged.
- Verify the publicly retrieved artifacts.
- Install and run verifier conformance from the public artifact.
- Archive post-release report.
- Add yank/incident procedure and release-support matrix.

Exit: release publication and post-release verification are reproducible and documented.

## Required CI gates

Every implementation PR must run the relevant subset of:

- Ruff and strict type checking;
- complete core tests;
- public API manifest test;
- import dependency graph test;
- import side-effect test;
- protocol and conformance vectors;
- wheel/sdist build and inspection;
- clean-environment installation;
- dependency audit;
- full-history secret scan where release-sensitive;
- SBOM validation;
- provenance validation;
- signature verification;
- reproducibility comparison.

## Sequencing constraints

- C4.1 may begin after C0-C1 approval.
- C4.2-C4.4 require the stable C1 API and approved compatibility strategy.
- C4.3 must include C2 schemas and C3 vectors before final closeout.
- C4.5-C4.7 require the complete C1-C3 implementation and exact release baseline.
- No public package release occurs before C5 approval.

## Completion evidence

C4 closes only when:

- the installed wheel performs offline verification in a clean environment;
- artifacts match the approved manifest;
- dependency and import boundaries pass;
- compatibility migration passes;
- reproducible-build comparison passes;
- SBOM, provenance, and signatures validate;
- signed release-candidate artifacts are ready for independent C5 testing.
