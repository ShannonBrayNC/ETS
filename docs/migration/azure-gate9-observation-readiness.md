# Azure migration Gate 9 — destination-only observation and source-retirement readiness

Tracking: #792, #766, #758.

Gate 9 is the final **authorization** gate before destructive source retirement. It is
not itself a deletion workflow.

A successful Gate 9 readiness run may set:

- `source_decommission_authorized=true`;
- `source_decommission_execution_performed=false`;
- `subscription_cancellation_performed=false`.

Actual Azure resource deletion, identity/RBAC cleanup, Key Vault retirement, storage
retirement, and subscription cancellation remain a separately reviewed destructive
operation.

## Evidence model

Gate 9 requires two distinct successful Gate 8 public-cutover verification runs:

1. a baseline run after public cutover;
2. a later observation run.

The two runs must remain bound to the same fenced source manifest and the same
production Lantern site manifest. This proves destination-only operation was observed
more than once without allowing a blind time-only rule to authorize retirement.

Gate 9 also requires:

- active destination Core and Gateway replicas;
- no known source-Azure identifier in active destination runtime configuration;
- a successful historical-key offline-verification workflow run;
- a protected operations-readiness record whose SHA-256 is supplied explicitly;
- explicit evidence references for monitoring, alerts, cost controls, certificate
  monitoring, backup/readback qualification, destination-native deployment automation,
  zero source management/data-plane use, retained rollback evidence, and the permanent
  prohibition on stale-source writer rollback.

## Operations-readiness record

Copy `docs/migration/gate9-ops-readiness-template.json` to protected operator storage
outside Git. Do not modify the checked-in template into a production attestation.

Set a field to `true` only after its evidence has been independently reviewed. Every
required boolean must have a non-empty `evidence_refs` entry. References should point
to durable non-secret evidence such as Azure resource identifiers, workflow run IDs,
retained report digests, or operator-controlled audit records.

The Gate 9 workflow requires both the protected relative path and its exact SHA-256.
It refuses a modified or incomplete record.

## Runtime authorization phrase

The observation/readiness workflow requires exactly:

`GATE9_SOURCE_DECOMMISSION_READINESS_AUTHORIZED`

This phrase authorizes production-read-only observation and creation of the Gate 9
readiness artifact. It does **not** authorize destructive source retirement.

## Stale-source rollback boundary

After Gate 7C transferred writer authority to the destination, rollback must never
mean automatically reactivating the old source writer. Gate 9 preserves rollback data
for forensic/recovery purposes, but recovery must proceed from retained evidence,
backups, or a newly reconciled deployment.

## Required destructive follow-on boundary

A later retirement execution must consume the successful Gate 9 readiness artifact,
retain its source-manifest binding, perform cleanup in dependency order, and run a
post-retirement smoke test before #758 can be closed.

That destructive workflow must have a distinct authorization phrase and must not be
triggered merely because this Gate 9 readiness implementation is merged.
