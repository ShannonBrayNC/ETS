# Microsoft P0 RC1D-bound 72-hour soak v1

Parent: #541
Implementation issue: #579

## Purpose

This contract governs the Microsoft P0 72-hour soak after a successful RC1D pre-soak reconciliation. It replaces the invalidated #479 hardcoded source/image binding. The #479 attempt is historical only and is never resumed or counted.

The coordinator is `.github/workflows/live-m365-source-to-proof-soak.yml`.

## Start prerequisites

Do not start this workflow until all of the following have completed on one unchanged `main` SHA and immutable image:

1. Hosted Azure Q0 immutable image publication is successful and its retained supply-chain evidence passes.
2. The private Core/Gateway deployment is bound to that exact source/image tuple.
3. RC1B read-only/live qualification passes with `rc1b_live_qualified=true` and its cursor/tombstone/replay/throttle/expired-cursor/evidence-loss matrix passing.
4. RC1C read-only preflight passes.
5. The protected RC1C `Audit.General` start/stop/restart recovery and polling fault matrix passes, finishes `enabled`, and produces `rc1c_live_qualified=true`.
6. The Gateway durable-state probe is healthy and reconciled.
7. The Gateway relay/gap recovery passes and leaves no failed relay state.
8. RC1D pre-soak reconciliation passes and emits `ets.live_microsoft.rc1d_pre_soak_candidate.v1` with `freeze_ready=true`, `candidate_frozen=false`, and `soak_clock_started=false`.

Do not publish Q0 until all source changes required for the soak coordinator have merged. A source change after Q0 or RC1D invalidates that exact-source handoff.

## Initial manual start

Dispatch `live-m365-source-to-proof-soak.yml` from the exact unchanged `main` SHA using:

- `rc1d_workflow_run_id`: the exact successful RC1D reconciliation run;
- `start_confirmation=START_72_HOUR_MICROSOFT_P0_SOAK`;
- `marker`: the bounded synthetic SharePoint marker retained for the candidate; and
- `restart_active=false` for a normal new attempt.

The coordinator validates that the RC1D run is a completed successful `workflow_dispatch` run from `main`, at the coordinator SHA, and from `.github/workflows/live-microsoft-rc1d-pre-soak-reconciliation.yml`. It downloads only the exact retained RC1D artifact and derives the frozen source, image, and digest from that artifact. Browser input or an arbitrary source/image string cannot establish the freeze.

The first successful governed observation records `candidate_frozen=true` and `soak_clock_started=true` in the #541 issue-backed state. If the initial canaries fail, the attempt does not claim a successful soak start.

## Hourly governed observations

The workflow is scheduled hourly. A scheduled run proceeds only when #541 contains an active state with schema `ets.live_microsoft.p0_soak.state.v1`.

Each observation uses only non-destructive/read-only live canaries:

1. **SharePoint source-to-proof** — the parameterized `live-m365-soak-source-to-proof-observation.yml` re-proves the frozen source/image, metadata-only Graph boundary, exact-version evidence, inclusion proof, duplicate suppression, durable retention, and delta recovery without notification delivery.
2. **RC1B Entra/OneDrive** — `live-microsoft-rc1b-preflight.yml` re-proves the dedicated directory identity, bounded users/groups delta state, OneDrive polling matrix, Core synchronization, and `Sites.Selected` negative boundary.
3. **RC1C Purview read-only** — `live-microsoft-rc1c-preflight.yml` re-proves the exact `ActivityFeed.Read` identity, `Audit.General` subscription visibility, enabled state, healthy polling posture, and Graph deferral boundary.
4. **Gateway state** — `live-sharepoint-state-boundary-probe.yml` re-proves healthy terminal delta state, no open gap, and clean relay state.

The soak coordinator never dispatches `live-microsoft-rc1c-subscription-recovery.yml`. Start/stop/restart subscription mutation and destructive/fault recovery belong before freeze only.

## Frozen boundary

After the first successful observation, the following are immutable for the attempt:

- exact `main` SHA;
- immutable private-ACR image digest;
- RC1D workflow run ID and evidence set;
- Microsoft managed identities and app-role assignments;
- tenant/workspace scope mapping;
- Graph deferral boundary;
- Gateway/Core deployment configuration; and
- synthetic qualification marker.

A change to source, image, identity, permission, scope, deployment configuration, or other out-of-contract state invalidates the attempt. In particular, a scheduled coordinator run whose `GITHUB_SHA` differs from the frozen source records `source_drift_after_freeze` and stops.

## Monitoring and failure rules

The attempt requires:

- at least 72 elapsed hours;
- at least 72 successful governed observations; and
- no observation gap greater than 110 minutes.

The attempt invalidates on a failed coordinator run, frozen-source drift, monitoring-gap breach, child canary failure, candidate/image mismatch, Purview subscription not enabled, an open collection gap, failed Gateway relay state, Graph subscription/public-callback appearance, or any public evidence that retains customer identifiers or reusable credentials.

An invalidated attempt is not resumed. A replacement attempt requires an explicit manual dispatch with a validated RC1D handoff. `restart_active=true` explicitly invalidates an existing active attempt before starting the replacement.

## Privacy and security boundary

Public coordinator state and artifacts retain only bounded workflow/run references, source/image identifiers, timestamps, pass/fail posture, and safe aggregate status. They do not retain raw Microsoft payloads, customer identifiers, bearer tokens, managed-identity tokens, connection strings, SAS values, private keys, or reusable credentials.

Graph drive subscriptions, notification delivery, broader Graph file permissions, and public Gateway callback ingress remain deferred under ADR-009 for this P0 candidate.

## Fleet separation

The Fleet C3E Entra application bootstrap is not a prerequisite for this Microsoft P0 soak. Fleet portal application registration may proceed separately and must not mutate the frozen M365 runtime identities, permissions, source, image, or configuration during an active attempt.

## Exit

When both the 72-hour duration and 72-successful-observation minimums are met without invalidation, the coordinator records the passed state and closes #541 as completed. The retained source/image pair and hourly canary evidence become the Microsoft P0 soak qualification record.
