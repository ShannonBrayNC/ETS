# ETS v0.1.0-alpha Release Readiness Assessment

## Executive summary

Current recommendation:

- Ready for Technical Alpha: **Yes, subject to final merged-main evidence**
- Ready for Beta: **No**
- Ready for Production: **No**

Release recommendation:

Proceed to the final alpha tag decision only after PR #156 merges to `main`, the freeze branch is rebased onto that merge commit, all required workflows pass on one exact candidate commit, and the release validation record is updated with those run URLs.

## Scope

This assessment covers engineering, protocol semantics, security, documentation, validation, CI/CD, and research/non-claim boundaries for `v0.1.0-alpha`.

## Engineering assessment

Status: **PASS for technical alpha**

Completed:

- 313 automated Python tests on the runtime and Merkle hardening candidate.
- Ruff and mypy validation.
- SQLite persistence and restart behavior.
- Durable artifact registry reconstruction.
- Artifact scope and tenant/workspace enforcement.
- FastAPI API, verifier CLI, SDK helpers, certificates, and Explorer workflow.
- RFC 6962 domain-separated Merkle semantics with active v0.2 vectors.
- Six-node Docker federation build and health validation.

Remaining engineering risks:

- RC consistency-proof behavior remains alpha behavior rather than final production-grade consistency auditing.
- SQLite is not the final horizontally scaled hosted storage architecture.
- Production key discovery, rotation automation, multi-region operation, and hosted tenancy controls remain incomplete.
- Edge appliance durability, offline synchronization, and operator UX are deferred.

## Security assessment

Status: **PASS for controlled alpha use**

Completed:

- Implicit all-local startup fails closed unless `ETS_ALLOW_INSECURE_LOCAL=1` is explicitly set.
- Local/demo authorization is confined to explicit profiles, including the Docker demonstration federation.
- Hosted JWT/JWKS posture is documented.
- Python dependency audit passes.
- Explorer dependency audit passes at moderate severity.
- Full-history Gitleaks scan passes.
- Raw evidence bytes remain outside the default ETS storage boundary.

Remaining security risks:

- Local unsigned tree heads are not production trust anchors.
- Local header and API-key authentication are demonstration/development modes only.
- Production signing-key custody, rotation, revocation, and discovery require deployment-owner controls.
- Production authorization, rate limiting, audit operations, and incident response require additional hardening.

## Documentation assessment

Status: **IN PROGRESS for final freeze**

Completed:

- README, security model, local-versus-production trust guidance, protocol documentation, ADR-001, release checklist, validation record, and research/non-claim boundaries.

Required before tag decision:

- Remove obsolete PR and commit references from all release documents.
- Finalize the release notes against the merged candidate.
- Confirm the OpenAPI artifact is regenerated and reproducible.
- Confirm package, API, UI, certificate, CHANGELOG, and documentation version naming is consistent.
- Record final workflow URLs and exact candidate SHA.

## CI/CD assessment

Status: **PASS on the current PR candidate; final merged-main evidence pending**

Passing gates include:

- CI and release readiness
- Security Audit: Python audit, Explorer audit/build, Gitleaks, Docker federation
- Formal Specs / TLC
- Apalache symbolic verification
- Lean mechanized proofs
- Benchmarks

The release decision must use workflows run against one exact commit after PR #156 is merged and the freeze changes are complete.

## Known limitations

- This alpha is for protocol review, local validation, SDK/API exploration, controlled demonstrations, and limited pilots.
- ETS stores evidence metadata and cryptographic hashes by default, not raw evidence bytes.
- Local unsigned operation does not create a production trust anchor.
- RC consistency proofs must not be represented as final production-grade consistency auditing.
- SQLite is acceptable for alpha validation and controlled demos, not final hosted production storage.
- Hosted identity, signing, key management, tenancy, scaling, retention operations, and disaster recovery require further work.

## Deferred work

Deferred to beta or later:

- Production hosted control plane and multi-tenant operations.
- Automated signing-key lifecycle and external trust-anchor integration.
- Final consistency-proof protocol and cross-log auditing.
- ETS Edge appliance, durable offline runtime, adapters, synchronization, and operator interface.
- Production SLOs, observability, backup/restore, disaster recovery, and compliance operations.

## Final recommendation

**Conditional GO for technical alpha freeze.**

Do not create `v0.1.0-alpha` until:

1. PR #156 is independently approved and merged to `main`.
2. The freeze branch is based on the resulting `main` commit.
3. All required validation gates pass on one exact freeze commit.
4. The OpenAPI artifact and release documents are current and reproducible.
5. The validation record contains the exact SHA and workflow URLs.
6. An independent approval is submitted on the freeze PR.

No recommendation is made for beta or production deployment.