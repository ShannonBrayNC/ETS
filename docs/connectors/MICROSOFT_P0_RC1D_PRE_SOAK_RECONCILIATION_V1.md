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
4. the hardened Gateway durable-state probe with a healthy terminal delta checkpoint and synchronized synthetic marker; and
5. the protected Gateway relay/gap recovery with recovery passing, healthy post-recovery state, no terminal/retryable relay rows, and the synthetic marker reconciled.

The Q0 manifest, RC1B handoff, RC1C handoff, Gateway state run metadata, and Gateway recovery run metadata must all bind to the same exact source. Q0, RC1B, and RC1C must bind to the exact same `registry/repository@sha256:<digest>` image.

## Fail-closed boundaries

RC1D rejects any candidate when:

- a selected workflow run is not successful, manual, on `main`, at the exact candidate SHA, or from the expected workflow file;
- any retained artifact is missing or has an unexpected schema;
- Q0 did not pass the fixable HIGH/CRITICAL vulnerability policy or does not retain the expected SPDX SBOM reference;
- RC1B or RC1C is not live-qualified;
- a required replay, cursor, tombstone, throttle, gap, evidence-loss, revision-conflict, or restart predicate is false;
- the Purview subscription does not finish enabled;
- the Gateway durable-state probe is not at a healthy terminal delta checkpoint;
- the Gateway marker has pending, in-flight, retryable, or terminal relay state;
- the protected Gateway recovery did not mutate only the intended Gateway queue/runtime state and finish healthy;
- Graph drive subscriptions are configured or operated, a public callback is present, a broader Graph file permission is claimed, a reusable credential is retained, or a customer identifier is retained; or
- any selected evidence claims the soak clock already started.

## Successful handoff

A passing run emits `ets.live_microsoft.rc1d_pre_soak_candidate.v1` with:

- exact candidate source SHA and immutable image digest;
- all source workflow run IDs;
- Q0 supply-chain gate status;
- RC1B and RC1C live-qualified status;
- Gateway durable-state and recovery status;
- the ADR-009 Graph deferral boundary;
- credential/customer-identifier retention false;
- `pre_soak_reconciliation_passed=true`;
- `freeze_ready=true`;
- `candidate_frozen=false`; and
- `soak_clock_started=false`.

`freeze_ready=true` means the evidence set is eligible for the next protected freeze action. It is not itself a freeze claim.

## Next action

After a passing RC1D reconciliation, freeze only the exact source/image pair named by that artifact. Any source, image, identity, permission, configuration, Gateway state mutation outside the governed freeze procedure, or other candidate change requires a new Q0 publication and a new RC1D reconciliation.

Only after the freeze record is retained may the new governed 72-hour soak begin. The invalidated #479 attempt is never resumed or counted.
