# Hosted Auth And Signing Incident Response Runbook

## Status

- Sprint: Hosted Readiness Sprint 1.
- Review state: Requires Human Review.
- Trust label: Real Analysis.
- Approval state: Approval Required before hosted use.
- Trace ID: `ets-hosted-auth-signing-ir-2026-07-18`.

## Triggers

Use this runbook when ETS detects or suspects:

- repeated `ETS_AUTH_REQUIRED` spikes;
- issuer, audience, or key ID mismatch spikes;
- JWKS fetch or parse failures;
- signing failures in production mode;
- suspected token signing key compromise;
- suspected tree-head signing key compromise;
- tenant/workspace claim mismatch attempts;
- unexpected unsigned tree heads in hosted mode.

## Immediate Containment

1. Assign an incident commander and human reviewer.
2. Preserve Application Insights logs, ETS audit records, latest tree heads, and
   external anchors.
3. If signing integrity is in doubt, stop writes or place ETS in maintenance mode.
4. If auth integrity is in doubt, disable affected clients or issuer keys through
   the managed issuer.
5. Do not delete logs, anchors, or historical tree heads.

## Evidence Capture

Create an ETS incident evidence record with:

- evidence ID;
- trust label: `Requires Human Review`;
- approval state: `Approval Required`;
- incident trace ID;
- affected tenant/workspace labels where applicable;
- telemetry query hash;
- current tree head hash;
- latest external anchor ID;
- containment decision;
- reviewer role.

Do not include bearer tokens, private keys, raw PII, customer secrets, or private
evidence payloads in the incident record.

## Recovery

1. Validate issuer/JWKS ownership.
2. Rotate compromised auth or signing keys.
3. Verify current and previous tree heads with trusted public key metadata.
4. Compare latest tree head to latest external anchor.
5. Request consistency proof from anchored tree size to current tree size when
   the log has advanced.
6. Re-enable writes only after approval.
7. Publish a superseding incident evidence record with final status.

## Post-Incident Review

Document:

- root cause;
- timeline;
- affected evidence IDs;
- affected tenants/workspaces;
- control failures;
- follow-up tasks;
- reviewer approval or rejection;
- whether any public notice or customer notice is required.
