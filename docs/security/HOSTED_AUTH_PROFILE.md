# ETS Hosted Auth Profile

This profile defines the recommended hosted authentication posture for ETS alpha deployments.

## Summary

Hosted ETS deployments should use JWKS-backed RS256 bearer-token validation through:

```text
ETS_AUTH_MODE=production_jwks
```

Local development modes are useful for laptops and demos, but they should not be used as hosted security boundaries.

## Supported auth modes

| Mode | Intended use | Hosted recommendation |
|---|---|---|
| `local_header` | Local development and unprotected test runs | Do not use for hosted deployments |
| `local_api_key` | Local protected demos | Do not use for hosted deployments |
| `production_jwt` | HS256 validation for controlled validation | Avoid for hosted multi-tenant deployments |
| `production_jwks` | RS256 validation using trusted public keys | Recommended hosted profile |

## Required hosted settings

A hosted profile should set:

```text
ETS_AUTH_MODE=production_jwks
ETS_AUTH_JWKS_URL=https://issuer.example/.well-known/jwks.json
ETS_AUTH_ISSUER=https://issuer.example
ETS_AUTH_AUDIENCE=ets-api
```

Alternatively, `ETS_AUTH_JWKS_JSON` may be used for controlled environments where the trusted JWKS is supplied by deployment configuration instead of a URL.

Do not commit environment files containing real issuer-specific values, tenant IDs, tokens, or credentials.

## Validation behavior

The hosted profile should fail closed when:

- the bearer token is missing
- the token is expired
- the signing key is not present in the configured JWKS
- the token algorithm is not RS256
- issuer validation is configured and `iss` does not match
- audience validation is configured and `aud` does not match
- tenant or workspace claims conflict with request headers

## Tenant and workspace scoping

When token claims include `tenant_id` or `workspace_id`, those values become the effective request scope. If a caller also supplies `X-ETS-Tenant` or `X-ETS-Workspace`, those headers must match the token claims.

Scope mismatches should not leak cross-tenant event details. ETS should return a generic not-found response for mismatched event reads or proof requests.

## Local mode boundary

Local auth modes are for development only:

- `local_header` trusts `X-ETS-Tenant` and `X-ETS-Workspace` headers.
- `local_api_key` protects local routes with a shared demo key.

Neither mode proves caller identity in a hosted environment.

## Release checklist

Before hosting ETS, confirm:

- `ETS_AUTH_MODE` is set to `production_jwks`.
- issuer and audience validation are configured.
- local auth modes are disabled.
- JWKS source ownership is documented.
- key rotation responsibility is documented.
- API examples use placeholders only.
- no local secrets are committed.

## Related tests

`tests/integration/test_api_security_persistence.py` covers JWKS behavior, including valid RS256 tokens and wrong-audience rejection. Additional hosted deployment tests should continue expanding missing-token, expired-token, wrong-issuer, wrong-key, and malformed-token scenarios.
