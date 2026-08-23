# Microsoft P0 hosted runtime composition v1

Parent: #543

## Purpose

The private hosted Gateway composes the bounded Microsoft P0 polling family as four explicit
connector instances. Each instance has a deployment-authoritative identity reference, source
principal, source identifier, runner, and durable checkpoint row.

| Instance suffix | Connector | Credential reference | Token audience |
| --- | --- | --- | --- |
| base instance | SharePoint/OneDrive metadata delta | `azure-mi://microsoft-graph` | Microsoft Graph `.default` |
| `.entra-users` | Entra users delta | `azure-mi://microsoft-graph/directory` | Microsoft Graph `.default` |
| `.entra-groups` | Entra groups delta | `azure-mi://microsoft-graph/directory` | Microsoft Graph `.default` |
| `.purview-audit-general` | Purview `Audit.General` | `azure-mi://office-365-management/purview` | Office 365 Management `.default` |

The directory instances intentionally share the directory UAMI and audience but do not share an
instance ID, source principal, runner, or checkpoint. SharePoint/Core and Purview use different
UAMIs. Runtime startup fails if the three configured managed-identity client IDs are not distinct or
if the SharePoint Microsoft application ID differs from the SharePoint/Core UAMI client ID.

## Server-owned composition

The deployment supplies only the three UAMI client IDs and the existing authoritative Microsoft,
ETS tenant/workspace, SharePoint drive, and source values. The runtime derives the additional
instance and source IDs with bounded suffixes and rejects an overlong result instead of truncating
or falling back.

At startup the runtime:

1. registers exactly three credential routes with fixed client ID and audience pairs;
2. creates separate SharePoint, Entra, and Purview tenant/profile objects;
3. validates all four connector instances against their checked-in manifests and adapters;
4. creates a durable runtime/checkpoint row for each missing instance;
5. rejects any persisted instance that differs from deployment-authoritative configuration; and
6. authorizes four distinct internal source principals in one immutable source registry.

No source payload can select a credential reference, client ID, audience, tenant, workspace,
source ID, Purview plan, content type, or publisher identifier.

## Scheduling and state isolation

Each connector instance owns a separate `GatewayConnectorCollectionRunner`. The scheduler passes
an explicit allowlist of the four composed instance IDs to the durable runtime store, so unrelated
management-plane instances cannot be leased accidentally. One cycle claims every due composed
instance at most once, releases each lease independently, persists each checkpoint with its own
compare-and-set revision, and then performs one bounded shared Core-relay drain.

Retry count, next-attempt time, last success, observation state, gap state, lease, and checkpoint
remain isolated by connector instance. The `/ready` response verifies all four deployment-owned
instances and reports their IDs without exposing identity client IDs, tenant identifiers,
credentials, tokens, source payloads, or opaque source cursors.

## Purview boundary

This slice composes only `Audit.General`, with `include_client_ip=false`.
It uses an empty service-specific allowlist. Additional Purview content types or fields require a
separate governed change and qualification.

Microsoft defines `PublisherIdentifier` as the tenant GUID of the vendor coding against the API.
For a client operating only against its own company tenant, Microsoft documents using that tenant
GUID. The hosted single-tenant profile therefore uses the exact configured Microsoft tenant ID and
adds `PublisherIdentifier` to content retrieval only after the source `contentUri` passes the
qualified origin/path/no-query checks.

References:

- [Office 365 Management Activity API reference](https://learn.microsoft.com/office/office-365-management-api/office-365-management-activity-api-reference)
- [Management Activity API troubleshooting](https://learn.microsoft.com/office/office-365-management-api/troubleshooting-the-office-365-management-activity-api)
- [Microsoft Graph delta query overview](https://learn.microsoft.com/graph/delta-query-overview)
- [Azure Container Apps managed identities](https://learn.microsoft.com/azure/container-apps/managed-identity)

## Evidence and nonclaims

This composition proves deterministic startup wiring, identity/audience separation, durable state
isolation, and bounded scheduler ownership. Unit and integration fixtures can prove independent
checkpoint progression without acquiring a live token.

It does not prove live token acquisition, Microsoft consent, source authorization, source
completeness, delta continuity, Purview subscription readiness, Graph webhook lifecycle, or
source-to-proof operation. It does not start live qualification, the 72-hour soak, or public
hostname activation.

The approved SharePoint-backed Microsoft Graph subscription lifecycle is composed by
[`MICROSOFT_P0_GRAPH_LIFECYCLE_COMPOSITION_V1.md`](./MICROSOFT_P0_GRAPH_LIFECYCLE_COMPOSITION_V1.md).
Protected live qualification under #539 and #540 still requires an approved immutable image and
explicit operator activation.

The first read-only #540 gate is defined by
[`MICROSOFT_P0_RC1B_LIVE_PREFLIGHT_V1.md`](./MICROSOFT_P0_RC1B_LIVE_PREFLIGHT_V1.md). It proves the
separated directory identity and durable users/groups polling posture without widening that
preflight into an RC1B qualification, candidate-freeze, or soak claim.

The first read-only #539 gate is defined by
[`MICROSOFT_P0_RC1C_LIVE_PREFLIGHT_V1.md`](./MICROSOFT_P0_RC1C_LIVE_PREFLIGHT_V1.md). It proves the
exact Purview identity/audience/role and `Audit.General` subscription-list boundary while keeping
Graph callback ingress, lifecycle configuration, permission widening, and durable subscription
state absent. ADR-009, approved through #552, makes that absence the P0 Graph deferral boundary;
Graph drive subscriptions remain a separately governed post-P0 capability.
