# Microsoft P0 RC1D pre-soak reconciliation v1

Parent: #537

Release gate: #541

## Purpose

RC1D reconciles the retained Microsoft P0 qualification evidence into one exact-source, immutable-image handoff that is eligible for candidate freeze. It does not itself freeze a candidate and it does not start the 72-hour soak.

Graph drive subscriptions remain deferred under ADR-009. RC1D must not configure, operate, or represent them as qualified, and no public Gateway callback or broader Graph file permission is part of this candidate.

The protected workflow is `.github/workflows/live-microsoft-rc1d-pre-soak-reconciliation.yml`.

## Required exact-source evidence

Every selected workflow run must be a completed successful `workflow_dispatch` run from `main` whose `head_sha` equals the RC1D reconciliation source SHA. The gate consumes exactly:

1. the hosted Azure Q0 image publication manifest, SPDX SBOM reference, vulnerability gate, and immutable private-ACR digest;
2. the RC1B protected handoff with `rc1b_live_qualified=true` and the users/groups/OneDrive cursor, tombstone, replay, throttling, expired-cursor, and evidence-loss matrix passing;
3. the RC1C protected `Audit.General` recovery handoff with `rc1c_live_qualified=true`, final subscription state `enabled`, and the polling/restart/fault matrix passing;
4. a later post-recovery RC1C read-only preflight proving the deployed live Purview durable runtime has converged: `Audit.General` remains enabled, checkpoint and last-success state are present, `purview_healthy_observation=true`, `purview_gap_open=false`, retry count is zero, no lease is active, and the Graph-deferral/evidence-safety boundary remains intact;
5. a bounded Gateway relay fault-stage artifact that itself binds to a successful healthy Gateway baseline state probe, proves the synchronized synthetic marker already has an immutable Core copy, and stages exactly one marker terminal row plus `collection_gap` without mutating Core;
6. the exact-stage Gateway relay/gap recovery artifact, bound to item 5, proving exactly that staged marker was verified and reconciled, the collection gap closed, and healthy state restored; and
7. a fresh post-recovery Gateway durable-state probe proving a healthy terminal delta checkpoint, synchronized synthetic marker, closed gap, zero retry state, and no failed relay rows.

The post-recovery RC1C live-health run must occur after the selected RC1C subscription-recovery run. It is query-only: it does not edit SQLite state, restart the subscription, configure a webhook, broaden Graph permissions, or manufacture a health claim. The shipped Gateway worker must first drive the real Purview collection path to a successful terminal page; the read-only preflight then independently observes the resulting durable state.

The mandatory Gateway ordering is baseline state → fault stage → recovery → post-recovery state. The baseline run ID is retained by the fault-stage artifact; the stage, recovery, and post-state run IDs are explicit RC1D inputs.

The Q0 manifest, RC1B handoff, RC1C recovery handoff, post-recovery RC1C live-health handoff, Gateway fault stage, Gateway recovery, and post-recovery Gateway state run metadata must all bind to the same exact source. Q0, RC1B, RC1C recovery, RC1C live-health, fault-stage, and recovery evidence bind to the exact same `registry/repository@sha256:<digest>` image.

## Live Purview state semantics

The post-recovery RC1C read-only preflight is directly RC1D-consumable only when all of these are true:

- the dedicated Purview managed identity acquires the exact Office 365 Management audience with exactly `ActivityFeed.Read`;
- the `Audit.General` subscription is present and `enabled` with no webhook;
- the deployment-authoritative Purview connector instance exists with a checkpoint revision >= 1 and last-success state present;
- `purview_healthy_observation=true`, `purview_gap_open=false`, retry count is zero, and no lease is active;
- Graph durable subscription state, lifecycle configuration, external callback ingress, permission mutation, and subscription operations remain absent; and
- raw Purview payloads, customer identifiers, and reusable credentials are not retained in public evidence.

This live-state proof closes the distinction between the RC1C synthetic polling fault matrix and the actual deployed Gateway durable runtime. `rc1c_live_qualified=true` from the recovery exercise is necessary but no longer sufficient for RC1D freeze readiness.

## Gateway state semantics

A successful protected Gateway state probe is directly RC1D-consumable. It must fail closed unless all of these are true:

- a checkpoint exists with revision >= 1 and last-success state present;
- the checkpoint is the terminal delta checkpoint for the dedicated SharePoint/OneDrive delta collector; Graph may represent that cursor opaquely rather than exposing a literal `$deltatoken` string;
- retry count is zero, no next attempt is scheduled, observation is `healthy_observation`, `gap_open=false`, and no lease is active;
- the bounded marker exists in immutable local evidence and a synchronized queue row is correlated to it by immutable `event_id`; and
- pending, in-flight, retryable, and terminal counts are zero globally and for the marker.

This keeps the standalone probe and RC1D contract identical: a green state probe cannot later be rejected by RC1D for a stricter interpretation of the same retained fields.

## Fail-closed boundaries

RC1D rejects any candidate when:

- a selected workflow run is not successful, manual, on `main`, at the exact candidate SHA, or from the expected workflow file;
- the post-recovery RC1C live-health run did not occur after the RC1C subscription-recovery run;
- the Gateway baseline → fault stage → recovery → post-state run order is invalid;
- any retained artifact is missing or has an unexpected schema;
- Q0 did not pass the fixable HIGH/CRITICAL vulnerability policy or does not retain the expected SPDX SBOM reference;
- RC1B or RC1C is not live-qualified;
- the live Purview durable runtime lacks a checkpoint or last-success state, is not `healthy_observation`, has an open gap, has retry state, or retains an active lease;
- a required replay, cursor, tombstone, throttle, gap, evidence-loss, revision-conflict, or restart predicate is false;
- the Purview subscription does not finish enabled or is not still enabled in the post-recovery live-health proof;
- the Gateway baseline or post-recovery state is not at a healthy terminal delta checkpoint with synchronized marker evidence;
- the fault stage did not begin from a healthy queue, did not prove the immutable Core marker copy, staged more or less than one marker terminal row, introduced retryable state, retained sensitive identifiers, or mutated Core;
- the recovery artifact is not bound to the supplied exact fault-stage run, does not recover exactly one marker, leaves terminal/retryable rows, fails to close the gap, or fails to restore healthy observation/upstream state;
- Graph drive subscriptions are configured or operated, a public callback is present, a broader Graph file permission is claimed, a reusable credential is retained, or a customer identifier is retained; or
- any selected evidence claims the soak clock already started.

## Successful handoff

A passing run emits `ets.live_microsoft.rc1d_pre_soak_candidate.v2` with:

- exact candidate source SHA and immutable image digest;
- all Q0, RC1B, RC1C recovery, post-recovery RC1C live-health, Gateway baseline, fault-stage, recovery, and post-state workflow run IDs;
- Q0 supply-chain gate status;
- RC1B and RC1C live-qualified status;
- `rc1c_live_health_verified=true`;
- `gateway_fault_stage_verified=true`;
- `gateway_recovery_verified=true`;
- `gateway_durable_state_healthy=true` for the post-recovery state;
- the ADR-009 Graph deferral boundary;
- credential/customer-identifier retention false;
- `pre_soak_reconciliation_passed=true`;
- `freeze_ready=true`;
- `candidate_frozen=false`; and
- `soak_clock_started=false`.

`freeze_ready=true` means the evidence set is eligible for the next protected freeze action. It is not itself a freeze claim. RC1D v1 handoffs are historical and are not eligible to start a new soak under this contract.

## Next action

After a passing RC1D reconciliation, freeze only the exact source/image pair named by that artifact. Fault injection and recovery are complete before freeze and must not run during the soak. Any source, image, identity, permission, configuration, Gateway state mutation outside the governed freeze procedure, or other candidate change requires a new Q0 publication and a new RC1D reconciliation.

Only after the freeze record is retained may the new governed 72-hour soak begin. The invalidated #479 attempt and any failed pre-start attempt are never resumed or counted.
