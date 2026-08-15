# ETS Azure Signer And Hosted Telemetry

## Status

- Sprint: Hosted Readiness Sprint 2.
- Review state: Requires Human Review.
- Trust label: Real Analysis.
- Approval state: Approval Required before hosted use.
- Risk level: High if hosted signing or auth telemetry is deployed without owner review.
- Trace ID: `ets-hosted-readiness-2-2026-07-18`.

## Purpose

Hosted ETS deployments need a production signer abstraction, JWKS rotation
behavior, and Application Insights-compatible security telemetry. This document
keeps ETS as the evidence, consent, trust, and authenticity layer while leaving
Azure resource provisioning to SignalForge.

## Azure Signer Abstraction

`AzureKeyVaultTreeHeadSigner` represents an Azure Key Vault or Managed HSM signer
without embedding Azure credentials in ETS core. Azure Key Vault does not provide
Ed25519/EdDSA keys, so the hosted Azure profile uses an RSA key with `PS256`.
ETS canonicalizes the tree head, computes its SHA-256 digest, and delegates only
that digest to the Managed Identity-backed Azure signing client.

Required hosted behavior:

- private key material remains in Key Vault or Managed HSM;
- the configured Azure key must support RSA-PSS/SHA-256 signing;
- `signature_alg=ps256` identifies the hosted Azure signing profile;
- `public_key_id` identifies vault URL, key name, and concrete key version;
- non-HTTPS vault URLs are rejected;
- empty key names are rejected;
- a missing key version is resolved to a concrete current version before signing;
- signing failures emit hosted security telemetry;
- key rotations preserve old public key metadata for historical verification;
- caller-supplied DER RSA public key material can independently verify retained
  PS256 tree-head signatures without private-key access.

Local ETS Ed25519 signing remains a separate supported profile and is not
relabelled as Azure Key Vault signing.

## JWKS Refresh And Cache Behavior

Hosted JWKS auth should cache trusted keys for a bounded interval and refresh
when:

- the cache expires;
- a token references an unknown key ID;
- issuer-owned key rotation publishes a new signing key.

If refresh fails, ETS must fail closed with `ETS_AUTH_REQUIRED` and emit
Application Insights-compatible auth telemetry. ETS must never fall back to local
auth modes in hosted deployments.

## Application Insights-Compatible Telemetry

Hosted security telemetry is emitted as structured JSON with:

- `name` such as `ets.auth.rejected` or `ets.signing.failed`;
- `time` in UTC;
- `severityLevel` such as `Warning` or `Error`;
- `customDimensions.component=ets-api`;
- correlation ID when available;
- auth mode, signing log ID, and sanitized reason.

Telemetry must not include bearer tokens, private keys, raw PII, customer
secrets, or raw evidence payloads.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_api_security_persistence.py tests\unit\test_tree_head_signing_envelope.py tests\unit\test_hosted_telemetry.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```
