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
- uses the SharePoint/Core UAMI only for the approved SharePoint drive, Graph subscription
  lifecycle, and ETS Core token acquisition;
- uses a directory UAMI only for Graph users/groups delta and a Purview UAMI only for the Office
  365 Management Activity audience;
- uses a separate pull-only identity for the private ACR image;
- uses production JWKS management authentication and server-derived ETS scope;
- polls one approved SharePoint drive, Entra users/groups, and Purview `Audit.General` through four
  isolated connector instances;
- commits normalized candidates through the existing Gateway local-append and durable
  synchronization queue;
- relays those exact locally committed events to ETS Core over HTTPS using a scoped
  managed-identity bearer;
- preserves connector checkpoint, retry, gap, queue, and local event state across
  Container App revision restart.

The management ingress remains internal. Graph lifecycle and webhook code are composed when their
complete server-owned configuration is present, but the checked-in Bicep retains `external: false`.
Public/protected callback exposure is a separate #539 qualification step and must not be inferred
from this profile.

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

The Core app-to-ETS-scope map establishes **where** the Gateway application may act; it is
not itself permission to create evidence. The exact Gateway managed-identity service
principal must also hold the Core application's `evidence_producer` app role so its
app-only bearer contains the server-recognized producer role. Hosted Core rejects evidence
ingestion from an authenticated principal that lacks `evidence.create`, even when its
tenant/workspace mapping is otherwise valid.

The live deployment gate must therefore prove all three identity bindings before relay is
qualified:

1. the token application/client ID is the exact pre-created Gateway runtime identity;
2. that client ID maps to the deployment-authoritative ETS tenant/workspace in Core; and
3. the app-only token carries `evidence_producer`, yielding `evidence.create` and no
   connector-administration authority by implication.

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

The management posture route is installed only when the exact Graph notification URL, secret-backed
clientState, and governed health policy are configured together. The runtime derives the approved
`drives/{drive-id}/root` resource, creates or renews its subscription through the SharePoint UAMI,
and reads the exact durable subscription for posture. Operator-supplied subscription identity/state
JSON is not trusted.

The provider combines:

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

1. Merge and qualify this hosted Gateway composition and its hosted evidence-create guard.
2. Publish a new immutable image from that final source commit.
3. Pre-create the exact Gateway runtime identity and grant its service principal the Core
   `evidence_producer` app role.
4. Deploy Core and Gateway from the same approved image/source release identity, with the
   exact Gateway client ID in Core's server-owned ETS scope map.
5. Prove the Gateway app-only Core token carries `evidence_producer` and that a principal
   without `evidence.create` is denied ingestion.
6. Provision the Gateway managed identity with EchoMedia `Sites.Selected` access to the
   designated SharePoint site.
7. Authorize protected Graph callback ingress, supply the exact lifecycle/posture configuration,
   and let the runtime create and validate the real subscription.
8. Complete #539 and #540 source-to-proof qualification, including renewal and
   notification/delta recovery.
9. Freeze source SHA, image digest, connector instance, ETS scope, Microsoft tenant and
   subscription, and health-policy profile.
10. Run probe 1 of the governed 72-hour soak. The clock begins only at that successful
    first retained probe.
