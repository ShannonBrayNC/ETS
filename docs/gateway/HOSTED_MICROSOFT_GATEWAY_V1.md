# Hosted Microsoft Gateway R1

Status: P0 hosted deployment candidate  
Issues: #389, #390, #309

## Purpose

This profile composes the already-qualified Gateway connector, durable queue, Microsoft
credential, Core relay, and operational-posture boundaries into one Azure Container Apps
runtime. It is the deployment prerequisite for the EchoMedia SharePoint source-to-proof
qualification and the 72-hour Microsoft soak.

It does not change ETS canonicalization, Merkle, proof, or verification semantics.

## Runtime boundary

The hosted profile:

- runs exactly one Gateway replica because local runtime state is SQLite-backed;
- mounts `/var/lib/ets` on a durable Azure Files volume;
- stores the Azure Files account key in Key Vault and does not place it in container
  environment variables;
- uses one user-assigned runtime identity for Microsoft Graph and ETS Core token
  acquisition;
- uses a separate pull-only identity for the private ACR image;
- uses production JWKS management authentication and server-derived ETS scope;
- polls one approved SharePoint drive through the existing
  `microsoft.sharepoint.onedrive_delta` adapter;
- commits normalized candidates through the existing Gateway local-append and durable
  synchronization queue;
- relays those exact locally committed events to ETS Core over HTTPS using a scoped
  managed-identity bearer;
- preserves connector checkpoint, retry, gap, queue, and local event state across
  Container App revision restart.

The management ingress remains internal. Public Microsoft Graph webhook exposure is a
separate #390 qualification step and must not be inferred from this profile.

## Deployment-authoritative identity

The following values are fixed by deployment configuration and must not be supplied by a
collection request:

- ETS tenant and workspace;
- connector instance ID;
- authoritative Gateway source ID;
- Microsoft tenant ID;
- managed-identity application/client ID;
- approved SharePoint drive ID;
- Core resource scope;
- management JWKS issuer/audience/tenant and app-to-ETS-scope mapping.

On restart, if the persisted connector instance differs from the deployment-authoritative
instance, startup fails closed. Configuration drift is not silently rewritten.

## Durable state

The profile retains these SQLite databases on the mounted state volume:

- `gateway-events.db` — immutable local Gateway event state;
- `gateway-sync.db` — bounded restart-safe Core synchronization queue;
- `connector-runtime.db` — instance, checkpoint, retry, gap, and audit state;
- `microsoft-graph-subscriptions.db` — Graph subscription operational state when #390
  posture support is enabled.

Raw SharePoint document content is not retained by this runtime. The existing SharePoint
adapter commits minimized metadata and source-reported fingerprints only.

## Health and readiness

`/health` reports process liveness. `/ready` verifies the persisted connector instance and
local event store are readable and returns 503 when the background worker has raised an
unhandled runtime exception. Microsoft source health, subscription lifecycle, collection
lag, queue backlog, and gaps remain in the policy-bound Microsoft posture endpoint rather
than being collapsed into generic liveness.

A healthy readiness response is not a source-completeness claim and is not ETS
cryptographic verification.

## Microsoft posture activation

The management posture route is installed only when both
`ETS_GATEWAY_GRAPH_SUBSCRIPTION_JSON` and
`ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON` are supplied. This allows #389 to deploy the
Gateway before #390 creates the real Graph subscription while preventing a synthetic
subscription from being represented as live health.

After #390 provisions the EchoMedia subscription, both values must describe that exact
subscription and the approved governed health policy. The provider then combines:

- live SharePoint adapter health;
- durable connector runtime;
- exact Graph subscription state;
- source-scoped synchronization queue posture; and
- the governed Microsoft operational-health policy.

The resulting model continues to assert `verification_claimed=false`,
`source_truth_claimed=false`, and `completeness_claimed=false`.

## Collection and retry

The worker uses the durable runtime lease before each collection pass. Successful pages
release their checkpoint only after local append and durable synchronization enqueue.
Known gaps remain open across later successful collection until an explicit reconciliation
decision closes them. Retryable source failures use bounded exponential scheduling; after
the configured consecutive retry budget is exhausted the runtime opens a collection gap
rather than silently continuing as healthy.

Each cycle also drains a bounded Core relay batch. Core relay validates exact local event
identity/hash and upstream acknowledgement before marking a queue row synchronized.

## Sequence to the live soak

1. Merge and qualify this hosted Gateway composition.
2. Publish a new immutable image from that final source commit.
3. Deploy Core and Gateway from the same approved image/source release identity.
4. Provision the Gateway managed identity with EchoMedia `Sites.Selected` access to the
   designated SharePoint site.
5. Create/register the real Microsoft Graph subscription and enable the exact posture
   configuration.
6. Complete #390 source-to-proof qualification, including notification/delta recovery.
7. Freeze source SHA, image digest, connector instance, ETS scope, Microsoft tenant and
   subscription, and health-policy profile.
8. Run probe 1 of the governed 72-hour soak. The clock begins only at that successful
   first retained probe.
