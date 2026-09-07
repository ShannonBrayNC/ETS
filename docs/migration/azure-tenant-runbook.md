# Controlled Azure migration — resumable record

## Checkpoint: 2026-09-06, ACCESS_BLOCKED

Scope: Lantern website, EchoMedia website, critical ETS. Parallel deployment is
the provisional method. Nothing has been deployed, backed up, cut over, stopped,
or deleted by this migration session. Source cost reduction is **not established**.

Inspected ETS main `f3b973aa63a3893437a2422a670278cf053b137e`, repository controls,
deployment workflows, infrastructure, Azure Table implementation, open Azure PRs,
and migration branch/PR searches. No existing Azure migration branch was found.
GitHub reports this repository as public despite the stale private classification
in `.repo-control/repo-profile.yml`. Keep protected operational records outside Git.

| Fact | Verification status |
| --- | --- |
| Source tenant/subscription | Live identity confirmation blocked; prior billing audit is only a discovery lead |
| Destination tenant/subscription | Unknown; intended account supplied by operator, not an Azure identifier |
| Destination billing account/profile/scope and offer | Unknown |
| Credit balance/expiry/spending limit | Operator reported $200 expiring 2026-12-02; current entitlement unverified |
| Azure status, roles, region availability, quotas | Not inventoried live |
| Microsoft billing-adjustment conditions | Unconfirmed; no written conditions retrieved |
| Source/destination costs and overlap | Unknown; no price or utilization basis yet |
| DNS provider, zone export, TTLs, live routing | Unverified; no DNS changes |
| Backups, restore, evidence verification | Not performed |

## Repository-derived mapping (not live inventory)

| Workload | Repository evidence | Dependencies and method | Validation and rollback | Cost |
| --- | --- | --- | --- | --- |
| Lantern apex/www, critical public site | `ops/lantern-site-backup/site`; `lantern-site-backup-deploy.yml`; Front Door workflows | Existing continuity Storage site in `rg-ets-live-eastus`; Front Door/DNS/TLS route must be discovered. Publish to isolated destination, keep source available. | Assets, dynamic `app.js`, forms, apex/www redirects, HTTPS; retain source version and original routes. | Unknown; price static hosting and routing separately |
| EchoMedia apex/www, critical public site | Separate website repository inspected; protected details retained there | Hosting-to-live-DNS mapping not established. Validate current host before classifying any Azure resource as redundant. | SPA deep links, assets, forms, HTTPS and apex/www; restore original route and build. | Unknown |
| ETS Core/Gateway, critical evidence service | `live-core-gateway-deployment.yml`, `infra/azure/ets-hosted.bicep`, `ets-gateway.bicep` | Existing workflow targets `rg-ets-live-eastus`, ACR `etsq1a352eb89` in `rg-ets-q1-eastus`, `ets-azure-q1` environment; all require live readback. Parallel infrastructure, immutable image, new identities, frozen state copy. | Auth positive/negative tests, ingestion, stored bytes, historical/new signatures, connectors and post-cutover write rollback. | Unknown; do not deploy full template until priced |

The existing Lantern README describes resource creation, but the current publish
workflow instead requires existing storage and deletes all `$web` blobs before
upload. Do not reuse it for a continuity-preserving migration. PR #589 addresses
dynamic website verification only; do not duplicate or merge it as migration work.

## Observed automation evidence

[Cleanup run 34002629018](https://github.com/ShannonBrayNC/ETS/actions/runs/34002629018),
2026-09-06 00:57 UTC: Azure OIDC login succeeded; `eligible_count=0`; protected-group
verification failed with `Forbidden`. This proves neither resource absence nor
adequate inventory permissions. No synthetic groups were selected in that run.

The source cleanup schedule is hourly and is not a provisioning job. The hourly
Microsoft soak controller also exists and can dispatch subordinate observations.
Do not disable an active evidence qualification or cleanup job without checking
its current state/dependencies. No workflows were disabled in this session.
Core/Gateway deployment is manual and release-gated. Do not rerun deployment jobs
to obtain discovery information or replace the source environment's credentials
with destination credentials.

## Resume: access and entitlement

1. Provide an authenticated Azure execution session accessible to the engineer.
   Sign in through the official Azure flow for the intended destination account
   and the authorized source principal; never share passwords, tokens or secrets.
   This Work session has GitHub access, no Azure CLI/session, and no discovered
   Azure integration. A local login elsewhere does not authenticate this session.
2. Initial discovery requires subscription Reader on both subscriptions and Cost
   Management Reader where supported. Billing-scope/credit visibility is separate:
   grant the appropriate offer-specific billing reader access or use the billing
   account owner's authenticated view. Record subscription linkage, remaining
   balance, currency, expiration, spending limit and overage rules in protected storage.
3. Use `az account list --all` in that authenticated environment to discover exact
   IDs. Verify the account-to-subscription relationship in the portal; email alone
   is insufficient. Run the collector separately for each explicitly verified pair:

   ```bash
   python scripts/azure_migration_discover.py \
     --tenant "$MIGRATION_TENANT_ID" \
     --subscription "$MIGRATION_SUBSCRIPTION_ID" \
     --output "$MIGRATION_PROTECTED_CAPTURE_DIR"
   ```

   Output must be a new protected directory outside Git. On Windows, configure
   an operator-only ACL on the parent; POSIX permissions alone do not set Windows
   ACLs. The collector reads metadata, never tokens, keys or application settings.
   Its hashes establish capture-file integrity only, not evidence completeness,
   Azure authenticity, backup success, billing entitlement or migration readiness.
   A blocked read exits nonzero and cannot be treated as an empty inventory.
4. Complete service-specific dependency inventory: exact resources/SKUs, runtimes,
   images, workers/jobs/leases, databases and table schema, blob versions/retention,
   queues, key versions and encryption dependencies, certificates, identities and
   grants, app registrations, OIDC subjects, callbacks, network/private DNS,
   monitoring, backup/restore and every DNS record including mail records.
   Inventory app settings only into protected storage; never expose secrets in CI.
5. For deployment, use destination resource-group Contributor and scoped RBAC
   administration only as needed, data-plane roles for the exact source/destination
   stores, and separately authorized Entra application administration. Source Reader
   alone cannot back up data or stop resources. Discover exact scopes before grants.

## Cost gate

Export posted source costs by resource ID, meter and day (last seven complete days
plus month-to-date); record ingestion lag and currency. Rank actual drivers before
stopping resources. Price destination SKUs for verified region, traffic, storage,
logs, requests, backups, networking and required security. Include source retention,
overlap and data egress. No fixed forecast is defensible before this inventory.

Planning arithmetic only: $200 over 87 days is about $2.30/day or $69 per 30 days,
assuming the full reported balance and expiration are confirmed. This is a budget
ceiling illustration, not a forecast or a claim that the workload fits. Runway is
remaining eligible credit divided by eligible daily spend, capped by credit expiry;
ineligible charges are separate. Never remove a spending limit or downgrade ETS
security to fit the credit without an explicit cost decision. Budget alerts are
not a substitute for verifying the subscription's spending behavior.

If minimal secure hosting exceeds credit, present itemized minimum viable choices
and continue offline preparation. Do not transfer a subscription's directory as a
billing migration. Azure resource moves across subscriptions require the same Entra
tenant; verify service-specific support before selecting any move operation.

## Data preservation and cutover gates

- Record a migration ID, actors, source/destination scopes, UTC times, tool versions,
  commit/image digests and hashes of protected manifests in the audit record.
- Back up and restore to isolated storage before modifying state. For Azure Table,
  preserve typed entities, partition/row keys, exact event JSON, event/leaf hashes,
  metadata, next index and event-ID indexes. Do not rebuild evidence by reinserting
  events through ingestion. Service-assigned ETags/timestamps can change on copy:
  retain originals in the backup manifest and do not rewrite historical event times.
- Inventory artifact bytes separately from Azure Table event records. Capture blob
  versions, metadata, legal holds/retention and encryption requirements. A successful
  transfer of current blobs alone does not preserve all historical versions.
- Keep original log IDs, identities and provenance. Retain historical public keys
  and exact versions; test old signatures using independently retained verification
  material. Nonexportable signing keys need a validated supported continuity or
  rotation strategy; preserve old key access where verification/decryption depends
  on it. Do not purge keys or invent rewritten historical identity references.
- Keep destination schedulers and consumers disabled. Establish exclusive writer
  ownership and a write freeze covering all API ingress, workers, webhooks and retry
  paths. Drain or capture queues, cursors, leases and dead letters. Take final sync,
  counts, hash comparisons and high-water marks before enabling one destination writer.
- Validate destination health, readiness, negative auth/authorization, end-to-end
  ingestion/storage/verification, old and new evidence, image deployment from intended
  repository, connectors, CORS/callbacks, monitoring and restore access.
- Export original DNS records/TTLs; prevalidate certificates and custom domains.
  Preserve MX/SPF/DKIM/DMARC/autodiscover and unrelated records. Keep registration,
  Entra domains and Microsoft 365 unchanged. Domain detachment needs separate approval.
- Cut over validated independent websites individually. Cut ETS consumers after its
  storage, signing, identity and APIs are ready. Record exact routing diffs and UTC
  timestamps. Do not claim readiness from HTTP 200 or a successful workflow alone.

## Rollback and source savings

Before destination writes: disable destination workers, restore captured routes,
and resume the source only after proving destination writer shutdown.

After destination writes: freeze destination and fence both writers; preserve a
complete post-cutover delta including evidence, custody, indexes, queues and side
effects. Validate a replay/import into the isolated source restoration using exact
evidence bytes and duplicate detection, preserving destination signing references.
Only switch back after reconciliation and validation. If that is unsupported, keep
writes paused and request a downtime/recovery decision; DNS reversal alone is unsafe.

Choose the observation period from actual DNS TTLs, queue drain and the longest
critical job cadence, plus traffic/auth/error/verification results. Then disable
source provisioning and redundant writers, stop/deallocate/scale down only confirmed
redundant resources with recoverable state. Retain rollback data, historical keys,
evidence and required backups. Check source traffic/write counters independently.

Itemize still-billable plans, Front Door/gateways, registries, DBs, disks, public IPs,
storage, snapshots and logs. Obtain separate approval for exact irreversible deletion
IDs, dependency analysis, retained backup references, retention obligations and
estimated savings. Never delete tenant/subscription, purge keys/evidence, transfer
registration or migrate mailboxes under this migration authorization.

## Billing-review factual record

2026-09-06: repository discovery and migration preparation completed. Live source
inventory and destination entitlement could not be verified from this execution
environment. No workload migration or source shutdown has occurred. No refund,
startup verification, credit approval or cost elimination is claimed. Append actual
resource actions/timestamps and posted billing evidence after execution; keep the
support case and Microsoft's exact written conditions in protected storage.

## Reference constraints checked 2026-09-06

Local validation: `python -m unittest discover -s tests -p
test_azure_migration_discover.py -v` passed four safety tests; CLI help and
`git diff --check` passed. Pytest is unavailable in this execution environment;
the full repository suite and Azure integration execution were not run.

- [Azure move prerequisites](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/move-resource-group-and-subscription)
- [Service move support](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/move-support-resources)
- [Azure spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit)

## Resume checkpoint: awaiting destination sign-in

The continuation installed Azure CLI 2.90.0 in an isolated execution environment.
Microsoft sign-in and ARM endpoints are reachable. An official device login has
been initiated for the operator to select the intended destination account. Login
is not yet confirmed; no destination identifiers or entitlement have been verified.
Authentication codes and token caches are deliberately excluded from this record.
The earlier generic execution-access blocker is now a destination sign-in gate.

PR #611 initially failed Ruff E501 on the collector's output argument line. Commit
`c7c97e3e5e8af0606757264d9d80ccc5b55fdf2a` fixes that line; four local safety tests
still pass. Replacement CI is pending. No Azure resource, DNS, data, or billing
mutation has occurred. Continue by checking destination login completion, then
list accessible subscriptions without exposing tokens and verify billing linkage.

## Authentication checkpoint: 2026-09-06 05:54 UTC

Destination Microsoft-account authentication succeeded using the persisted device
handoff. Azure tenant discovery returned a Default Directory, but token acquisition
for that directory failed with AADSTS530035 (BlockedBySecurityDefaults). The empty
subscription result is therefore incomplete discovery, not proof of no subscription.
Exact directory identifiers and authentication state are kept in protected execution
storage. The common Microsoft-account token's tenant is not the deployment tenant.

Azure CLI recommends directory-specific interactive login for the failed tenant.
A saved, directory-specific login handoff has been initiated to allow the operator
to complete any tenant MFA/security requirements. No policy, security default, role,
resource, DNS record or evidence was changed. If the tenant rejects this interactive
flow, stop and use an administrator-approved authentication path; do not weaken policy.
Billing scope, subscription ID, entitlement and source cost reduction remain unverified.

## Confirmed device-flow block: 2026-09-06 05:58 UTC

Operator supplied a directory-specific Azure CLI denial with error 530035. Stop
all device-code retries. Microsoft Security Defaults documentation now explicitly
states that new tenants block device code flow starting 2026-07-01. This supersedes
the prior suggestion that tenant targeting alone might resolve the authentication
gate. Successful Microsoft-account authentication does not grant ARM access.

Next supported path: operator browser sign-in to Azure portal with the intended
account, complete required MFA, verify the directory and Subscriptions/credit billing
views. For execution, use browser/WAM Azure CLI authentication in an accessible
operator environment or an administrator-approved workload identity with scoped
roles. Do not disable Security Defaults, exempt the account, transfer session tokens,
or interpret this error as proof that a subscription does not exist. This Work
session has no authenticated browser-control capability or approved Azure workload
identity. No destination entitlement, deployment, cutover or source savings claimed.

Reference: https://learn.microsoft.com/en-us/entra/fundamentals/security-defaults#block-device-code-flow

## Portal observation: destination subscription identified

Operator supplied the subscription Overview screenshot on 2026-09-06. It shows
Azure subscription 1, Active, Owner, Azure Plan, and Default Directory. The displayed
directory is consistent with prior authenticated tenant discovery. Exact identifiers
are recorded in the protected destination-portal-observation.json checkpoint; this is
portal evidence, not successful ARM discovery from the Work execution environment.
The screenshot does not establish the credit-bearing billing scope, current balance,
expiry, or spending-limit state. Azure Plan must not be treated as proof of credits.

Next: verify subscription-to-billing-profile linkage and that profile's Azure credits
view, and use the operator's authenticated Cloud Shell (without storage if offered)
for read-only resource discovery. No additional device-code authentication attempts.
No resources deployed/stopped or traffic changed; source spending remains unverified.

## Billing account credit observation: 2026-09-06

Operator supplied a billing account Summary screenshot displaying $200.00 credits
remaining, $0.00 used of $200, $0.00 due and no charges reported this month. This
confirms the displayed account-level balance, not the credit expiration, spending
limit, eligibility rules, or linkage to the identified destination subscription.
Account details are recorded in the protected portal observation checkpoint. The
portal URL is truncated, so the full billing scope ID must not be reconstructed.
Next evidence: View credits for validity/terms and View billing subscriptions for
the exact destination subscription linkage. No deployment or source savings yet.

## Execution checkpoint: destination foundation and state inventory

Status at 2026-09-07T03:14:29Z: `AUTHORIZATION_BLOCKED`. The operator's
protected checkpoint supersedes the earlier discovery-only status. Exact tenant,
subscription, billing-scope, role-assignment, and key-version identifiers remain
in protected migration records outside this public repository.

Confirmed destination state:

- The ETS Protocol Azure tenant/subscription and its Microsoft Customer Agreement
  billing linkage were verified by the operator. The billing profile displayed
  $200 Azure credit and spending limit Off; this is not permission to create
  unnecessary resources.
- Resource groups for ETS production, ETS shared services, and Lantern web
  continuity exist in East US. Required providers for Container Apps,
  App Configuration, ACR, Key Vault, Storage, Managed Identity, Network,
  Operational Insights, and Insights are registered.
- Destination ACR exists at `etsprod7c8ab70380.azurecr.io`, Basic SKU, with
  its admin account disabled.
- The qualified ETS image was imported without rebuilding and independently
  verified at the identical immutable digest
  `sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63`.
  Qualified source commit:
  `9a4c3a8aefc50a960bdd3ce34b28f86fd69f1535`.

Confirmed source state:

- The source tenant/subscription and critical resource groups were verified.
  Core/Gateway and Lantern continuity resources remain in
  `rg-ets-live-eastus`; the fleet/PostgreSQL group remains outside the current
  migration gate and must not be modified until Core/Gateway is safely proven.
- Core Azure Table `ETSEvents` contains 73 entities in one log partition:
  36 `entry`, 36 `event_index`, and one `metadata` entity. This is
  internally consistent with `AzureTableEventStore`. Evidence migration must
  preserve the exact typed entity representation and must not replay events
  through the API.
- The source tree-head key has exactly one observed historical version. Preserve
  its exact historical key ID and public verification material in protected
  records; a destination key starts a new continuity boundary and cannot replace
  the historical identity. Retain the source vault until independent old-evidence
  verification succeeds.
- Gateway storage has shares `ets-gateway-state-q1-v2` and
  `ets-gateway-state`. The active share is `ets-gateway-state-q1-v2`;
  observed use is 262144 bytes. The live Gateway mounts it at
  `/var/lib/ets` for single-replica SQLite compatibility.

Exact resume gate:

1. Verify the signed-in source operator has `Storage File Data Privileged Reader`
   at the `etsgwo23bf2d6oq44s` storage-account scope. Do not combine
   `az role assignment list --all` with `--scope`.
2. Using OAuth and `--backup-intent`, recursively inventory both Gateway shares
   and then create protected point-in-time source snapshots.
3. Verify and remove the temporary source ACR token
   `ets-migration-read-20260906` if it still exists; it was scoped only to the
   completed cross-tenant image import.
4. Export `ETSEvents` into protected storage with exact fields and Azure data
   types, plus independently hashed manifests. Do not commit protected data.

This Work continuation began from PR head
`495e06cef50e4f85ca8b72a31c03248f69a089bd`. Its transient container no
longer held the earlier Azure CLI installation or authentication cache. A fresh
destination portal authentication reached the ETS Protocol account's additional
email-verification boundary. The browser required submission of the complete
recovery email address before sending a code; that sensitive-data transmission
was not approved, so execution stopped before submission. No role assignment,
resource, secret, DNS, traffic, evidence, storage, key, or billing setting was
changed. The Gateway authorization check, share inventory/snapshots, source ACR
token cleanup, and table backup remain unexecuted in this continuation.

## Live destination verification: 2026-09-07

At 2026-09-07T03:39:53Z, interactive Azure portal authentication completed for
the confirmed ETS Protocol account with multifactor authentication. Azure Cloud
Shell was started in ephemeral mode; no persistent Cloud Shell storage was
created by this session.

Live ARM/portal verification established:

- `Azure subscription 1` is Enabled/Active in the confirmed destination tenant.
  The signed-in migration operator is Owner. The account's accessible-subscription
  list contains only this destination subscription.
- The Startups billing surface displays `$200 in credits - Exp Dec 2, 2026`.
  Treat this as a live display observation, not permission to create unnecessary
  resources or proof that every meter is credit eligible.
- Four destination resource groups exist and report Succeeded:
  `rg-ets-prod-eastus`, `rg-ets-shared-eastus`,
  `rg-lantern-web-eastus` in East US, plus pre-existing
  `rg-ets.protocol-3456` in West US 3.
- The pre-existing non-migration group contains one Foundry account, one Foundry
  project, and one Search service. They were not created, modified, classified
  as redundant, or deleted by this migration session.
- All required migration providers report Registered:
  `Microsoft.App`, `Microsoft.AppConfiguration`,
  `Microsoft.ContainerRegistry`, `Microsoft.KeyVault`,
  `Microsoft.Storage`, `Microsoft.ManagedIdentity`,
  `Microsoft.Network`, `Microsoft.OperationalInsights`, and
  `Microsoft.Insights`.
- ACR `etsprod7c8ab70380.azurecr.io` reports provisioning Succeeded, Basic SKU,
  and admin user disabled.
- Repository `ets/hosted-q1` contains the qualified immutable manifest
  `sha256:e37f78a32dd995bcd73b1dfb4f3ae590bcc0694d8170f0a0a748d937be35fd63`.
  It is untagged, consistent with digest-only deployment. Two additional untagged
  manifests are present and were not modified. No image was rebuilt, retagged,
  imported, or deleted.

The destination account has no access to the source subscription, so it cannot
perform the Gateway file-role check. Azure's account-selector flow is open for a
separate source-operator sign-in. Resume there, authenticate the authorized source
work account, verify the exact subscription/tenant before any write, and then
continue with `Storage File Data Privileged Reader` verification at the Gateway
storage-account scope. No Azure mutation occurred in this checkpoint.

## Source authorization checkpoint: 2026-09-07

At 2026-09-07T03:56:24Z, separate MFA-backed authentication completed for the
authorized Echo Media source operator. Cloud Shell confirmed the expected source
subscription and tenant as Enabled/default before any scoped operation.

The exact Gateway storage authorization gate was then evaluated without combining
`az role assignment list --all` with `--scope`:

- No direct `Storage File Data Privileged Reader` assignment was returned for
  the signed-in operator at the `etsgwo23bf2d6oq44s` storage-account scope.
- Repeating the check with `--include-inherited` returned no matching assignment.
- A scope-wide inherited query returned no matching role for any visible principal.
- OAuth listing of `ets-gateway-state-q1-v2` with `--backup-intent` reproduced
  the insufficient-permissions failure. Azure CLI suggested account-key fallback;
  it was deliberately not used.

The next bounded write is to grant `Storage File Data Privileged Reader` to the
signed-in source operator at only the Gateway storage-account scope. Browser safety
requires action-time approval for this permission change; approval was not returned,
so no role assignment was created. Both share inventories and snapshots remain
blocked. No account key, SAS, secret, file content, evidence, or mutable Azure
resource was exposed or changed.

## Gateway snapshots and protected evidence backup: 2026-09-07

The source operator approved and received the least-privilege
`Storage File Data Privileged Reader` role at only the Gateway storage-account
scope. Azure reports the assignment created at
`2026-09-07T04:10:54.159846Z`. No account key or SAS was used.

OAuth plus backup intent produced the following recursive inventory:

- Active share `ets-gateway-state-q1-v2`: root only, no directories, five files,
  299008 logical bytes at inventory time: `connector-runtime.db` (53248),
  `gateway-events.db` (143360), `gateway-sync.db` (69632),
  `gateway-sync.db-shm` (32768), and `gateway-sync.db-wal` (0).
  This supersedes the earlier 256 KiB observation because the live writer
  continued to update state.
- Legacy share `ets-gateway-state`: root only, no directories, one zero-byte
  `connector-runtime.db`.

Control-plane share snapshots were created without storage keys and read back
through OAuth plus backup intent:

- active share snapshot: `2026-09-07T04:12:12.0000000Z`;
- legacy share snapshot: `2026-09-07T04:12:22.0000000Z`.

Both snapshot listings match their source file sets and lengths. These are
storage point-in-time/crash-consistent captures while the Gateway remained live;
application-consistent SQLite restoration still requires an exclusive-writer
freeze/final sync before cutover.

The temporary source ACR token `ets-migration-read-20260906` was queried on
`etsq1a352eb89` and returned ResourceNotFound. No token deletion was necessary.

A protected Azure Tables REST capture of `ETSEvents` completed at
`2026-09-07T04:16:40Z` using
`Accept: application/json;odata=fullmetadata`. The 168122-byte payload contains
75 entities: 37 `entry`, 37 `event_index`, and one `metadata` row.
The metadata row reports `next_index=37`, `schema_version=1`, and log ID
`ets-live-primary`. Validation confirmed required fields and types, unique
partition/row keys, contiguous entry and event-index log indexes 0 through 36,
and agreement between metadata high-water mark and both row counts.

Payload SHA-256:
`fe93a5a27ddb4bd0e5c09f0b5f333de77bdbc44d37b58959d69194e45b2caa21`.
The protected archive is 19792 bytes with SHA-256
`8554fe8ab3ccb37464f09573260898879b782e1dba6415edf5df9ab202bcdc6c`.
It contains the full-metadata payload, manifest, and checksum file and is retained
outside this public repository. The source-to-protected-copy archive hash was
independently rechecked after download and matched exactly.

No production traffic, DNS, Core/Gateway deployment, writer ownership, source
resource availability, signing key, or fleet/PostgreSQL resource was changed.
Next safe gate: preserve independent historical public verification material for
the exact source key version, then adapt destination infrastructure and
cross-tenant identity handling before any no-traffic deployment.

