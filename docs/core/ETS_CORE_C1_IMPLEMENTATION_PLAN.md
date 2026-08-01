# ETS Core C1 Implementation Plan

Status: execution plan after C0 approval

## Work package 1 — Public contracts

1. Add `ets/core/api.py` with only the approved manifest.
2. Add `ets/core/results.py`, `errors.py`, and `profiles.py`.
3. Freeze `__all__` and type signatures with tests.
4. Keep `ets.core.__init__` as a documented compatibility facade during transition.

## Work package 2 — Canonicalization and profile resolution

1. Wrap or refactor the existing canonical JSON implementation behind `ets.canonical.json.v1`.
2. Add duplicate-key-safe JSON parsing for portable artifact inputs.
3. Add immutable profile records and registry resolution.
4. Reject profile guessing, conflicts, and production generation under verification-only profiles.
5. Add canonicalization and profile vector tests.

## Work package 3 — Pure hashing and Merkle functions

1. Isolate leaf/node hashing from storage and event services.
2. Expose explicit profile parameters.
3. Preserve active RFC 6962 behavior.
4. Isolate legacy unprefixed behavior under compatibility verification.
5. Add roots, inclusion, consistency, downgrade, and malformed vectors.

## Work package 4 — Verification result model

1. Implement closed status and reason enums.
2. Convert normal proof/signature/bundle invalidity to structured results.
3. Preserve exceptions only for programmer/configuration/invariant failures.
4. Add normative component order and first-terminal-result tests.
5. Confirm result serialization is deterministic.

## Work package 5 — Tree heads and bundles

1. Freeze signed-tree-head canonical payload.
2. Verify Ed25519 signatures through explicit signature profiles.
3. Make bundle verification pure and offline.
4. Validate all component linkages and profile consistency.
5. Add synthetic-key fixtures and negative linkage vectors.

## Work package 6 — Boundary enforcement

1. Add AST forbidden-import tests.
2. Add dependency-cycle tests.
3. Add clean-environment import tests without API/storage extras.
4. Add subprocess side-effect tests.
5. Add package-content and public-manifest tests.

## Work package 7 — Validation

Required commands/workflows:

- Ruff
- strict mypy
- full pytest
- public API manifest gate
- conformance-vector gate
- Windows/Linux/macOS determinism matrix
- dependency and secret audits
- formal specifications and approved proof/vector checks
- package import smoke test
- release-readiness checks

## Commit and PR slicing

Recommended narrow PRs after the C1 specification is approved:

1. `core/c1-results-profiles`
2. `core/c1-canonical-api`
3. `core/c1-merkle-profiles`
4. `core/c1-verification-results`
5. `core/c1-tree-head-bundles`
6. `core/c1-import-boundary-tests`
7. `core/c1-conformance-vectors`
8. `core/c1-integration-closeout`

Each PR SHALL preserve historical tests and include a protocol-impact statement. Hash-preimage or profile changes require independent protocol review.

## C1 definition of done

- Stable API manifest implemented and frozen.
- Active and legacy profiles explicitly supported as specified.
- Verification result model implemented with deterministic codes.
- Pure verification works without network, environment, storage, or side effects.
- Forbidden dependencies are CI-blocked.
- Complete C1 vector set passes.
- Current alpha artifacts remain verifiable.
- Exact-head CI and independent protocol review approve the implementation.
