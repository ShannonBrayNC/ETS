# ETS Complete Solution Requirements

ETS is the Evidence Transparency System: an open protocol and reference
implementation for turning digital assertions, file metadata, AI outputs, and
workflow records into independently verifiable evidence.

This document is the checked-in RC requirements baseline. It keeps the current
alpha implementation honest while separating local protocol work from future
hosted platform work.

## v0.1 Reference Scope

- Deterministic canonical JSON and SHA-256 event hashing.
- EvidenceEvent v1 metadata contract.
- Append-only event store with in-memory and SQLite providers.
- Merkle inclusion proofs and simplified linear consistency proofs.
- Optional Ed25519 tree-head signing with explicit unsigned local mode.
- FastAPI service with `/api/v1/*` routes and RC lab compatibility routes.
- Offline verifier CLI, SDK facade, and certificate generation.
- Explorer UI for browsing, proof fetch, and proof verification.
- Experiments for fork simulation, omission detection, and benchmark output.

## Safety Boundaries

- ETS stores event metadata and hashes by default, not raw evidence bytes.
- Local unsigned tree heads are not production trust anchors.
- HS256 bearer auth is an RC validation policy; production OIDC/JWKS uses
  fail-closed RS256 bearer verification with issuer/audience checks.
- Consistency proofs are intentionally simplified for RC6 and documented as a
  roadmap area before production claims.
- No real PII, secrets, private keys, or attorney-client material belong in
  fixtures or committed artifacts.

## Remaining Release Gates

1. Complete hosted identity operations around the implemented JWKS/OIDC hook,
   including issuer ownership, key rotation runbooks, and incident response.
2. Promote consistency proofs from simplified linear validation to a formal
   compact proof only if the public protocol requires it; RC6 documents the
   current non-compact policy in `docs/spec/rfc/ETS-RFC-0005-CONSISTENCY.md`.
3. Run Docker and federation validation in an environment with Docker available.
4. Complete IP and public release checklist review before tagging a public v0.1.
5. Add PostgreSQL-backed hosted storage only after core protocol tests are stable.

## Done Definition

A feature is complete only when the canonical core implementation is used by API,
CLI, SDK, reports, and Explorer; tests cover success and failure behavior; docs
state the implemented trust boundary; and CI can run lint, type checks, tests,
and frontend build.
