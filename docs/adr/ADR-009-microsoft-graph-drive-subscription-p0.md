# ADR-009: Defer Microsoft Graph drive subscriptions from the P0 release candidate

Status: Accepted
Date: 2026-08-23
Accepted through: #552 (`3e40e73b807d93f67d707cac567e154b8f37d60e`)
Parent: #537
Related: #539, #540, #541

## Context

The bounded P0 Microsoft profile already collects the approved SharePoint/OneDrive drive through
delta polling under `Sites.Selected`. The Graph lifecycle implementation can create, renew,
reconcile, and receive a `drives/{drive-id}/root` subscription, but it remains inactive because its
live permission and delivery boundary has not been approved.

Microsoft's current v1.0 subscription permission table lists application `Files.Read.All` for
creating a OneDrive for Business `driveItem` subscription. The list-subscriptions permission table
lists application `Files.ReadWrite.All` for that resource class, while its basic-scenario guidance
also says an application can retrieve subscriptions it created using the original resource
permission. Neither table lists `Sites.Selected` for the drive subscription operations.

Microsoft Graph can deliver change notifications through webhooks, Azure Event Hubs, or Azure Event
Grid. Event Hubs with Microsoft Entra RBAC avoids a publicly exposed Gateway callback and avoids the
deprecated shared-access-signature path. It does not reduce the Microsoft Graph resource permission
needed to create the drive subscription. It would also add a dedicated Event Hubs resource,
Microsoft Graph Change Tracking sender assignment, private consumer, checkpoint, and recovery
boundary that the current RC1 candidate has not composed or live-qualified.

Primary references:

- [Create subscription](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions?view=graph-rest-1.0)
- [List subscriptions](https://learn.microsoft.com/en-us/graph/api/subscription-list?view=graph-rest-1.0)
- [Change-notification delivery channels](https://learn.microsoft.com/en-us/graph/change-notifications-overview)
- [Azure Event Hubs delivery](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-event-hubs)
- [Webhook delivery](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)

## Decision

For the bounded P0 release candidate:

1. Keep SharePoint/OneDrive collection on the approved `Sites.Selected` delta-polling path.
2. Do not grant `Files.Read.All`, `Files.ReadWrite.All`, `Sites.Read.All`, or a Graph subscription
   role to the SharePoint/Core, directory, Purview, or GitHub deployment identities.
3. Keep Graph subscription creation, renewal, notification, and lifecycle configuration inactive.
4. Do not expose the private Gateway or add a public callback hostname for this release candidate.
5. Qualify Purview `Audit.General` polling independently under its dedicated
   `ActivityFeed.Read` identity.
6. Treat the existing Graph lifecycle implementation and deterministic tests as an unqualified,
   post-P0 capability. They do not count toward RC1 or soak evidence.
7. Evaluate Entra-RBAC Event Hubs as the preferred future delivery candidate before considering a
   public webhook. SAS/connection-string delivery is not an acceptable production fallback.

The project owner approved the exact #552 head after all checks passed, LanternProtocol supplied the
independent approval, and the governed exit language in #537, #539, and #541 was reconciled after
merge. The pre-soak gate remains blocked by the protected live RC1B, Purview, recovery, evidence
reconciliation, candidate-freeze, and soak requirements; accepting this ADR satisfies none of those
live gates.

## Re-entry gate for Graph subscriptions

Graph drive subscriptions can return to a release candidate only through a separate reviewed slice
that proves all of the following:

- a dedicated subscription identity with an explicitly approved resource-permission expansion;
- no permission fallback to the directory or Purview identities;
- exact `drives/{drive-id}/root` resource and `updated` basic notifications;
- Entra-RBAC delivery with no SAS, connection string, client secret, or public Gateway ingress;
- private consumer authentication, partition/checkpoint ownership, deduplication, replay, bounded
  retention, lifecycle notification handling, and gap reconciliation;
- exact-source, immutable-image, sanitized live evidence; and
- no claim that notification delivery proves Microsoft source truth or universal completeness.

If Event Hubs is not viable under those constraints, the project must make a new explicit decision;
it must not silently fall back to a public unauthenticated webhook or tenant-wide permission on an
existing runtime identity.

## Consequences

- P0 preserves the narrow approved drive boundary and private Gateway ingress.
- RC1B delta polling remains the authoritative SharePoint/OneDrive change-discovery mechanism.
- RC1C can proceed with Purview polling under its protected live qualification contract.
- Near-real-time drive notifications and Graph lifecycle evidence are deferred and cannot be
  represented as P0-qualified.
- The candidate freeze and 72-hour soak remain blocked by the still-required live RC1B, Purview,
  recovery, evidence-reconciliation, and governance gates.

## Validation

Architecture tests pin the exact P0 role allowlists, empty Graph lifecycle defaults, private Gateway
ingress, the RC1C explicit deferral flags, and the prohibition on SAS/public-callback fallback. They
do not perform a live Azure or Microsoft operation.
