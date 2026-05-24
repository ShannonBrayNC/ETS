# ETS v0.1.0-alpha RC Sprint Plan

This plan organizes the open RC issues into small, reviewable sprints for Codex-driven development.

## Sprint 1: Release Control and Public Shape

**Goal:** Establish the release lane, naming decision, and release checklist before deeper protocol changes.

**Issues:**

- #2 RC-001: Promote active implementation branch to release-candidate branch
- #3 RC-002: Resolve ETS naming and public terminology
- #14 RC-012: Add v0.1.0-alpha release checklist

**Definition of done:**

- Draft PR exists from the active implementation branch toward `main`.
- Branch divergence is visible and documented.
- Public naming decision is recorded for RC work.
- Release checklist exists and references all RC workstreams.
- No production deployment or release tag is created.

**Current status:**

- Draft PR #15 exists for the active implementation branch.
- PR #15 is intentionally kept in draft because the source branch is ahead of `main` and behind `main`.
- RC-002 is complete through `docs/decisions/ADR-0001-ets-public-name.md`.
- RC-012 is complete through `docs/release/v0.1.0-alpha-checklist.md`.
- RC-001 release-control setup is complete once this plan and the PR comment are present; the physical merge remains blocked until branch divergence is resolved and CI is reviewed.

**Next Codex task after Sprint 1:**

Resolve PR #15 branch divergence in a bounded commit, preserve active implementation behavior, run CI, and leave the PR in draft until checks are reviewed.

## Sprint 2: Protocol and Verifier Fidelity

**Goal:** Freeze the v0.1 protocol contract and prove offline verification behavior.

**Issues:**

- #4 RC-003: Freeze v0.1 protocol test vectors
- #5 RC-004: Add verifier bundle golden tests
- #6 RC-005: Add tree-head signing verification tests and key rotation docs
- #8 RC-006: Document consistency proof limitations and production roadmap

**Definition of done:**

- Deterministic protocol vectors exist.
- Verifier golden tests pass for valid bundles and fail for tampered bundles.
- Tree-head signing tests and operator docs exist.
- Consistency proof limitations are explicit in protocol and release docs.

## Sprint 3: Hosted and Storage Readiness

**Goal:** Clarify safe hosted-auth posture and prove SQLite durability for RC demos.

**Issues:**

- #9 RC-007: Add hosted-auth deployment profile using JWKS only
- #10 RC-008: Add SQLite persistence smoke test and migration notes

**Definition of done:**

- Hosted-auth profile documents JWKS-only behavior and local-auth boundaries.
- Tests cover hosted-auth success and failure paths.
- SQLite smoke tests prove persisted append/read/list/proof behavior.
- Migration notes define the path before hosted storage expansion.

## Sprint 4: Demo and API Experience

**Goal:** Make ETS easy to demonstrate, inspect, and validate locally.

**Issues:**

- #11 RC-009: Improve Explorer UI for RC demo workflow
- #12 RC-010: Add OpenAPI artifact and local API request examples
- #13 RC-011: Add fictional demo bundles and certificate examples

**Definition of done:**

- Explorer supports the RC demo path without browser developer tools.
- API examples and OpenAPI artifact support local verification.
- Fictional demo bundles and certificates are available for CLI and UI demos.

## Operating rules

- Keep each PR small enough for focused review.
- Prefer documentation and tests before production behavior changes.
- Do not create a release tag until the release checklist passes.
- Do not auto-merge RC work.
- Do not add real secrets, credentials, customer data, or private evidence material.
