# Microsoft P0 soak readiness: evidence and operator checklist

## Current disposition (2026-10-22 15:12 UTC)

**NO-GO for launch.** This checklist and the companion offline checker do not deploy,
create cloud resources, change identities, inject faults, freeze a candidate, or start a soak.
A passing offline evidence lint is not live verification or launch permission.

Main was `406a2cf5daddd9805b2ba3c40eb6f6d517bf3fa3` after #921 and #922 merged.
This is a reference snapshot, not the final candidate: these coordinator
fixes must land first, with required CI on the actual final head. Source cannot change
between Q0 publication, deployment, all qualification/recovery evidence and soak completion.

The retained attempt `microsoft-p0-soak-33273802197` is invalidated, with only 2/72
observations. Its last successful observation was 2026-08-29 21:52:31.986023Z;
it was invalidated at 2026-08-30 00:26:20.718963Z after 153.812 minutes (>110).
Source: https://github.com/ShannonBrayNC/ETS/issues/541#issuecomment-5465739581
Do not reuse its source/image or resume its observation count.

The confirmed proximate failure is missing governed success within 110 minutes.
The available issue record does not distinguish delayed/dropped scheduling, queued
runners, environment approval wait, or child-run latency. Historical run/job creation,
start/completion and queue timestamps are required to establish that root cause.
Do not label it an Azure failure without that evidence.

## Coordinator defects addressed by the local patch

- Read every issue-comment page. First-page-only state becomes stale after 100
  comments, including invalidations or fresh attempts beyond that page.
- Recheck the 110-minute gap at completed observation time, before incrementing
  success_count. Previously a run starting just below the threshold could count
  success after its child canaries took it beyond the threshold.
- Explain inactive scheduled no-ops in the Actions summary. Existing green
  `skipped_no_active_attempt` artifacts mean no canaries ran, not readiness or progress.

These defects are independently reproducible; they are not asserted to have caused
that historical gap. The patch preserves the hourly cron, all safety gates, permissions,
resource behavior, and 72-hour / 72-observation / 110-minute rules.

## Freeze prerequisites, in order

1. **Source:** select the full final main SHA only after all intended changes merge and
   required CI passes. Read main again immediately before every governed action.
2. **Identities and role readback:** use existing separated SharePoint/Core, directory,
   Purview and ACR-pull identities. Verify directory Graph roles are exactly
   `User.Read.All` + `Group.Read.All`; Purview Office 365 Management audience/role is
   exactly `ActivityFeed.Read`; SharePoint retains `Sites.Selected` negative boundary.
   Verify identity lifecycle `Main` for runtime identities, `None` for ACR pull, exact
   scope mapping, distinct identity assignment and no public callback/Graph subscription.
   Missing or drifted roles require a separate reviewed change, not automatic repair.
3. **Q0 and deployment:** retain successful exact-source manual
   `hosted-azure-q0-image.yml` manifest, immutable private ACR digest, SPDX SBOM,
   provenance and fixable HIGH/CRITICAL vulnerability result. Verify Core and Gateway
   actually use that digest, private ingress, single replicas, exact configuration.
   No mutable tag or local synthetic test can establish deployed identity.
4. **RC1B:** successful exact-source/image `live-microsoft-rc1b-preflight.yml`,
   `rc1b_live_qualified=true`, healthy users/groups and passing OneDrive/cursor/tombstone/
   replay/throttle/expired-cursor/evidence-loss matrix.
5. **RC1C recovery:** read-only preflight followed by the explicitly approved protected
   `Audit.General` recovery, ending enabled, with its isolated polling fault matrix passed.
   Existing enabled subscriptions need the workflow's permitted recovery/resume evidence;
   never stop one merely to manufacture the required initial state.
6. **Post-recovery live RC1C:** a later preflight independently observes the real mounted
   Gateway runtime after recovery completed: checkpoint revision >=1, last success,
   healthy observation, closed gap, zero retry, inactive lease, enabled subscription,
   no webhook. Synthetic recovery success is insufficient.
7. **Gateway chain:** healthy terminal delta checkpoint and synchronized synthetic
   marker -> bounded one-marker fault stage with verified immutable Core copy ->
   exact-stage recovery -> independent healthy post-state. Strictly ordered, same
   source/image/marker, zero pending/in-flight/retryable/terminal queue state globally
   and for marker. All fault mutation happens before freeze.
8. **RC1D v2:** successful `live-microsoft-rc1d-pre-soak-reconciliation.yml`, same SHA,
   exact immutable image, with all selected run IDs and underlying retained artifacts;
   `freeze_ready=true`, `candidate_frozen=false`, `soak_clock_started=false`,
   `rc1c_live_health_verified=true`. RC1D v1 and old-source handoffs are ineligible.
9. **Cadence and permission:** obtain explicit approved scope/cost for the cloud
   preparation and observation jobs, recovery mutation and new soak. Confirm an operator
   can respond before the gap deadline. A schedule expression alone is not evidence of
   reliable completion cadence. No blanket cloud-cost permission is assumed.

## Reproducible offline check

Download the selected RC1D `reconciliation.json` and API metadata for every run ID in
it using existing authorized read access. Keep raw evidence private. Create bundle.json:

    {"reconciliation": <unmodified reconciliation.json>,
     "runs": {"<run ID>": <unmodified GitHub run metadata>, ...}}

Include the RC1D run itself, Q0, RC1B, RC1C recovery, later RC1C health, Gateway baseline,
fault-stage, recovery, and later Gateway state. Then, from the repo root:

    python scripts/check_microsoft_soak_readiness.py bundle.json --source <full-final-main-SHA>

Exit 2 / NO_GO means missing or contradictory evidence. Exit 0 / PASS_OFFLINE_ONLY
checks exact-source metadata, artifact predicates and strict ordering only. It never
claims artifact authenticity, live readback, identity/config stability or launch authorization.
A hand-edited test fixture is not evidence. Independently retrieve the original artifacts
and verify the protected RC1D run and the current live state before using the result.

## Cadence safeguards before approving start

Keep the hard 110-minute continuity limit. Record expected completion interval, observed
runner/approval/child duration and an operational response budget. A concrete target is
an alert at 70 minutes since last governed success, leaving 40 minutes to diagnose before
invalidation. This alert target is advisory, not a changed acceptance threshold.

Do not dispatch the current manual coordinator to "top up" an active attempt: manual
workflow_dispatch is a new-attempt path, not a resume operation. A redundant observation
trigger would need a separately reviewed implementation and source requalification.
Before freeze, review whether the existing hourly trigger has adequate demonstrated margin;
if not, design and test a read-only observer/trigger separately. Do not silently increase
job frequency or cost. No approved watchdog or guaranteed cadence is claimed here.

During an authorized soak, assess the issue's latest paginated state and actual successful
observation artifact timestamps, not just workflow conclusion. Observe source/image identity,
all four child proofs and continuity. At >110 minutes or any failed governed condition,
retain invalidation and stop; no backdating, threshold widening or resuming invalid attempts.
Exit requires both >=72 elapsed hours and >=72 successful governed observations.

## Exact missing live readback for this readiness pass

- Final intended source after all changes and its required CI.
- New Q0 supply-chain artifacts/digest and deployed Core/Gateway image/config readback.
- Current exact managed-identity/app-role/scope boundary evidence.
- Fresh same-source RC1B, RC1C recovery and later live-health artifacts.
- Fresh complete Gateway baseline/fault/recovery/post-state chain.
- New RC1D v2 reconciled artifact and current-source workflow metadata.
- Historical queue/run/child timing to distinguish the original cadence failure mechanism.
- Explicit resource/cost/recovery scope and new-attempt authorization plus cadence owner.

Even workflows called "read-only preflight" create/delete ephemeral Azure Container Apps
jobs. They are not pure infrastructure-read actions and were not dispatched in this pass.
