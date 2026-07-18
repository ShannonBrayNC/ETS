# ETS Hosted Auth Operations

## Status

- Sprint: Hosted Readiness Sprint 1.
- Review state: Requires Human Review.
- Trust label: Real Analysis.
- Approval state: Approval Required before hosted use.
- Risk level: High if exposed publicly without these controls.
- Trace ID: `ets-hosted-auth-ops-2026-07-18`.

## Purpose

Hosted ETS deployments must fail closed and must not rely on local development
auth modes. ETS remains the evidence, consent, trust, and authenticity layer;
SignalForge should provide the reusable Azure deployment layer for hosted
operation.

## Required Hosted Profile

Hosted deployments must use:

```text
ETS_AUTH_MODE=production_jwks
ETS_AUTH_JWKS_URL=<managed OIDC issuer JWKS URL from deployment configuration>
ETS_AUTH_ISSUER=<managed OIDC issuer URL from deployment configuration>
ETS_AUTH_AUDIENCE=<ETS API audience from deployment configuration>
```

Use Azure App Configuration, Key Vault references, or GitHub Actions secrets for
deployment configuration. Do not commit issuer-specific values, tenant IDs,
client IDs, secrets, tokens, or private keys.

## Fail-Closed Requirements

The API must reject:

- missing bearer tokens;
- malformed JWTs;
- expired tokens;
- not-yet-valid tokens;
- wrong issuer;
- wrong audience;
- wrong key ID;
- unsupported token algorithms;
- unsupported JWKS key use or algorithm;
- non-string tenant, workspace, or subject claims;
- tenant or workspace claims that conflict with request headers.

Authentication failures must return a generic `ETS_AUTH_REQUIRED` error and must
emit audit/telemetry suitable for incident review without logging token values.

## Azure Operations Posture

Recommended Azure posture:

- Microsoft Entra ID or another managed OIDC issuer owns token issuance.
- JWKS is loaded from the issuer discovery/JWKS endpoint, not from committed JSON.
- Managed Identity accesses Key Vault/App Configuration at runtime.
- Application Insights records auth failure count, issuer/audience mismatch
  categories, and correlation IDs without recording bearer tokens.
- Deployment runbooks identify issuer owner, API audience owner, key rotation
  owner, incident commander, and reviewer.

## Evidence and Approval Records

Each hosted-auth configuration change should create or reference an ETS evidence
record containing:

- evidence ID;
- configuration version hash;
- issuer and audience labels, not secret values;
- trust label: `Requires Human Review` until approved;
- approval state;
- reviewer identity or role;
- deployment trace ID;
- rollback plan hash;
- incident response runbook version.

## Validation

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_api_security_persistence.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
