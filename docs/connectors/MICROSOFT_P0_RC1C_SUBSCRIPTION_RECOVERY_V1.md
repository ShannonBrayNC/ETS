# Microsoft P0 RC1C Audit.General subscription recovery v1

Parent: #537
Live qualification: #539

## Purpose

This protected gate proves the bounded Microsoft Purview Management Activity lifecycle needed by
the P0 polling connector. It starts the exact `Audit.General` subscription without a webhook,
proves bounded content-list reachability, stops the subscription, and starts it again to prove
recovery. The final required state is `enabled`.

The workflow is manual, protected by `ets-azure-q1`, and pinned to one exact `main` source SHA and
one already-deployed private-ACR digest. Merging the workflow does not execute it. Dispatch also
requires the exact confirmation string `START_STOP_RESTART_AUDIT_GENERAL`.

The exact-source prerequisite order is defined by
[`MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md`](./MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md).

Microsoft documents that a stopped subscription cannot list or retrieve available content, that
content produced between stop and restart cannot be recovered through the subscription, and that
start requests require a fifteen-minute waiting period between calls. A first attempt requires the
pre-mutation state to be `absent`. A protected retry may begin `enabled` only after the operator
supplies both the prior protected failure run and a later, exact-source RC1C read-only preflight
run. The prior failure must prove a bounded mutation and recovery attempt. It may either prove the
subscription was restored `enabled`, or record the narrow `recovery_restore_failed`/`unknown`
outcome. The later preflight must independently prove the current live state is `enabled` without a
webhook, using the exact deployed source and image digest. Both artifacts are downloaded and
validated before Azure login. This avoids relying on stale state evidence or adding a stop-only
cleanup interval. For that reason this gate:

- requires `absent` on a first attempt or the fresh, post-failure verified `enabled` resume state;
- starts before content reachability only when the initial state is `absent`;
- waits the documented fifteen minutes before the recovery start when a first attempt had to start
  an absent subscription;
- skips the redundant initial start for an evidence-gated `enabled` resume;
- keeps the stop interval bounded to the one job execution;
- observes start and stop state transitions with bounded polling;
- avoids issuing a duplicate recovery start inside Microsoft's cooldown window;
- attempts a fail-closed restart if an assertion fails before a recovery start was attempted; and
- treats failure to restore `enabled` as `recovery_restore_failed`.

Reference:
[Office 365 Management Activity API reference](https://learn.microsoft.com/en-us/office/office-365-management-api/office-365-management-activity-api-reference).

## Exact protected boundary

The workflow rediscovers the deployment-authoritative live Gateway and requires:

- internal ingress, one replica, and the exact approved immutable image;
- one private ACR binding and exactly four attached user-assigned identities;
- distinct SharePoint/Core, directory, Purview, and pull identities;
- no Graph notification URL, client state, lifecycle timing, or health-policy configuration; and
- an exact tenant GUID plus the dedicated Purview client ID from deployed configuration.

The ephemeral Container Apps Job attaches only the pull-only ACR identity and the Purview runtime
identity. It mounts no Gateway state volume. Its managed-identity token must have the exact
`https://manage.office.com` audience, deployment tenant and application claims, exactly the
`ActivityFeed.Read` role, and no delegated scope.

## Lifecycle sequence

The job performs only these Office 365 Management Activity operations for `Audit.General`, always
with the deployment-authoritative publisher identifier and without a webhook:

1. list subscriptions and require `absent` or the verified restored `enabled` state;
2. if initially `absent`, start and require `enabled` with `webhook=null`; otherwise retain the
   evidence-gated `enabled` state without another start request;
3. list available content once, retaining only a bounded descriptor count;
4. for a first attempt only, wait the documented fifteen-minute start-request cooldown;
5. stop and require `absent` or `disabled`; and
6. start once and require the final state `enabled` with `webhook=null`.

Credential-bearing redirects fail closed. List, start, and content operations require HTTP 200.
The stop operation accepts HTTP 200 or an empty HTTP 204; every other successful status fails with
an operation-specific code. Responses are limited to 2 MiB, subscriptions to sixteen, and content
descriptors to 5,000. HTTP 429 and bounded server failures receive at most two retries, with
`Retry-After` capped at eight seconds for this controlled gate. This records only retry counts; it
does not claim the separate throttling-injection matrix.

## Evidence and nonclaims

The retained artifact includes only exact-source identity, image digest, workflow run ID, lifecycle
state enums, booleans, and bounded counters. It retains no token, tenant/application ID, content ID,
content URI, audit record, webhook, customer identifier, or raw Purview response.

A successful gate fixes:

- `purview_subscription_mutation_performed=true`;
- `subscription_final_state=enabled`;
- `purview_webhook_configured=false`;
- `graph_permission_mutation_performed=false`;
- `graph_subscription_operation_performed=false`;
- `rc1c_live_qualified=false`; and
- `soak_clock_started=false`.

Passing this gate is not completion of #539. Audit cursor progression, content retrieval and
canonicalization, replay/idempotency, throttling/backoff, gap recovery, and evidence-loss behavior
remain separate protected qualification steps before candidate freeze and the 72-hour soak.
