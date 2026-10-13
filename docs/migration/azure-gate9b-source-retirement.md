# Azure migration Gate 9B — explicitly planned source-resource retirement

Tracking: #809, #792, #766, #758.

Gate 9B is the first migration phase allowed to delete source Azure resources. It is
separate from Gate 9 readiness and from whole-subscription cancellation.

A successful Gate 9 readiness artifact proves that source retirement is safe enough to
be **authorized for separate execution**. It does not itself remove any resource.

## Non-negotiable boundaries

Gate 9B requires the exact runtime phrase:

`GATE9_SOURCE_RETIREMENT_EXECUTE_AUTHORIZED`

Merging the implementation, approving the PR, or saying `continue` does not satisfy this
runtime authorization.

Gate 9B does not:

- cancel the source Azure subscription;
- delete the source resource group wholesale;
- modify production DNS;
- remove `Microsoft.Authorization/*` resources through the generic retirement plan;
- delete Azure DNS zones;
- remove the intentional EchoMedia/M365 cross-tenant trust used by the destination;
- automatically reactivate a stale source writer under any failure condition.

## Phase A — read-only retirement inventory

Run `Azure Migration Gate 9B Source Retirement Inventory` only after Gate 9 readiness
has completed successfully.

The inventory workflow uses the existing read-only source-transfer identity and records
the exact source-resource set, resource IDs, types, locations, resource-group locks,
source-manifest binding, and inventory digest. No mutation is performed.

The retained artifact is:

`azure-migration-gate9b-source-retirement-inventory`

If the source inventory changes after review, destructive execution fails closed.

## Phase B — protected retirement plan

Create the production plan in operator-controlled protected storage outside Git. Start
from `docs/migration/gate9b-retirement-plan-template.json`; do not turn the checked-in
template itself into a production attestation.

Every resource from the reviewed inventory must appear exactly once with one action:

- `retain`; or
- `delete`.

Every entry requires a reason. Delete entries also require a unique positive integer
`order`. The order is the reviewed dependency order and is executed exactly.

The plan must contain:

- exact source subscription ID;
- exact source resource group `rg-ets-live-eastus`;
- exact Gate 9 source-manifest SHA-256;
- `subscription_cancellation_requested=false`;
- exact resource ID/name/type triples from the reviewed inventory.

The plan SHA-256 is supplied independently to the execution workflow.

### Preserve intentional M365 trust

The destination Gateway intentionally uses cross-tenant identity and Graph/SharePoint
objects in the EchoMedia Microsoft 365 tenant. Those objects are not source-Azure
migration debris. Preserve the destination multitenant application/FIC chain,
EchoMedia enterprise application, Graph `Sites.Selected`, and the exact `/sites/ETS`
permission unless a separately reviewed M365 redesign supersedes them.

## Phase C — destructive execution

`Azure Migration Gate 9B Source Retirement Execute` uses a distinct, temporary,
narrowly scoped source-retirement workload identity exposed as
`SOURCE_RETIREMENT_AZURE_CLIENT_ID` in the protected source-retirement environment.

Do not give this identity subscription Owner. Its scope should cover only the exact
source resource group/resources that the reviewed plan may retire, with the minimum
roles required for those deletes.

Immediately before the first delete, the controller:

1. validates Gate 9 readiness;
2. validates the reviewed inventory and source-manifest binding;
3. validates the protected plan SHA-256;
4. refuses any resource-group deletion lock;
5. re-captures the source inventory;
6. requires the fresh inventory digest to equal the reviewed digest.

Only then are `delete` entries processed in explicit order. Each resource must disappear
before the next delete begins. After the plan completes, the live source inventory must
equal the plan's exact `retain` set.

The workflow never calls subscription cancellation.

## Phase D — mandatory post-retirement destination smoke

A source-retirement execution is not complete merely because Azure accepted delete
commands. The same workflow must then prove the destination remains operational by:

- re-running the active destination Gateway → EchoMedia `/sites/ETS` workload-identity
  read;
- performing a fresh normal ETS event append and independent inclusion-proof check;
- verifying HTTPS/TLS and non-empty successful responses for `lanternprotocol.net`,
  `www.lanternprotocol.net`, and `azure.lanternprotocol.net`.

The final retained artifact is:

`azure-migration-gate9b-source-retirement-final`

It may prove resource retirement complete while still recording
`subscription_cancellation_performed=false`.

## Failure semantics

After Gate 7C, destination writer authority is permanent unless a new reconciliation
procedure proves a different state transition. A Gate 9B failure must never trigger an
automatic source-writer restart.

If a deletion fails, an unexpected resource exists, an inventory digest changes, a lock
appears, or destination smoke fails:

1. stop further destructive actions;
2. preserve all available source/destination evidence;
3. keep destination authoritative;
4. investigate and reconcile explicitly;
5. do not cancel the subscription;
6. do not reactivate stale source writers.

## Separate subscription-cancellation boundary

Subscription cancellation is intentionally outside Gate 9B. Consider it only after a
fresh subscription-wide inventory proves no unrelated or deliberately retained resource
remains, all required evidence exists outside the retiring subscription, billing/export
needs are satisfied, and a separate explicit cancellation authorization is reviewed.
