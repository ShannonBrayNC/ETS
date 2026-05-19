# ETS Security Controls

Implemented RC controls:

- request body and metadata size limits;
- tenant/workspace scoping through headers or authenticated claims;
- deterministic redaction profiles;
- structured audit logging without raw evidence content;
- RS256 JWKS bearer auth for production OIDC integration;
- explicit unsigned versus Ed25519 signing policy;
- deterministic API error envelopes.

Future hosted controls:

- OIDC/JWKS issuer operations and rotation runbooks;
- rate limiting and abuse protection;
- managed signing keys;
- PostgreSQL row-level tenant isolation;
- external witness or anchoring policy.
