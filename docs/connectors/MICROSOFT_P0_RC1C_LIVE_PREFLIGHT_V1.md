# Microsoft P0 RC1C read-only live preflight v1

Parent: #537
Live qualification: #539

## Purpose

This gate proves the dedicated Purview managed identity, Office 365 Management audience,
exact `ActivityFeed.Read` role, and bounded `Audit.General` polling composition before any
subscription mutation. It also proves that the Microsoft Graph drive-subscription boundary deferred
by ADR-009 has not been activated accidentally.

The preflight is manual, protected by the `ets-azure-q1` environment, pinned to one exact
`main` source SHA and one already-deployed private-ACR digest, and implemented as an ephemeral
Azure Container Apps Job. Merging the workflow does not execute it.

The identity, Q0 publication, and private deployment prerequisites are ordered by
[`MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md`](./MICROSOFT_P0_LIVE_RELEASE_SEQUENCE_V1.md).

## Permission correction

Microsoft's current Graph documentation lists `Files.Read.All` as the application permission for
creating a OneDrive for Business `driveItem` change-notification subscription and
`Files.ReadWrite.All` for listing that subscription class. Neither operation lists
`Sites.Selected`. The existing SharePoint/Core UAMI is deliberately bounded to the approved site's
`Sites.Selected` grant.

RC1C therefore MUST NOT assume that the polling permission also authorizes Graph subscription
lifecycle. This slice does not add `Files.Read.All`, `Files.ReadWrite.All`, `Sites.Read.All`,
`Subscription.Read.All`, or any other Graph role. Microsoft supports Event Hubs delivery with Entra
RBAC and no public webhook, but that delivery option does not reduce the drive subscription
permission and requires a separately qualified consumer boundary.

ADR-009 approved the second option for P0: retain polling/delta, qualify Purview independently, and
defer the Graph subscription slice. Entra-RBAC Event Hubs is the preferred future delivery candidate,
but it requires a new post-P0 permission review and separately qualified private consumer boundary.
The project owner and LanternProtocol approved #552, and the #537/#539/#541 issue contracts were
reconciled after merge:

- [`ADR-009-microsoft-graph-drive-subscription-p0.md`](../adr/ADR-009-microsoft-graph-drive-subscription-p0.md)

References:

- [Create a Microsoft Graph subscription](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions?view=graph-rest-1.0)
- [List Microsoft Graph subscriptions](https://learn.microsoft.com/en-us/graph/api/subscription-list?view=graph-rest-1.0)
- [Receive Graph change notifications through webhooks](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)
- [Receive Graph change notifications through Azure Event Hubs](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-event-hubs)
- [Office 365 Management Activity API reference](https://learn.microsoft.com/en-us/office/office-365-management-api/office-365-management-activity-api-reference)

## Exact live assertions

The workflow discovers exactly one live Gateway by its deployment-authoritative base connector
instance ID and requires:

- the exact approved immutable image digest;
- private ingress and one replica;
- one ACR binding and exactly four attached UAMIs;
- distinct SharePoint/Core, directory, Purview, and pull identities;
- pull identity lifecycle `None` and Purview job identity lifecycle `Main`;
- the existing Gateway state share mounted query-only by the preflight; and
- no Graph notification URL, clientState, lifecycle timing, or health-policy environment
  configuration.

The ephemeral job obtains a token only for `https://manage.office.com/.default` from the exact
Purview UAMI. It validates, without retaining the token, that:

- the audience is exactly `https://manage.office.com`;
- the tenant and application claims match deployment configuration;
- the application role list is exactly `ActivityFeed.Read`; and
- no delegated `scp` claim is present.

It then performs only:

```text
GET /api/v1.0/{tenant}/activity/feed/subscriptions/list
    ?PublisherIdentifier={tenant}
```

The response is bounded to 2 MiB and sixteen entries. Because the UAMI is dedicated to the P0
`Audit.General` profile, duplicate or different content-type subscriptions fail closed. A Purview
webhook also fails closed; RC1 uses polling.

An absent `Audit.General` subscription is a valid preflight result. Starting it is a separate,
explicit Microsoft mutation. The workflow reports only `absent`, `enabled`, or `disabled` and
never retains a webhook address, tenant ID, application ID, token, audit record, content URL, or
publisher identifier.

## Durable-state boundary

The job opens `connector-runtime.db` with SQLite `mode=ro` and `PRAGMA query_only=ON`. It requires
the exact derived `.purview-audit-general` instance, credential reference, content type, empty
service-field allowlist, and `include_client_ip=false` profile. Runtime checkpoint, retry, health,
gap, and lease facts are emitted only as sanitized booleans and counters; they are observations,
not pass predicates for this pre-mutation gate.

If `microsoft-graph-subscriptions.db` exists, it is also opened query-only and must contain zero
subscription rows. Stale durable Graph subscription state before callback authorization fails the
preflight.

## Evidence and nonclaims

The retained artifact contains only the exact source SHA, image digest, workflow run ID, bounded
booleans/counters, and the Purview subscription status enum. It fixes:

- `graph_callback_ingress_external=false`;
- `graph_lifecycle_configuration_present=false`;
- `graph_subscription_scope_decision=deferred_from_p0`;
- `graph_subscription_scope_decision_record=ADR-009`;
- `graph_subscription_deferred_from_p0=true`;
- `graph_future_delivery_profile=azure_event_hubs_entra_rbac`;
- `graph_permission_mutation_performed=false`;
- `graph_subscription_operation_performed=false`;
- `rc1c_live_qualified=false`; and
- `soak_clock_started=false`.

Passing this gate is not completion of #539. It does not start or stop a Purview subscription,
retrieve audit content, create/list/renew/delete a Graph subscription, validate a callback,
exercise lifecycle recovery, claim source completeness, freeze a candidate, or begin the soak.
