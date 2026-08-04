# ETS Hosted Validation Evidence

## Status

- Sprint: Hosted Readiness Sprint 5.
- Review state: Requires Human Review.
- Trust label: Real Analysis.
- Approval state: Approval Required before hosted use.
- Risk level: High until live Azure validation evidence is reviewed by deployment owners.
- Trace ID: `ets-hosted-readiness-5-2026-07-18`.

## Purpose

Hosted Readiness Sprint 5 defines the evidence record created by optional live
Azure validation. ETS remains the evidence, consent, trust, and authenticity
layer. SignalForge owns the Azure deployment and supplies runtime references
through repository secrets or managed environment variables.

## Sanitized Evidence Record

`HostedValidationEvidence` records:

- evidence ID;
- CI run ID;
- UTC creation time;
- trust label;
- approval state;
- trace ID;
- managed identity label;
- SHA-256 hash of the Azure key ID;
- SHA-256 hash of validated RBAC role names;
- SHA-256 hash of the signer test result;
- reviewer role;
- notes.

It must not contain bearer tokens, private keys, raw key IDs, tenant IDs, client
IDs, real vault URLs, raw customer data, or raw evidence payloads.

## Optional Live Validation Path

`tests/hosted/test_azure_live_signer.py` skips unless
`ETS_AZURE_HOSTED_TESTS_ENABLED=true` and all required Azure signer references are
provided by the CI/runtime environment. When enabled, it constructs the Managed
Identity signer, signs a synthetic tree head, and creates a sanitized validation
evidence object.

## Review Boundary

The evidence record is advisory until a deployment owner reviews:

- managed identity assignment;
- Key Vault or Managed HSM RBAC scope;
- signing key approval;
- Application Insights telemetry routing;
- incident response readiness;
- rollback plan.
