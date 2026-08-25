# Microsoft P0 RC1B read-only live preflight v1

Parent qualification: #540

## Purpose

This protected workflow is the first live gate after the separated Microsoft identity and hosted
runtime composition in #543. It proves that the deployed private Gateway is using one exact
immutable image, that the dedicated directory identity can reach only the bounded Entra users and
groups delta surfaces, and that both deployment-owned Entra connector instances have reached a
healthy durable delta checkpoint and synchronized committed observations to Core. After that live
read-only proof passes, the same exact image must pass an isolated directory/drive polling fault
matrix before the workflow may set `rc1b_live_qualified=true`.

The preflight is deliberately read-only against Microsoft Graph. It creates and removes only an
ephemeral Azure Container Apps job. Passing it is not completion of #540, candidate freeze, or soak
entry.

The identity, Q0 publication, and private deployment prerequisites are ordered by
[`MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md`](./MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md).

## Protected invocation

Run `.github/workflows/live-microsoft-rc1b-preflight.yml` from `main` in the protected
`ets-azure-q1` environment with:

- `image_source_sha`: the exact approved `main` SHA used to publish the live image;
- `container_image`: the exact deployed private-ACR `registry/repository@sha256:<digest>`; and
- `connector_instance_id`: the deployment-authoritative base instance ID.

The workflow requires `image_source_sha == GITHUB_SHA`, verifies the deployed Gateway uses the
same image, keeps ingress internal, requires a single replica, and rejects any identity assignment
set other than these four exact user-assigned managed identities:

1. SharePoint/Core runtime identity;
2. directory-only runtime identity;
3. Purview-only runtime identity; and
4. ACR pull-only identity.

The three runtime client IDs must be distinct. The pull identity must remain distinct from every
runtime identity. The ephemeral job attaches only the directory identity with `Main` lifecycle and
the ACR identity with `None` lifecycle, so token acquisition cannot fall back to the SharePoint or
Purview identities.

## Read-only proof

The job obtains a Microsoft Graph `.default` token through the exact directory UAMI and makes three
bounded requests:

1. `GET /v1.0/users/delta?$select=id&$top=1`;
2. `GET /v1.0/groups/delta?$select=id&$top=1`; and
3. `GET /v1.0/drives/{approved-drive-id}/root?$select=id`.

The users and groups requests must return JSON delta pages with an exact Graph continuation URL.
The drive request must return `403`, proving the directory identity did not inherit or fall back to
the SharePoint/Core `Sites.Selected` identity.

The probe never writes a directory object, group, user, drive item, subscription, permission, or
connector state. Response payloads and access tokens remain in process memory only.

Primary contracts:

- [Microsoft Graph user delta](https://learn.microsoft.com/en-us/graph/api/user-delta?view=graph-rest-1.0)
- [Microsoft Graph group delta](https://learn.microsoft.com/en-us/graph/api/group-delta?view=graph-rest-1.0)
- [Managed identities in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)
- [Microsoft.App jobs template reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/jobs)

## Durable-state proof

The job mounts the live single-replica Gateway state volume and opens the databases in SQLite
query-only mode. Both derived instances must have:

- a terminal delta cursor and positive checkpoint revision;
- a recorded successful collection;
- zero retry count;
- `healthy_observation` state;
- no open gap or active lease;
- at least one locally committed observation; and
- at least one synchronized Core queue record with no pending or failure state for that instance.

Only public-safe booleans, checkpoint revisions, and the cursor kind are retained. User IDs, group
IDs, names, tenant IDs, drive IDs, identity IDs, source payloads, access tokens, and reusable
credentials are not written to the retained artifact or issue comment.

## Isolated directory/drive fault matrix

A successful preflight establishes identity separation, live delta reachability, initial terminal
checkpoint progression, local commitment, Core synchronization, and a clean operational posture.
The same ephemeral job then exercises the shipped Entra users/groups and SharePoint/OneDrive delta
adapters, HTTP retry policy, and Gateway commit path with synthetic non-customer fixtures and
isolated temporary state. Every bounded predicate must pass:

- users, groups, and OneDrive cursor progression and tombstone normalization;
- Entra and OneDrive replay idempotency through the Gateway commit boundary;
- both Microsoft clients honoring an HTTP `Retry-After` response;
- checkpoint withholding under throttling and partial/evidence-loss commit failure; and
- expired-cursor gap detection that retains the last durable checkpoint.

The matrix does not call Microsoft Graph, mutate the live tenant, or write the live Gateway
database. It qualifies the exact shipped adapter/runtime behavior; it does not establish
Microsoft source truth or universal tenant completeness. A passing protected handoff sets
`rc1b_live_qualified=true` and `soak_clock_started=false`. #540 closure, shared candidate evidence
reconciliation, the #541 candidate freeze, and 72-hour soak entry remain separate gates.

## Evidence boundary

On success the workflow uploads one sanitized JSON handoff and comments on #540 with the exact
source SHA, immutable image digest, live read-only outcomes, all isolated matrix predicates, and
`rc1b_live_qualified=true`. On failure it retains a fail-closed
artifact that sets `preflight_passed=false`, `rc1b_live_qualified=false`, and
`soak_clock_started=false` without copying raw job logs into public evidence. An in-container
exception hook emits only an allow-listed `failure_code`; the workflow retrieves that marker even
when the Container Apps execution status is `Failed`, validates its exact public-safe shape, and
deletes the private raw log before uploading evidence. If no valid marker is available, the
workflow retains only `bounded_failure_marker_unavailable`. Both paths use the same sanitized
`ets.live_microsoft.rc1b_preflight_failure.v2` evidence shape.

The directory runtime boundary classifies only bounded posture. It distinguishes unavailable
state, an open collection gap, a pending retry/degraded observation, an invalid checkpoint,
incomplete checkpoint initialization, another unhealthy observation, and an active collection.
The ordering prioritizes completeness risk before retry and initialization posture. It never
retains the affected collection family, checkpoint or retry counts, revisions, cursor values,
timestamps, lease values, identifiers, payloads, or error text.

The Core synchronization boundary classifies only bounded queue posture. It distinguishes an
unavailable queue, terminal failure, retryable failure, pending/in-flight backlog, invalid state,
and absence of a synchronized users/groups observation. Matching uses the exact minimized
`capture.source_id`; counts, event identifiers, payloads, acknowledgements, timestamps, and error
text are never copied into public evidence.

No live preflight is performed merely by merging these assets.
