# ETS Core C4 Compatibility and Release Policy

Status: Proposed engineering specification

## Transition objective

Move from the current `ets` distribution to an independently installable `ets-core` distribution without silently breaking existing consumers or treating every historical `ets.core` export as permanently supported.

## Supported transition surfaces

### New code

New consumers shall import from:

```python
from ets.core.api import ...
```

### Existing code

Selected legacy imports may remain temporarily available through compatibility re-exports. Each shim must identify:

- the old import;
- the supported replacement;
- the first version carrying the warning;
- the earliest permitted removal version;
- any behavioral or typing differences.

Compatibility shims must not import product services, initialize storage, or mask protocol-profile differences.

## Deprecation stages

1. **Documented:** replacement published; no runtime warning required.
2. **Warned:** runtime or static warning for direct deprecated imports.
3. **Removal scheduled:** exact major release identified.
4. **Removed:** migration guide and compatibility test retained.

Normative verification support for a historical protocol profile is distinct from Python API deprecation. Removing a Python alias does not authorize removing artifact verification support.

## Compatibility package options

C4 implementation shall choose one reviewed transition pattern:

- keep the existing `ets` distribution temporarily and add `ets-core` as a separately built subset;
- publish a thin `ets` compatibility/meta-package depending on `ets-core` plus product packages;
- perform a coordinated major-version transition with explicit migration tooling.

Publishing two distributions that install conflicting files into the same namespace is prohibited unless packaging tests demonstrate deterministic ownership and upgrade behavior across supported installers.

## Consumer migration tests

CI shall test representative consumers:

- existing verifier CLI invocation;
- direct canonicalization and proof imports;
- current API service using core functionality;
- Edge branch consuming the stable API;
- clean install, upgrade, downgrade, and uninstall scenarios;
- installation with and without optional extras.

## Release-candidate workflow

A release candidate shall:

1. originate from an exact reviewed commit;
2. use immutable version metadata;
3. build in a clean isolated environment;
4. run unit, type, conformance, import-boundary, side-effect, dependency-audit, and secret-scan gates;
5. inspect wheel and sdist contents;
6. install artifacts into a second clean environment;
7. run offline verification from the installed wheel;
8. generate SBOM and provenance;
9. sign artifacts and attestations;
10. publish only to a staging or release-candidate location;
11. undergo C5 independent reproduction and review.

## General-release workflow

A general release requires:

- C5 approval;
- exact-head CI success;
- merged-main validation;
- release notes and limitations;
- verified artifact digests, signatures, SBOM, and provenance;
- installation and conformance checks against the exact published artifact;
- explicit release go/no-go approval.

No release job may rebuild artifacts after approval. The approved release-candidate bytes are promoted unchanged.

## Post-release verification

After publication, automation shall:

- download artifacts from the public index or release location;
- verify digest and signature;
- compare provenance to the intended source commit and workflow;
- install into a clean environment;
- execute offline verifier smoke tests and the mandatory verifier conformance profile;
- archive the verification report.

Failure triggers release incident handling and prohibits representing the release as verified.

## Yank and revocation policy

A release may be yanked or marked affected for severe packaging, security, or protocol defects. Published artifacts and their digests are never silently replaced under the same version.

A corrected build receives a new version and references the affected release. Signature or trust-anchor revocation is recorded separately from cryptographic artifact verification.

## Support windows

The project shall publish:

- supported Python versions;
- maintained package major versions;
- supported protocol/profile verification periods;
- security-fix policy;
- deprecation timelines.

Protocol compatibility commitments must be explicit and must not be inferred solely from package semantic versions.
