# ETS Azure Key Custody Posture

## Status

- Sprint: Hosted Readiness Sprint 1.
- Review state: Requires Human Review.
- Trust label: Real Analysis.
- Approval state: Approval Required before hosted use.
- Risk level: High if production signing keys are filesystem or environment-only secrets.
- Trace ID: `ets-azure-key-custody-2026-07-18`.

## Purpose

ETS tree heads need production key custody before hosted trust claims. Local
unsigned mode and environment-provided Ed25519 private keys are acceptable for
local validation, but hosted deployments should use Azure Key Vault or Managed
HSM through the SignalForge platform layer.

## Required Production Signing Behavior

- `ETS_SIGNING_MODE=local_unsigned` is development/demo only.
- `ETS_SIGNING_MODE=production` must fail closed unless a production signer is
  configured.
- Production signers must keep private key material outside the repository and
  outside committed environment files.
- Key IDs must be stable and published with tree heads.
- Rotation must preserve historical verification by retaining trusted public key
  metadata for older tree heads.
- Revocation must not rewrite historical evidence.

## Azure Key Custody Recommendation

Preferred hosted posture:

1. Store signing keys in Azure Key Vault or Managed HSM.
2. Grant ETS runtime access using Managed Identity.
3. Use Key Vault key versions as signer provenance.
4. Publish `public_key_id` values that identify key name and version without
   exposing private key material.
5. Emit Application Insights telemetry for signing success/failure counts and
   correlation IDs.
6. Store key rotation approval and verification evidence in ETS.

## Rotation Evidence Requirements

Every rotation should capture:

- old key ID and new key ID;
- rotation approval state;
- reviewer role;
- first signed tree head using the new key;
- last accepted tree head using the old key;
- verification command output hash;
- rollback plan hash;
- incident response runbook version.

## Incident Boundaries

If a signing key is suspected compromised:

- stop hosted writes or move the service to maintenance mode;
- preserve current tree heads, anchors, audit logs, and signing telemetry;
- revoke or disable the compromised key according to Azure operations policy;
- rotate to a new key only after human approval;
- publish a superseding incident evidence record;
- do not rewrite historical tree heads or evidence events.
