# Microsoft P0 RC1B read-only live preflight v1

Parent qualification: #540

## Purpose

This protected workflow is the first live gate after the separated Microsoft identity and hosted
runtime composition in #543. It proves that the deployed private Gateway is using one exact
immutable image, that the dedicated directory identity can reach only the bounded Entra users and
groups delta surfaces, and that both deployment-owned Entra connector instances have reached a
healthy durable delta checkpoint and synchronized committed observations to Core.

The preflight is deliberately read-only against Microsoft Graph. It creates and removes only an
ephemeral Azure Container Apps job. Passing it is not completion of #540, candidate freeze, or soak
entry.

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

## Remaining #540 gates

A successful preflight establishes identity separation, live delta reachability, initial terminal
checkpoint progression, local commitment, Core synchronization, and a clean operational posture.
It does not establish:

- controlled user or group tombstone/deletion observation;
- repeated-page and restart replay/idempotency under a governed canary;
- throttling/backoff behavior against the protected live deployment;
- invalid/expired cursor reconciliation and gap closure;
- complete OneDrive revision/recovery evidence for the new candidate;
- Microsoft source truth or universal tenant completeness; or
- eligibility for the #541 candidate freeze and 72-hour soak.

Those remaining scenarios require explicit protected operator approval and must complete before
#540 can close. Destructive or fault scenarios occur before candidate freeze. The soak itself uses
only non-destructive canaries.

## Evidence boundary

On success the workflow uploads one sanitized JSON handoff and comments on #540 with the exact
source SHA, immutable image digest, and boolean outcomes. On failure it retains a fail-closed
artifact that sets `preflight_passed=false`, `rc1b_live_qualified=false`, and
`soak_clock_started=false` without copying raw job logs into public evidence.

No live preflight is performed merely by merging these assets.
