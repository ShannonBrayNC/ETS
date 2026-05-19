# ETS Security Model

## Threat Model

ETS protects the integrity of evidence metadata and content hashes after append.
It does not prove that the external evidence is true, complete, or lawfully
obtained.

## Trust Boundaries

- ETS stores event metadata, event hashes, leaf hashes, and tree metadata.
- ETS does not store raw evidence bytes.
- Clients must keep trusted tree-head checkpoints to detect rollback or
  equivocation.

## Tenant And Workspace Isolation

Local mode can scope requests with `X-ETS-Tenant` and `X-ETS-Workspace`.
`production_jwt` mode uses bearer-token `tenant_id` and `workspace_id` claims as
the authoritative request scope. Header values must match token claims.

## Metadata Sensitivity

Metadata can leak sensitive facts even when evidence bytes are not stored.
Redaction profiles run before hashing and storage:

- `none`
- `basic_pii`
- `strict`

## Content Hash Privacy

Content hashes can reveal whether a known file is present. Operators should avoid
using ETS as a public oracle for sensitive evidence sets.

## Replay And Equivocation Risks

Signed tree heads reduce forgery risk, but clients still need checkpoint
retention and consistency proof verification to detect rollback or equivocation.

## Key Management

Ed25519 signing requires `ETS_SIGNING_PRIVATE_KEY_HEX` and
`ETS_SIGNING_PUBLIC_KEY_ID`. Private keys must be stored in a managed secret
store outside source control. Key rotation and retired-key validation remain
future production work.

## API Authentication

Supported modes:

- `local_header`: development only.
- `local_api_key`: shared local key via `X-ETS-API-Key`.
- `production_jwt`: HS256 bearer validation with required `exp`.

External OIDC/JWKS and Entra ID validation are production roadmap items.

## Authorization Model

All event list/read/proof routes apply tenant/workspace scope. Unauthorized
cross-scope access returns a generic not-found envelope and emits an audit event.

## Audit Event Model

Audit events are structured JSON logs. They include operation, result, tenant,
workspace, event ID, reason, and correlation ID when available. They must not
include raw evidence bytes, request bodies, or sensitive metadata values.

## Rate Limiting

Rate limiting is not implemented in-process. Production deployments should place
ETS behind an API gateway or service mesh rate limiter.

## Input Limits

- Event JSON body: 256 KB.
- Metadata and external refs: 64 KB canonical JSON each.
- IDs and event types: 128 characters.
- Hash algorithm: `sha256` only.

## Logging Rules

Do not log raw evidence, request bodies, tokens, API keys, or unredacted
metadata. Audit logs should be treated as sensitive operational records.

## Secure Deployment Profile

Minimum production-like profile:

- `ETS_STORAGE_PROVIDER=sqlite` for alpha durability, PostgreSQL in future.
- `ETS_AUTH_MODE=production_jwt`.
- `ETS_SIGNING_MODE=ed25519` or `production`.
- Redaction profile selected intentionally.
- HTTPS termination, rate limiting, backup/restore, and log retention configured
  outside the app.

## Production Gaps

- OIDC/JWKS validation.
- Managed signing keys and rotation.
- Compact consistency proofs.
- PostgreSQL provider.
- Rate limiting middleware.
- Incident response automation.
