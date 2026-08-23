# Microsoft P0 Graph lifecycle composition v1

Parent: #543
Live qualification: #539

## Purpose

The hosted Gateway now composes the existing Microsoft Graph subscription client, durable
subscription-state store, bounded webhook ingress, resource-notification committer, and Microsoft
operational posture for the one approved SharePoint-backed drive. This is runtime wiring for later
protected live qualification; it is not a live tenant mutation or public-ingress authorization.

## Fixed subscription boundary

The deployment supplies the approved SharePoint drive ID. The runtime derives the Graph resource as
`drives/{percent-encoded-drive-id}/root`; an environment value cannot select a different resource.
The subscription requests only the `updated` change type and uses basic notifications. Microsoft
documents that OneDrive for Business subscriptions support only the root folder and that drive-root
notifications support only `updated`.

The same exact HTTPS endpoint is used for resource and lifecycle notifications:
`/gateway/v1/microsoft/graph`. The configured URL must have that path, no query, no fragment, no user
information, and the default HTTPS port. The SharePoint/Core UAMI acquires the Graph `.default`
audience through only `azure-mi://microsoft-graph`; directory and Purview identities cannot be used as
fallbacks.

References:

- [Create a Microsoft Graph subscription](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions?view=graph-rest-1.0)
- [Microsoft Graph subscription resource and lifetime](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0)
- [Receive Graph change notifications through webhooks](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)
- [Renew a Microsoft Graph subscription](https://learn.microsoft.com/en-us/graph/api/subscription-update?view=graph-rest-1.0)

## Lifecycle convergence

One worker-cycle action converges the durable state for the exact tenant/resource pair:

| Durable state | Bounded action | Resulting gap state |
| --- | --- | --- |
| absent | create | `none` |
| active, outside renewal window | no token acquisition | unchanged |
| active, inside renewal window | renew | preserved |
| `reauthorization_required` | reauthorize, then renew if due | preserved |
| removed or expired | create replacement and atomically distrust the old ID | `possible` |
| disabled | fail closed for governed operator review | unchanged |
| throttled | honor the bounded `Retry-After` time in-process | unchanged |

The requested lifetime defaults to 28 days and is bounded between one hour and Microsoft's current
42,300-minute OneDrive maximum. The default renewal window is 24 hours and must be shorter than the
requested lifetime. Subscription ID, exact tenant/resource, clientState hash, expiration, status,
and gap state survive restart in `microsoft-graph-subscriptions.db`. The clientState value and access
token do not.

Replacement never clears possible loss. A removed or expired subscription is therefore not treated
as continuous observation merely because creation of a new subscription succeeds. Gap closure still
requires the governed SharePoint delta reconciliation path in #539.

## Webhook and evidence boundary

The hosted FastAPI application installs the existing bounded Graph webhook route only when the full
lifecycle configuration is present. Endpoint validation echoes only the qualified opaque validation
token. Notification admission verifies the exact subscription ID, tenant, and constant-time
clientState hash before accepting lifecycle state or minimized resource metadata.

Resource notifications use a distinct internal principal but the same deployment-authoritative
source ID as the approved SharePoint drive, so its durable Core-sync backlog remains inside the same
source-scoped posture. They enter the existing Gateway local append plus durable Core-sync queue
before a committed response is returned. Lifecycle notifications update operational subscription/gap
state only and are never promoted to ETS evidence.

## Deployment configuration

Graph lifecycle activation is all-or-none:

- `ETS_GATEWAY_GRAPH_NOTIFICATION_URL` — exact HTTPS webhook URL;
- `ETS_GATEWAY_GRAPH_CLIENT_STATE` — server-owned trust secret, at most 128 characters;
- `ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON` — governed operational thresholds;
- `ETS_GATEWAY_GRAPH_SUBSCRIPTION_LIFETIME_SECONDS` — bounded desired lifetime; and
- `ETS_GATEWAY_GRAPH_SUBSCRIPTION_RENEWAL_WINDOW_SECONDS` — bounded proactive renewal window.

The Bicep template accepts clientState as a secure parameter and exposes it to the container only by
Container Apps `secretRef`. It is not an output, regular environment value, SQLite field, log field,
or evidence attribute. Partial lifecycle configuration and a renewal window greater than or equal to
the lifetime fail before runtime activation.

The checked-in hosted template deliberately retains `external: false`. Enabling public or protected
Microsoft callback ingress, supplying these activation values, and exercising creation/validation/
renewal remain explicit #539 operator actions against an approved immutable image.

## Evidence and nonclaims

Deterministic tests cover first creation, no-op token avoidance, renewal, reauthorization, atomic
replacement, throttle deferral, restart-safe state, exact URL/resource derivation, secret handling,
and hosted composition. They use fake clients and tokens.

This slice does not acquire a live token, create or delete a live subscription, validate a public
endpoint, activate a public hostname, prove notification delivery, close a gap, start live
qualification, or freeze a candidate. It does not start the 72-hour soak.
