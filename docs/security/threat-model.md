# ETS Local Threat Model

ETS v0.1.0-alpha proves that event metadata and content hashes were appended to
a local transparency log and can be verified with deterministic Merkle inclusion
proofs.

ETS does not prove the truth of the underlying evidence, does not store raw
evidence bytes, and does not yet provide production signing, OAuth/AuthN, or
cross-log consistency proofs.

## Implemented Local Controls

- SQLite persistence stores canonical event JSON, event hash, leaf hash, and log
  index metadata.
- Tenant and workspace headers scope reads, lists, and proof generation.
- Metadata redaction can remove common sensitive fields before hashing/storage.
- Tree heads are explicitly unsigned in local mode or Ed25519-signed when key
  material is configured.
- Production JWT mode rejects unauthenticated API requests and applies tenant
  and workspace claims as request scope.
- Consistency proofs verify tree-head growth for the current duplicate-last
  Merkle algorithm using a linear leaf-hash proof.
- Audit logs record operations without raw metadata or evidence content.

## Production Gaps

- External OIDC/JWKS integration is still roadmap work.
- Header-only tenant scoping is for local mode; production JWT mode should be
  backed by a real issuer and secret management.
- Consistency proofs are correct but linear, not compact.
- Replay and rollback protection depends on clients saving and comparing trusted
  tree heads.
